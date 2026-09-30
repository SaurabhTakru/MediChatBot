import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    secret_key: str = "CHANGE_ME_TO_A_LONG_RANDOM_SECRET"
    token_exp_minutes: int = 480
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "mediassist_docs"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    database_path: str = "../data/mediassist.db"
    demo_password: str = "demo123"

settings = Settings()
