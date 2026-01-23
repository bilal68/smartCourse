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
    
    # Unified Embedding Configuration
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "sentence-transformers")  # "openai" or "sentence-transformers"
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "multi-qa-MiniLM-L6-cos-v1")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")  # For local models
    
    # OpenAI Configuration (when using OpenAI embeddings)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")  # "openai", "groq", "ollama"
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3.1")  # Default to Llama 3.1 for Ollama
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "500"))
    
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