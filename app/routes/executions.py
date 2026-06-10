from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from app.models import Execution, Script

executions_bp = Blueprint('executions', __name__, url_prefix='/executions')


def _safe_int(value, default=None):
    """Converte para int, retornando default em caso de valor inválido/ausente."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@executions_bp.route('/')
@login_required
def index():
    page = _safe_int(request.args.get('page'), 1)
    if page < 1:
        page = 1
    per_page = 25

    query = Execution.query.order_by(Execution.start_time.desc())

    # Filtros
    script_id = request.args.get('script_id')
    status = request.args.get('status')

    script_id_int = _safe_int(script_id)
    if script_id_int is not None:
        query = query.filter_by(script_id=script_id_int)
    if status:
        query = query.filter_by(status=status)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    executions = pagination.items

    scripts = Script.query.order_by(Script.name).all()

    return render_template('executions/index.html',
                           executions=executions,
                           pagination=pagination,
                           scripts=scripts,
                           current_script_id=script_id,
                           current_status=status)


@executions_bp.route('/<int:execution_id>')
@login_required
def detail(execution_id):
    execution = Execution.query.get_or_404(execution_id)
    return render_template('executions/detail.html', execution=execution)


@executions_bp.route('/<int:execution_id>/log')
@login_required
def log_api(execution_id):
    """API endpoint para polling do log de uma execução em andamento."""
    execution = Execution.query.get_or_404(execution_id)
    return jsonify({
        'id': execution.id,
        'status': execution.status,
        'status_badge': execution.status_badge,
        'log_output': execution.log_output or '',
        'duration': execution.duration,
        'exit_code': execution.exit_code,
        'end_time': execution.end_time.strftime('%d/%m/%Y %H:%M:%S') if execution.end_time else None,
    })
