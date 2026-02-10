import click
from werkzeug.security import generate_password_hash


def register_commands(app):
    @app.cli.command('create-admin')
    @click.option('--username', prompt='Username do admin', help='Username do administrador')
    @click.option('--password', prompt='Senha', hide_input=True, confirmation_prompt=True, help='Senha do administrador')
    def create_admin(username, password):
        """Cria um usuário administrador."""
        from app import db
        from app.models import User

        existing = User.query.filter_by(username=username).first()
        if existing:
            click.echo(f'Erro: Usuário "{username}" já existe.')
            return

        admin = User(
            username=username,
            password_hash=generate_password_hash(password),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        click.echo(f'Admin "{username}" criado com sucesso!')

    @app.cli.command('reset-running')
    def reset_running():
        """Reseta o flag is_running de todos os scripts (útil após crash)."""
        from app import db
        from app.models import Script, Execution

        scripts = Script.query.filter_by(is_running=True).all()
        for script in scripts:
            script.is_running = False
            # Marca execuções que ficaram como 'running' como 'failed'
            running_execs = Execution.query.filter_by(
                script_id=script.id, status='running'
            ).all()
            for ex in running_execs:
                ex.status = 'failed'
                ex.log_output = (ex.log_output or '') + '\n[SISTEMA] Execução interrompida por reinício do servidor.'

        db.session.commit()
        click.echo(f'{len(scripts)} script(s) resetado(s).')
