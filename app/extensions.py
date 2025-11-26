from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_mail import Mail


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
socketio = SocketIO(
    async_mode="threading",
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25
)
mail = Mail()


def init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    socketio.init_app(app)
    mail.init_app(app)

    login_manager.login_view = "auth.login_view"  # Redirect to login page if not authenticated


