import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    
    # Database configuration from .env
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "chat-python")
    
    # Build database URL
    if DB_PASSWORD:
        db_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    else:
        db_url = f"mysql+pymysql://{DB_USER}:@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", db_url)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB max file size
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def get_config() -> type[Config]:
    return Config


