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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(120), nullable=False, index=True)
    created_by_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='documents')
    versions = db.relationship('DocumentVersion', backref='document', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Document {self.name}>'

    def get_latest_version(self):
        return self.versions.order_by(DocumentVersion.version_number.desc()).first()

    def get_latest_approved_version(self):
        return self.versions.filter_by(status='approved').order_by(DocumentVersion.version_number.desc()).first()

class DocumentVersion(db.Model):
    __tablename__ = 'document_versions'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id'), nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False)
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
    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id], backref='versions_uploaded')
    decision_by_user = db.relationship('User', foreign_keys=[decision_by_id], backref='versions_decided')
    comparisons = db.relationship('Comparison', foreign_keys='Comparison.document_version_id', backref='version', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<DocumentVersion {self.original_filename} v{self.version_number}>'

    def can_modify(self):
        return not self.is_locked

    def lock(self):
        self.is_locked = True

class Comparison(db.Model):
    __tablename__ = 'comparisons'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_version_id = db.Column(db.String(36), db.ForeignKey('document_versions.id'), nullable=False, index=True)
    compare_version_id = db.Column(db.String(36), db.ForeignKey('document_versions.id'), nullable=True)
    differences_count = db.Column(db.Integer, default=0)
    differences_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    compare_version = db.relationship('DocumentVersion', foreign_keys=[compare_version_id])

    def __repr__(self):
        return f'<Comparison {self.id} for version {self.document_version_id}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    user = db.relationship('User', foreign_keys=[user_id], lazy='joined', overlaps='audit_logs')
    action = db.Column(db.String(50), nullable=False, index=True)
    entity_type = db.Column(db.String(50), index=True)
    entity_id = db.Column(db.String(36), index=True)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user_id}>'
db.Index('idx_user_created', User.created_at)
db.Index('idx_document_created', Document.created_at)
db.Index('idx_version_created', DocumentVersion.created_at)
db.Index('idx_version_status', DocumentVersion.status)
db.Index('idx_audit_created', AuditLog.created_at)
db.Index('idx_audit_user_action', AuditLog.user_id, AuditLog.action)