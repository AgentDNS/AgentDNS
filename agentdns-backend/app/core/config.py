from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://agentdns:your_password_here@localhost:5432/agentdns"
    REDIS_URL: str = "redis://localhost:6379"
    
    # Milvus Vector Database
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION_NAME: str = "agentdns_services"
    MILVUS_DIMENSION: int = 2560  # keep 2560 dimension for compatibility with existing vectors
    
    # JWT
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AgentDNS"
    VERSION: str = "0.1.0"
    
    # External Services
    OPENAI_API_KEY: Optional[str] = None
    
    # Security
    ENCRYPTION_KEY: Optional[str] = None
    
    # OpenAI Embedding (custom configuration)
    OPENAI_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    OPENAI_EMBEDDING_MODEL: str = "doubao-embedding-text-240715"
    OPENAI_MAX_TOKENS: int = 4096
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"


settings = Settings() 