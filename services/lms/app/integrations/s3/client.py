"""Main S3 client - switches between dummy and real AWS S3."""

from typing import Union
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class S3Client:
    """
    Unified S3 client that works with both dummy (local) and real AWS S3.
    Automatically selects implementation based on USE_DUMMY_S3 setting.
    """

    def __init__(self):
        if settings.USE_DUMMY_S3:
            # Use local filesystem storage
            from .dummy_storage import DummyS3Client
            self._client = DummyS3Client()
            self._mode = "dummy"
            logger.info("S3Client initialized in DUMMY mode (local storage)")
        else:
            # Use real AWS S3
            try:
                import boto3
                self._client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                self._bucket = settings.AWS_S3_BUCKET
                self._mode = "real"
                logger.info("S3Client initialized in REAL mode", bucket=self._bucket)
            except ImportError:
                raise ImportError(
                    "boto3 is required for real S3 mode. "
                    "Install it with: pip install boto3"
                )

    def upload_file(self, file_path: str, key: str) -> dict:
        """
        Upload a file.
        
        Args:
            file_path: Local path to file
            key: S3 key (path) where to store
            
        Returns:
            Upload metadata
        """
        if self._mode == "dummy":
            return self._client.upload_file(file_path, key)
        else:
            self._client.upload_file(file_path, self._bucket, key)
            return {"Key": key, "Bucket": self._bucket}

    def download_file(self, key: str, file_path: str) -> None:
        """
        Download a file.
        
        Args:
            key: S3 key (path) of file
            file_path: Local path where to save
        """
        if self._mode == "dummy":
            self._client.download_file(key, file_path)
        else:
            self._client.download_file(self._bucket, key, file_path)

    def get_object(self, key: str) -> dict:
        """
        Get object content and metadata.
        
        Args:
            key: S3 key (path) of file
            
        Returns:
            Object data with Body and metadata
        """
        if self._mode == "dummy":
            return self._client.get_object(key)
        else:
            return self._client.get_object(Bucket=self._bucket, Key=key)

    def put_object(self, key: str, body: bytes, content_type: str = None) -> dict:
        """
        Store object from bytes.
        
        Args:
            key: S3 key (path) where to store
            body: File content as bytes
            content_type: MIME type (optional)
            
        Returns:
            Upload metadata
        """
        if self._mode == "dummy":
            return self._client.put_object(key, body, content_type)
        else:
            params = {"Bucket": self._bucket, "Key": key, "Body": body}
            if content_type:
                params["ContentType"] = content_type
            return self._client.put_object(**params)

    def delete_object(self, key: str) -> dict:
        """
        Delete an object.
        
        Args:
            key: S3 key (path) of file to delete
            
        Returns:
            Deletion metadata
        """
        if self._mode == "dummy":
            return self._client.delete_object(key)
        else:
            return self._client.delete_object(Bucket=self._bucket, Key=key)

    def list_objects(self, prefix: str = "") -> dict:
        """
        List objects with prefix.
        
        Args:
            prefix: Key prefix to filter by
            
        Returns:
            dict with Contents list
        """
        if self._mode == "dummy":
            return self._client.list_objects(prefix)
        else:
            response = self._client.list_objects_v2(
                Bucket=self._bucket,
                Prefix=prefix
            )
            return {"Contents": response.get("Contents", [])}

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for temporary access.
        
        Args:
            key: S3 key (path)
            expiration: URL expiration in seconds
            
        Returns:
            Presigned URL
        """
        if self._mode == "dummy":
            return self._client.generate_presigned_url(key, expiration)
        else:
            return self._client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self._bucket, 'Key': key},
                ExpiresIn=expiration
            )


# Singleton instance
_s3_client = None


def get_s3_client() -> S3Client:
    """Get singleton S3 client instance."""
    global _s3_client
    if _s3_client is None:
        _s3_client = S3Client()
    return _s3_client
