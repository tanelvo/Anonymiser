from transformers import BertTokenizer, BertForTokenClassification
from transformers import pipeline
from docx import Document

# Eemaldada väikse esitähega sõnad, et ruumi säästa? 
def remove_non_capitalized_words(input_string):
    # Split the input string into words
    words = input_string.split()

    # Filter out words that don't start with a capitalized letter
    filtered_words = [word for word in words if word[0].isupper()]

    # Reconstruct the string from filtered words
    filtered_string = ' '.join(filtered_words)

    return filtered_string

tokenizer = BertTokenizer.from_pretrained('tartuNLP/EstBERT_NER')
bertner = BertForTokenClassification.from_pretrained('tartuNLP/EstBERT_NER')

nlp = pipeline("ner", model=bertner, tokenizer=tokenizer)
sentence = 'Hispaania President on Ivan Frolov. Ma elan Sakus, Lasnamäel on mul ka maja. Sündisin 12.05.2007. Töötan firmas nimega Aktors OÜ.'

docx_file_path = './essee.docx'
doc = Document(docx_file_path)

sentence = ""
for paragraph in doc.paragraphs:
    sentence += paragraph.text + "\n"
print(sentence)
sentence = sentence.strip()

sentence = remove_non_capitalized_words(sentence)

ner_results = nlp(sentence)
print(ner_results)
for result in ner_results:
    print(result)



