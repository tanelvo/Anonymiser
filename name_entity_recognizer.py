import difflib
from fuzzysearch import find_near_matches
from transformers import BertTokenizer, BertForTokenClassification
from transformers import pipeline
from collections import defaultdict
from morphology import to_nominative
import string
import re
import numpy as np
import requests

_KNOWN_PERSON_CACHE = {}
_WIKIDATA_HEADERS = {
    "User-Agent": "Anonymiser/1.0 (contact: you@example.com)"
}

# Load pre-trained BERT tokenizer and model for NER (Estonian model)
tokenizer = BertTokenizer.from_pretrained('tartuNLP/EstBERT_NER')
bertner = BertForTokenClassification.from_pretrained('tartuNLP/EstBERT_NER')
nlp = pipeline("ner", model=bertner, tokenizer=tokenizer)

# Define regex patterns for phone numbers and email addresses
# Phone: allow +country, spaces, and hyphens; avoid dot-separated decimals
phone_number_pattern = re.compile(
    r'\b(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{1,4}\)?[\s-]?){1,3}\d{2,4}\b'
)
email_address_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
id_number_pattern = re.compile(r'^[1-6]{1}[0-9]{10}$')
address_pattern = re.compile(
    r'\b(?:'
    r'(?:[A-ZÄÖÜÕ][a-zäöüõ]+(?:\s+[A-ZÄÖÜÕ][a-zäöüõ]+)*)\s+'
    r'(?:tn|tänav|tee|puiestee|pst|maantee|mnt|väljak|plats|allee|põik)\.?\s+\d{1,3}[A-Za-z]?'
    r'|(?:[A-ZÄÖÜÕ][a-zäöüõ]+(?:\s+[A-ZÄÖÜÕ][a-zäöüõ]+)*)\s+\d{1,3}[A-Za-z]?(?:,\s*[A-ZÄÖÜÕ][a-zäöüõ]+(?:\s+[A-ZÄÖÜÕ][a-zäöüõ]+)*)'
    r')\b'
)

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
    phone_numbers = filter_phone_numbers(phone_numbers, text)
    email_addresses = extract_entity_with_slots(email_address_pattern, text)
    id_numbers = extract_id_numbers_from_phone_numbers(phone_numbers, text)
    addresses = extract_entity_with_slots(address_pattern, text)

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
        "dates": [],
        "addresses": addresses,
        "count": 0
    }
    print("========================================")
    # Find matches for persons, organizations, and locations in the text
    print(result['person'])
    result['person'], per_no_match = find_all_matches(ner_person, text, entity_type="person")
    result['organisation'], org_no_match = find_all_matches(ner_organisation, text, entity_type="organisation")
    result['location'], loc_no_match = find_all_matches(ner_location, text, entity_type="location")

    # Attempt to match unmatched organizations and resolve overlaps
    per_no_match = find_all_matches(match_no_match_strings(text, per_no_match, entity_type="person"), text, entity_type="person")[0]
    org_no_match = find_all_matches(match_no_match_strings(text, org_no_match, entity_type="organisation"), text, entity_type="organisation")[0]
    loc_no_match = find_all_matches(match_no_match_strings(text, loc_no_match, entity_type="location"), text, entity_type="location")[0]

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
    result['dates'] = []
    result['addresses'] = merge_duplicates(result['addresses'])
    result['person'] = set_longest_match_from_slots(
        remove_smaller_slots(result['person']),
        text
    )
    result['person'] = merge_adjacent_person_names(result['person'], text)
    result['person'] = normalize_person_matches(result['person'])
    result['person'] = filter_known_persons(result['person'])

    keys = ['person', 'organisation', 'location', 'phone_numbers', 'email_addresses', 'id_numbers', 'addresses']
    result['count'] = sum(len(result[key]) for key in keys)
    print("========================================")
    print(f"[matches] person={result['person']}")
    print(f"[matches] organisation={result['organisation']}")
    print(f"[matches] location={result['location']}")
    print(f"[matches] phone_numbers={result['phone_numbers']}")
    print(f"[matches] email_addresses={result['email_addresses']}")
    print(f"[matches] id_numbers={result['id_numbers']}")
    print(f"[matches] addresses={result['addresses']}")
    return convert_floats(result)


def normalize_person_matches(person_array):
    """
    Normalize person match strings to nominative and merge slots for duplicates.
    """
    if not person_array:
        return person_array
    if to_nominative is None:
        return person_array

    merged = {}
    print("========================================")
    for match in person_array:
        raw = match.get("match", "")
        nom = to_nominative(raw) or raw
        print(f"[nominative] raw='{raw}' nom='{nom}'")
        if nom.lower() == raw.lower():
            nom = raw
        elif len(raw.split()) == 1:
            nom = nom[:1].upper() + nom[1:]
        if len(nom.split()) < len(raw.split()):
            nom = raw
        if nom in merged:
            merged[nom]["slots"].extend(match.get("slots", []))
        else:
            merged[nom] = {"match": nom, "slots": list(match.get("slots", []))}

    # de-dup slots
    for obj in merged.values():
        obj["slots"] = list(set(obj["slots"]))

    return list(merged.values())


def merge_adjacent_person_names(person_array, text):
    """
    Merge adjacent person names like "Mart" + "Sander" into "Mart Sander".
    """
    if not person_array:
        return person_array

    # Build a flat list of slot entries
    entries = []
    for person in person_array:
        for slot in person.get("slots", []):
            entries.append({"match": person.get("match", ""), "slot": slot})

    entries.sort(key=lambda e: e["slot"][0])
    merged = []
    i = 0
    while i < len(entries):
        curr = entries[i]
        start, end = curr["slot"]
        curr_text = text[start:end]
        merged_text = curr_text
        merged_start, merged_end = start, end
        j = i + 1
        while j < len(entries):
            next_start, next_end = entries[j]["slot"]
            if next_start == merged_end + 1 and text[merged_end:next_start] == " ":
                next_text = text[next_start:next_end]
                merged_text = merged_text + " " + next_text
                merged_end = next_end
                j += 1
            else:
                break
        merged.append({"match": merged_text, "slots": [(merged_start, merged_end)]})
        i = j

    return merged




def filter_known_persons(person_array):
    """
    Remove person matches that are confirmed as known people via Wikidata.
    Only checks names with at least two tokens (first + last).
    """
    if not person_array:
        return person_array

    known_slots = []
    known_single_tokens = set()
    filtered = []
    print("========================================")
    for match in person_array:
        name = (match.get("match") or "").strip()
        if not name or len(name.split()) < 2:
            continue
        if is_known_person(name):
            known_slots.extend(match.get("slots", []))
            for token in name.split():
                known_single_tokens.add(token.lower())
        else:
            filtered.append(match)

    if not known_slots:
        # keep original single-name entries if no known full names
        for match in person_array:
            name = (match.get("match") or "").strip()
            if name and len(name.split()) < 2:
                filtered.append(match)
        return filtered

    def overlaps(slot1, slot2):
        return not (slot1[1] <= slot2[0] or slot2[1] <= slot1[0])

    # Remove single-name matches that overlap known full-name slots
    for match in person_array:
        name = (match.get("match") or "").strip()
        if not name or len(name.split()) >= 2:
            continue
        slots = match.get("slots", [])
        name_key = name.lower()
        if to_nominative is not None:
            try:
                name_key = (to_nominative(name) or name).lower()
            except Exception:
                name_key = name.lower()
        if name_key in known_single_tokens:
            continue
        # If a known full-name token is a prefix and the remainder is a case suffix, drop it
        case_suffixes = {
            "i", "ile", "ilt", "ist", "iga", "iks",
            "lt", "st", "ga", "na", "ni", "ta", "l", "s"
        }
        for token in known_single_tokens:
            if name_key.startswith(token):
                rest = name_key[len(token):]
                if rest in case_suffixes:
                    continue
        if any(name_key.startswith(t) and name_key[len(t):] in case_suffixes for t in known_single_tokens):
            continue
        if any(overlaps(slot, known) for slot in slots for known in known_slots):
            continue
        filtered.append(match)

    return filtered


def is_known_person(name):
    """
    Return True if Wikidata confirms this name as a human (Q5).
    Uses a small in-memory cache and fails open (False) on errors.
    """
    print(f"[wikidata] check name='{name}'")
    key = name.lower().strip()
    if key in _KNOWN_PERSON_CACHE:
        return _KNOWN_PERSON_CACHE[key]

    try:
        search_params = {
            "action": "wbsearchentities",
            "search": name,
            "language": "et",
            "format": "json",
            "limit": 3,
            "type": "item",
        }
        search_resp = requests.get(
            "https://www.wikidata.org/w/api.php",
            params=search_params,
            headers=_WIKIDATA_HEADERS,
            timeout=3
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()
        results = search_data.get("search", [])
        for item in results:
            qid = item.get("id")
            if not qid:
                continue
            if _wikidata_is_human(qid):
                _KNOWN_PERSON_CACHE[key] = True
                return True
    except Exception as exc:
        print("========================================")
        print(f"[wikidata] error for '{name}': {exc}")
        _KNOWN_PERSON_CACHE[key] = False
        return False

    _KNOWN_PERSON_CACHE[key] = False
    return False


def _wikidata_is_human(qid):
    """
    Check if Wikidata entity has P31 (instance of) Q5 (human).
    """
    try:
        params = {
            "action": "wbgetentities",
            "ids": qid,
            "props": "claims",
            "format": "json",
        }
        resp = requests.get(
            "https://www.wikidata.org/w/api.php",
            params=params,
            headers=_WIKIDATA_HEADERS,
            timeout=3
        )
        resp.raise_for_status()
        data = resp.json()
        entity = data.get("entities", {}).get(qid, {})
        claims = entity.get("claims", {})
        for claim in claims.get("P31", []):
            mainsnak = claim.get("mainsnak", {})
            datavalue = mainsnak.get("datavalue", {})
            value = datavalue.get("value", {})
            if isinstance(value, dict) and value.get("id") == "Q5":
                return True
    except Exception:
        return False
    return False

def extract_entity_with_slots(pattern, text):
    """
    Extract entities like phone numbers or email addresses with their corresponding text slots.
    """
    entities = []
    print("========================================")
    for match in re.finditer(pattern, text):
        print(match)
        entity_obj = {
            'match': match.group(),
            'slots': [(match.start(), match.end())]
        }
        entities.append(entity_obj)
    return entities

def filter_phone_numbers(phone_numbers, text):
    """
    Filter out numeric formats that look like decimals or thousands separators.
    """
    filtered = []
    for phone in phone_numbers:
        raw = phone['match']
        slots = phone.get('slots', [])
        if slots:
            start, end = slots[0]
            if start > 0 and text[start - 1] == '+':
                phone['match'] = '+' + raw
                phone['slots'] = [(start - 1, end)]
                raw = phone['match']
        if '.' in raw:
            continue
        if re.fullmatch(r'\d+\.\d+', raw):
            continue
        if re.fullmatch(r'\d{1,3}(?:\.\d{3})+', raw):
            continue
        digit_count = len(re.sub(r'\D', '', raw))
        if digit_count < 7:
            continue
        filtered.append(phone)
    return filtered

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

def normalize_date_match(match_text):
    """
    Normalize date strings to YYYY-MM-DD when possible.
    """
    numeric_match = re.match(r'^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})$', match_text)
    if numeric_match:
        day, month, year = numeric_match.groups()
        if len(year) == 2:
            year = f"20{year}"
        return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"

    estonian_months = {
        "jaanuar": "01",
        "veebruar": "02",
        "marts": "03",
        "aprill": "04",
        "mai": "05",
        "juuni": "06",
        "juuli": "07",
        "august": "08",
        "september": "09",
        "oktoober": "10",
        "november": "11",
        "detsember": "12",
    }
    words_match = re.match(
        r'^(\d{1,2})\.\s*([A-Za-zÄÖÜÕäöüõ]+)\s+(\d{4})$',
        match_text,
        re.IGNORECASE
    )
    if words_match:
        day, month_name, year = words_match.groups()
        month = estonian_months.get(month_name.lower())
        if month:
            return f"{year.zfill(4)}-{month}-{day.zfill(2)}"

    return match_text

def merge_duplicates_normalized(entity_list, normalizer):
    """
    Merge duplicate entities using a normalized key for matching.
    """
    seen = {}
    for entity in entity_list:
        key = normalizer(entity['match'])
        if key in seen:
            seen[key]['slots'].extend(entity['slots'])
            seen[key]['slots'] = list(set(seen[key]['slots']))
        else:
            seen[key] = entity
    return list(seen.values())


def categorize(results):
    """
    Categorize NER results into person, organization, and location lists.
    """
    ner_person, ner_organisation, ner_location = [], [], []

    print("========================================")
    for result in results:
        if result['entity'] in ['B-PER', 'I-PER']:
            print(result)
            ner_person.append({'entity': result['entity'], 'word': result['word'], 'start': result.get('start'), 'end': result.get('end')})
        elif result['entity'] in ['B-ORG', 'I-ORG']:
            ner_organisation.append({'entity': result['entity'], 'word': result['word'], 'start': result.get('start'), 'end': result.get('end')})
        elif result['entity'] in ['B-LOC', 'I-LOC']:
            ner_location.append({'entity': result['entity'], 'word': result['word'], 'start': result.get('start'), 'end': result.get('end')})

    # Handle BERT subword tokens and group them properly
    ner_person = move_hashtag_words(ner_person)
    ner_organisation = move_hashtag_words(ner_organisation)
    ner_location = move_hashtag_words(ner_location)
    print("========================================")
    print(f"[categorize] person={ner_person}")
    print(f"[categorize] organisation={ner_organisation}")
    print(f"[categorize] location={ner_location}")
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
        next_start = array[i + 1].get('start')
        curr_end = array[i].get('end')
        adjacent = False
        if curr_end is not None and next_start is not None:
            adjacent = next_start <= curr_end + 1

        # Check if the next word is part of the same entity
        if (next_entity.startswith('I') or next_word.startswith('##')) and adjacent:
            if next_word == '.':  # Concatenate if next word is a period
                array[i]['word'] += next_word
                array[i]['end'] = array[i + 1].get('end', array[i].get('end'))
                del array[i + 1]
            elif next_word.startswith('##'):  # Handle subwords (BERT output tokens)
                array[i]['word'] += next_word[2:]  # Remove ## prefix
                array[i]['end'] = array[i + 1].get('end', array[i].get('end'))
                del array[i + 1]
            else:
                array[i]['word'] += ' ' + next_word  # Normal concatenation
                array[i]['end'] = array[i + 1].get('end', array[i].get('end'))
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

PERSON_MIN_LEN = 3
PERSON_STOPWORDS = {
    "de", "di", "da", "la", "le", "el", "van", "von", "der", "den", "del",
    "della", "du", "des", "dos", "das", "san", "st", "saint"
}


def is_plausible_person_token(word):
    stripped = word.replace("#", "").strip()
    if len(stripped) < PERSON_MIN_LEN:
        return False
    if stripped.lower() in PERSON_STOPWORDS:
        return False
    if not any(ch.isalpha() for ch in stripped):
        return False
    if stripped.islower():
        return False
    return True


def find_all_matches(entity_list, text, entity_type=None):
    word_array = []
    no_match_array = []

    def is_abbreviated_name(word):
        """
        Skip abbreviated names like "J. H" or "J.H.".
        """
        tokens = word.replace('.', ' . ').split()
        letter_tokens = [t for t in tokens if t != '.']
        if len(letter_tokens) >= 2 and all(len(t) == 1 for t in letter_tokens):
            return True
        return False

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
            if entity_type == "person" and not is_plausible_person_token(word):
                continue
            if is_abbreviated_name(word):
                continue
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
            if is_abbreviated_name(word):
                continue
            if len(word) == 1:  # Skip single-letter entities
                continue
            if entity_type == "person" and not is_plausible_person_token(word):
                continue

            allow_suffix = True
            if entity_type == "person" and word.islower():
                allow_suffix = False
            if allow_suffix:
                pattern = r'\b' + re.escape(word) + r'(?:[A-Za-zÄÖÜÕäöüõšž]{1,6})?\b'
            else:
                pattern = r'\b' + re.escape(word) + r'\b'
            matches = list(re.finditer(pattern, text))
            if not matches:
                no_match_array.append(word)
            else:
                for match in matches:
                    span = match.span()
                    add_match(word_obj, span)
                if word_obj['slots']:
                    word_array.append(word_obj)

        # Handle grouped multiple words with fuzzy matching
        for group in match_array:
            main_word = group[0]
            if entity_type == "person" and not is_plausible_person_token(main_word):
                continue
            if is_abbreviated_name(main_word):
                continue
            word_obj = {'match': main_word, 'slots': []}
            strict_phrase = False
            if entity_type == "person":
                tokens = [t for t in main_word.split() if t]
                strict_phrase = any(len(t) < PERSON_MIN_LEN for t in tokens)
            for word in group:
                if strict_phrase:
                    pattern = r'\b' + re.escape(word) + r'\b'
                    for match in re.finditer(pattern, text):
                        span = match.span()
                        add_match(word_obj, span)
                else:
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

def match_no_match_strings(text, no_match_array, entity_type=None):
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
        if entity_type == "person" and not is_plausible_person_token(string):
            continue
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

def extract_id_numbers_from_phone_numbers(phone_numbers, text):
    """
    Extracts ID numbers from the given phone numbers if they match the ID number regex pattern.
    Skips numbers that start with '+', as they are international phone numbers.
    """
    id_numbers = []
    phone_numbers_to_keep = []

    for phone in phone_numbers:
        phone_number = phone['match']
        slots = phone.get('slots', [])
        if slots:
            start, _ = slots[0]
            if start > 0 and text[start - 1] == '+':
                phone_numbers_to_keep.append(phone)
                continue
        if '+' in phone_number:
            phone_numbers_to_keep.append(phone)
            continue
        match = re.fullmatch(id_number_pattern, phone_number)

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
