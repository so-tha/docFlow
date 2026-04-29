"""
Diálogo de envio para upload de arquivo de relatório.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt
from pathlib import Path
from src.services import ReportService, AuditService
from src.services.excel_comparator_service import ExcelComparatorService
from src.services.azure_auth_service import AzureAuthService
from src.ui.dialogs.azure_login_dialog import AzureLoginDialog
from src.utils.file_handler import FileHandler
from src.utils.validators import Validator
from src.utils.logger import get_logger
from src.core.config import config_obj
from src.utils.constants import AuditAction

logger = get_logger(__name__)


class UploadDialog(QDialog):
    """Diálogo para upload de arquivos de relatórios."""
    
    def __init__(self, parent=None, current_user=None):
        """
        Initialize upload dialog.
        
        Args:
            parent: Parent widget
            current_user: Currently logged-in user
        """
        super().__init__(parent)
        self.current_user = current_user
        self.selected_file = None
        self.init_ui()
    
    def init_ui(self):
        """Inicializar a interface do usuário."""
        self.setWindowTitle("Enviar Relatório")
        self.setGeometry(100, 100, 500, 300)
        self.setModal(True)
        
        # Layout principal
        layout = QVBoxLayout()
        
        # Título
        title = QLabel("Enviar Relatório")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 20px;")
        layout.addWidget(title)
        
        # Seção de informações de arquivo
        info_label = QLabel("Formatos suportados: Excel (.xlsx, .xls), CSV, PDF")
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)
        
        max_size_mb = config_obj.MAX_FILE_SIZE / (1024 * 1024)
        size_label = QLabel(f"Tamanho máximo de arquivo: {max_size_mb:.1f} MB")
        size_label.setStyleSheet("color: gray;")
        layout.addWidget(size_label)
        
        # Exibição de arquivo selecionado
        self.file_label = QLabel("Nenhum arquivo selecionado")
        self.file_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        layout.addWidget(self.file_label)
        
        # Barra de progresso (oculta por padrão)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Layout de botões
        button_layout = QHBoxLayout()
        
        select_button = QPushButton("Selecionar Arquivo")
        select_button.clicked.connect(self.on_select_file)
        button_layout.addWidget(select_button)
        
        upload_button = QPushButton("Enviar")
        upload_button.clicked.connect(self.on_upload)
        button_layout.addWidget(upload_button)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def on_select_file(self):
        """Tratar seleção de arquivo."""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self,
            "Selecionar Arquivo de Relatório",
            "",
            "Arquivos Excel (*.xlsx *.xls);;Arquivos CSV (*.csv);;Arquivos PDF (*.pdf);;Todos os Arquivos (*)"
        )
        
        if file_path:
            self.selected_file = file_path
            
            # Obter informações do arquivo
            file_name = file_path.split('/')[-1]
            file_size = FileHandler.get_file_size(file_path)
            
            if file_size:
                size_str = FileHandler.format_file_size(file_size)
                self.file_label.setText(f"📄 {file_name} ({size_str})")
            else:
                self.file_label.setText(f"📄 {file_name}")
            
            logger.info(f"Arquivo selecionado para envio: {file_path}")
    
    def on_upload(self):
        """Tratar envio de arquivo."""
        if not self.selected_file:
            QMessageBox.warning(self, "Nenhum Arquivo Selecionado", "Por favor, selecione um arquivo primeiro")
            return
        
        # Se usuário não autenticado, verificar se autenticação está habilitada
        if not self.current_user:
            if config_obj.AUTHENTICATION_ENABLED:
                # Autenticação habilitada - mostrar diálogo de login Azure AD
                logger.info("Usuário não autenticado - exibindo diálogo de login Azure AD")
                
                login_dialog = AzureLoginDialog(self)
                if login_dialog.exec():
                    self.current_user = login_dialog.get_user()
                    if not self.current_user:
                        QMessageBox.critical(self, "Autenticação Falhada", "Não foi possível autenticar usuário")
                        return
                    user_email = self.current_user.email if hasattr(self.current_user, 'email') else self.current_user.get('email', 'Usuário')
                    logger.info(f"Usuário {user_email} autenticado com sucesso")
                else:
                    logger.info("Usuário cancelou autenticação")
                    return
            else:
                # Autenticação desabilitada - usar usuário demo
                logger.info("Autenticação desabilitada - usando usuário demo")
                self.current_user = config_obj.get_demo_user()
                if not self.current_user:
                    QMessageBox.critical(self, "Erro", "Não foi possível criar sessão de usuário demo")
                    return
                user_email = self.current_user.email if hasattr(self.current_user, 'email') else self.current_user.get('email', 'Usuário')
                logger.info(f"Usando usuário demo: {user_email}")

        
        file_name = self.selected_file.split('/')[-1]
        
        # Validar extensão
        is_valid, error = Validator.validate_file_extension(
            file_name,
            config_obj.ALLOWED_EXTENSIONS
        )
        if not is_valid:
            QMessageBox.warning(self, "Tipo de Arquivo Inválido", error)
            return
        
        # Validar tamanho do arquivo
        file_size = FileHandler.get_file_size(self.selected_file)
        is_valid, error = Validator.validate_file_size(
            file_size,
            config_obj.MAX_FILE_SIZE
        )
        if not is_valid:
            QMessageBox.warning(self, "Arquivo Muito Grande", error)
            return
        
        # Exibir progresso
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(100)
        
        try:
            self.progress_bar.setValue(20)
            
            # Validar arquivo
            if not Path(self.selected_file).exists():
                raise Exception("Arquivo não encontrado")
            
            # Obter user_id
            user_id = self.current_user.id if hasattr(self.current_user, 'id') else self.current_user.get('oid', 'unknown')
            
            self.progress_bar.setValue(40)
            
            from werkzeug.datastructures import FileStorage
            from io import BytesIO
            
            with open(self.selected_file, 'rb') as f:
                file_data = f.read()
            
            file_stream = BytesIO(file_data)
            virtual_file = FileStorage(
                stream=file_stream,
                filename=file_name,
                content_type='application/octet-stream'
            )
            
            self.progress_bar.setValue(50)
            
            from app.services.report_service import ReportService
            from app.services.audit_service import AuditService
            from app import create_app
            

            app = create_app()
            
            with app.app_context():
                # ✅ Criar tabelas se não existirem
                from app.models import db, User
                db.create_all()
                
                # ✅ Garantir que usuário existe no banco
                user = User.query.get(user_id)
                if not user:
                    # Criar usuário se não existir
                    user_email = 'demo@loglife.local'
                    user_name = 'Usuário Desktop'
                    
                    if isinstance(self.current_user, dict):
                        user_email = self.current_user.get('email', user_email)
                        user_name = self.current_user.get('name', user_name)
                    else:
                        if hasattr(self.current_user, 'email'):
                            user_email = self.current_user.email
                        if hasattr(self.current_user, 'name'):
                            user_name = self.current_user.name
                    
                    user = User(
                        id=user_id,
                        email=user_email,
                        name=user_name,
                        password_hash='demo_user'
                    )
                    db.session.add(user)
                    db.session.commit()
                    logger.info(f"Usuário criado: {user_email}")
                
                report, comparison, is_duplicate = ReportService.process_uploaded_file(
                    file=virtual_file,
                    user_id=user_id,
                    sharepoint_service=None
                )
                
                self.progress_bar.setValue(70)
                
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
                
                self.progress_bar.setValue(100)
                
                # Mensagem de sucesso
                if is_duplicate:
                    QMessageBox.information(
                        self,
                        "✅ Upload Realizado (Duplicata)",
                        f"Arquivo já foi processado anteriormente.\n\n"
                        f"ID do Relatório: {report.id}\n"
                        f"Status: Pendente de Aprovação"
                    )
                    logger.info(f"Upload de duplicata realizado: {report.id}")
                else:
                    QMessageBox.information(
                        self,
                        "✅ Upload Realizado com Sucesso",
                        f"Arquivo enviado com sucesso!\n\n"
                        f"ID do Relatório: {report.id}\n"
                        f"Status: Pendente de Aprovação\n\n"
                        f"O seu relatório será comparado com o SharePoint."
                    )
                    logger.info(f"Upload realizado com sucesso: {report.id}")
                
                self.accept()
        
        except Exception as e:
            logger.error(f"Envio falhou: {str(e)}")
            QMessageBox.critical(self, "Envio Falhou", f"Erro: {str(e)}")
            self.progress_bar.setVisible(False)
