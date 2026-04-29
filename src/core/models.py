"""
SQLAlchemy models for Loglife application.
Defines database schemas for users, reports, comparisons, and audit logs.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from src.core.database import Base


class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(120), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for Azure AD users
    azure_id = Column(String(255), unique=True, nullable=True)  # Azure AD Object ID
    role = Column(String(50), default='user')  # 'user', 'admin', 'reviewer'
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships (placeholders - defined after Report to avoid circular reference)
    audit_logs = None  # Will set after AuditLog definition
    reports_uploaded = None  # Reports enviados por este usuário
    reports_decided = None  # Reports decididos por este usuário
    
    __table_args__ = (
        Index('idx_email_active', 'email', 'is_active'),
    )
    
    def set_password(self, password: str) -> None:
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self) -> str:
        return f'<User {self.email}>'


class Report(Base):
    """Report model for uploaded Excel/CSV files."""
    __tablename__ = 'reports'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # in bytes
    file_hash = Column(String(64), unique=True)  # SHA256
    
    # User relationship
    uploaded_by_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    
    # Status and approval
    status = Column(String(20), default='pending', index=True)  # 'pending', 'approved', 'rejected'
    is_locked = Column(Boolean, default=False)
    approved_at = Column(DateTime)
    rejected_at = Column(DateTime)
    
    # Decision metadata
    decision_by_id = Column(String(36), ForeignKey('users.id'))
    decision_comment = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - Especificar explicitamente qual FK usar
    uploaded_by_user = None  # Para quem enviou (uploaded_by_id)
    decision_by_user = None  # Para quem decidiu (decision_by_id)
    comparisons = None
    
    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f'<Report {self.original_filename}>'


class Comparison(Base):
    """Comparison model for comparing reports with SharePoint data."""
    __tablename__ = 'comparisons'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String(36), ForeignKey('reports.id'), nullable=False, index=True)
    
    # Comparison data
    differences_count = Column(Integer, default=0)
    differences_data = Column(JSON)  # {sheet: [{row, column, current_value, new_value}]}
    
    # SharePoint metadata
    sharepoint_file_path = Column(String(500))
    sharepoint_version = Column(String(50))
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships - will be configured after all models defined
    report = None
    
    def __repr__(self) -> str:
        return f'<Comparison {self.report_id}>'


class AuditLog(Base):
    """Audit log model for tracking all user actions."""
    __tablename__ = 'audit_logs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Action metadata
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    # action examples: 'login', 'logout', 'upload', 'view_comparison', 'approve', 'reject'
    
    # Details
    details = Column(JSON)  # Additional action details
    ip_address = Column(String(50))
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships - will be configured after all models defined
    user = None
    
    __table_args__ = (
        Index('idx_user_action_created', 'user_id', 'action', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f'<AuditLog {self.action} by {self.user_id}>'


# Configure relationships after all models are defined to avoid circular imports
# This fixes SQLAlchemy ambiguous relationship errors
User.audit_logs = relationship(
    'AuditLog',
    back_populates='user',
    cascade='all, delete-orphan',
    foreign_keys='AuditLog.user_id'
)

User.reports_uploaded = relationship(
    'Report',
    back_populates='uploaded_by_user',
    cascade='all, delete-orphan',
    foreign_keys='Report.uploaded_by_id',
    primaryjoin='User.id == Report.uploaded_by_id'
)

User.reports_decided = relationship(
    'Report',
    back_populates='decision_by_user',
    foreign_keys='Report.decision_by_id',
    primaryjoin='User.id == Report.decision_by_id'
)

# Configure Report relationships
Report.uploaded_by_user = relationship(
    'User',
    back_populates='reports_uploaded',
    foreign_keys='Report.uploaded_by_id',
    primaryjoin='User.id == Report.uploaded_by_id'
)

Report.decision_by_user = relationship(
    'User',
    back_populates='reports_decided',
    foreign_keys='Report.decision_by_id',
    primaryjoin='User.id == Report.decision_by_id'
)

Report.comparisons = relationship(
    'Comparison',
    back_populates='report',
    cascade='all, delete-orphan'
)

# Configure Comparison relationships
Comparison.report = relationship(
    'Report',
    back_populates='comparisons'
)

# Configure AuditLog relationships
AuditLog.user = relationship(
    'User',
    back_populates='audit_logs',
    overlaps='audit_logs'
)
