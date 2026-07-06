from app.models import db, AuditLog, User
from datetime import datetime
from flask import request

class AuditService:

    @staticmethod
    def log_action(user_id, action, entity_type=None, entity_id=None, details=None):
        try:
            log = AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details or {}, ip_address=request.remote_addr if request else None, user_agent=request.headers.get('User-Agent') if request else None)
            db.session.add(log)
            db.session.commit()
            return log
        except Exception as e:
            db.session.rollback()
            print(f'Erro ao registrar auditoria: {str(e)}')
            return None

    @staticmethod
    def get_user_activity(user_id, limit=50):
        return AuditLog.query.filter_by(user_id=user_id).order_by(AuditLog.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_action_history(action, limit=50):
        return AuditLog.query.filter_by(action=action).order_by(AuditLog.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_entity_history(entity_type, entity_id):
        return AuditLog.query.filter_by(entity_type=entity_type, entity_id=entity_id).order_by(AuditLog.created_at.desc()).all()

    @staticmethod
    def get_all_logs(limit=100, offset=0):
        from sqlalchemy.orm import joinedload
        return AuditLog.query.options(joinedload(AuditLog.user)).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset).all()

    @staticmethod
    def get_report_timeline(report_id):
        return AuditLog.query.filter(AuditLog.entity_type == 'report', AuditLog.entity_id == report_id).order_by(AuditLog.created_at.asc()).all()

    @staticmethod
    def format_log(log):
        if hasattr(log, 'user') and log.user:
            user = log.user
        else:
            user = User.query.get(log.user_id)
        filename = 'N/A'
        file_size = None
        if log.details and 'filename' in log.details:
            filename = log.details['filename']
        if log.details and 'file_size' in log.details:
            file_size = log.details['file_size']
        return {'id': log.id, 'user_name': user.name if user else 'Desconhecido', 'user_email': user.email if user else 'N/A', 'action': log.action, 'entity_type': log.entity_type, 'entity_id': log.entity_id, 'details': log.details, 'filename': filename, 'file_size': file_size, 'created_at': log.created_at.isoformat(), 'created_at_formatted': log.created_at.strftime('%d/%m/%Y %H:%M:%S'), 'ip_address': log.ip_address}