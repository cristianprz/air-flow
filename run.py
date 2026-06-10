import os

from app import create_app

app = create_app()

if __name__ == '__main__':
    # Servidor de DESENVOLVIMENTO apenas. Em produção use serve.py (Waitress).
    # O debugger do Werkzeug permite execução remota de código, então só é
    # ativado explicitamente via FLASK_DEBUG=1.
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug, host=os.environ.get('HOST', '127.0.0.1'),
            port=int(os.environ.get('PORT', '5000')))
