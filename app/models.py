from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
from app.utils import now_brt


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')  # 'admin' ou 'user'
    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=now_brt)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Script(db.Model):
    __tablename__ = 'scripts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, default='')
    cron_expression = db.Column(db.String(100), nullable=True)  # ex: "0 8 * * *"
    is_active = db.Column(db.Boolean, default=True)
    is_running = db.Column(db.Boolean, default=False)
    timeout_seconds = db.Column(db.Integer, default=3600)
    created_at = db.Column(db.DateTime, default=now_brt)
    updated_at = db.Column(db.DateTime, default=now_brt, onupdate=now_brt)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relacionamentos
    created_by = db.relationship('User', backref='scripts')
    executions = db.relationship('Execution', backref='script', lazy='dynamic',
                                 order_by='Execution.start_time.desc()')

    @property
    def last_execution(self):
        return self.executions.first()

    @property
    def cron_display(self):
        if not self.cron_expression:
            return 'Sem agendamento'
        return self.cron_expression

    def __repr__(self):
        return f'<Script {self.name}>'


class Execution(db.Model):
    __tablename__ = 'executions'

    id = db.Column(db.Integer, primary_key=True)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    # status: pending, running, success, failed, skipped, timeout
    triggered_by = db.Column(db.String(50), default='manual')  # 'manual', 'cron', username
    start_time = db.Column(db.DateTime, default=now_brt)
    end_time = db.Column(db.DateTime, nullable=True)
    log_output = db.Column(db.Text, default='')
    exit_code = db.Column(db.Integer, nullable=True)
    pid = db.Column(db.Integer, nullable=True)  # PID do processo para possível kill futuro

    @property
    def duration(self):
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            total_seconds = int(delta.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                return f'{hours}h {minutes}m {seconds}s'
            elif minutes:
                return f'{minutes}m {seconds}s'
            return f'{seconds}s'
        return 'Em andamento...'

    @property
    def status_badge(self):
        badges = {
            'pending': 'secondary',
            'running': 'primary',
            'success': 'success',
            'failed': 'danger',
            'skipped': 'warning',
            'timeout': 'dark',
        }
        return badges.get(self.status, 'secondary')

    @property
    def status_icon(self):
        icons = {
            'pending': 'bi-hourglass-split',
            'running': 'bi-arrow-repeat spin',
            'success': 'bi-check-circle-fill',
            'failed': 'bi-x-circle-fill',
            'skipped': 'bi-skip-forward-fill',
            'timeout': 'bi-clock-fill',
        }
        return icons.get(self.status, 'bi-question-circle')

    def __repr__(self):
        return f'<Execution {self.id} - Script {self.script_id} - {self.status}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
