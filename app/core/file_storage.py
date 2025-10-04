import os
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from fastapi import UploadFile, HTTPException
import aiofiles

class FileStorageManager:
    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = Path(base_dir)
        self.evidence_dir = self.base_dir / "evidence"
        self.temp_dir = self.base_dir / "temp"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories"""
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_file_path(self, report_id: int, filename: str) -> Path:
        """Generate organized file path"""
        now = datetime.now()
        year_month = f"{now.year}/{now.month:02d}"
        report_dir = self.evidence_dir / year_month / f"report_{report_id}"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_ext = Path(filename).suffix
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        return report_dir / unique_filename
    
    async def save_upload_file(self, file: UploadFile, report_id: int) -> Dict:
        """Save uploaded file and return metadata"""
        file_path = self.generate_file_path(report_id, file.filename)
        
        # Read file content
        content = await file.read()
        
        # Generate file hash
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Save file
        async with aiofiles.open(file_path, "wb") as buffer:
            await buffer.write(content)
        
        return {
            "original_filename": file.filename,
            "stored_filename": file_path.name,
            "file_path": str(file_path),
            "file_size": len(content),
            "content_type": file.content_type,
            "file_hash": file_hash,
            "uploaded_at": datetime.utcnow()
        }
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def get_file_url(self, file_path: str) -> str:
        """Generate file URL for serving"""
        # In production, this would be a CDN URL
        return f"/uploads/{Path(file_path).relative_to(self.base_dir)}"
