from transformers import BertTokenizer, BertForTokenClassification
from transformers import pipeline
from docx import Document

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
        if array[i+1]['entity'].startswith('I'):
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
    
    move_hashtag_words(ner_organisation)
    

# Split the text into chunks and process each chunk individually
max_chunk_length = 512

for i in range(0, len(text), max_chunk_length):
    chunk = text[i:i + max_chunk_length]
    chunk = chunk.strip()  # Remove leading and trailing whitespace

    # Perform NER on the chunk
    ner_results = nlp(chunk)
    #print(ner_results)
    categorize(ner_results)

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

