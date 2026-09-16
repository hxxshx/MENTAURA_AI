"""
Configuration and Environment Settings for Mentaura Platform.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv(override=True)

class Settings(BaseSettings):
    APP_NAME: str = "Mentaura Support Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database URL: Primary is PostgreSQL, with SQLite fallback if PostgreSQL is not active
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./mentaura.db"
    )
    
    # Secret Key for cryptographic operations & tokens
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", 
        "mentaura_super_secure_case_aware_key_2026_change_in_production"
    )
    
    # Session / Cookie Settings
    COOKIE_NAME: str = "mentaura_session"
    SESSION_EXPIRE_MINUTES: int = 1440  # 24 Hours
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE: str = "lax"
    
    # Rate Limiting & Account Security
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15
    
    # Privacy Policy & Consent Notice
    CURRENT_CONSENT_VERSION: str = "1.0"
    CURRENT_NOTICE_VERSION: str = "1.0"

    # Email OTP & Transactional Email Settings (SMTP & HTTPS APIs)
    GMAIL_ADDRESS: str = os.getenv("GMAIL_ADDRESS", "")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_TIMEOUT: int = int(os.getenv("SMTP_TIMEOUT", "3"))
    RESEND_API_KEY: Optional[str] = os.getenv("RESEND_API_KEY", "")
    BREVO_API_KEY: Optional[str] = os.getenv("BREVO_API_KEY", "")
    OTP_EXPIRE_MINUTES: int = 10

    # JWT Authentication
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # Google Gemini AI Service
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: Optional[str] = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

settings = Settings()
