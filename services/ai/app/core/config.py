"""Configuration settings for AI service."""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Service Info
    SERVICE_NAME: str = "ai-service"
    SERVICE_VERSION: str = "1.0.0"
    
    # AI Service Database - separate from LMS
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://smartcourse:password@127.0.0.1:5432/smartcourse_ai"
    )
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_GROUP_ID: str = "ai-service-group"
    
    # Content Processing
    CHUNK_SIZE_WORDS: int = 500
    CHUNK_OVERLAP_WORDS: int = 50
    
    # S3 Settings (shared with LMS)
    USE_DUMMY_S3: bool = True
    AWS_ACCESS_KEY_ID: str = "dummy_key_id"
    AWS_SECRET_ACCESS_KEY: str = "dummy_secret_key"
    AWS_S3_BUCKET: str = "smartcourse-dev"
    AWS_REGION: str = "us-east-1"
    S3_STORAGE_PATH: str = os.getenv("S3_STORAGE_PATH", "./storage/s3")  # For dummy S3
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields


settings = Settings()