from flask import Flask
from flask_login import LoginManager
from app.config import get_config
from app.models import db, User
from app.routes import register_blueprints
import os
from pathlib import Path


def create_app():
    config = get_config()
    
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config)
    
    db_path = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///loglife.db')
    
    if db_path.startswith('sqlite:///'):
        db_file = db_path.replace('sqlite:///', '')
        db_dir = os.path.dirname(db_file)
        
        if db_dir and not db_dir.startswith(':'):
            Path(db_dir).mkdir(parents=True, exist_ok=True)
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para continuar'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
    
    register_blueprints(app)
    
    with app.app_context():
        db.create_all()
    
    return app
