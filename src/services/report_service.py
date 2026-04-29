"""
Report service module.
Handles report management, upload, and approval operations.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import selectinload
from src.core import get_session
from src.core.models import Report, User
from src.utils.logger import get_logger
from src.utils.file_handler import FileHandler
from src.utils.constants import ReportStatus

logger = get_logger(__name__)


class ReportService:
    """Service for managing reports."""
    
    @staticmethod
    def create_report(
        original_filename: str,
        file_path: str,
        file_size: int,
        file_hash: str,
        uploaded_by_id: str
    ) -> Optional[Report]:
        """
        Create a new report record.
        
        Args:
            original_filename: Original filename
            file_path: Path to stored file
            file_size: File size in bytes
            file_hash: SHA256 hash of file
            uploaded_by_id: User ID who uploaded
        
        Returns:
            Created Report object or None if failed
        """
        try:
            session = get_session()
            
            # Check for duplicate file (by hash)
            existing = session.query(Report).filter_by(file_hash=file_hash).first()
            if existing:
                logger.warning(f"Duplicate file detected: {file_hash}")
                session.close()
                return None
            
            # Create new report
            report = Report(
                filename=FileHandler.generate_unique_filename(original_filename),
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                file_hash=file_hash,
                uploaded_by_id=uploaded_by_id,
                status=ReportStatus.PENDING
            )
            
            session.add(report)
            session.commit()
            
            # Refresh object to ensure all attributes are loaded before session closes
            session.refresh(report)
            
            logger.info(f"Report created: {report.id} - {original_filename}")
            session.close()
            
            return report
        
        except Exception as e:
            logger.error(f"Report creation failed: {str(e)}")
            return None
    
    @staticmethod
    def get_report_by_id(report_id: str) -> Optional[Report]:
        """
        Get report by ID.
        
        Args:
            report_id: Report ID
        
        Returns:
            Report object or None if not found
        """
        try:
            session = get_session()
            report = session.query(Report).options(
                selectinload(Report.uploaded_by_user),
                selectinload(Report.decision_by_user)
            ).filter_by(id=report_id).first()
            if report:
                session.refresh(report)  # Ensure all attributes are loaded
            session.close()
            return report
        except Exception as e:
            logger.error(f"Get report failed: {str(e)}")
            return None
    
    @staticmethod
    def get_all_reports(limit: int = 100, offset: int = 0) -> List[Report]:
        """
        Get all reports with pagination.
        
        Args:
            limit: Maximum number of reports
            offset: Number of reports to skip
        
        Returns:
            List of Report objects
        """
        try:
            session = get_session()
            reports = session.query(Report).options(
                selectinload(Report.uploaded_by_user),
                selectinload(Report.decision_by_user)
            ).order_by(
                Report.created_at.desc()
            ).limit(limit).offset(offset).all()
            session.close()
            return reports
        except Exception as e:
            logger.error(f"Get all reports failed: {str(e)}")
            return []
    
    @staticmethod
    def get_reports_by_status(status: str, limit: int = 100, offset: int = 0) -> List[Report]:
        """
        Get reports filtered by status.
        
        Args:
            status: Report status (pending, approved, rejected)
            limit: Maximum number of reports
            offset: Number of reports to skip
        
        Returns:
            List of Report objects
        """
        try:
            session = get_session()
            reports = session.query(Report).options(
                selectinload(Report.uploaded_by_user),
                selectinload(Report.decision_by_user)
            ).filter_by(status=status).order_by(
                Report.created_at.desc()
            ).limit(limit).offset(offset).all()
            session.close()
            return reports
        except Exception as e:
            logger.error(f"Get reports by status failed: {str(e)}")
            return []
    
    @staticmethod
    def get_user_reports(user_id: str, limit: int = 100, offset: int = 0) -> List[Report]:
        """
        Get reports uploaded by a specific user.
        
        Args:
            user_id: User ID
            limit: Maximum number of reports
            offset: Number of reports to skip
        
        Returns:
            List of Report objects
        """
        try:
            session = get_session()
            reports = session.query(Report).options(
                selectinload(Report.uploaded_by_user),
                selectinload(Report.decision_by_user)
            ).filter_by(uploaded_by_id=user_id).order_by(
                Report.created_at.desc()
            ).limit(limit).offset(offset).all()
            session.close()
            return reports
        except Exception as e:
            logger.error(f"Get user reports failed: {str(e)}")
            return []
    
    @staticmethod
    def approve_report(report_id: str, decision_by_id: str, comment: str = "") -> bool:
        """
        Approve a report.
        
        Args:
            report_id: Report ID
            decision_by_id: User ID making decision
            comment: Optional decision comment
        
        Returns:
            True if approved successfully, False otherwise
        """
        try:
            session = get_session()
            report = session.query(Report).filter_by(id=report_id).first()
            
            if report:
                report.status = ReportStatus.APPROVED
                report.approved_at = datetime.utcnow()
                report.decision_by_id = decision_by_id
                report.decision_comment = comment
                
                session.commit()
                session.close()
                
                logger.info(f"Report approved: {report_id}")
                return True
            
            session.close()
            return False
        
        except Exception as e:
            logger.error(f"Report approval failed: {str(e)}")
            return False
    
    @staticmethod
    def reject_report(report_id: str, decision_by_id: str, comment: str = "") -> bool:
        """
        Reject a report.
        
        Args:
            report_id: Report ID
            decision_by_id: User ID making decision
            comment: Optional rejection reason
        
        Returns:
            True if rejected successfully, False otherwise
        """
        try:
            session = get_session()
            report = session.query(Report).filter_by(id=report_id).first()
            
            if report:
                report.status = ReportStatus.REJECTED
                report.rejected_at = datetime.utcnow()
                report.decision_by_id = decision_by_id
                report.decision_comment = comment
                
                session.commit()
                session.close()
                
                logger.info(f"Report rejected: {report_id}")
                return True
            
            session.close()
            return False
        
        except Exception as e:
            logger.error(f"Report rejection failed: {str(e)}")
            return False
    
    @staticmethod
    def delete_report(report_id: str) -> bool:
        """
        Delete a report and its file.
        
        Args:
            report_id: Report ID
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            session = get_session()
            report = session.query(Report).filter_by(id=report_id).first()
            
            if report:
                # Delete file
                FileHandler.delete_file(report.file_path)
                
                # Delete record
                session.delete(report)
                session.commit()
                session.close()
                
                logger.info(f"Report deleted: {report_id}")
                return True
            
            session.close()
            return False
        
        except Exception as e:
            logger.error(f"Report deletion failed: {str(e)}")
            return False
    
    @staticmethod
    def count_reports_by_status(status: str) -> int:
        """
        Count reports by status.
        
        Args:
            status: Report status
        
        Returns:
            Count of reports with given status
        """
        try:
            session = get_session()
            count = session.query(Report).filter_by(status=status).count()
            session.close()
            return count
        except Exception as e:
            logger.error(f"Count reports failed: {str(e)}")
            return 0
    
    @staticmethod
    def get_dashboard_stats() -> dict:
        """
        Get dashboard statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            session = get_session()
            
            total = session.query(Report).count()
            pending = session.query(Report).filter_by(status=ReportStatus.PENDING).count()
            approved = session.query(Report).filter_by(status=ReportStatus.APPROVED).count()
            rejected = session.query(Report).filter_by(status=ReportStatus.REJECTED).count()
            
            session.close()
            
            return {
                'total': total,
                'pending': pending,
                'approved': approved,
                'rejected': rejected
            }
        
        except Exception as e:
            logger.error(f"Get dashboard stats failed: {str(e)}")
            return {'total': 0, 'pending': 0, 'approved': 0, 'rejected': 0}
