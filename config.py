import os

UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}

SKYQ_BASE_URL = "https://ai.skyq.tech"
SKYQ_JWT_TOKEN = "Your_SkyQ_JWT_Token_Here"
SKYQ_HEADERS = {
    "Authorization": f"Bearer {SKYQ_JWT_TOKEN}",
    "Content-Type": "application/json"
}

YECC_BASE_URL = "https://api.yecc.tech"
YECC_API_TOKEN = "Your_YECC_API_Token_Here"
YECC_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Authorization": YECC_API_TOKEN,
    "Content-Type": "application/json",
    "Origin": "https://beta.yecc.tech",
    "Referer": "https://beta.yecc.tech/"
}

EXCEL_FILE = 'resumes_database.xlsx'

MODEL_CONFIGS = [
    {"model": "llama3:8b", "temperature": 0.1, "max_tokens": 1500},
    {"model": "llama3.2:3b", "temperature": 0.1, "max_tokens": 1500},
    {"model": "deepseek-r1:8b", "temperature": 0.1, "max_tokens": 1500},
    {"model": "gpt-oss:20b", "temperature": 0.1, "max_tokens": 1500},
]

MAX_TEXT_LENGTHS = [5000, 4000, 3000, 2500]

LOCAL_DOCS_DIR = 'docs_for_rag'