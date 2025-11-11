import os
from flask import Flask

from config import UPLOAD_FOLDER, MAX_CONTENT_LENGTH, ALLOWED_EXTENSIONS
from routes import register_routes


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    register_routes(app)
    
    return app


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 YourERPCoach Resume Parser - SkyQ AI Edition")
    print("="*60)
    print("✅ SkyQ AI token configured")
    print("📊 Using models: llama3:8b, llama3.2:3b, deepseek-r1:8b, gpt-oss:20b")
    print("="*60 + "\n")
    
    app = create_app()
    app.run(debug=True, port=5000)