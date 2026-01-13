"""Database initialization utilities for AI service."""

from sqlalchemy.orm import Session
from app.db.base import engine, Base
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_database():
    """Create all database tables."""
    logger.info("Creating AI service database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("AI service database tables created successfully")


def drop_database():
    """Drop all database tables."""
    logger.info("Dropping AI service database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.info("AI service database tables dropped successfully")


if __name__ == "__main__":
    create_database()