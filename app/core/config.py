from pydantic_settings import BaseSettings, SettingsConfigDict


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

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int


settings = Settings()
