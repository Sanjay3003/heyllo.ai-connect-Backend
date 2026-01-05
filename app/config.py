"""Application configuration using Pydantic Settings"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    PROJECT_NAME: str = "Heyllo.ai Call Center"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str
    
    # JWT Authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Bland AI (for AI calling)
    BLAND_AI_API_KEY: str = ""
    BLAND_AI_BASE_URL: str = "https://api.bland.ai"
    BLAND_WEBHOOK_URL: str = ""
    
    # OpenAI (used by Bland AI for conversation intelligence)
    OPEN_AI_API: str = ""
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
