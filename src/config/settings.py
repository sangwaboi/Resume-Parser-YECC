import os
from dotenv import load_dotenv
load_dotenv()
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    UPLOAD_FOLDER = "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"pdf", "docx", "doc"}
    DATABASE_FILE = "resumes.db"
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = "gemini-2.0-flash-exp"
    GROK_API_KEY = os.getenv("GROK_API_KEY")
    GROK_API_BASE = "https://openrouter.ai/api/v1"
    GROK_MODEL = "x-ai/grok-3-mini-beta"
    USE_BETA = True
    YECC_API_TOKEN = os.getenv("YECC_API_TOKEN")
    YECC_BASE_URL = "https://api.yecc.tech"
    YECC_FRONTEND_URL = "https://beta.yecc.tech" if USE_BETA else "https://yecc.tech"
    @classmethod
    def get_yecc_headers(cls):
        return {
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"{cls.YECC_API_TOKEN}",
            "Content-Type": "application/json",
            "Origin": cls.YECC_FRONTEND_URL,
            "Referer": f"{cls.YECC_FRONTEND_URL}/"
        }
config = Config()
