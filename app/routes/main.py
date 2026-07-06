from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.services import DocumentService, AuditService
from app.models import Document, DocumentVersion
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    pending_versions = DocumentVersion.query.filter_by(status='pending').order_by(DocumentVersion.created_at.desc()).limit(5).all()
    formatted_pending = [DocumentService.format_version(v) for v in pending_versions]
    recent_versions = DocumentVersion.query.filter_by(uploaded_by_id=current_user.id).order_by(DocumentVersion.created_at.desc()).limit(10).all()
    formatted_recent = [DocumentService.format_version(v) for v in recent_versions]
    recent_activity = AuditService.get_user_activity(current_user.id, limit=5)
    formatted_activity = [AuditService.format_log(log) for log in recent_activity]
    total_docs = Document.query.count()
    pending_count = DocumentVersion.query.filter_by(status='pending').count()
    approved_count = DocumentVersion.query.filter_by(status='approved').count()
    rejected_count = DocumentVersion.query.filter_by(status='rejected').count()
    stats = {'total_documents': total_docs, 'pending_versions': pending_count, 'approved_versions': approved_count, 'rejected_versions': rejected_count}
    return render_template('dashboard.html', pending_reports=formatted_pending, recent_reports=formatted_recent, recent_activity=formatted_activity, stats=stats)

@main_bp.route('/help')
def help():
    return render_template('help.html')