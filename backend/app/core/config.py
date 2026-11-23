"""Core application settings and structured logging configuration for ShopMind AI."""

import logging
import os
import re
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


class SensitiveLogFilter(logging.Filter):
    """Redacts API keys, JWTs, passwords, and secrets from all structured log messages."""

    PATTERNS = [
        (re.compile(r"(gsk_[A-Za-z0-9]{20,})"), "[REDACTED_GROQ_KEY]"),
        (re.compile(r"(Bearer\s+[A-Za-z0-9\-_\.]+)", re.IGNORECASE), "Bearer [REDACTED_JWT]"),
        (re.compile(r'("password"\s*:\s*")[^"]+(")', re.IGNORECASE), r"\1[REDACTED_PASSWORD]\2"),
        (re.compile(r'("api_key"\s*:\s*")[^"]+(")', re.IGNORECASE), r"\1[REDACTED_API_KEY]\2"),
        (re.compile(r'("secret"\s*:\s*")[^"]+(")', re.IGNORECASE), r"\1[REDACTED_SECRET]\2"),
        (re.compile(r"(sk-[A-Za-z0-9]{20,})"), "[REDACTED_API_KEY]"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage())
        for pattern, replacement in self.PATTERNS:
            msg = pattern.sub(replacement, msg)
        record.msg = msg
        record.args = ()
        return True


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("shopmind")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}'
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveLogFilter())
        logger.addHandler(handler)
    return logger


class Settings(BaseSettings):
    APP_NAME: str = "ShopMind AI — RAG-Based Intelligent Shopping Assistant"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    # Groq LLM Configuration
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Embedding & RAG Configuration
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    CROSS_ENCODER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    VECTOR_STORE_BACKEND: str = "faiss"
    VECTOR_INDEX_DIR: str = str(DATA_DIR / "vector_index")

    # Database & Redis
    DATABASE_URL: str = f"sqlite:///{(DATA_DIR / 'shopmind.db').as_posix()}"
    SQLITE_FALLBACK_URL: str = f"sqlite:///{(DATA_DIR / 'shopmind.db').as_posix()}"
    USE_SQLITE_FALLBACK: bool = True
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security & Auth
    SECRET_KEY: str = "shopmind-ai-production-grade-secret-key-2026-secure-jwt-hmac256"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:8000"
    RATE_LIMIT_PER_MINUTE: int = 90
    MAX_UPLOAD_SIZE_MB: int = 10

    # Evaluation Pass/Fail Thresholds
    EVAL_MIN_PRECISION_AT_K: float = 0.65
    EVAL_MIN_RECALL_AT_K: float = 0.75
    EVAL_MIN_MRR: float = 0.75
    EVAL_MIN_NDCG: float = 0.75
    EVAL_MIN_FAITHFULNESS: float = 0.85
    EVAL_MIN_ANSWER_RELEVANCY: float = 0.80
    EVAL_MAX_HALLUCINATION_RATE: float = 0.10

    model_config = SettingsConfigDict(
        env_file=[str(BASE_DIR / ".env"), str(BACKEND_DIR / ".env")],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def groq_configured(self) -> bool:
        key = (self.GROQ_API_KEY or os.environ.get("GROQ_API_KEY") or "").strip()
        return bool(key and len(key) > 10 and not key.startswith("your_"))


settings = Settings()
logger = setup_logging()
