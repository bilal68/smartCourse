"""Dummy S3 implementation using local filesystem."""

import os
import shutil
from pathlib import Path
from typing import Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DummyS3Client:
    """
    Mock S3 client that stores files locally.
    Mimics boto3 S3 client API but uses filesystem.
    """

    def __init__(self):
        self.storage_path = Path(settings.S3_STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info("Initialized DummyS3Client", storage_path=str(self.storage_path))

    def _get_full_path(self, key: str) -> Path:
        """Convert S3 key to local filesystem path."""
        # Remove leading slash if present
        key = key.lstrip('/')
        return self.storage_path / key

    def upload_file(self, file_path: str, key: str) -> dict:
        """
        Upload a file to local storage.
        
        Args:
            file_path: Local path to file to upload
            key: S3-style key (path) where to store the file
            
        Returns:
            dict with upload metadata
        """
        destination = self._get_full_path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(file_path, destination)
        
        logger.info("File uploaded", source=file_path, destination=str(destination))
        
        return {
            "ETag": f'"{os.path.getsize(destination)}"',  # Mock ETag
            "Location": str(destination),
            "Key": key
        }

    def download_file(self, key: str, file_path: str) -> None:
        """
        Download a file from local storage.
        
        Args:
            key: S3-style key (path) of file to download
            file_path: Local path where to save the file
        """
        source = self._get_full_path(key)
        
        if not source.exists():
            raise FileNotFoundError(f"File not found: {key}")
        
        # Ensure destination directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(source, file_path)
        
        logger.info("File downloaded", source=str(source), destination=file_path)

    def get_object(self, key: str) -> dict:
        """
        Get object metadata and content.
        
        Args:
            key: S3-style key (path) of file
            
        Returns:
            dict with Body (file content) and metadata
        """
        file_path = self._get_full_path(key)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        return {
            "Body": content,
            "ContentLength": len(content),
            "ContentType": self._guess_content_type(file_path),
            "Key": key
        }

    def put_object(self, key: str, body: bytes, content_type: Optional[str] = None) -> dict:
        """
        Put object directly from bytes.
        
        Args:
            key: S3-style key (path) where to store
            body: File content as bytes
            content_type: MIME type (optional)
            
        Returns:
            dict with upload metadata
        """
        destination = self._get_full_path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        with open(destination, 'wb') as f:
            f.write(body)
        
        logger.info("Object stored", destination=str(destination), size=len(body))
        
        return {
            "ETag": f'"{len(body)}"',
            "Location": str(destination),
            "Key": key
        }

    def delete_object(self, key: str) -> dict:
        """
        Delete a file from local storage.
        
        Args:
            key: S3-style key (path) of file to delete
            
        Returns:
            dict with deletion metadata
        """
        file_path = self._get_full_path(key)
        
        if file_path.exists():
            file_path.unlink()
            logger.info("File deleted", path=str(file_path))
        else:
            logger.warning("File not found for deletion", path=str(file_path))
        
        return {"DeleteMarker": False, "Key": key}

    def list_objects(self, prefix: str = "") -> dict:
        """
        List objects with given prefix.
        
        Args:
            prefix: Key prefix to filter by
            
        Returns:
            dict with Contents list
        """
        base_path = self._get_full_path(prefix)
        
        if not base_path.exists():
            return {"Contents": []}
        
        contents = []
        if base_path.is_file():
            # Single file
            contents.append(self._file_to_object_dict(base_path, prefix))
        else:
            # Directory - list all files recursively
            for file_path in base_path.rglob("*"):
                if file_path.is_file():
                    relative_key = str(file_path.relative_to(self.storage_path))
                    contents.append(self._file_to_object_dict(file_path, relative_key))
        
        return {"Contents": contents}

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL (in dummy mode, just returns local path).
        
        Args:
            key: S3-style key
            expiration: URL expiration in seconds (ignored in dummy mode)
            
        Returns:
            Local file path (mimics presigned URL)
        """
        file_path = self._get_full_path(key)
        return f"file://{file_path.absolute()}"

    def _file_to_object_dict(self, file_path: Path, key: str) -> dict:
        """Convert file path to S3-style object dict."""
        stat = file_path.stat()
        return {
            "Key": key,
            "Size": stat.st_size,
            "LastModified": stat.st_mtime,
            "ETag": f'"{stat.st_size}"'
        }

    def _guess_content_type(self, file_path: Path) -> str:
        """Guess MIME type from file extension."""
        suffix = file_path.suffix.lower()
        content_types = {
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.json': 'application/json',
            '.mp4': 'video/mp4',
            '.mp3': 'audio/mpeg',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
        }
        return content_types.get(suffix, 'application/octet-stream')
