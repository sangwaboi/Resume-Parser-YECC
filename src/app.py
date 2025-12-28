import os
from flask import Flask
from src.config import config
from src.api import api
def create_app():
    app = Flask(__name__, template_folder='../templates')
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
    app.secret_key = config.SECRET_KEY
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    app.register_blueprint(api)
    return app
def run():
    print("\n" + "="*60)
    print("🚀 YECC Resume Parser - Production Ready")
    print("="*60)
    print(f"✅ Gemini API configured")
    print(f"📊 Using model: {config.GEMINI_MODEL}")
    print(f"🔗 YECC API: {config.YECC_BASE_URL}")
    print("="*60 + "\n")
    app = create_app()
    app.run(debug=config.DEBUG, port=5000)
if __name__ == '__main__':
    run()
