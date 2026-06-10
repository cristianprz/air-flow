import os
import sys
import time
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

# Registro de processos em execução (execution_id -> Popen) para permitir parada
# manual. Protegido por lock pois é acessado pela thread do executor e por
# requisições web concorrentes.
_running_processes = {}
_cancelled_executions = set()
_proc_lock = threading.Lock()


def _register_process(execution_id, process):
    with _proc_lock:
        _running_processes[execution_id] = process


def _unregister_process(execution_id):
    with _proc_lock:
        _running_processes.pop(execution_id, None)
        _cancelled_executions.discard(execution_id)


def stop_execution(execution_id):
    """Termina o processo de uma execução em andamento.

    Retorna True se um processo foi localizado e o kill foi disparado; False se
    não havia processo (já finalizou ou nunca existiu nesta instância).
    """
    with _proc_lock:
        process = _running_processes.get(execution_id)
        if process is None:
            return False
        _cancelled_executions.add(execution_id)

    logger.info(f'Parada solicitada para execução {execution_id} (PID {process.pid}).')
    try:
        if sys.platform == 'win32':
            # taskkill /T encerra também os processos-filhos que o script tenha criado.
            subprocess.run(
                ['taskkill', '/F', '/T', '/PID', str(process.pid)],
                capture_output=True,
            )
        else:
            process.kill()
    except Exception as e:
        logger.error(f'Erro ao parar execução {execution_id}: {e}')
        try:
            process.kill()
        except Exception:
            pass
    return True


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

    # Evita iniciar duas vezes (ex.: reloader do Flask ou re-inicialização da factory).
    # Com Waitress (1 processo) há apenas uma instância do scheduler — não use
    # múltiplos workers/processos, ou os jobs de cron rodariam duplicados.
    if not scheduler.running:
        scheduler.start()
        logger.info(f'Scheduler iniciado com {len(active_scripts)} job(s) de cron.')
    else:
        logger.info('Scheduler já estava em execução; reuso da instância existente.')


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

            # Executar o script com subprocess.
            # IMPORTANTE: usamos communicate() (não wait() + read()) para drenar
            # stdout/stderr concorrentemente. Caso contrário, um script que produza
            # mais output que o buffer do pipe (~64KB no Windows) bloqueia no write
            # e o processo pai trava indefinidamente.
            process = subprocess.Popen(
                [sys.executable, '-u', script.file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=os.path.dirname(script.file_path) or None,
                env={**os.environ, 'PYTHONUNBUFFERED': '1', 'PYTHONIOENCODING': 'utf-8'}
            )

            # Salvar PID e registrar o processo para permitir parada manual
            execution.pid = process.pid
            db.session.commit()
            _register_process(execution_id, process)

            # Aplica o limite de tamanho ao log.
            def _montar_log(texto):
                if len(texto) > max_log_size:
                    aviso = (f'\n\n[SISTEMA] Log truncado. Mostrando os últimos '
                             f'{max_log_size // 1024}KB.\n')
                    return aviso + texto[-max_log_size:]
                return texto

            # Drena o stdout em uma thread, acumulando as linhas conforme chegam.
            # Isso permite gravar o log no banco DE FORMA INCREMENTAL para o front
            # exibir a saída em tempo real (o endpoint /log faz polling de log_output).
            buffer = []
            buffer_lock = threading.Lock()

            def _drenar():
                for linha in process.stdout:
                    with buffer_lock:
                        buffer.append(linha)

            leitor = threading.Thread(target=_drenar, daemon=True)
            leitor.start()

            timeout_s = script.timeout_seconds or None
            deadline = (time.monotonic() + timeout_s) if timeout_s else None
            timed_out = False

            # Loop de supervisão: persiste o log a cada ~1s enquanto o processo roda.
            while True:
                terminou = process.poll() is not None
                with buffer_lock:
                    parcial = ''.join(buffer)
                execution.log_output = _montar_log(parcial)
                db.session.commit()

                if terminou:
                    break
                if deadline and time.monotonic() > deadline:
                    timed_out = True
                    break
                with _proc_lock:
                    if execution_id in _cancelled_executions:
                        break
                time.sleep(1.0)

            if timed_out:
                process.kill()

            # Aguarda a leitora drenar o que restou no pipe e o processo encerrar.
            leitor.join(timeout=5)
            process.wait()
            with buffer_lock:
                output = ''.join(buffer)

            if timed_out:
                output += f'\n[SISTEMA] Execução interrompida por timeout ({timeout_s}s).'
                execution.status = 'timeout'
                execution.exit_code = -9
            else:
                execution.exit_code = process.returncode
                execution.status = 'success' if process.returncode == 0 else 'failed'

            # Se a parada foi solicitada manualmente, sobrescreve o status
            with _proc_lock:
                was_cancelled = execution_id in _cancelled_executions
            if was_cancelled:
                execution.status = 'stopped'
                if execution.exit_code is None or execution.exit_code == 0:
                    execution.exit_code = -15
                output += '\n[SISTEMA] Execução interrompida manualmente pelo usuário.'

            execution.log_output = _montar_log(output)
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
            _unregister_process(execution_id)
            script.is_running = False
            execution.pid = None
            db.session.commit()
