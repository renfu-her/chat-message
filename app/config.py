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
    
    # Email configuration from .env
    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    # Support both TLS (587) and SSL (465) ports
    try:
        MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    except (ValueError, TypeError):
        MAIL_PORT = 587
    
    # TLS and SSL are mutually exclusive
    mail_use_tls = os.getenv("MAIL_USE_TLS", "").lower()
    mail_use_ssl = os.getenv("MAIL_USE_SSL", "").lower()
    
    if mail_use_tls == "true":
        MAIL_USE_TLS = True
        MAIL_USE_SSL = False
    elif mail_use_ssl == "true":
        MAIL_USE_TLS = False
        MAIL_USE_SSL = True
    else:
        # Default to TLS for port 587, SSL for port 465
        MAIL_USE_TLS = (MAIL_PORT == 587)
        MAIL_USE_SSL = (MAIL_PORT == 465)
    
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "").strip()
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "").strip()
    MAIL_FROM = os.getenv("MAIL_FROM", "noreply@example.com").strip()
    MAIL_TO = os.getenv("MAIL_TO", "admin@example.com").strip()  # Recipient for feedback emails
    
    # Optional: Mail debug mode
    MAIL_DEBUG = os.getenv("MAIL_DEBUG", "false").lower() == "true"


def get_config() -> type[Config]:
    return Config


