from docx import Document
from flask import Flask, request, jsonify
from flask_cors import CORS
from anonymiser import process_document  # Assume you refactored `anonymiser.py` to have a callable function

app = Flask(__name__)
CORS(app)

@app.route('/file/', methods = ['POST'])
def file_process():
    file = request.files['file']
    doc = Document(file)
    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    response_data = {
        'highlightables': process_document(text),
        'text': text
    }
    return jsonify(response_data)

@app.route('/text/', methods=['POST'])
def text_process():
    text = request.json.get('text', '')
    response_data = process_document(text)
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(host='localhost', port=8080)