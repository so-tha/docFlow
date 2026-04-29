"""
Main application window for the desktop application.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTabWidget, QGridLayout, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from src.core.config import config_obj
from src.services import ReportService, AuditService
from src.ui.dialogs.upload_dialog import UploadDialog
from src.ui.dialogs.report_detail_dialog import ReportDetailDialog
from src.ui.widgets.report_table import ReportTable
from src.ui.widgets.audit_log_view import AuditLogView
from src.utils.constants import ReportStatus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, current_user=None):
        """
        Initialize the main window.
        
        Args:
            current_user: Currently logged-in user
        """
        super().__init__()
        self.current_user = current_user
        self.init_ui()
        
        # Auto-refresh reports every 30 seconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_dashboard)
        self.refresh_timer.start(30000)  # 30 seconds
    
    def init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle(f"{config_obj.APP_NAME} v{config_obj.APP_VERSION}")
        self.setGeometry(100, 100, config_obj.WINDOW_WIDTH, config_obj.WINDOW_HEIGHT)
        self.setMinimumSize(1000, 700)
        
        # Apply global stylesheet
        self.apply_stylesheet()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Header with user info
        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)
        
        title_label = QLabel(f"Sistema de Recebimento")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        if self.current_user:
            # Suportar tanto dict quanto objeto User
            email = self.current_user.email if hasattr(self.current_user, 'email') else self.current_user.get('email', 'Usuário')
            user_label = QLabel(f"👤 {email}")
            user_label.setStyleSheet("color: #0078D4; font-weight: bold; font-size: 12px;")
        else:
            user_label = QLabel("🔓 Não logado")
            user_label.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 12px;")
        
        header_layout.addWidget(user_label)
        
        layout.addLayout(header_layout)
        
        # Create tabs
        self.tabs = QTabWidget()
        
        # Dashboard tab
        self.dashboard_tab = QWidget()
        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        self.setup_dashboard_tab()
        
        # Reports tab
        self.reports_tab = QWidget()
        self.tabs.addTab(self.reports_tab, "📄 Relatórios")
        self.setup_reports_tab()
        
        # Audit tab
        self.audit_tab = QWidget()
        self.tabs.addTab(self.audit_tab, "📝 Logs")
        self.setup_audit_tab()
        
        layout.addWidget(self.tabs)
        
        # Set central widget layout
        central_widget.setLayout(layout)
        
        # Create menu bar
        self.create_menu_bar()
        
        logger.info("Main window initialized successfully")
    
    def apply_stylesheet(self):
        """Apply global stylesheet to the application."""
        stylesheet = """
        QWidget {
            background-color: #F5F5F5;
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 10pt;
        }
        
        QMainWindow {
            background-color: #FFFFFF;
        }
        
        QPushButton {
            background-color: #0078D4;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: 500;
            min-height: 32px;
        }
        
        QPushButton:hover {
            background-color: #1084D7;
        }
        
        QPushButton:pressed {
            background-color: #005A9E;
        }
        
        QPushButton:disabled {
            background-color: #CCCCCC;
            color: #666666;
        }
        
        QGroupBox {
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
            color: #333333;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 3px;
        }
        
        QTabWidget::pane {
            border: 1px solid #E0E0E0;
        }
        
        QTabBar::tab {
            background-color: #F0F0F0;
            color: #333333;
            padding: 8px 20px;
            border: 1px solid #E0E0E0;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #FFFFFF;
            color: #0078D4;
            border: 1px solid #E0E0E0;
            border-bottom: 2px solid #0078D4;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #EBEBEB;
        }
        
        QLabel {
            color: #333333;
        }
        
        QTableWidget {
            background-color: #FFFFFF;
            gridline-color: #E0E0E0;
            border: 1px solid #E0E0E0;
        }
        
        QTableWidget::item {
            padding: 5px;
        }
        
        QTableWidget::item:selected {
            background-color: #DCE8F7;
            color: #333333;
        }
        
        QHeaderView::section {
            background-color: #F0F0F0;
            color: #333333;
            padding: 5px;
            border: 1px solid #E0E0E0;
            font-weight: bold;
        }
        """
        self.setStyleSheet(stylesheet)
    
    def setup_dashboard_tab(self):
        """Setup the dashboard tab."""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Statistics section
        stats_group = QGroupBox("📊 Estatísticas")
        stats_group.setStyleSheet("QGroupBox { font-size: 11pt; }")
        stats_layout = QGridLayout()
        stats_layout.setSpacing(15)
        
        self.total_label = self.create_stat_label("Relatórios Totais", "0")
        self.pending_label = self.create_stat_label("Pendentes", "0", color="orange")
        self.approved_label = self.create_stat_label("Aprovados", "0", color="green")
        self.rejected_label = self.create_stat_label("Rejeitados", "0", color="red")
        
        stats_layout.addWidget(self.total_label, 0, 0)
        stats_layout.addWidget(self.pending_label, 0, 1)
        stats_layout.addWidget(self.approved_label, 0, 2)
        stats_layout.addWidget(self.rejected_label, 0, 3)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Seção de ações rápidas
        actions_group = QGroupBox("🔧 Ações Rápidas")
        actions_group.setStyleSheet("QGroupBox { font-size: 11pt; }")
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        upload_button = QPushButton("📤 Enviar Novo Relatório")
        upload_button.setMinimumWidth(150)
        upload_button.clicked.connect(self.on_upload_report)
        actions_layout.addWidget(upload_button)
        
        refresh_button = QPushButton("🔄 Atualizar")
        refresh_button.setMinimumWidth(120)
        refresh_button.clicked.connect(self.refresh_dashboard)
        actions_layout.addWidget(refresh_button)
        
        actions_layout.addStretch()
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # Seção de relatórios recentes
        recent_group = QGroupBox("📋 Relatórios Recentes")
        recent_layout = QVBoxLayout()
        
        self.recent_table = ReportTable()
        self.recent_table.report_selected.connect(self.on_report_selected)
        recent_layout.addWidget(self.recent_table)
        
        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)
        
        layout.addStretch()
        self.dashboard_tab.setLayout(layout)
        
        # Load initial data
        self.refresh_dashboard()
    
    def setup_reports_tab(self):
        """Configurar a aba de relatórios."""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Seção de filtros
        filter_group = QGroupBox("🔍 Filtros")
        filter_group.setStyleSheet("QGroupBox { font-size: 11pt; }")
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        all_button = QPushButton("Todos")
        all_button.setMinimumWidth(100)
        all_button.clicked.connect(lambda: self.reports_table.load_reports())
        filter_layout.addWidget(all_button)
        
        pending_button = QPushButton("⏳ Pendente")
        pending_button.setMinimumWidth(100)
        pending_button.clicked.connect(lambda: self.reports_table.load_reports(status=ReportStatus.PENDING))
        filter_layout.addWidget(pending_button)
        
        approved_button = QPushButton("✓ Aprovado")
        approved_button.setMinimumWidth(100)
        approved_button.clicked.connect(lambda: self.reports_table.load_reports(status=ReportStatus.APPROVED))
        filter_layout.addWidget(approved_button)
        
        rejected_button = QPushButton("✗ Rejeitado")
        rejected_button.setMinimumWidth(100)
        rejected_button.clicked.connect(lambda: self.reports_table.load_reports(status=ReportStatus.REJECTED))
        filter_layout.addWidget(rejected_button)
        
        filter_layout.addStretch()
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Tabela de relatórios
        reports_group = QGroupBox("📋 Relatórios")
        reports_group.setStyleSheet("QGroupBox { font-size: 11pt; }")
        reports_layout = QVBoxLayout()
        reports_layout.setContentsMargins(5, 5, 5, 5)
        
        self.reports_table = ReportTable()
        self.reports_table.report_selected.connect(self.on_report_selected)
        reports_layout.addWidget(self.reports_table)
        
        reports_group.setLayout(reports_layout)
        layout.addWidget(reports_group)
        
        self.reports_tab.setLayout(layout)
    
    def setup_audit_tab(self):
        """Configurar a aba de logs de auditoria."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Usar o widget AuditLogView
        audit_view = AuditLogView()
        layout.addWidget(audit_view)
        
        self.audit_tab.setLayout(layout)
    
    def create_stat_label(self, title: str, value: str, color: str = "black") -> QGroupBox:
        """
        Create a statistic label widget.
        
        Args:
            title: Statistic title
            value: Statistic value
            color: Text color
        
        Returns:
            QGroupBox with statistic
        """
        group = QGroupBox(title)
        layout = QVBoxLayout()
        
        label = QLabel(value)
        label.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {color};")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(label)
        group.setLayout(layout)
        
        return group
    
    def refresh_dashboard(self):
        """Refresh dashboard statistics and recent reports."""
        try:
            # Get statistics
            stats = ReportService.get_dashboard_stats()
            
            # Update labels
            self.total_label.findChild(QLabel).setText(str(stats['total']))
            self.pending_label.findChild(QLabel).setText(str(stats['pending']))
            self.approved_label.findChild(QLabel).setText(str(stats['approved']))
            self.rejected_label.findChild(QLabel).setText(str(stats['rejected']))
            
            # Refresh tables
            self.recent_table.refresh()
            
            logger.info("Dashboard refreshed")
        
        except Exception as e:
            logger.error(f"Failed to refresh dashboard: {str(e)}")
    
    def on_upload_report(self):
        """Handle upload report button."""
        dialog = UploadDialog(self, self.current_user)
        if dialog.exec():
            # Update current user if authenticated during upload
            if dialog.current_user and not self.current_user:
                self.current_user = dialog.current_user
                email = self.current_user.email if hasattr(self.current_user, 'email') else self.current_user.get('email', 'Usuário')
                logger.info(f"User authenticated: {email}")
                # Update header to show logged-in user
                self.init_ui()
            
            self.refresh_dashboard()
            QMessageBox.information(self, "Success", "Report uploaded successfully!")
    
    def on_report_selected(self, report_id: str):
        """
        Tratar seleção de relatório.
        
        Args:
            report_id: ID do relatório selecionado
        """
        dialog = ReportDetailDialog(self, report_id, self.current_user)
        # Conectar signal de atualização do relatório
        dialog.report_updated.connect(self.on_report_updated)
        if dialog.exec():
            self.refresh_dashboard()
            # Também atualizar a tabela de relatórios
            self.reports_table.refresh()
    
    def on_report_updated(self, report_id: str):
        """
        Lidar com atualização de relatório.
        
        Args:
            report_id: ID do relatório atualizado
        """
        self.refresh_dashboard()
        self.reports_table.refresh()
    
    def create_menu_bar(self):
        """Criar barra de menu da aplicação."""
        menubar = self.menuBar()
        
        # Menu de arquivo
        file_menu = menubar.addMenu("📁 Arquivo")
        
        upload_action = file_menu.addAction("Enviar Relatório")
        upload_action.triggered.connect(self.on_upload_report)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Sair")
        exit_action.triggered.connect(self.close)
        
        # Menu de visualização
        view_menu = menubar.addMenu("👁️ Visualizar")
        
        refresh_action = view_menu.addAction("Atualizar")
        refresh_action.triggered.connect(self.refresh_dashboard)
        
        # Menu de ajuda
        help_menu = menubar.addMenu("❓ Ajuda")
        
        about_action = help_menu.addAction("Sobre")
        about_action.triggered.connect(self.on_about)
        
        if self.current_user:
            user_email = self.current_user.email if hasattr(self.current_user, 'email') else self.current_user.get('email', 'Usuário')
            help_menu.addSeparator()
            logout_action = help_menu.addAction(f"Sair da Conta ({user_email})")
            logout_action.triggered.connect(self.on_logout)
    
    def on_about(self):
        """Exibir diálogo sobre."""
        QMessageBox.information(
            self,
            "Sobre Loglife",
            f"{config_obj.APP_NAME} v{config_obj.APP_VERSION}\n\n"
            "Aplicação desktop para gerenciamento de relatórios e auditoria.\n\n"
            "Construído com PyQt6 e SQLAlchemy"
        )
    
    def on_logout(self):
        """Tratar logout."""
        if self.current_user:
            user_id = self.current_user.id if hasattr(self.current_user, 'id') else self.current_user.get('oid', 'unknown')
            user_email = self.current_user.email if hasattr(self.current_user, 'email') else self.current_user.get('email', 'Usuário')
            AuditService.log_action(user_id, "logout")
            logger.info(f"Usuário saiu: {user_email}")
            QMessageBox.information(self, "Sucesso", "Desconectado com sucesso!")
            self.close()
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.refresh_timer.stop()
        event.accept()
