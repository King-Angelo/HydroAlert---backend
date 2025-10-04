import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, BinaryIO
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings
import logging
import asyncio
from io import BytesIO

logger = logging.getLogger(__name__)

class CloudStorageService:
    """Abstract cloud storage service for file operations"""
    
    def __init__(self):
        self.bucket_name = settings.cloud_storage_bucket
        self.public_base_url = settings.cloud_storage_public_url
        self.credentials_path = settings.cloud_storage_credentials_path
        self._client = None
    
    async def _get_client(self):
        """Get or create cloud storage client"""
        if self._client is None:
            try:
                # Import here to avoid dependency issues if not using cloud storage
                from google.cloud import storage
                
                if self.credentials_path and os.path.exists(self.credentials_path):
                    # Use service account credentials
                    self._client = storage.Client.from_service_account_json(
                        self.credentials_path
                    )
                else:
                    # Use default credentials (e.g., from environment)
                    self._client = storage.Client()
                
                logger.info(f"Cloud storage client initialized for bucket: {self.bucket_name}")
            except ImportError:
                logger.error("Google Cloud Storage library not installed. Install with: pip install google-cloud-storage")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Cloud storage service not available"
                )
            except Exception as e:
                logger.error(f"Failed to initialize cloud storage client: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Cloud storage initialization failed"
                )
        
        return self._client
    
    def _generate_file_path(self, report_id: int, filename: str) -> str:
        """Generate organized file path for cloud storage"""
        now = datetime.now()
        year_month = f"{now.year}/{now.month:02d}"
        file_ext = Path(filename).suffix
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        return f"evidence/{year_month}/report_{report_id}/{unique_filename}"
    
    async def save_file(
        self, 
        file: UploadFile, 
        report_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save uploaded file to cloud storage
        
        Args:
            file: FastAPI UploadFile object
            report_id: ID of the report this file belongs to
            metadata: Optional metadata to store with the file
            
        Returns:
            Dict containing file information and public URL
        """
        try:
            client = await self._get_client()
            bucket = client.bucket(self.bucket_name)
            
            # Generate cloud storage path
            cloud_path = self._generate_file_path(report_id, file.filename)
            blob = bucket.blob(cloud_path)
            
            # Set content type
            blob.content_type = file.content_type or "application/octet-stream"
            
            # Set metadata
            if metadata:
                blob.metadata = metadata
            
            # Upload file content
            file_content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            # Upload to cloud storage
            blob.upload_from_string(
                file_content,
                content_type=file.content_type or "application/octet-stream"
            )
            
            # Make blob publicly readable (optional, depending on security requirements)
            if settings.cloud_storage_make_public:
                blob.make_public()
            
            # Generate public URL
            public_url = f"{self.public_base_url}/{cloud_path}" if self.public_base_url else blob.public_url
            
            logger.info(f"File uploaded to cloud storage: {cloud_path}")
            
            return {
                "original_filename": file.filename,
                "stored_filename": Path(cloud_path).name,
                "cloud_path": cloud_path,
                "public_url": public_url,
                "file_size": len(file_content),
                "content_type": file.content_type,
                "uploaded_at": datetime.utcnow(),
                "bucket_name": self.bucket_name
            }
            
        except Exception as e:
            logger.error(f"Failed to save file to cloud storage: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to cloud storage"
            )
    
    async def delete_file(self, cloud_path: str) -> bool:
        """
        Delete file from cloud storage
        
        Args:
            cloud_path: Path to the file in cloud storage
            
        Returns:
            True if file was deleted successfully, False otherwise
        """
        try:
            client = await self._get_client()
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(cloud_path)
            
            # Check if blob exists before attempting to delete
            if not blob.exists():
                logger.warning(f"File not found in cloud storage: {cloud_path}")
                return False
            
            # Delete the blob
            blob.delete()
            logger.info(f"File deleted from cloud storage: {cloud_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file from cloud storage: {str(e)}")
            return False
    
    async def get_file_url(self, cloud_path: str, expiration_minutes: int = 60) -> str:
        """
        Get a signed URL for accessing a file
        
        Args:
            cloud_path: Path to the file in cloud storage
            expiration_minutes: URL expiration time in minutes
            
        Returns:
            Signed URL for file access
        """
        try:
            client = await self._get_client()
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(cloud_path)
            
            # Generate signed URL
            url = blob.generate_signed_url(
                expiration=datetime.utcnow().timestamp() + (expiration_minutes * 60),
                method="GET"
            )
            
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate signed URL for file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate file access URL"
            )
    
    async def file_exists(self, cloud_path: str) -> bool:
        """
        Check if a file exists in cloud storage
        
        Args:
            cloud_path: Path to the file in cloud storage
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            client = await self._get_client()
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(cloud_path)
            return blob.exists()
            
        except Exception as e:
            logger.error(f"Failed to check file existence: {str(e)}")
            return False
    
    async def get_file_metadata(self, cloud_path: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata from cloud storage
        
        Args:
            cloud_path: Path to the file in cloud storage
            
        Returns:
            Dict containing file metadata or None if file doesn't exist
        """
        try:
            client = await self._get_client()
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(cloud_path)
            
            if not blob.exists():
                return None
            
            blob.reload()  # Refresh blob metadata
            
            return {
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "created": blob.time_created,
                "updated": blob.updated,
                "metadata": blob.metadata or {}
            }
            
        except Exception as e:
            logger.error(f"Failed to get file metadata: {str(e)}")
            return None

# Global cloud storage service instance
cloud_storage_service = CloudStorageService()
