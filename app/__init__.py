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
        # Ensure new columns are present if DB pre-existed (simple auto-migration)
        try:
            from sqlalchemy import inspect, text

            inspector = inspect(db.engine)
            user_columns = {c["name"] for c in inspector.get_columns("users")}
            if "name" not in user_columns:
                db.session.execute(text("ALTER TABLE users ADD COLUMN name VARCHAR(120) NULL"))
                db.session.commit()
        except Exception:
            # Soft-fail; continue startup and allow manual migration if needed
            pass
        # Seed admin user and default rooms if not present
        admin = User.query.filter_by(email="admin@example.com").first()
        if not admin:
            admin = User(email="admin@example.com", role="admin", name="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
        else:
            updated = False
            if admin.name != "admin":
                admin.name = "admin"
                updated = True
            if not admin.password_hash or not admin.password_hash.startswith("$2"):
                admin.set_password("admin123")
                updated = True
            if updated:
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


