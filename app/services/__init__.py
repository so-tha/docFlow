"""Inicializador dos serviços"""

from app.services.audit_service import AuditService
from app.services.document_service import DocumentService
from app.services.comparator_service import ComparatorService

__all__ = [
    'AuditService',
    'DocumentService',
    'ComparatorService'
]
