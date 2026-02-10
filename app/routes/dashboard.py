from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from app.models import Script, Execution
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    scripts = Script.query.order_by(Script.name).all()

    # Estatísticas
    total_scripts = Script.query.count()
    active_scripts = Script.query.filter_by(is_active=True).count()
    running_scripts = Script.query.filter_by(is_running=True).count()

    total_executions = Execution.query.count()
    successful = Execution.query.filter_by(status='success').count()
    failed = Execution.query.filter_by(status='failed').count()

    # Últimas 10 execuções
    recent_executions = Execution.query.order_by(
        Execution.start_time.desc()
    ).limit(10).all()

    return render_template('dashboard.html',
                           scripts=scripts,
                           total_scripts=total_scripts,
                           active_scripts=active_scripts,
                           running_scripts=running_scripts,
                           total_executions=total_executions,
                           successful=successful,
                           failed=failed,
                           recent_executions=recent_executions)


@dashboard_bp.route('/api/status')
@login_required
def api_status():
    """Endpoint de polling para atualizar status na UI."""
    scripts = Script.query.order_by(Script.name).all()
    data = []
    for s in scripts:
        last_exec = s.last_execution
        data.append({
            'id': s.id,
            'name': s.name,
            'is_running': s.is_running,
            'is_active': s.is_active,
            'last_status': last_exec.status if last_exec else None,
            'last_status_badge': last_exec.status_badge if last_exec else 'secondary',
            'last_duration': last_exec.duration if last_exec else None,
            'last_time': last_exec.start_time.strftime('%d/%m/%Y %H:%M:%S') if last_exec else None,
        })

    running_count = Script.query.filter_by(is_running=True).count()
    return jsonify({'scripts': data, 'running_count': running_count})
