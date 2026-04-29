"""
Login dialog for user authentication.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from src.services import AuthenticationService, AuditService
from src.utils.logger import get_logger
from src.utils.validators import Validator

logger = get_logger(__name__)


class LoginDialog(QDialog):
    """Login dialog for authentication."""
    
    def __init__(self, parent=None):
        """Initialize login dialog."""
        super().__init__(parent)
        self.current_user = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Loglife - Login")
        self.setGeometry(100, 100, 400, 200)
        self.setModal(True)
        
        # Main layout
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Login")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 20px;")
        layout.addWidget(title)
        
        # Email field
        email_label = QLabel("Email:")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("user@example.com")
        layout.addWidget(email_label)
        layout.addWidget(self.email_input)
        
        # Password field
        password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter your password")
        layout.addWidget(password_label)
        layout.addWidget(self.password_input)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        
        login_button = QPushButton("Login")
        login_button.clicked.connect(self.on_login)
        button_layout.addWidget(login_button)
        
        register_button = QPushButton("Register")
        register_button.clicked.connect(self.on_register)
        button_layout.addWidget(register_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Connect Enter key to login
        self.email_input.returnPressed.connect(self.on_login)
        self.password_input.returnPressed.connect(self.on_login)
    
    def on_login(self):
        """Handle login button click."""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        # Validate email
        is_valid, error = Validator.validate_email(email)
        if not is_valid:
            QMessageBox.warning(self, "Invalid Email", error)
            return
        
        if not password:
            QMessageBox.warning(self, "Missing Password", "Please enter your password")
            return
        
        # Authenticate user
        user = AuthenticationService.authenticate_user(email, password)
        
        if user:
            self.current_user = user
            logger.info(f"User logged in: {email}")
            
            # Log action
            AuditService.log_action(user.id, "login")
            
            # Close dialog with accepted status
            self.accept()
        else:
            logger.warning(f"Failed login attempt: {email}")
            QMessageBox.critical(self, "Login Failed", "Invalid email or password")
            self.password_input.clear()
    
    def on_register(self):
        """Handle register button click."""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        # Validate email
        is_valid, error = Validator.validate_email(email)
        if not is_valid:
            QMessageBox.warning(self, "Invalid Email", error)
            return
        
        # Validate password
        is_valid, error = Validator.validate_password(password)
        if not is_valid:
            QMessageBox.warning(self, "Weak Password", error)
            return
        
        # Create user (use email as name for now)
        user = AuthenticationService.create_user(email, email.split('@')[0], password)
        
        if user:
            logger.info(f"User registered: {email}")
            QMessageBox.information(self, "Success", f"Account created for {email}!\nYou can now login.")
            self.email_input.clear()
            self.password_input.clear()
        else:
            logger.warning(f"User already exists: {email}")
            QMessageBox.warning(self, "Registration Failed", "This email is already registered")
