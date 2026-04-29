"""Rotas de Relatórios - Upload, Comparação, Aprovação"""

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, Report
from app.services import ReportService, ComparatorService, AuditService
import os

report_bp = Blueprint('report', __name__, url_prefix='/reports')

@report_bp.route('/upload-api', methods=['POST'])
def upload_api():
    try:
        # Validar arquivo
        if 'file' not in request.files:
            return jsonify({'error': 'Arquivo não fornecido'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Arquivo vazio'}), 400
        
        # Obter user_id
        user_id = request.form.get('user_id') or request.headers.get('X-User-Id')
        if not user_id:
            # Usar usuário demo se not autenticado
            from app.models import User
            demo_user = User.query.filter_by(email='demo@loglife.com').first()
            if demo_user:
                user_id = demo_user.id
            else:
                return jsonify({'error': 'Usuário não identificado'}), 401
        
        # ✅ Processar arquivo (novo fluxo JSON-only)
        report, comparison, is_duplicate = ReportService.process_uploaded_file(
            file=file,
            user_id=user_id,
            sharepoint_service=None
        )
        
        # Registrar auditoria
        if is_duplicate:
            action_type = 'upload_duplicate'
        else:
            action_type = 'upload'
        
        AuditService.log_action(
            user_id=user_id,
            action=action_type,
            entity_type='report',
            entity_id=report.id,
            details={
                'filename': report.original_filename,
                'file_size': report.file_size,
                'file_hash': report.file_hash
            }
        )
        
        return jsonify({
            'status': 'success',
            'report_id': report.id,
            'filename': report.original_filename,
            'is_duplicate': is_duplicate,
            'message': 'Arquivo duplicado' if is_duplicate else 'Upload realizado com sucesso'
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@report_bp.route('/')
@login_required
def list_reports():
    """Lista todos os relatórios"""
    page = request.args.get('page', 1, type=int)
    limit = 20
    offset = (page - 1) * limit
    
    # Caso seja admin, ver todos os relatórios. Caso contrário, apenas seus relatórios
    if current_user.email == 'admin@example.com':  # TODO: Implementar role de admin
        reports = ReportService.get_all_reports(limit=limit, offset=offset)
    else:
        reports = ReportService.get_report_by_user(current_user.id, limit=limit)
    
    formatted_reports = [ReportService.format_report(r) for r in reports]
    
    return render_template('report_list.html', reports=formatted_reports)


@report_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload de novo relatório - Extrai dados, compara com SharePoint, não salva arquivo"""
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('upload.html', error='Nenhum arquivo foi selecionado')
        
        file = request.files['file']
        
        if file.filename == '':
            return render_template('upload.html', error='Nenhum arquivo foi selecionado')
        
        try:
            # Processar arquivo: extrai dados, compara com SharePoint
            # NÃO salva arquivo localmente
            report, comparison, is_duplicate = ReportService.process_uploaded_file(
                file=file,
                user_id=current_user.id,
                sharepoint_service=None  # TODO: Integrar com SharePointService
            )
            
            # Registrar no audit
            if is_duplicate:
                # Arquivo duplicado
                AuditService.log_action(
                    user_id=current_user.id,
                    action='upload_duplicate',
                    entity_type='report',
                    entity_id=report.id,
                    details={
                        'filename': report.original_filename,
                        'file_size': report.file_size,
                        'file_hash': report.file_hash,
                        'status': 'duplicate',
                        'message': 'Arquivo já foi processado anteriormente'
                    }
                )
            else:
                # Upload novo
                AuditService.log_action(
                    user_id=current_user.id,
                    action='upload',
                    entity_type='report',
                    entity_id=report.id,
                    details={
                        'filename': report.original_filename,
                        'file_size': report.file_size,
                        'file_hash': report.file_hash,
                        'status': 'pending'
                    }
                )
            
            return redirect(url_for('report.view_report', report_id=report.id))
        
        except Exception as e:
            return render_template('upload.html', error=f"Erro ao fazer upload: {str(e)}")
    
    return render_template('upload.html')


@report_bp.route('/<report_id>')
@login_required
def view_report(report_id):
    """Exibe detalhes do relatório"""
    report = Report.query.get(report_id)
    
    if not report:
        return render_template('error.html', error='Relatório não encontrado'), 404
    
    # Verificar permissões
    if report.uploaded_by_id != current_user.id and current_user.email != 'admin@example.com':
        return render_template('error.html', error='Acesso negado'), 403
    
    formatted = ReportService.format_report(report)
    
    # Se tem comparação, buscar detalhes
    comparison = report.comparisons.first()
    if comparison:
        differences = comparison.differences_data.get('differences', [])
        by_sheet = ComparatorService.format_differences_for_display(differences)
    else:
        differences = []
        by_sheet = {}
    
    return render_template('report_view.html', 
                         report=formatted,
                         comparison=comparison,
                         differences=differences,
                         by_sheet=by_sheet)


@report_bp.route('/<report_id>/compare', methods=['POST'])
@login_required
def compare_report(report_id):
    """Compara relatório com versão SharePoint"""
    report = Report.query.get(report_id)
    
    if not report:
        return jsonify({'error': 'Relatório não encontrado'}), 404
    
    try:
        # TODO: Buscar arquivo do SharePoint
        # sharepoint_file = SharePointService.get_file_from_sharepoint(report.original_filename)
        
        # Por enquanto, usar um arquivo de exemplo
        example_file = os.path.join(current_app.config['UPLOAD_FOLDER'], 'example_old.xlsx')
        
        if not os.path.exists(example_file):
            return jsonify({'error': 'Arquivo comparativo não encontrado'}), 404
        
        # Fazer comparação
        result = ComparatorService.compare_excel_files(
            report.file_path,
            example_file,
            report_id=report_id
        )
        
        # Registrar no audit
        AuditService.log_action(
            user_id=current_user.id,
            action='view_comparison',
            entity_type='report',
            entity_id=report_id,
            details={
                'differences_count': result['differences_count'],
                'comparison_id': result['comparison_id']
            }
        )
        
        return jsonify({
            'success': True,
            'comparison_id': result['comparison_id'],
            'differences_count': result['differences_count'],
            'differences': result['differences']
        })
    
    except Exception as e:
        return jsonify({'error': f"Erro ao comparar: {str(e)}"}), 500


@report_bp.route('/<report_id>/approve', methods=['POST'])
@login_required
def approve_report(report_id):
    """Aprova um relatório"""
    report = Report.query.get(report_id)
    
    if not report:
        return jsonify({'error': 'Relatório não encontrado'}), 404
    
    try:
        comment = request.json.get('comment', '')
        
        ReportService.approve_report(report_id, current_user.id, comment)
        
        # Registrar no audit
        AuditService.log_action(
            user_id=current_user.id,
            action='approve',
            entity_type='report',
            entity_id=report_id,
            details={
                'filename': report.original_filename,
                'comment': comment
            }
        )
        
        return jsonify({'success': True, 'message': 'Relatório aprovado'})
    
    except Exception as e:
        return jsonify({'error': f"Erro ao aprovar: {str(e)}"}), 500


@report_bp.route('/<report_id>/reject', methods=['POST'])
@login_required
def reject_report(report_id):
    """Rejeita um relatório"""
    report = Report.query.get(report_id)
    
    if not report:
        return jsonify({'error': 'Relatório não encontrado'}), 404
    
    try:
        comment = request.json.get('comment', '')
        
        ReportService.reject_report(report_id, current_user.id, comment)
        
        # Registrar no audit
        AuditService.log_action(
            user_id=current_user.id,
            action='reject',
            entity_type='report',
            entity_id=report_id,
            details={
                'filename': report.original_filename,
                'comment': comment
            }
        )
        
        return jsonify({'success': True, 'message': 'Relatório rejeitado'})
    
    except Exception as e:
        return jsonify({'error': f"Erro ao rejeitar: {str(e)}"}), 500
