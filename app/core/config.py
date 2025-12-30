from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    RABBITMQ_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int


settings = Settings()
