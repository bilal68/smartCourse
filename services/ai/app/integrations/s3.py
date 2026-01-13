"""Copy S3 integration from LMS service for AI service."""

import os
from pathlib import Path
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError
import uuid

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DummyS3Client:
    """Dummy S3 client that uses local filesystem."""
    
    def __init__(self):
        self.storage_path = Path(settings.S3_STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"DummyS3Client initialized, storage_path={str(self.storage_path)}")
    
    def upload_file(self, file_path: str, key: str) -> bool:
        """Upload a file to dummy S3 (copy to local storage)."""
        try:
            dest_path = self.storage_path / key
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            import shutil
            shutil.copy2(file_path, dest_path)
            
            logger.debug("File uploaded to dummy S3", key=key, dest=str(dest_path))
            return True
        except Exception as e:
            logger.error("Failed to upload file to dummy S3", key=key, error=str(e))
            return False
    
    def download_file(self, key: str, file_path: str) -> bool:
        """Download a file from dummy S3."""
        try:
            src_path = self.storage_path / key
            if not src_path.exists():
                logger.warning("File not found in dummy S3", key=key)
                return False
            
            # Ensure destination directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            import shutil
            shutil.copy2(src_path, file_path)
            
            logger.debug("File downloaded from dummy S3", key=key, dest=file_path)
            return True
        except Exception as e:
            logger.error("Failed to download file from dummy S3", key=key, error=str(e))
            return False
    
    def get_object(self, key: str) -> bytes:
        """Get object content as bytes."""
        src_path = self.storage_path / key
        if not src_path.exists():
            raise FileNotFoundError(f"Object not found: {key}")
        
        return src_path.read_bytes()
    
    def put_object(self, key: str, body: bytes, content_type: str = None) -> bool:
        """Put object content."""
        try:
            dest_path = self.storage_path / key
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(body)
            
            logger.debug("Object stored in dummy S3", key=key, size=len(body))
            return True
        except Exception as e:
            logger.error("Failed to store object in dummy S3", key=key, error=str(e))
            return False
    
    def delete_object(self, key: str) -> bool:
        """Delete an object."""
        try:
            dest_path = self.storage_path / key
            if dest_path.exists():
                dest_path.unlink()
                logger.debug("Object deleted from dummy S3", key=key)
            return True
        except Exception as e:
            logger.error("Failed to delete object from dummy S3", key=key, error=str(e))
            return False
    
    def list_objects(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List objects with optional prefix."""
        objects = []
        prefix_path = self.storage_path / prefix if prefix else self.storage_path
        
        try:
            if prefix_path.is_file():
                # Single file
                stat = prefix_path.stat()
                objects.append({
                    "Key": str(prefix_path.relative_to(self.storage_path)),
                    "Size": stat.st_size,
                    "LastModified": stat.st_mtime
                })
            else:
                # Directory - list all files recursively
                for file_path in prefix_path.rglob("*"):
                    if file_path.is_file():
                        stat = file_path.stat()
                        objects.append({
                            "Key": str(file_path.relative_to(self.storage_path)),
                            "Size": stat.st_size,
                            "LastModified": stat.st_mtime
                        })
        except Exception as e:
            logger.error("Failed to list objects in dummy S3", prefix=prefix, error=str(e))
        
        return objects
    
    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL (dummy implementation)."""
        # For dummy mode, return a file:// URL
        file_path = self.storage_path / key
        return f"file://{file_path.absolute()}"


class S3Client:
    """S3 client wrapper that switches between real and dummy implementation."""
    
    def __init__(self):
        if settings.USE_DUMMY_S3:
            self.client = DummyS3Client()
            self._is_dummy = True
        else:
            self.client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            self._is_dummy = False
        
        logger.info(f"S3Client initialized, is_dummy={self._is_dummy}")
    
    def upload_file(self, file_path: str, key: str) -> bool:
        """Upload a file to S3."""
        if self._is_dummy:
            return self.client.upload_file(file_path, key)
        else:
            try:
                self.client.upload_file(
                    file_path, 
                    settings.AWS_S3_BUCKET, 
                    key
                )
                return True
            except ClientError as e:
                logger.error("Failed to upload file to S3", key=key, error=str(e))
                return False
    
    def download_file(self, key: str, file_path: str) -> bool:
        """Download a file from S3."""
        if self._is_dummy:
            return self.client.download_file(key, file_path)
        else:
            try:
                self.client.download_file(
                    settings.AWS_S3_BUCKET,
                    key,
                    file_path
                )
                return True
            except ClientError as e:
                logger.error("Failed to download file from S3", key=key, error=str(e))
                return False
    
    def get_object(self, key: str) -> bytes:
        """Get object content as bytes."""
        if self._is_dummy:
            return self.client.get_object(key)
        else:
            try:
                response = self.client.get_object(
                    Bucket=settings.AWS_S3_BUCKET,
                    Key=key
                )
                return response['Body'].read()
            except ClientError as e:
                logger.error("Failed to get object from S3", key=key, error=str(e))
                raise
    
    def put_object(self, key: str, body: bytes, content_type: str = None) -> bool:
        """Put object content."""
        if self._is_dummy:
            return self.client.put_object(key, body, content_type)
        else:
            try:
                extra_args = {}
                if content_type:
                    extra_args['ContentType'] = content_type
                
                self.client.put_object(
                    Bucket=settings.AWS_S3_BUCKET,
                    Key=key,
                    Body=body,
                    **extra_args
                )
                return True
            except ClientError as e:
                logger.error("Failed to put object to S3", key=key, error=str(e))
                return False
    
    def delete_object(self, key: str) -> bool:
        """Delete an object."""
        if self._is_dummy:
            return self.client.delete_object(key)
        else:
            try:
                self.client.delete_object(
                    Bucket=settings.AWS_S3_BUCKET,
                    Key=key
                )
                return True
            except ClientError as e:
                logger.error("Failed to delete object from S3", key=key, error=str(e))
                return False
    
    def list_objects(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List objects with optional prefix."""
        if self._is_dummy:
            return self.client.list_objects(prefix)
        else:
            try:
                response = self.client.list_objects_v2(
                    Bucket=settings.AWS_S3_BUCKET,
                    Prefix=prefix
                )
                return response.get('Contents', [])
            except ClientError as e:
                logger.error("Failed to list objects in S3", prefix=prefix, error=str(e))
                return []
    
    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL."""
        if self._is_dummy:
            return self.client.generate_presigned_url(key, expires_in)
        else:
            try:
                return self.client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': settings.AWS_S3_BUCKET, 'Key': key},
                    ExpiresIn=expires_in
                )
            except ClientError as e:
                logger.error("Failed to generate presigned URL", key=key, error=str(e))
                return ""


# Global client instance
_s3_client = None


def get_s3_client() -> S3Client:
    """Get the global S3 client instance."""
    global _s3_client
    if _s3_client is None:
        _s3_client = S3Client()
    return _s3_client