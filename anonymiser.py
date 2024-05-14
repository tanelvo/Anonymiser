from transformers import BertTokenizer, BertForTokenClassification
from transformers import pipeline
from collections import defaultdict
from docx import Document
import string
import re
import numpy as np

tokenizer = BertTokenizer.from_pretrained('tartuNLP/EstBERT_NER')
bertner = BertForTokenClassification.from_pretrained('tartuNLP/EstBERT_NER')

phone_number_pattern = re.compile(r'\b(?:\+\d{1,2}\s?)?\(?\d{1,4}\)?[-.\s]?\d{1,9}[-.\s]?\d{1,9}\b')
email_address_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

nlp = pipeline("ner", model=bertner, tokenizer=tokenizer)

class NerResult:
    def __init__(self, entity, word, score, index, start, end):
        self.entity = entity
        self.word = word
        self.score = score
        self.index = index
        self.start = start
        self.end = end

# Read the content of the Word document
ner_person = []
ner_organisation = []
ner_location = []

def move_hashtag_words(array):
    i = 0
    simplifiedArray = []
    while i < len(array) - 1:  # Iterate up to the second-to-last element
        if array[i+1]['entity'].startswith('I') or array[i+1]['word'].startswith('#'):
            if array[i+1]['word'].startswith('##'):
                array[i]['word'] = array[i]['word'] + array[i+1]['word'].strip("#")
            else:
                array[i]['word'] = array[i]['word'] + ' ' + array[i+1]['word']
            del array[i+1]
        else:
            i += 1  # Move to the next element if no deletion is done

    for element in array:
        simplifiedArray.append(element['word'])
    simplifiedArray = list(dict.fromkeys(simplifiedArray))
    return array

def categorize(results):
    ner_person, ner_organisation, ner_location = [], [], []
    for result in results:
        if result['entity'] in ['B-PER', 'I-PER']:
            ner_person.append(result)
        elif result['entity'] in ['B-ORG', 'I-ORG']:
            ner_organisation.append(result)
        elif result['entity'] in ['B-LOC', 'I-LOC']:
            ner_location.append(result)

    ner_person = move_hashtag_words(ner_person)
    ner_organisation = move_hashtag_words(ner_organisation)
    ner_location = move_hashtag_words(ner_location)
    return ner_person, ner_organisation, ner_location
    

def find_split_index(chunk):
    # Find the index of the last space or punctuation within the first 512 characters
    for i in range(min(len(chunk), 512) - 1, -1, -1):
        if chunk[i] in string.whitespace or chunk[i] in string.punctuation:
            return i + 1
    return 512

def convert_floats(data):
    if isinstance(data, dict):
        return {k: convert_floats(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_floats(item) for item in data]
    elif isinstance(data, np.float32):
        return float(data)  # Convert numpy float32 to Python float
    else:
        return data
    
def process_document(text):
    ner_person, ner_organisation, ner_location = [], [], []
    phone_numbers = re.findall(phone_number_pattern, text)
    email_addresses = re.findall(email_address_pattern, text)

    start_index = 0
    last_word_capitalized = False
    while start_index < len(text):
        end_index = find_split_index(text[start_index:])
        chunk = text[start_index:start_index + end_index].strip()

        if last_word_capitalized:
            last_space_index = chunk.rfind(' ')
            chunk = chunk[:last_space_index].strip()

        ner_results = nlp(chunk)
        persons, organisations, locations = categorize(ner_results)
        ner_person.extend(persons)
        ner_organisation.extend(organisations)
        ner_location.extend(locations)

        last_word_capitalized = chunk.split()[-1][0].isupper()
        start_index += end_index

    result = {
        "person": [],
        "organisation": [],
        "location": [],
        "phone_numbers": phone_numbers,
        "email_addresses": email_addresses
    }

    def append_span_info(entity_list, text):
        print(entity_list)
        word_array = []
        for entity in entity_list:
            word = {
                'match': entity,
                'slots': []
            }
            pattern = r"\b{}\b".format(re.escape(entity['word']))  # Use re.escape to avoid regex errors
            print(pattern)
            matches = re.finditer(pattern, text)
            for match in matches:
                print(match.span())
                word['slots'].append(match.span())
            word_array.append(word)
        return word_array

    result['person'] = append_span_info(simplify(ner_person), text)
    result['organisation'] = append_span_info(simplify(ner_organisation), text)
    result['location'] = append_span_info(simplify(ner_location), text)

    return convert_floats(result)

def simplify(ner_array):
    # Use a dictionary to track words to avoid duplicates
    simplified_dict = {}
    for ner in ner_array:
        word = ner['word']
        if word not in simplified_dict:
            simplified_dict[word] = ner  # Store the whole dictionary
    return list(simplified_dict.values())  # Return a list of unique dictionaries

def process_chunk(chunk):
    # If using transformers' pipeline, specify truncation and max_length
    return nlp(chunk, truncation=True, max_length=512)