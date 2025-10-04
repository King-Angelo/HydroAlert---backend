from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.emergency_report import (
    EmergencyReport, 
    EmergencyReportCreate, 
    ReportAttachment, 
    ReportStatus
)
from app.repositories.report_repository import ReportRepository, AttachmentRepository
from app.core.file_storage import FileStorageManager
from app.core.file_validation import FileValidator
from app.core.cloud_storage import cloud_storage_service
from app.core.config import settings
from app.core.logging_config import metrics_logger
from app.websocket.websocket_service import websocket_service
from fastapi import UploadFile, HTTPException

class ReportService:
    def __init__(self):
        self.report_repo = ReportRepository()
        self.attachment_repo = AttachmentRepository()
        self.storage_manager = FileStorageManager()

    async def create_report(
        self, 
        report_data: EmergencyReportCreate, 
        user_id: int, 
        session: AsyncSession,
        submitter: Optional["User"] = None
    ) -> EmergencyReport:
        """Create a new emergency report"""
        db_report = EmergencyReport(
            user_id=user_id,
            title=report_data.title,
            description=report_data.description,
            location_lat=report_data.location_lat,
            location_lng=report_data.location_lng,
            severity=report_data.severity,
            category=report_data.category,
            contact_phone=report_data.contact_phone,
            status=ReportStatus.PENDING
        )
        
        created_report = await self.report_repo.create(db_report, session)
        
        # Notify via WebSocket if submitter is provided
        if submitter:
            await websocket_service.notify_new_report(created_report, submitter)
        
        return created_report

    async def create_attachment(
        self, 
        report_id: int, 
        file_metadata: Dict[str, Any], 
        session: AsyncSession
    ) -> ReportAttachment:
        """Create attachment record"""
        db_attachment = ReportAttachment(
            report_id=report_id,
            original_filename=file_metadata["original_filename"],
            stored_filename=file_metadata["stored_filename"],
            file_path=file_metadata["file_path"],
            file_size=file_metadata["file_size"],
            content_type=file_metadata["content_type"],
            file_hash=file_metadata["file_hash"],
            uploaded_at=file_metadata["uploaded_at"]
        )
        
        return await self.attachment_repo.create(db_attachment, session)
    
    async def upload_file_to_storage(
        self, 
        file: UploadFile, 
        report_id: int,
        file_hash: str
    ) -> Dict[str, Any]:
        """
        Upload file to storage (cloud or local based on configuration)
        
        Args:
            file: FastAPI UploadFile object
            report_id: ID of the report this file belongs to
            file_hash: SHA256 hash of the file content
            
        Returns:
            Dict containing file metadata and storage information
        """
        try:
            if settings.cloud_storage_enabled:
                # Use cloud storage
                metadata = {
                    "report_id": str(report_id),
                    "file_hash": file_hash,
                    "uploaded_by": "hydroalert_api"
                }
                
                file_info = await cloud_storage_service.save_file(
                    file, report_id, metadata
                )
                
                return {
                    "original_filename": file_info["original_filename"],
                    "stored_filename": file_info["stored_filename"],
                    "file_path": file_info["cloud_path"],  # Store cloud path
                    "public_url": file_info["public_url"],
                    "file_size": file_info["file_size"],
                    "content_type": file_info["content_type"],
                    "uploaded_at": file_info["uploaded_at"],
                    "storage_type": "cloud",
                    "bucket_name": file_info["bucket_name"]
                }
            else:
                # Use local storage (fallback)
                file_metadata = await self.storage_manager.save_upload_file(file, report_id)
                return {
                    **file_metadata,
                    "storage_type": "local"
                }
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file: {str(e)}"
            )
    
    async def delete_file_from_storage(self, file_path: str, storage_type: str = "local") -> bool:
        """
        Delete file from storage
        
        Args:
            file_path: Path to the file in storage
            storage_type: Type of storage ("cloud" or "local")
            
        Returns:
            True if file was deleted successfully, False otherwise
        """
        try:
            if storage_type == "cloud":
                return await cloud_storage_service.delete_file(file_path)
            else:
                # Local file deletion
                import os
                if os.path.exists(file_path):
                    os.remove(file_path)
                    return True
                return False
                
        except Exception as e:
            # Log error but don't raise exception to avoid breaking report deletion
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to delete file {file_path}: {str(e)}")
            return False

    async def process_file_upload(
        self, 
        file: UploadFile, 
        report_id: int, 
        session: AsyncSession
    ) -> ReportAttachment:
        """Process file upload with validation"""
        # Validate file
        validation_result = await FileValidator.validate_file(file)
        
        # Check for duplicate files
        existing_attachment = await self.attachment_repo.get_by_hash(
            validation_result["file_hash"], session
        )
        if existing_attachment:
            raise HTTPException(
                status_code=400,
                detail="File already exists in the system"
            )
        
        # Save file to storage
        file_metadata = await self.storage_manager.save_upload_file(file, report_id)
        
        # Create attachment record
        return await self.create_attachment(report_id, file_metadata, session)

    async def get_report_by_id(
        self, 
        report_id: int, 
        session: AsyncSession
    ) -> Optional[EmergencyReport]:
        """Get report by ID with attachments"""
        report = await self.report_repo.get(report_id, session)
        if report:
            # Load attachments
            report.attachments = await self.attachment_repo.get_by_report(report_id, session)
        return report

    async def get_user_reports(
        self, 
        user_id: int, 
        session: AsyncSession
    ) -> List[EmergencyReport]:
        """Get all reports for a user"""
        return await self.report_repo.get_by_user(user_id, session)

    async def get_pending_reports(self, session: AsyncSession) -> List[EmergencyReport]:
        """Get all pending reports for triage"""
        return await self.report_repo.get_pending_reports(session)

    async def triage_report(
        self, 
        report_id: int, 
        status: ReportStatus, 
        triaged_by: int, 
        notes: Optional[str],
        session: AsyncSession,
        triager: Optional["User"] = None
    ) -> Optional[EmergencyReport]:
        """Triage a report (approve/reject)"""
        # Get original report to calculate triage time
        original_report = await self.report_repo.get(report_id, session)
        
        updated_report = await self.report_repo.update_status(
            report_id, status, triaged_by, notes, session
        )
        
        # Log triage time metrics
        if updated_report and original_report:
            metrics_logger.log_triage_time(
                report_id=report_id,
                submission_time=original_report.submitted_at,
                triage_time=updated_report.triaged_at or datetime.utcnow(),
                triaged_by=triaged_by
            )
        
        # Notify via WebSocket if triager is provided
        if updated_report and triager:
            await websocket_service.notify_report_triage_update(updated_report, triager)
        
        return updated_report

    async def get_reports_by_location(
        self, 
        lat: float, 
        lng: float, 
        radius_km: float, 
        session: AsyncSession
    ) -> List[EmergencyReport]:
        """Get reports within a radius using PostGIS"""
        from app.repositories.geospatial_repository import GeospatialRepository
        
        geospatial_repo = GeospatialRepository()
        return await geospatial_repo.get_reports_within_radius(lat, lng, radius_km, session)
