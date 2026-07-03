"""Inicializador das rotas"""

from app.routes.auth_routes import auth_bp
from app.routes.document_routes import document_bp
from app.routes.audit_routes import audit_bp
from app.routes.main import main_bp

def register_blueprints(app):
    """Registra todos os blueprints na aplicação"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(main_bp)
