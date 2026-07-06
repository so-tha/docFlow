from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app.models import db, User
from app.services import AuditService
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=request.form.get('remember'))
            AuditService.log_action(user_id=user.id, action='login', entity_type='user', entity_id=user.id)
            return redirect(url_for('main.dashboard'))
        else:
            return render_template('login.html', error='Email ou senha inválidos')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        if not email or not name or (not password):
            return render_template('register.html', error='Todos os campos são obrigatórios')
        if password != password_confirm:
            return render_template('register.html', error='As senhas não coincidem')
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email já usado')
        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        AuditService.log_action(user_id=user.id, action='register', entity_type='user', entity_id=user.id, details={'email': email, 'name': name})
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    AuditService.log_action(user_id=current_user.id, action='logout', entity_type='user', entity_id=current_user.id)
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    recent_activity = AuditService.get_user_activity(current_user.id, limit=10)
    return render_template('profile.html', user=current_user, recent_activity=recent_activity)