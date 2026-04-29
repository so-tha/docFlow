"""Rotas de Auditoria - Histórico de ações dos usuários"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.services import AuditService
from app.models import AuditLog

audit_bp = Blueprint('audit', __name__, url_prefix='/audit')


@audit_bp.route('/')
@login_required
def logs():
    """Lista logs de auditoria"""
    page = request.args.get('page', 1, type=int)
    limit = 50
    offset = (page - 1) * limit
    
    all_logs = AuditService.get_all_logs(limit=limit, offset=offset)
    formatted_logs = [AuditService.format_log(log) for log in all_logs]
    
    return render_template('audit_logs.html', logs=formatted_logs)


@audit_bp.route('/user/<user_id>')
@login_required
def user_activity(user_id):
    """Histórico de atividades de um usuário"""
    user_logs = AuditService.get_user_activity(user_id, limit=100)
    formatted_logs = [AuditService.format_log(log) for log in user_logs]
    
    return render_template('user_activity.html', 
                         user_id=user_id,
                         logs=formatted_logs)


@audit_bp.route('/report/<report_id>')
@login_required
def report_timeline(report_id):
    """Timeline completa de um relatório"""
    timeline = AuditService.get_report_timeline(report_id)
    formatted_logs = [AuditService.format_log(log) for log in timeline]
    
    return render_template('report_timeline.html',
                         report_id=report_id,
                         timeline=formatted_logs)


@audit_bp.route('/action/<action>')
@login_required
def action_history(action):
    """Histórico de uma ação específica"""
    logs = AuditService.get_action_history(action, limit=100)
    formatted_logs = [AuditService.format_log(log) for log in logs]
    
    return render_template('action_history.html',
                         action=action,
                         logs=formatted_logs)


@audit_bp.route('/uploads')
@login_required
def upload_history():
    """Histórico de uploads"""
    logs = AuditService.get_action_history('upload', limit=200)
    formatted_logs = [AuditService.format_log(log) for log in logs]
    
    return render_template('audit_uploads.html', logs=formatted_logs)


@audit_bp.route('/api/logs')
@login_required
def api_logs():
    """API para retornar logs em JSON"""
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    
    limit = 50
    offset = (page - 1) * limit
    
    query = AuditLog.query
    
    if action_filter:
        query = query.filter_by(action=action_filter)
    
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset).all()
    total = query.count()
    
    formatted_logs = [AuditService.format_log(log) for log in logs]
    
    return jsonify({
        'logs': formatted_logs,
        'total': total,
        'page': page,
        'per_page': limit
    })
