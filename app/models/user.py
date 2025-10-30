from werkzeug.security import generate_password_hash, check_password_hash
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
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


