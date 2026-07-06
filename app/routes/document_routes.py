from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_required, current_user
from app.models import db, Document, DocumentVersion, Comparison
from app.services.document_service import DocumentService
from app.services.comparator_service import ComparatorService
from app.services.audit_service import AuditService
document_bp = Blueprint('document', __name__, url_prefix='/documents')

@document_bp.route('/')
@login_required
def list_documents():
    documents = DocumentService.get_all_documents()
    return render_template('document_list.html', documents=documents)

@document_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo enviado', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Selecione um arquivo', 'error')
            return redirect(request.url)
        upload_type = request.form.get('upload_type')
        document_id = request.form.get('document_id')
        document_name = request.form.get('document_name')
        try:
            if upload_type == 'new':
                if not document_name or document_name.strip() == '':
                    flash('Digite um nome para o novo documento', 'error')
                    return redirect(request.url)
                version, comparison, is_duplicate = DocumentService.process_uploaded_file(file=file, user_id=current_user.id, document_name=document_name.strip())
            else:
                if not document_id:
                    flash('Selecione um documento existente', 'error')
                    return redirect(request.url)
                version, comparison, is_duplicate = DocumentService.process_uploaded_file(file=file, user_id=current_user.id, document_id=document_id)
            action_name = 'upload_duplicate' if is_duplicate else 'upload'
            AuditService.log_action(user_id=current_user.id, action=action_name, entity_type='document_version', entity_id=version.id, details={'document_name': version.document.name, 'filename': version.original_filename, 'version': version.version_number, 'file_size': version.file_size})
            if is_duplicate:
                flash(f'Este arquivo é idêntico a uma versão já enviada (v{version.version_number})!', 'info')
            else:
                flash(f'Versão {version.version_number} enviada com sucesso!', 'success')
            return redirect(url_for('document.view_version', version_id=version.id))
        except Exception as e:
            flash(f'Erro ao processar upload: {str(e)}', 'error')
            return redirect(request.url)
    documents = DocumentService.get_all_documents()
    selected_doc_id = request.args.get('document_id', '')
    return render_template('upload.html', documents=documents, selected_doc_id=selected_doc_id)

@document_bp.route('/version/<version_id>')
@login_required
def view_version(version_id):
    version = DocumentVersion.query.get(version_id)
    if not version:
        flash('Versão não encontrada', 'error')
        return redirect(url_for('document.list_documents'))
    formatted = DocumentService.format_version(version)
    extracted_data = version.extracted_data or {}
    comparison = version.comparisons.first()
    if comparison:
        differences = comparison.differences_data.get('differences', [])
        by_sheet = ComparatorService.format_differences_for_display(differences)
    else:
        differences = []
        by_sheet = {}
    return render_template('report_view.html', version=formatted, extracted_data=extracted_data, comparison=comparison, differences=differences, by_sheet=by_sheet)

@document_bp.route('/version/<version_id>/approve', methods=['POST'])
@login_required
def approve(version_id):
    try:
        comment = request.json.get('comment', '')
        version = DocumentService.approve_version(version_id, current_user.id, comment)
        AuditService.log_action(user_id=current_user.id, action='approve', entity_type='document_version', entity_id=version_id, details={'document_name': version.document.name, 'version': version.version_number, 'comment': comment})
        return jsonify({'success': True, 'message': 'Versão aprovada com sucesso!'})
    except Exception as e:
        return (jsonify({'error': str(e)}), 500)

@document_bp.route('/version/<version_id>/reject', methods=['POST'])
@login_required
def reject(version_id):
    try:
        comment = request.json.get('comment', '')
        version = DocumentService.reject_version(version_id, current_user.id, comment)
        AuditService.log_action(user_id=current_user.id, action='reject', entity_type='document_version', entity_id=version_id, details={'document_name': version.document.name, 'version': version.version_number, 'comment': comment})
        return jsonify({'success': True, 'message': 'Versão rejeitada.'})
    except Exception as e:
        return (jsonify({'error': str(e)}), 500)

@document_bp.route('/<document_id>')
@login_required
def view_document(document_id):
    document = Document.query.get(document_id)
    if not document:
        flash('Documento não encontrado', 'error')
        return redirect(url_for('document.list_documents'))
    versions = document.versions.order_by(DocumentVersion.version_number.desc()).all()
    formatted_versions = [DocumentService.format_version(v) for v in versions]
    return render_template('document_history.html', document=document, versions=formatted_versions)