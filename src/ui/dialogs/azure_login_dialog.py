"""
Azure AD Login Dialog for Loglife Desktop Application.
Uses MSAL for enterprise authentication via Microsoft Entra ID.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from src.services.azure_auth_service import AzureAuthService
from src.core.config import config_obj
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AzureLoginDialog(QDialog):
    """Login dialog using Azure AD (Enterprise Authentication)."""
    
    # Signal emitted on successful authentication
    authentication_successful = pyqtSignal(object)  # Emits User object
    
    def __init__(self, parent=None):
        """
        Initialize Azure AD login dialog.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        
        # Only initialize auth service if authentication is enabled
        self.auth_service = None
        if config_obj.AUTHENTICATION_ENABLED:
            try:
                self.auth_service = AzureAuthService()
            except ValueError as e:
                logger.warning(f"Could not initialize auth service: {e}")
        
        self.user = None
        self.init_ui()
    
    def init_ui(self) -> None:
        """Initialize user interface."""
        self.setWindowTitle('Loglife - Azure AD Login')
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1084d7;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Logo/Title
        title = QLabel('Loglife')
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel('Gerenciamento de Relatórios Corporativo')
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle.setFont(subtitle_font)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)
        
        layout.addSpacing(30)
        
        # Info text
        info = QLabel(
            'Faça login usando sua conta corporativa Microsoft.\n\n'
            'Uma janela do navegador será aberta para autenticação segura.'
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: #555; line-height: 1.5;")
        layout.addWidget(info)
        
        layout.addSpacing(20)
        
        # Login button
        login_btn = QPushButton('🔐 Entrar com Azure AD')
        login_btn.setMinimumHeight(50)
        login_btn.clicked.connect(self.on_login_clicked)
        layout.addWidget(login_btn)
        
        # Help text
        help_text = QLabel(
            '💡 Dica: Use sua conta do @seudominio.com.br\n'
            'Suporte: contato@empresa.com.br'
        )
        help_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_text.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(help_text)
        
        layout.addStretch()
        
        self.setLayout(layout)
    
    def on_login_clicked(self) -> None:
        """Handle login button click - open browser for Azure AD authentication."""
        try:
            # If authentication is disabled, use demo user
            if not config_obj.AUTHENTICATION_ENABLED:
                logger.info("Authentication disabled - loading demo user")
                self.user = config_obj.get_demo_user()
                
                if self.user:
                    logger.info(f"Demo user loaded: {self.user.email}")
                    QMessageBox.information(
                        self,
                        'Modo Demo',
                        f'Usando conta de demonstração: {self.user.email}\n\n'
                        f'Para ativar autenticação Azure AD, configure AUTH_ENABLED=true no .env'
                    )
                    self.authentication_successful.emit(self.user)
                    self.accept()
                else:
                    logger.error("Failed to load demo user")
                    QMessageBox.critical(
                        self,
                        'Erro',
                        'Não foi possível carregar o usuário de demonstração.\n\n'
                        'Verifique os logs para mais detalhes.'
                    )
                return
            
            # Show info message
            QMessageBox.information(
                self,
                'Autenticação',
                'Uma janela do navegador será aberta.\n\n'
                'Faça login com sua conta corporativa Microsoft.'
            )
            
            # Acquire token via interactive browser
            result = self.auth_service.acquire_token_interactive()
            
            if result and 'access_token' in result:
                # Authenticate user and sync with database
                self.user = self.auth_service.authenticate_user(result['access_token'])
                
                if self.user:
                    logger.info(f"User {self.user.email} authenticated via Azure AD")
                    
                    # Emit signal and accept dialog
                    self.authentication_successful.emit(self.user)
                    self.accept()
                else:
                    QMessageBox.warning(
                        self,
                        'Erro',
                        'Erro ao sincronizar usuário com o banco de dados.\n\n'
                        'Contate o administrador.'
                    )
                    logger.error("Failed to sync user from Azure AD")
            else:
                error = result.get('error', 'Autenticação cancelada') if result else 'Autenticação cancelada'
                logger.warning(f"Azure AD login failed: {error}")
                
                # If user cancelled, just close the dialog
                if error != 'Autenticação cancelada':
                    QMessageBox.warning(
                        self,
                        'Erro de Autenticação',
                        f'Falha na autenticação:\n\n{error}'
                    )
        
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            QMessageBox.critical(
                self,
                'Erro',
                f'Erro durante autenticação:\n\n{str(e)}'
            )
    
    def get_user(self) -> object:
        """
        Get authenticated user.
        
        Returns:
            User object from database, or None if not authenticated.
        """
        return self.user
