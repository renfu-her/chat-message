from flask import Flask
from .config import get_config
from .extensions import init_extensions


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None, template_folder="../public")
    app.config.from_object(get_config())

    # Initialize extensions (db, migrate, login, socketio)
    init_extensions(app)

    # Register blueprints
    register_blueprints(app)

    # Socket.IO namespaces
    from .services.socketio import register_socketio_namespaces

    register_socketio_namespaces()

    # Bootstrap DB and seed minimal data for dev if tables missing
    from .extensions import db
    from .models.user import User
    from .models.room import Room

    with app.app_context():
        db.create_all()
        # Seed admin user and a default room if not present
        if not User.query.filter_by(email="admin@example.com").first():
            admin = User(email="admin@example.com", role="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
        admin = User.query.filter_by(email="admin@example.com").first()
        if admin:
            default_rooms = ["測試 1 Room", "測試 2 Room", "測試 3 Room"]
            for rn in default_rooms:
                if not Room.query.filter_by(name=rn).first():
                    db.session.add(Room(name=rn, created_by=admin.id))
            db.session.commit()

    return app


def register_blueprints(app: Flask) -> None:
    from .controllers.main import bp as main_bp
    from .controllers.auth import bp as auth_bp
    from .controllers.rooms import bp as rooms_bp
    from .controllers.messages import bp as messages_bp
    from .extensions import login_manager
    from .models.user import User

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(rooms_bp)
    app.register_blueprint(messages_bp)

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))


