import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    APIFY_TOKEN: str = os.getenv("APIFY_TOKEN", "")
    BREVO_SMTP_USER: str = os.getenv("BREVO_SMTP_USER", "")
    BREVO_SMTP_PASSWORD: str = os.getenv("BREVO_SMTP_PASSWORD", "")
    LINKEDIN_EMAIL: str = os.getenv("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD: str = os.getenv("LINKEDIN_PASSWORD", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-70b-instruct"

    # Path Constants
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
    APPLICATIONS_DIR: Path = DATA_DIR / "applications"
    INTERVIEW_SESSIONS_DIR: Path = DATA_DIR / "interview_sessions"
    LOGS_DIR: Path = BASE_DIR / "logs"

    # Specific Files
    PROFILE_FILE: Path = DATA_DIR / "profile.json"
    HISTORY_FILE: Path = DATA_DIR / "history.json"
    TARGETS_FILE: Path = DATA_DIR / "targets.json"
    DECISIONS_LOG: Path = LOGS_DIR / "decisions.log"
    DEBUG_LOG: Path = LOGS_DIR / "debug.log"

    # Behavioral Constants
    MAX_GAN_ITERATIONS: int = 5
    MAX_DAILY_APPLICATIONS: int = 20
    MIN_APPLY_DELAY_SECONDS: int = 2
    MAX_APPLY_DELAY_SECONDS: int = 8
    MIN_CV_SCORE: float = 9.0
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    class Config:
        env_file = ".env"

# Instantiate settings
settings = Settings()
