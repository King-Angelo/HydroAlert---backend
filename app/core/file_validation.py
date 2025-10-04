import hashlib
from pathlib import Path
from typing import Dict, Optional
from fastapi import HTTPException, UploadFile

class FileValidator:
    ALLOWED_MIME_TYPES = [
        "image/jpeg",
        "image/png", 
        "image/webp",
        "image/gif"
    ]
    
    ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_FILES_PER_REPORT = 5
    
    @classmethod
    async def validate_file(cls, file: UploadFile) -> Dict:
        """Comprehensive file validation"""
        # Check file size
        if file.size and file.size > cls.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds 10MB limit"
            )
        
        # Check file extension
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )
            
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in cls.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not allowed. Allowed: {cls.ALLOWED_EXTENSIONS}"
            )
        
        # Read file content for validation
        content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        # Check actual file size
        if len(content) > cls.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds 10MB limit"
            )
        
        # Validate MIME type (basic check)
        if file.content_type and file.content_type not in cls.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file.content_type} not allowed"
            )
        
        # Generate file hash for duplicate detection
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Check for malicious content (basic)
        if cls._contains_malicious_content(content):
            raise HTTPException(
                status_code=400,
                detail="File contains potentially malicious content"
            )
        
        return {
            "filename": file.filename,
            "size": len(content),
            "mime_type": file.content_type,
            "file_hash": file_hash,
            "is_valid": True
        }
    
    @classmethod
    def _contains_malicious_content(cls, content: bytes) -> bool:
        """Basic malicious content detection"""
        # Check for executable signatures
        executable_signatures = [
            b'\x4d\x5a',  # PE executable
            b'\x7f\x45\x4c\x46',  # ELF executable
            b'<script',  # JavaScript
            b'javascript:',  # JavaScript protocol
        ]
        
        content_lower = content.lower()
        for signature in executable_signatures:
            if signature in content_lower:
                return True
        
        return False
    
    @classmethod
    def validate_file_count(cls, file_count: int) -> None:
        """Validate number of files"""
        if file_count > cls.MAX_FILES_PER_REPORT:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {cls.MAX_FILES_PER_REPORT} files allowed per report"
            )
