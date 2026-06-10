import os

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Carrega variáveis de um arquivo .env na raiz do projeto (se existir).
# Variáveis já definidas no ambiente têm precedência (override=False).
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(basedir, 'airflow_lite.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Diretórios permitidos para scripts Python (whitelist)
    # Separe múltiplos diretórios com ; na variável de ambiente
    ALLOWED_SCRIPT_DIRS = os.environ.get(
        'ALLOWED_SCRIPT_DIRS',
        os.path.join(basedir, 'scripts')  # padrão: pasta scripts/ do projeto
    ).split(';')

    # Timeout padrão para execução de scripts (em segundos)
    DEFAULT_TIMEOUT = int(os.environ.get('DEFAULT_TIMEOUT', 3600))

    # Tamanho máximo do log armazenado por execução (em bytes)
    MAX_LOG_SIZE = int(os.environ.get('MAX_LOG_SIZE', 50 * 1024))  # 50KB

    # Fuso horário (America/Sao_Paulo = UTC-3)
    TIMEZONE = 'America/Sao_Paulo'
