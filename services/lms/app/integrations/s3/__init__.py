"""S3 storage integration - supports both dummy (local) and real AWS S3."""

from .client import get_s3_client, S3Client

__all__ = ["get_s3_client", "S3Client"]
