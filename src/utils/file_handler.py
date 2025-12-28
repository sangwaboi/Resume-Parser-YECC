import re
import pdfplumber
from docx import Document
from src.config import config
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS
def extract_text_from_pdf(filepath):
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()
def extract_text_from_docx(filepath):
    doc = Document(filepath)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text.strip()
def extract_text(filepath, filename):
    if filename.lower().endswith(".pdf"):
        return extract_text_from_pdf(filepath)
    return extract_text_from_docx(filepath)
