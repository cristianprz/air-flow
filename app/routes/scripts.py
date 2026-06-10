import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Script, Execution
from app.routes.auth import admin_required
from app.scheduler.engine import execute_script

scripts_bp = Blueprint('scripts', __name__, url_prefix='/scripts')


def _is_within_directory(file_path, directory):
    """True se file_path estiver dentro de directory (à prova de prefixos e symlinks)."""
    try:
        real_file = os.path.realpath(file_path)
        real_dir = os.path.realpath(directory)
        # commonpath compara componentes inteiros, então 'C:\scripts_evil'
        # não é considerado dentro de 'C:\scripts'. normcase trata
        # maiúsc/minúsc e separadores no Windows.
        common = os.path.commonpath([os.path.normcase(real_file), os.path.normcase(real_dir)])
        return common == os.path.normcase(real_dir)
    except (ValueError, OSError):
        # ValueError: caminhos em drives diferentes (Windows). OSError: caminho inválido.
        return False


def validate_file_path(file_path):
    """Valida se o caminho do script é permitido e existe."""
    errors = []

    if not file_path:
        errors.append('O caminho do arquivo é obrigatório.')
        return errors

    # Normalizar o caminho
    file_path = os.path.normpath(file_path)

    # Verificar extensão .py
    if not file_path.endswith('.py'):
        errors.append('O arquivo deve ter extensão .py')

    # Verificar se o arquivo existe
    if not os.path.isfile(file_path):
        errors.append(f'Arquivo não encontrado: {file_path}')

    # Verificar se está em um diretório permitido (whitelist)
    allowed_dirs = current_app.config.get('ALLOWED_SCRIPT_DIRS', [])
    is_allowed = any(
        _is_within_directory(file_path, allowed_dir.strip())
        for allowed_dir in allowed_dirs if allowed_dir.strip()
    )

    if not is_allowed:
        dirs_str = ', '.join(allowed_dirs)
        errors.append(f'O arquivo deve estar em um dos diretórios permitidos: {dirs_str}')

    return errors


@scripts_bp.route('/')
@login_required
def index():
    scripts = Script.query.order_by(Script.name).all()
    return render_template('scripts/index.html', scripts=scripts)


@scripts_bp.route('/new', methods=['GET', 'POST'])
@admin_required
def create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        file_path = request.form.get('file_path', '').strip()
        description = request.form.get('description', '').strip()
        cron_expression = request.form.get('cron_expression', '').strip() or None
        timeout_seconds = request.form.get('timeout_seconds', current_app.config['DEFAULT_TIMEOUT'])
        is_active = request.form.get('is_active') == 'on'

        # Validações
        if not name:
            flash('O nome do script é obrigatório.', 'danger')
            return render_template('scripts/form.html', script=None)

        path_errors = validate_file_path(file_path)
        if path_errors:
            for err in path_errors:
                flash(err, 'danger')
            return render_template('scripts/form.html', script=None)

        try:
            timeout_seconds = int(timeout_seconds)
            if timeout_seconds < 10:
                timeout_seconds = 10
        except (ValueError, TypeError):
            timeout_seconds = current_app.config['DEFAULT_TIMEOUT']

        script = Script(
            name=name,
            file_path=os.path.normpath(file_path),
            description=description,
            cron_expression=cron_expression,
            timeout_seconds=timeout_seconds,
            is_active=is_active,
            created_by_id=current_user.id
        )
        db.session.add(script)
        db.session.commit()

        # Registrar no scheduler se tiver cron e estiver ativo
        if cron_expression and is_active:
            from app.scheduler.engine import add_cron_job
            add_cron_job(script)

        flash(f'Script "{name}" criado com sucesso.', 'success')
        return redirect(url_for('scripts.index'))

    return render_template('scripts/form.html', script=None)


@scripts_bp.route('/<int:script_id>')
@login_required
def detail(script_id):
    script = Script.query.get_or_404(script_id)
    executions = script.executions.limit(50).all()
    return render_template('scripts/detail.html', script=script, executions=executions)


@scripts_bp.route('/<int:script_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(script_id):
    script = Script.query.get_or_404(script_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        file_path = request.form.get('file_path', '').strip()
        description = request.form.get('description', '').strip()
        cron_expression = request.form.get('cron_expression', '').strip() or None
        timeout_seconds = request.form.get('timeout_seconds', current_app.config['DEFAULT_TIMEOUT'])
        is_active = request.form.get('is_active') == 'on'

        if not name:
            flash('O nome do script é obrigatório.', 'danger')
            return render_template('scripts/form.html', script=script)

        path_errors = validate_file_path(file_path)
        if path_errors:
            for err in path_errors:
                flash(err, 'danger')
            return render_template('scripts/form.html', script=script)

        try:
            timeout_seconds = int(timeout_seconds)
            if timeout_seconds < 10:
                timeout_seconds = 10
        except (ValueError, TypeError):
            timeout_seconds = current_app.config['DEFAULT_TIMEOUT']

        old_cron = script.cron_expression
        old_active = script.is_active

        script.name = name
        script.file_path = os.path.normpath(file_path)
        script.description = description
        script.cron_expression = cron_expression
        script.timeout_seconds = timeout_seconds
        script.is_active = is_active
        db.session.commit()

        # Atualizar scheduler
        from app.scheduler.engine import remove_cron_job, add_cron_job
        remove_cron_job(script.id)
        if cron_expression and is_active:
            add_cron_job(script)

        flash(f'Script "{name}" atualizado com sucesso.', 'success')
        return redirect(url_for('scripts.detail', script_id=script.id))

    return render_template('scripts/form.html', script=script)


@scripts_bp.route('/<int:script_id>/delete', methods=['POST'])
@admin_required
def delete(script_id):
    script = Script.query.get_or_404(script_id)

    if script.is_running:
        flash('Não é possível excluir um script em execução.', 'danger')
        return redirect(url_for('scripts.detail', script_id=script.id))

    # Remover do scheduler
    from app.scheduler.engine import remove_cron_job
    remove_cron_job(script.id)

    # Remover execuções associadas
    Execution.query.filter_by(script_id=script.id).delete()

    name = script.name
    db.session.delete(script)
    db.session.commit()
    flash(f'Script "{name}" excluído.', 'success')
    return redirect(url_for('scripts.index'))


@scripts_bp.route('/<int:script_id>/execute', methods=['POST'])
@login_required
def execute(script_id):
    script = Script.query.get_or_404(script_id)

    if script.is_running:
        flash('Este script já está em execução. Aguarde a finalização.', 'warning')
        return redirect(url_for('scripts.detail', script_id=script.id))

    triggered_by = f'manual:{current_user.username}'
    execute_script(script.id, triggered_by=triggered_by)

    flash(f'Execução do script "{script.name}" iniciada.', 'success')
    return redirect(url_for('scripts.detail', script_id=script.id))


@scripts_bp.route('/<int:script_id>/toggle', methods=['POST'])
@admin_required
def toggle_active(script_id):
    script = Script.query.get_or_404(script_id)
    script.is_active = not script.is_active
    db.session.commit()

    from app.scheduler.engine import remove_cron_job, add_cron_job
    if script.is_active and script.cron_expression:
        add_cron_job(script)
    else:
        remove_cron_job(script.id)

    status_text = 'ativado' if script.is_active else 'desativado'
    flash(f'Script "{script.name}" {status_text}.', 'success')
    return redirect(url_for('scripts.detail', script_id=script.id))
