from transformers import BertTokenizer, BertForTokenClassification
from transformers import pipeline
from docx import Document
import string

tokenizer = BertTokenizer.from_pretrained('tartuNLP/EstBERT_NER')
bertner = BertForTokenClassification.from_pretrained('tartuNLP/EstBERT_NER')

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
docx_file_path = './essee.docx'
doc = Document(docx_file_path)
text = "\n".join([paragraph.text for paragraph in doc.paragraphs])

ner_person = []
ner_organisation = []
ner_location = []

def move_hashtag_words(array):
    i = 0
    while i < len(array) - 1:  # Iterate up to the second-to-last element
        if array[i+1]['entity'].startswith('I') or array[i+1]['word'].startswith('#'):
            if array[i+1]['word'].startswith('##'):
                array[i]['word'] = array[i]['word'] + array[i+1]['word'].strip("#")
            else:
                array[i]['word'] = array[i]['word'] + ' ' + array[i+1]['word']
            del array[i+1]
        else:
            i += 1  # Move to the next element if no deletion is done

def categorize(results):
    for result in results:
        if result['entity'] in ['B-PER', 'I-PER']:
            ner_person.append(result)
        elif result['entity'] in ['B-ORG', 'I-ORG']:
            ner_organisation.append(result)
        elif result['entity'] in ['B-LOC', 'I-LOC']:
            ner_location.append(result)
    
    move_hashtag_words(ner_person)
    move_hashtag_words(ner_organisation)
    move_hashtag_words(ner_location)


def find_split_index(chunk):
    # Find the index of the last space or punctuation within the first 512 characters
    for i in range(min(len(chunk), 512) - 1, -1, -1):
        if chunk[i] in string.whitespace or chunk[i] in string.punctuation:
            return i + 1
    return 512

    

# Split the text into chunks and process each chunk individually
start_index = 0
last_word_capitalized = False
while start_index < len(text):
    end_index = find_split_index(text[start_index:])
    chunk = text[start_index:start_index + end_index].strip()

    # Ensure last word is not capitalized
    if last_word_capitalized:
        last_space_index = chunk.rfind(' ')
        chunk = chunk[:last_space_index].strip()
    
    print("---------------------")
    print(chunk)
    # Perform NER on the chunk
    ner_results = nlp(chunk)
    categorize(ner_results)

    # Check if the last word in the chunk is capitalized
    last_word_capitalized = chunk.split()[-1][0].isupper()

    start_index += end_index

#print("Persons:", ner_person)
for per in ner_person:
    print(per)
print("------------------------------------------------------------")
for org in ner_organisation:
    print(org)
print("------------------------------------------------------------")
for loc in ner_location:
    print(loc)
#print("Organisations:", ner_organisation)
#print("Locations:", ner_location)

