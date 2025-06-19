"""
Modern configuration using Pydantic Settings
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Configuration
    api_port: int = Field(default=8000, description="API port")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Database
    database_url: str = Field(
        default="mysql+pymysql://user:pass@localhost/db",
        description="MySQL database URL"
    )
    
    # ChromaDB
    chroma_persist_directory: Optional[str] = Field(
        default=None,
        description="ChromaDB persistence directory"
    )
    
    # OpenAI
    openai_api_key: str = Field(
        description="OpenAI API key",
        min_length=1
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use"
    )
    openai_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="OpenAI temperature"
    )
    openai_max_tokens: int = Field(
        default=500,
        gt=0,
        description="Max tokens for OpenAI responses"
    )
    
    # Security
    secret_key: str = Field(
        default="change-this-in-production",
        min_length=32,
        description="Secret key for JWT"
    )
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    
    # CORS
    cors_origins: str = Field(
        default="*",
        description="Allowed CORS origins (comma-separated)"
    )
    
    # Rate limiting
    rate_limit_per_minute: int = Field(
        default=60,
        gt=0,
        description="Rate limit per minute"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list"""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]
        return [self.cors_origins]
    
    @field_validator('debug', mode='before')
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return v
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

# Create global settings instance
settings = Settings()