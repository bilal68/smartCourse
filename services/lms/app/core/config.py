from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure env file is loaded before Settings() reads environment variables
from app.core.env import load_env
load_env()


class Settings(BaseSettings):
    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=None,  # we load via app.core.env (ENV_FILE)
        extra="ignore",
        case_sensitive=True,
    )

    DATABASE_URL: str
    REDIS_URL: str
    RABBITMQ_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str

    # External Services
    AI_SERVICE_URL: str = "http://localhost:8001"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # S3 Storage Configuration
    USE_DUMMY_S3: bool = True  # Use local filesystem instead of real S3 (for dev)
    AWS_ACCESS_KEY_ID: str = "dummy-key-id"
    AWS_SECRET_ACCESS_KEY: str = "dummy-secret-key"
    AWS_S3_BUCKET: str = "smartcourse-dev"
    AWS_REGION: str = "us-east-1"
    S3_STORAGE_PATH: str = "./storage/s3"  # Local path for dummy S3


settings = Settings()
