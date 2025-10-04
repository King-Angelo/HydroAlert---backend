from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc
from datetime import datetime, timedelta
from app.models.emergency_report import EmergencyReport, ReportAttachment, ReportStatus
from .base_repository import BaseRepository

class ReportRepository(BaseRepository[EmergencyReport]):
    def __init__(self):
        super().__init__(EmergencyReport)

    async def get_by_user(self, user_id: int, session: AsyncSession) -> List[EmergencyReport]:
        """Get all reports by a specific user"""
        result = await session.execute(
            select(EmergencyReport)
            .where(EmergencyReport.user_id == user_id)
            .order_by(desc(EmergencyReport.submitted_at))
        )
        return list(result.scalars().all())

    async def get_pending_reports(self, session: AsyncSession) -> List[EmergencyReport]:
        """Get all pending reports for triage"""
        result = await session.execute(
            select(EmergencyReport)
            .where(EmergencyReport.status == ReportStatus.PENDING)
            .order_by(desc(EmergencyReport.submitted_at))
        )
        return list(result.scalars().all())

    async def get_by_status(self, status: ReportStatus, session: AsyncSession) -> List[EmergencyReport]:
        """Get reports by status"""
        result = await session.execute(
            select(EmergencyReport)
            .where(EmergencyReport.status == status)
            .order_by(desc(EmergencyReport.submitted_at))
        )
        return list(result.scalars().all())

    async def get_recent_reports(self, hours: int, session: AsyncSession) -> List[EmergencyReport]:
        """Get reports from the last N hours"""
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        result = await session.execute(
            select(EmergencyReport)
            .where(EmergencyReport.submitted_at >= time_threshold)
            .order_by(desc(EmergencyReport.submitted_at))
        )
        return list(result.scalars().all())

    async def update_status(
        self, 
        report_id: int, 
        status: ReportStatus, 
        triaged_by: int, 
        notes: Optional[str],
        session: AsyncSession
    ) -> Optional[EmergencyReport]:
        """Update report status and triage information"""
        report = await self.get(report_id, session)
        if report:
            report.status = status
            report.triaged_at = datetime.utcnow()
            report.triaged_by = triaged_by
            report.triage_notes = notes
            session.add(report)
            await session.commit()
            await session.refresh(report)
            return report
        return None

class AttachmentRepository(BaseRepository[ReportAttachment]):
    def __init__(self):
        super().__init__(ReportAttachment)

    async def get_by_report(self, report_id: int, session: AsyncSession) -> List[ReportAttachment]:
        """Get all attachments for a report"""
        result = await session.execute(
            select(ReportAttachment)
            .where(ReportAttachment.report_id == report_id)
            .order_by(ReportAttachment.uploaded_at)
        )
        return list(result.scalars().all())

    async def get_by_hash(self, file_hash: str, session: AsyncSession) -> Optional[ReportAttachment]:
        """Check for duplicate files by hash"""
        result = await session.execute(
            select(ReportAttachment).where(ReportAttachment.file_hash == file_hash)
        )
        return result.scalar_one_or_none()
