import os

UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}

SKYQ_BASE_URL = "https://ai.skyq.tech"
SKYQ_JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImQ5NTIzM2VhLTYxY2ItNDY1NC05MGI4LTFkNjRhZGI0ZjE0YiJ9.bBlFzDMgLkNNim-8jGBXBeIkBNYC9HBqEvPPkgjRv3Q"
SKYQ_HEADERS = {
    "Authorization": f"Bearer {SKYQ_JWT_TOKEN}",
    "Content-Type": "application/json"
}

YECC_BASE_URL = "https://api.yecc.tech"
YECC_API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NjI3NTM4NTMsIm5iZiI6MTc2Mjc1Mzg1MywiZXhwIjoxNzYzMDEzMDUzLCJ1c2VySW5mbyI6eyJJRCI6Ik1qaz0iLCJSb2xlSUQiOiJBZG1pbiIsIkZpcnN0TmFtZSI6IlNhdXJhYmgiLCJMYXN0TmFtZSI6IkthcnZlIiwiUmVzdW1lVXJsIjoiIiwiQWNjZXNzQ29udHJvbCI6Int9IiwiRG9tYWluIjpudWxsLCJEZXNpZ25hdGlvbiI6bnVsbCwiVW5pcXVlRGV2aWNlSUQiOjgsInByb2ZpbGVJbWFnZSI6IlwvaW1nXC9wcm9maWxlXC9iaXMtbWFuLnBuZyJ9LCJsb2dpbk1ldGhvZCI6Im1vYmlsZSJ9.ct29ezeHrYMVUGSjIARBP838hglegnwBNrBgoI0ysvQ"
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