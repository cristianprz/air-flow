from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User

auth_bp = Blueprint('auth', __name__)


def admin_required(f):
    """Decorator que exige role 'admin' para acessar a rota."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Acesso negado. Apenas administradores podem acessar esta página.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active_user:
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Bem-vindo, {user.username}!', 'success')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('auth.login'))


# ─── Gestão de Usuários (Admin) ────────────────────────────────────────────────

@auth_bp.route('/users')
@admin_required
def users_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users/index.html', users=users)


@auth_bp.route('/users/new', methods=['GET', 'POST'])
@admin_required
def users_create():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'user')

        if not username or not password:
            flash('Username e senha são obrigatórios.', 'danger')
            return render_template('users/form.html', user=None)

        if User.query.filter_by(username=username).first():
            flash(f'Usuário "{username}" já existe.', 'danger')
            return render_template('users/form.html', user=None)

        if role not in ('admin', 'user'):
            role = 'user'

        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f'Usuário "{username}" criado com sucesso.', 'success')
        return redirect(url_for('auth.users_list'))

    return render_template('users/form.html', user=None)


@auth_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def users_edit(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        role = request.form.get('role', 'user')
        password = request.form.get('password', '').strip()
        is_active = request.form.get('is_active') == 'on'

        if role not in ('admin', 'user'):
            role = 'user'

        user.role = role
        user.is_active_user = is_active

        if password:
            user.set_password(password)

        db.session.commit()
        flash(f'Usuário "{user.username}" atualizado com sucesso.', 'success')
        return redirect(url_for('auth.users_list'))

    return render_template('users/form.html', user=user)


@auth_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def users_delete(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('Você não pode excluir seu próprio usuário.', 'danger')
        return redirect(url_for('auth.users_list'))

    db.session.delete(user)
    db.session.commit()
    flash(f'Usuário "{user.username}" excluído.', 'success')
    return redirect(url_for('auth.users_list'))
