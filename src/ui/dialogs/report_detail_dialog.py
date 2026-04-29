"""
Report detail dialog for viewing and managing individual reports.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, 
    QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from src.services import ReportService, AuditService
from src.ui.dialogs.azure_login_dialog import AzureLoginDialog
from src.core.config import config_obj
from src.utils.logger import get_logger
from src.utils.constants import AuditAction, ReportStatus
from src.utils.file_handler import FileHandler

logger = get_logger(__name__)


class ReportDetailDialog(QDialog):
    """Dialog for viewing and managing report details."""
    
    # Signal quando um relatório foi aprovado ou rejeitado
    report_updated = pyqtSignal(str)  # report_id
    
    def __init__(self, parent=None, report_id: str = None, current_user=None):
        """
        Initialize report detail dialog.
        
        Args:
            parent: Parent widget
            report_id: Report ID to display
            current_user: Currently logged-in user
        """
        super().__init__(parent)
        self.report_id = report_id
        self.report = None
        self.current_user = current_user
        self.init_ui()
        
        if report_id:
            self.load_report()
    
    def init_ui(self):
        """Inicializar a interface do usuário."""
        self.setWindowTitle("Detalhes do Relatório")
        self.setGeometry(100, 100, 700, 600)
        self.setModal(True)
        
        # Main layout
        layout = QVBoxLayout()
        
        # Título
        self.title = QLabel("Detalhes do Relatório")
        self.title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 20px;")
        layout.addWidget(self.title)
        
        # Seção de informações
        info_layout = QHBoxLayout()
        
        info_group = QGroupBox("Informações")
        info_group_layout = QVBoxLayout()
        
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        info_group_layout.addWidget(self.info_label)
        
        info_group.setLayout(info_group_layout)
        info_layout.addWidget(info_group)
        layout.addLayout(info_layout)
        
        # Seção de comentário/observações
        comment_group = QGroupBox("Comentário da Decisão")
        comment_layout = QVBoxLayout()
        
        self.comment_input = QTextEdit()
        self.comment_input.setPlaceholderText("Digite seu comentário de decisão aqui...")
        self.comment_input.setMaximumHeight(150)
        comment_layout.addWidget(self.comment_input)
        
        comment_group.setLayout(comment_layout)
        layout.addWidget(comment_group)
        
        # Layout de botões
        button_layout = QHBoxLayout()
        
        open_button = QPushButton("Abrir Arquivo")
        open_button.clicked.connect(self.on_open_file)
        button_layout.addWidget(open_button)
        
        button_layout.addStretch()
        
        approve_button = QPushButton("✓ Aprovar")
        approve_button.setStyleSheet("background-color: #00AA00; color: white; padding: 10px;")
        approve_button.clicked.connect(self.on_approve)
        button_layout.addWidget(approve_button)
        
        reject_button = QPushButton("✗ Rejeitar")
        reject_button.setStyleSheet("background-color: #FF0000; color: white; padding: 10px;")
        reject_button.clicked.connect(self.on_reject)
        button_layout.addWidget(reject_button)
        
        close_button = QPushButton("Fechar")
        close_button.clicked.connect(self.reject)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_report(self):
        """Load and display report details."""
        if not self.report_id:
            return
        
        self.report = ReportService.get_report_by_id(self.report_id)
        
        if not self.report:
            QMessageBox.critical(self, "Error", "Report not found")
            self.reject()
            return
        
        # Build info text
        size_str = FileHandler.format_file_size(self.report.file_size or 0)
        
        info_text = f"""
<b>Report ID:</b> {self.report.id}<br>
<b>Filename:</b> {self.report.original_filename}<br>
<b>File Size:</b> {size_str}<br>
<b>Status:</b> <font color="{'green' if self.report.status == 'approved' else 'red' if self.report.status == 'rejected' else 'orange'}">{self.report.status.upper()}</font><br>
<br>
<b>Uploaded By:</b> {self.report.uploaded_by_user.email if self.report.uploaded_by_user else 'Unknown'}<br>
<b>Uploaded At:</b> {self.report.created_at.strftime("%Y-%m-%d %H:%M:%S")}<br>
<br>
<b>File Hash:</b> {self.report.file_hash[:16]}...<br>
        """
        
        # Add decision info if already decided
        if self.report.decision_by_user:
            info_text += f"""
<b>Decision By:</b> {self.report.decision_by_user.email}<br>
<b>Decision Comment:</b> {self.report.decision_comment or 'No comment'}<br>
            """
            
            # Pre-fill comment if showing existing decision
            if self.report.decision_comment:
                self.comment_input.setText(self.report.decision_comment)
        
        self.info_label.setText(info_text)
        self.title.setText(f"Report: {self.report.original_filename}")
        
        logger.info(f"Loaded report details: {self.report_id}")
    
    def on_open_file(self):
        """Open the report file with default application."""
        if not self.report:
            QMessageBox.warning(self, "Error", "No report loaded")
            return
        
        import os
        import subprocess
        
        file_path = self.report.file_path
        
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Erro", f"Arquivo não encontrado: {file_path}")
            return
        
        try:
            # Abrir baseado no SO
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # Linux/Mac
                subprocess.Popen(['xdg-open' if os.uname().sysname == 'Linux' else 'open', file_path])
            
            logger.info(f"Arquivo aberto: {file_path}")
        
        except Exception as e:
            logger.error(f"Falha ao abrir arquivo: {str(e)}")
            QMessageBox.critical(self, "Erro", f"Não foi possível abrir arquivo: {str(e)}")
    
    def on_approve(self):
        """Aprovar o relatório."""
        if not self.report:
            QMessageBox.warning(self, "Erro", "Nenhum relatório carregado")
            return
        
        # Se usuário não autenticado, verificar se autenticação está habilitada
        if not self.current_user:
            if config_obj.AUTHENTICATION_ENABLED:
                logger.info("Usuário não autenticado - exibindo dialog de login Azure AD para aprovação")
                
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
                logger.info("Autenticação desabilitada - usando usuário demo para aprovação")
                self.current_user = config_obj.get_demo_user()
                if not self.current_user:
                    QMessageBox.critical(self, "Erro", "Não foi possível criar sessão de usuário demo")
                    return
                user_email = self.current_user.email if hasattr(self.current_user, 'email') else self.current_user.get('email', 'Usuário')
                logger.info(f"Usando usuário demo: {user_email}")

        # Obter comentário
        comment = self.comment_input.toPlainText().strip()
        
        # Obter user_id (dict ou objeto)
        user_id = self.current_user.id if hasattr(self.current_user, 'id') else self.current_user.get('oid', 'unknown')
        
        # Aprovar relatório
        success = ReportService.approve_report(
            self.report.id,
            user_id,
            comment
        )
        
        if success:
            # Log de ação
            AuditService.log_action(
                user_id=user_id,
                action=AuditAction.APPROVE,
                details={
                    'report_id': self.report.id,
                    'filename': self.report.original_filename,
                    'comment': comment
                }
            )
            
            logger.info(f"Relatório aprovado: {self.report.id}")
            QMessageBox.information(self, "Sucesso", "Relatório aprovado com sucesso!")
            self.report_updated.emit(self.report.id)  # Emitir sinal de atualização
            self.accept()
        else:
            logger.error(f"Falha ao aprovar relatório: {self.report.id}")
            QMessageBox.critical(self, "Erro", "Falha ao aprovar relatório")
    
    def on_reject(self):
        """Rejeitar o relatório."""
        if not self.report:
            QMessageBox.warning(self, "Erro", "Nenhum relatório carregado")
            return
        
        # Se usuário não autenticado, verificar se autenticação está habilitada
        if not self.current_user:
            if config_obj.AUTHENTICATION_ENABLED:
                logger.info("Usuário não autenticado - exibindo dialog de login Azure AD para rejeição")
                
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
                logger.info("Autenticação desabilitada - usando usuário demo para rejeição")
                self.current_user = config_obj.get_demo_user()
                if not self.current_user:
                    QMessageBox.critical(self, "Erro", "Não foi possível criar sessão de usuário demo")
                    return
                user_email = self.current_user.email if hasattr(self.current_user, 'email') else self.current_user.get('email', 'Usuário')
                logger.info(f"Usando usuário demo: {user_email}")
        
        comment = self.comment_input.toPlainText().strip()
        
        if not comment:
            QMessageBox.warning(self, "Obrigatório", "Por favor, forneça um motivo para rejeição")
            return
        
        # Obter user_id (dict ou objeto)
        user_id = self.current_user.id if hasattr(self.current_user, 'id') else self.current_user.get('oid', 'unknown')
        
        # Rejeitar relatório
        success = ReportService.reject_report(
            self.report.id,
            user_id,
            comment
        )
        
        if success:
            # Log de ação
            AuditService.log_action(
                user_id=user_id,
                action=AuditAction.REJECT,
                details={
                    'report_id': self.report.id,
                    'filename': self.report.original_filename,
                    'reason': comment
                }
            )
            
            logger.info(f"Relatório rejeitado: {self.report.id}")
            QMessageBox.information(self, "Sucesso", "Relatório rejeitado com sucesso!")
            self.report_updated.emit(self.report.id)  # Emitir sinal de atualização
            self.accept()
        else:
            logger.error(f"Falha ao rejeitar relatório: {self.report.id}")
            QMessageBox.critical(self, "Erro", "Falha ao rejeitar relatório")
