import difflib
from fuzzysearch import find_near_matches
from transformers import BertTokenizer, BertForTokenClassification
from transformers import pipeline
from collections import defaultdict
from docx import Document
import string
import re
import numpy as np

# Load pre-trained BERT tokenizer and model for NER (Estonian model)
tokenizer = BertTokenizer.from_pretrained('tartuNLP/EstBERT_NER')
bertner = BertForTokenClassification.from_pretrained('tartuNLP/EstBERT_NER')
nlp = pipeline("ner", model=bertner, tokenizer=tokenizer)

# Define regex patterns for phone numbers and email addresses
phone_number_pattern = re.compile(r'(?:\+?\(?\d{1,3}\)?[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}')
email_address_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
id_number_pattern = re.compile(r'^[1-6]{1}[0-9]{10}$')

class NerResult:
    """
    Class to store named entity recognition (NER) result attributes.
    """
    def __init__(self, entity, word, score, index, start, end):
        self.entity = entity
        self.word = word
        self.score = score
        self.index = index
        self.start = start
        self.end = end

# Initialize global NER result lists
ner_person = []
ner_organisation = []
ner_location = []

org_array = []

def process_document(text):
    """
    Main function to process the document text and extract NER results along with phone numbers and email addresses.
    """
    ner_array = []
    phone_numbers = extract_entity_with_slots(phone_number_pattern, text)
    email_addresses = extract_entity_with_slots(email_address_pattern, text)
    id_numbers = extract_id_numbers_from_phone_numbers(phone_numbers)

    start_index = 0
    last_word_capitalized = False

    while start_index < len(text):
        end_index = find_split_index(text[start_index:])
        chunk = text[start_index:start_index + end_index].strip()

        if last_word_capitalized:
            last_space_index = chunk.rfind(' ')
            chunk = chunk[:last_space_index].strip()

        ner_results = nlp(chunk)
        ner_array.extend(ner_results)
        last_word_capitalized = chunk.split()[-1][0].isupper()
        start_index += end_index

    ner_person, ner_organisation, ner_location = categorize(ner_array)

    result = {
        "text": text,
        "person": [],
        "organisation": [],
        "location": [],
        "phone_numbers": phone_numbers,
        "email_addresses": email_addresses,
        "id_numbers": id_numbers,
        "count": 0
    }
    print(result['person'])
    # Find matches for persons, organizations, and locations in the text
    print(result['person'])
    result['person'], per_no_match = find_all_matches(ner_person, text)
    result['organisation'], org_no_match = find_all_matches(ner_organisation, text)
    result['location'], loc_no_match = find_all_matches(ner_location, text)

    # Attempt to match unmatched organizations and resolve overlaps
    per_no_match = find_all_matches(match_no_match_strings(text, per_no_match), text)[0]
    org_no_match = find_all_matches(match_no_match_strings(text, org_no_match), text)[0]
    loc_no_match = find_all_matches(match_no_match_strings(text, loc_no_match), text)[0]

    result['person'] = remove_overlapping_slots(result['person'], per_no_match)
    result['organisation'] = remove_overlapping_slots(result['organisation'], org_no_match)
    result['location'] = remove_overlapping_slots(result['location'], loc_no_match)

    for match in per_no_match:
        result['person'].append(match)
    result['person'] = merge_first_last_name(result['person'])
    
    for match in org_no_match:
        result['organisation'].append(match)
    
    for match in loc_no_match:
        result['location'].append(match)

    result['phone_numbers'] = merge_duplicates(result['phone_numbers'])
    result['email_addresses'] = merge_duplicates(result['email_addresses'])
    result['person'] = set_longest_match_from_slots(
        remove_smaller_slots(result['person']),
        text
    )

    keys = ['person', 'organisation', 'location', 'phone_numbers', 'email_addresses', 'id_numbers']
    result['count'] = sum(len(result[key]) for key in keys)
    return convert_floats(result)

def extract_entity_with_slots(pattern, text):
    """
    Extract entities like phone numbers or email addresses with their corresponding text slots.
    """
    entities = []
    for match in re.finditer(pattern, text):
        print(match)
        entity_obj = {
            'match': match.group(),
            'slots': [(match.start(), match.end())]
        }
        entities.append(entity_obj)
    return entities

def merge_duplicates(entity_list):
    """
    Merge duplicate entities (phone numbers or email addresses) by combining their slots.
    """
    seen = {}
    for entity in entity_list:
        key = entity['match']
        if key in seen:
            seen[key]['slots'].extend(entity['slots'])
            seen[key]['slots'] = list(set(seen[key]['slots']))  # Remove duplicate slots
        else:
            seen[key] = entity
    return list(seen.values())


def categorize(results):
    """
    Categorize NER results into person, organization, and location lists.
    """
    ner_person, ner_organisation, ner_location = [], [], []

    for result in results:
        if result['entity'] in ['B-PER', 'I-PER']:
            print(result)
            ner_person.append({'entity': result['entity'], 'word': result['word']})
        elif result['entity'] in ['B-ORG', 'I-ORG']:
            ner_organisation.append({'entity': result['entity'], 'word': result['word']})
        elif result['entity'] in ['B-LOC', 'I-LOC']:
            ner_location.append({'entity': result['entity'], 'word': result['word']})

    # Handle BERT subword tokens and group them properly
    ner_person = move_hashtag_words(ner_person)
    ner_organisation = move_hashtag_words(ner_organisation)
    ner_location = move_hashtag_words(ner_location)
    return ner_person, ner_organisation, ner_location

def move_hashtag_words(array):
    """
    Handle subword tokens (tokens starting with ##) and merge them into full words or phrases.
    """
    i = 0
    singleWord = []
    multibleWord = []
    simplifiedArray = []

    while i < len(array) - 1:
        next_word = array[i + 1]['word']
        next_entity = array[i + 1]['entity']

        # Check if the next word is part of the same entity
        if next_entity.startswith('I') or next_word.startswith('##'):
            if next_word == '.':  # Concatenate if next word is a period
                array[i]['word'] += next_word
                del array[i + 1]
            elif next_word.startswith('##'):  # Handle subwords (BERT output tokens)
                array[i]['word'] += next_word[2:]  # Remove ## prefix
                del array[i + 1]
            else:
                array[i]['word'] += ' ' + next_word  # Normal concatenation
                del array[i + 1]
        else:
            i += 1

    # Create lists for single words and multiple words (phrases)
    for element in array:
        simplifiedArray.append(element['word'])
    simplifiedArray = list(dict.fromkeys(simplifiedArray))  # Remove duplicates

    for word in simplifiedArray:
        if ' ' in word:
            multibleWord.append(word)
        else:
            singleWord.append(word)

    return {
        "singleWord": singleWord,
        "multibleWord": multibleWord
    }

def find_split_index(chunk):
    """
    Find a suitable index to split a chunk of text, prioritizing spaces and punctuation.
    """
    for i in range(min(len(chunk), 428) - 1, -1, -1):
        if chunk[i] in string.whitespace or chunk[i] in string.punctuation:
            return i + 1
    return 428

def convert_floats(data):
    """
    Convert numpy float32 values to Python floats in a nested dictionary or list.
    """
    if isinstance(data, dict):
        return {k: convert_floats(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_floats(item) for item in data]
    elif isinstance(data, np.float32):
        return float(data)
    else:
        return data

def find_all_matches(entity_list, text):
    word_array = []
    no_match_array = []

    def is_start_of_sentence(index):
        """Check if the match is at the start of a sentence."""
        if index == 0:
            return True
        prev_char = text[index - 1]
        return prev_char in '.!?'

    def add_match(word_obj, match_span):
        """Add a match span to the word object if not already added."""
        if match_span not in seen_slots:
            word_obj['slots'].append(match_span)
            seen_slots.add(match_span)

    seen_slots = set()  # Track already added slots to avoid duplicates

    if isinstance(entity_list, list):
        for word in entity_list:
            word_obj = {'match': word, 'slots': []}
            fuzzy_matches = find_near_matches(word, text, max_l_dist=1)
            if fuzzy_matches:
                for match in fuzzy_matches:
                    span = (match.start, match.end)
                    add_match(word_obj, span)
            else:
                no_match_array.append(word)
            if word_obj['slots']:
                word_array.append(word_obj)
    else:
        # Group similar words together
        match_array = group_similar_strings(entity_list['multibleWord'])
        
        # Handle single words with fuzzy matching
        for word in entity_list['singleWord']:
            word_obj = {'match': word, 'slots': []}
            if len(word) == 1:  # Skip single-letter entities
                continue

            pattern = re.escape(word) + r'\w*'
            matches = list(re.finditer(pattern, text))
            if not matches:
                no_match_array.append(word)
            else:
                for match in matches:
                    span = match.span()
                    if not is_start_of_sentence(span[0]):
                        add_match(word_obj, span)
                if word_obj['slots']:
                    word_array.append(word_obj)

        # Handle grouped multiple words with fuzzy matching
        for group in match_array:
            main_word = group[0]
            word_obj = {'match': main_word, 'slots': []}
            for word in group:
                fuzzy_matches = find_near_matches(word, text, max_l_dist=1)
                if fuzzy_matches:
                    for match in fuzzy_matches:
                        span = (match.start, match.end)
                        add_match(word_obj, span)
            if not word_obj['slots']:
                no_match_array.append(main_word)
            else:
                word_array.append(word_obj)
    
    # Additional step: Check if slots are sufficiently similar to the original word
    for word_obj in word_array[:]:
        new_word_objs = []
        for slot in word_obj['slots']:
            matched_text = text[slot[0]:slot[1]]
            similarity = difflib.SequenceMatcher(None, word_obj['match'], matched_text).ratio()
            if similarity < 0.7:
                new_word_obj = {'match': matched_text, 'slots': [slot]}
                new_word_objs.append(new_word_obj)
            else:
                continue
        if new_word_objs:
            word_array.extend(new_word_objs)
            word_obj['slots'] = [slot for slot in word_obj['slots'] if slot not in [obj['slots'][0] for obj in new_word_objs]]
    
    # Remove word objects with no slots after filtering
    word_array = [word_obj for word_obj in word_array if word_obj['slots']]

    return word_array, no_match_array

def group_similar_strings(strings, threshold=0.8):
    """
    Group similar strings based on a similarity threshold using SequenceMatcher.
    """
    groups = []
    used = [False] * len(strings)

    for i in range(len(strings)):
        if not used[i]:
            group = [strings[i]]
            used[i] = True
            for j in range(i + 1, len(strings)):
                if not used[j]:
                    similarity = difflib.SequenceMatcher(None, strings[i], strings[j]).ratio()
                    if similarity >= threshold:
                        group.append(strings[j])
                        used[j] = True
            groups.append(group)
    
    return groups

def match_no_match_strings(text, no_match_array):
    """
    Try to match unmatched strings with capitalized words in the text using similarity comparison.
    """
    capitalized_words = [word for word in text.split() if word[0].isupper()]

    def clean_word(word):
        return re.sub(r'[^\w\s]', '', word)  # Remove unwanted symbols

    def is_similar(word1, word2, threshold=0.5):
        return difflib.SequenceMatcher(None, word1, word2).ratio() >= threshold

    recovered_matches = []

    for string in no_match_array:
        words = string.split()

        for i, cap_word in enumerate(capitalized_words):
            if is_similar(words[0], cap_word):
                match_found = True
                for j in range(1, len(words)):
                    if i + j >= len(capitalized_words) or not is_similar(words[j], capitalized_words[i + j]):
                        match_found = False
                        break
                if match_found:
                    recovered_matches.append(" ".join(capitalized_words[i:i + len(words)]))
                    break

    return [clean_word(word) for word in recovered_matches]

def remove_overlapping_slots(ner_array, no_match_array):
    """
    Remove overlapping slots between NER matches and unmatched strings.
    """
    def is_overlapping(slot1, slot2):
        return not (slot1[1] <= slot2[0] or slot2[1] <= slot1[0])

    no_match_slots = [slot for match in no_match_array for slot in match['slots']]

    for match in ner_array:
        match['slots'] = [slot for slot in match['slots'] if not any(is_overlapping(slot, no_match_slot) for no_match_slot in no_match_slots)]

    ner_array = [match for match in ner_array if match['slots']]
    return ner_array

def merge_first_last_name(ner_array):
    """
    Merge entities where the first name and full name are considered the same.
    """
    first_name_dict = {}
    merged_array = []

    for match in ner_array:
        full_name = match['match']
        first_name = full_name.split()[0]  # Get the first word (usually the first name)

        # Check if the first name already exists in the dictionary
        if first_name in first_name_dict:
            # Add the slots of the current full name to the first name match
            first_name_dict[first_name]['slots'].extend(match['slots'])
            first_name_dict[first_name]['slots'] = list(set(first_name_dict[first_name]['slots']))  # Remove duplicates
        else:
            # If first name doesn't exist, store it in the dictionary
            first_name_dict[first_name] = match

    # Convert the dictionary back to the merged array
    merged_array = list(first_name_dict.values())
    return merged_array

def extract_id_numbers_from_phone_numbers(phone_numbers):
    """
    Extracts ID numbers from the given phone numbers if they match the ID number regex pattern.
    Skips numbers that start with '+', as they are international phone numbers.
    """
    id_numbers = []
    phone_numbers_to_keep = []

    for phone in phone_numbers:
        phone_number = phone['match']
        match = re.search(id_number_pattern, phone_number)

        if match:
            id_numbers.append(phone)  # Add the phone number and its slots to id_numbers
        else:
            phone_numbers_to_keep.append(phone)  # Keep the phone number if it's not an ID number

    # Modify the original phone_numbers array to only include non-ID phone numbers
    phone_numbers[:] = phone_numbers_to_keep

    return id_numbers

def remove_smaller_slots(person_array):
    """
    Remove slots with the smaller second element if the first element matches any other slot.
    """
    for person in person_array:
        slots = person['slots']
        unique_first_slots = defaultdict(list)

        # Group slots by their first element
        for slot in slots:
            unique_first_slots[slot[0]].append(slot)

        # For each group, keep the slot with the largest second element
        new_slots = []
        for first_element, slot_group in unique_first_slots.items():
            # Sort by second element and keep the one with the largest second element
            largest_slot = max(slot_group, key=lambda x: x[1])
            new_slots.append(largest_slot)

        # Update the person's slots with the filtered slots
        person['slots'] = new_slots

    return person_array

def set_longest_match_from_slots(person_array, text):
    """
    For each element in the person_array, find the longest substring based on the slots 
    and set it as the match.
    """
    for person in person_array:
        longest_match = ""
        for slot in person['slots']:
            # Extract substring from the text based on the slot
            substring = text[slot[0]:slot[1]]
            # Keep the longest substring
            if len(substring) > len(longest_match):
                longest_match = substring
        # Set the longest substring as the match
        person['match'] = longest_match
    
    return person_array

def process_chunk(chunk):
    """
    Process a chunk of text using the NER pipeline with truncation and a maximum length.
    """
    return nlp(chunk, truncation=True, max_length=512)
