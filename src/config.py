import os
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class DatabaseConfig(BaseModel):
    url: str = os.getenv("DATABASE_URL", "sqlite:///../crawler/data/products.db")
    chroma_persist_directory: str = os.getenv("CHROMA_PERSIST_DIRECTORY", "../crawler/data/chroma")


class OpenAIConfig(BaseModel):
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    max_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS", "500"))


class APIConfig(BaseModel):
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))
    debug: bool = os.getenv("API_DEBUG", "true").lower() == "true"
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # CORS
    cors_origins: List[str] = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else ["*"]
    
    # Rate limiting
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))


class Config:
    database = DatabaseConfig()
    openai = OpenAIConfig()
    api = APIConfig()


config = Config()