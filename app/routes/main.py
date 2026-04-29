"""Rotas principais - Dashboard e páginas gerais"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.services import ReportService, AuditService
from app.models import Report

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Página inicial"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal"""
    # Dados para o dashboard
    pending_reports = ReportService.get_pending_reports(limit=5)
    recent_reports = ReportService.get_report_by_user(current_user.id, limit=10)
    recent_activity = AuditService.get_user_activity(current_user.id, limit=5)
    
    # Estatísticas
    total_reports = Report.query.count()
    pending_count = Report.query.filter_by(status='pending').count()
    approved_count = Report.query.filter_by(status='approved').count()
    
    stats = {
        'total_reports': total_reports,
        'pending': pending_count,
        'approved': approved_count,
        'rejected': total_reports - pending_count - approved_count
    }
    
    return render_template('dashboard.html',
                         pending_reports=pending_reports,
                         recent_reports=recent_reports,
                         recent_activity=recent_activity,
                         stats=stats)


@main_bp.route('/help')
def help():
    """Página de help/documentação"""
    return render_template('help.html')


from flask import redirect, url_for
