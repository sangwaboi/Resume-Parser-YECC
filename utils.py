import PyPDF2
import docx
import re
from config import ALLOWED_EXTENSIONS


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")


def extract_text_from_docx(file_path):
    """Extract text from Word document"""
    try:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting DOCX text: {e}")
        raise Exception(f"Failed to extract text from Word document: {str(e)}")


def clean_array(arr):
    """Clean and normalize array data"""
    if not arr:
        return []
    cleaned = []
    for item in arr:
        if isinstance(item, dict):
            cleaned.append(str(item.get('Title', item.get('title', str(item)))))
        elif isinstance(item, str):
            cleaned.append(item)
        else:
            cleaned.append(str(item))
    return cleaned


def extract_email(text):
    """Extract email from text using regex"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    return emails[0] if emails else None


def extract_phone(text):
    """Extract phone number from text using regex"""
    phone_pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
    phones = re.findall(phone_pattern, text)
    return phones[0].strip() if phones else None


def extract_linkedin(text):
    """Extract LinkedIn URL from text"""
    linkedin_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+'
    linkedin = re.findall(linkedin_pattern, text, re.IGNORECASE)
    return linkedin[0] if linkedin else None


def extract_years_experience(text):
    """Extract years of experience from text"""
    years_pattern = r'(\d+)[\+]?\s*(?:years?|yrs?)'
    years_matches = re.findall(years_pattern, text.lower())
    return max(map(int, years_matches)) if years_matches else None


def safe_join(arr):
    """Safely join array elements into a string"""
    if not arr:
        return 'N/A'
    result = []
    for item in arr:
        if isinstance(item, dict):
            result.append(item.get('Title', str(item)))
        elif isinstance(item, str):
            result.append(item)
        else:
            result.append(str(item))
    return ', '.join(result)