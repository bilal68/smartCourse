"""Configuration settings for AI service."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Get the directory containing this config file
CONFIG_DIR = Path(__file__).parent.parent.parent  # Go up to services/ai/

# Explicitly load .env files 
env_local_path = CONFIG_DIR / ".env.local"
env_path = CONFIG_DIR / ".env"

if env_local_path.exists():
    load_dotenv(env_local_path)
    print(f"Loaded {env_local_path}")
elif env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded {env_path}")


class Settings(BaseSettings):
    # Service Info
    SERVICE_NAME: str = "ai-service"
    SERVICE_VERSION: str = "1.0.0"
    
    # AI Service Database - separate from LMS
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://smartcourse:password@127.0.0.1:5432/smartcourse_ai"
    )
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_GROUP_ID: str = "ai-service-group"
    KAFKA_COURSE_TOPIC: str = "course.events"
    KAFKA_AI_TOPIC: str = "ai"
    
    # OpenAI Configuration for RAG
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBEDDING_DIMENSION: int = 1536
    OPENAI_CHAT_MODEL: str = "gpt-3.5-turbo"
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 500
    
    # Content Chunking Configuration
    CHUNK_SIZE: int = 1000  # Characters per chunk
    CHUNK_OVERLAP: int = 100  # Character overlap between chunks
    
    # Retrieval Configuration
    RETRIEVAL_TOP_K: int = 5  # Number of chunks to retrieve for RAG
    SIMILARITY_THRESHOLD: float = 0.3  # Minimum cosine similarity score
    
    # Embedding Batch Configuration
    EMBEDDING_BATCH_SIZE: int = 100  # Texts per batch to OpenAI API
    
    # S3/MinIO Settings - use environment variables
    USE_DUMMY_S3: bool = os.getenv("USE_DUMMY_S3", "true").lower() == "true"
    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "")
    S3_USE_SSL: bool = os.getenv("S3_USE_SSL", "false").lower() == "true"
    AWS_ACCESS_KEY_ID: str = os.getenv("S3_ACCESS_KEY", "dummy_key_id")  
    AWS_SECRET_ACCESS_KEY: str = os.getenv("S3_SECRET_KEY", "dummy_secret_key")
    AWS_S3_BUCKET: str = os.getenv("S3_BUCKET", "smartcourse-dev")
    AWS_REGION: str = os.getenv("S3_REGION", "us-east-1")
    S3_STORAGE_PATH: str = os.getenv("S3_STORAGE_PATH", "./storage/s3")  # For dummy S3
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = [str(CONFIG_DIR / ".env.local"), str(CONFIG_DIR / ".env")]
        extra = "ignore"  # Ignore extra fields


settings = Settings()