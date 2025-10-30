import bcrypt
from flask_login import UserMixin
from . import db, datetime


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("admin", "member", name="user_roles"), nullable=False, default="member")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    rooms_created = db.relationship("Room", back_populates="creator", lazy="select")
    messages = db.relationship("Message", back_populates="author", lazy="dynamic")

    def set_password(self, password: str) -> None:
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))
        except ValueError:
            return False


