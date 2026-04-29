from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    audit_logs = db.relationship('AuditLog', lazy='dynamic')
    
    # Relacionamentos com Report serão acessados via reports.uploaded_by_user
    # Não criar relacionamento ambíguo aqui (Report tem 2 FK para User)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


class Report(db.Model):
    """Modelo de Relatório - Armazena apenas metadados e dados extraídos"""
    __tablename__ = 'reports'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer) 
    file_hash = db.Column(db.String(64))  
    
    extracted_data = db.Column(db.JSON)  
    uploaded_by_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    

    status = db.Column(db.String(20), default='pending', index=True)  
    is_locked = db.Column(db.Boolean, default=False) 
    
    approved_at = db.Column(db.DateTime)
    rejected_at = db.Column(db.DateTime)
    
    decision_by_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    decision_comment = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos explícitos para User (2 FK diferentes)
    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id], backref='reports_uploaded')
    decision_by_user = db.relationship('User', foreign_keys=[decision_by_id], backref='reports_decided')
    comparisons = db.relationship('Comparison', backref='report', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Report {self.original_filename}>'
    
    def can_modify(self):
        """Verifica se o relatório pode ser modificado"""
        return not self.is_locked
    
    def lock(self):
        """Bloqueia o relatório após decisão"""
        self.is_locked = True


class Comparison(db.Model):
    """Modelo de Comparação: Relatório vs SharePoint"""
    __tablename__ = 'comparisons'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = db.Column(db.String(36), db.ForeignKey('reports.id'), nullable=False, index=True)
    
    # Dados comparados
    differences_count = db.Column(db.Integer, default=0)
    differences_data = db.Column(db.JSON)  # {sheet: [{row, col, current, new}]}
    
    # SharePoint
    sharepoint_file_path = db.Column(db.String(500))
    sharepoint_version = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Comparison {self.report_id}>'


class AuditLog(db.Model):
    """Modelo de Auditoria: Rastreamento de todas as ações"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Ação e usuário
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    user = db.relationship('User', foreign_keys=[user_id], lazy='joined', overlaps="audit_logs")
    action = db.Column(db.String(50), nullable=False, index=True)  # upload, view_comparison, approve, reject, login, logout
    
    # Entidade envolvida
    entity_type = db.Column(db.String(50), index=True)  # report, user, comparison
    entity_id = db.Column(db.String(36), index=True)
    
    # Detalhes
    details = db.Column(db.JSON)  # {filename: ..., status: ..., differences: ...}
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user_id}>'


# Índices para otimizar queries
db.Index('idx_user_created', User.created_at)
db.Index('idx_report_created', Report.created_at)
db.Index('idx_report_status', Report.status)
db.Index('idx_audit_created', AuditLog.created_at)
db.Index('idx_audit_user_action', AuditLog.user_id, AuditLog.action)
