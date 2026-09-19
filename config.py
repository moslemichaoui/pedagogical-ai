import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-pedagogical-ai-2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL') or 'gemini-3.6-flash'
    GEMINI_EMBEDDING_MODEL = os.environ.get('GEMINI_EMBEDDING_MODEL') or 'embedding-001'
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(basedir, 'uploads')
    CHROMA_PERSIST_DIR = os.environ.get('CHROMA_PERSIST_DIR') or os.path.join(basedir, 'chromadb_data')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
