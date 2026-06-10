from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()


def _ensure_sqlite_dir(app):
    """Cria o diretório do arquivo SQLite se ele não existir.

    O SQLite não cria diretórios ausentes e falha com 'unable to open database
    file'. Isto evita esse erro quando DATABASE_URL aponta para uma pasta nova
    (ex.: sqlite:///C:/airflow-lite/airflow_lite.db).
    """
    import os
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not uri.startswith('sqlite:///') or ':memory:' in uri:
        return
    db_path = uri[len('sqlite:///'):]
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.isdir(db_dir):
        os.makedirs(db_dir, exist_ok=True)


def register_error_handlers(app):
    import logging
    logger = logging.getLogger(__name__)

    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', code=404,
                               message='Página não encontrada.'), 404

    @app.errorhandler(500)
    def internal_error(error):
        # Garante que uma transação quebrada não contamine as próximas requisições.
        db.session.rollback()
        logger.exception('Erro interno não tratado')
        return render_template('error.html', code=500,
                               message='Ocorreu um erro interno. Tente novamente.'), 500


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Garante que o diretório do banco SQLite exista antes de conectar
    _ensure_sqlite_dir(app)

    # Inicializar extensões
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'

    # Registrar blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.scripts import scripts_bp
    from app.routes.executions import executions_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(scripts_bp)
    app.register_blueprint(executions_bp)

    # Registrar comandos CLI
    from app.cli import register_commands
    register_commands(app)

    # Handlers de erro: evitam stacktrace cru e deixam a sessão do banco limpa
    register_error_handlers(app)

    # Inicializar o scheduler
    from app.scheduler.engine import init_scheduler
    with app.app_context():
        db.create_all()
        init_scheduler(app)

    return app
