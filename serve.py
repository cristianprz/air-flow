"""Entrypoint de PRODUÇÃO — serve a aplicação com Waitress (WSGI).

Use este arquivo no Windows Server (via deploy/start.bat), não o run.py.
O scheduler roda em um único processo; NÃO inicie múltiplas instâncias deste
servidor apontando para o mesmo banco, ou os jobs de cron seriam duplicados.
"""
import os
import logging

from waitress import serve

from app import create_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)

app = create_app()

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    threads = int(os.environ.get('THREADS', '8'))

    logging.getLogger(__name__).info(
        'Iniciando AirFlow Lite (Waitress) em http://%s:%s com %s threads',
        host, port, threads,
    )
    serve(app, host=host, port=port, threads=threads)
