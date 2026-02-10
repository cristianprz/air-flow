import os
import subprocess
import threading
import logging
from datetime import datetime
from app.utils import now_brt, BRT

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone=BRT)
_app = None


def init_scheduler(app):
    """Inicializa o APScheduler e registra os jobs de cron ativos."""
    global _app
    _app = app

    # Resetar scripts que ficaram como 'running' após crash
    from app.models import Script, Execution
    from app import db

    stuck_scripts = Script.query.filter_by(is_running=True).all()
    for script in stuck_scripts:
        script.is_running = False
        running_execs = Execution.query.filter_by(
            script_id=script.id, status='running'
        ).all()
        for ex in running_execs:
            ex.status = 'failed'
            ex.end_time = now_brt()
            ex.log_output = (ex.log_output or '') + '\n[SISTEMA] Execução interrompida por reinício do servidor.'
    db.session.commit()

    if stuck_scripts:
        logger.info(f'Resetados {len(stuck_scripts)} script(s) presos como "running".')

    # Carregar jobs de cron ativos
    active_scripts = Script.query.filter(
        Script.is_active == True,
        Script.cron_expression.isnot(None),
        Script.cron_expression != ''
    ).all()

    for script in active_scripts:
        add_cron_job(script)

    scheduler.start()
    logger.info(f'Scheduler iniciado com {len(active_scripts)} job(s) de cron.')


def add_cron_job(script):
    """Adiciona um job de cron ao scheduler para um script."""
    job_id = f'script_{script.id}'

    # Remover se já existir
    remove_cron_job(script.id)

    try:
        parts = script.cron_expression.strip().split()
        if len(parts) == 5:
            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4]
            )
        else:
            logger.error(f'Expressão cron inválida para script {script.id}: {script.cron_expression}')
            return

        scheduler.add_job(
            func=_cron_execute,
            trigger=trigger,
            id=job_id,
            args=[script.id],
            name=f'Cron: {script.name}',
            replace_existing=True,
            max_instances=1,
        )
        logger.info(f'Job de cron adicionado: {script.name} ({script.cron_expression})')
    except Exception as e:
        logger.error(f'Erro ao adicionar job de cron para script {script.id}: {e}')


def remove_cron_job(script_id):
    """Remove um job de cron do scheduler."""
    job_id = f'script_{script_id}'
    try:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info(f'Job de cron removido: {job_id}')
    except Exception as e:
        logger.error(f'Erro ao remover job {job_id}: {e}')


def _cron_execute(script_id):
    """Função chamada pelo scheduler de cron para executar um script."""
    with _app.app_context():
        execute_script(script_id, triggered_by='cron')


def execute_script(script_id, triggered_by='manual'):
    """
    Executa um script Python em uma thread separada.
    Verifica o lock is_running para impedir execução simultânea.
    """
    from app.models import Script, Execution
    from app import db

    script = Script.query.get(script_id)
    if not script:
        logger.error(f'Script {script_id} não encontrado.')
        return

    # Verificar lock de execução simultânea
    if script.is_running:
        logger.warning(f'Script "{script.name}" já está em execução. Skipping.')
        execution = Execution(
            script_id=script.id,
            status='skipped',
            triggered_by=triggered_by,
            start_time=now_brt(),
            end_time=now_brt(),
            log_output='[SISTEMA] Execução ignorada: script já em andamento.'
        )
        db.session.add(execution)
        db.session.commit()
        return

    # Criar registro de execução
    execution = Execution(
        script_id=script.id,
        status='running',
        triggered_by=triggered_by,
        start_time=now_brt()
    )
    db.session.add(execution)

    # Ativar lock
    script.is_running = True
    db.session.commit()

    execution_id = execution.id

    # Executar em thread separada para não bloquear
    thread = threading.Thread(
        target=_run_script_process,
        args=(script_id, execution_id),
        daemon=True
    )
    thread.start()


def _run_script_process(script_id, execution_id):
    """Executa o script em subprocess e captura o output."""
    with _app.app_context():
        from app.models import Script, Execution
        from app import db

        script = Script.query.get(script_id)
        execution = Execution.query.get(execution_id)

        if not script or not execution:
            return

        max_log_size = _app.config.get('MAX_LOG_SIZE', 50 * 1024)

        try:
            # Validar que o arquivo ainda existe
            if not os.path.isfile(script.file_path):
                execution.status = 'failed'
                execution.end_time = now_brt()
                execution.log_output = f'[ERRO] Arquivo não encontrado: {script.file_path}'
                execution.exit_code = -1
                return

            logger.info(f'Executando script: {script.name} ({script.file_path})')

            # Executar o script com subprocess
            process = subprocess.Popen(
                ['python', script.file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=os.path.dirname(script.file_path),
                env={**os.environ, 'PYTHONUNBUFFERED': '1'}
            )

            # Salvar PID
            execution.pid = process.pid
            db.session.commit()

            # Capturar output em tempo real (salvar no banco periodicamente)
            output_lines = []
            total_size = 0

            try:
                process.wait(timeout=script.timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                output = process.stdout.read() if process.stdout else ''
                output_lines.append(output)
                output_lines.append(f'\n[SISTEMA] Execução interrompida por timeout ({script.timeout_seconds}s).')
                execution.status = 'timeout'
                execution.exit_code = -9
            else:
                output = process.stdout.read() if process.stdout else ''
                output_lines.append(output)
                execution.exit_code = process.returncode
                execution.status = 'success' if process.returncode == 0 else 'failed'

            # Montar log final (limitado ao MAX_LOG_SIZE)
            full_output = ''.join(output_lines)
            if len(full_output) > max_log_size:
                truncated_msg = f'\n\n[SISTEMA] Log truncado. Mostrando os últimos {max_log_size // 1024}KB.\n'
                full_output = truncated_msg + full_output[-max_log_size:]

            execution.log_output = full_output
            execution.end_time = now_brt()

            logger.info(
                f'Script "{script.name}" finalizado com status: {execution.status} '
                f'(exit code: {execution.exit_code})'
            )

        except Exception as e:
            execution.status = 'failed'
            execution.end_time = now_brt()
            execution.log_output = f'[ERRO INTERNO] {str(e)}'
            execution.exit_code = -1
            logger.exception(f'Erro ao executar script {script.name}')

        finally:
            # Liberar lock SEMPRE
            script.is_running = False
            execution.pid = None
            db.session.commit()
