"""
Application constants and enumerations.
"""

# User Roles
class UserRole:
    """User role constants."""
    ADMIN = 'admin'
    REVIEWER = 'reviewer'
    USER = 'user'


# Report Status
class ReportStatus:
    """Report status constants."""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'


# Audit Actions
class AuditAction:
    """Audit action constants."""
    LOGIN = 'login'
    LOGOUT = 'logout'
    UPLOAD = 'upload'
    VIEW_COMPARISON = 'view_comparison'
    APPROVE = 'approve'
    REJECT = 'reject'
    DELETE = 'delete'
    EDIT = 'edit'


# File Extensions
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'pdf'}

# Default Page Size for Data Tables
DEFAULT_PAGE_SIZE = 25

# Timeout Values (in seconds)
SESSION_TIMEOUT = 3600  # 1 hour
REQUEST_TIMEOUT = 30

# Message Types
class MessageType:
    """Message box types."""
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    SUCCESS = 'success'
