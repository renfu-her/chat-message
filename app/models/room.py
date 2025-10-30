from . import db, datetime


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    creator = db.relationship("User", back_populates="rooms_created")
    memberships = db.relationship("RoomMembership", back_populates="room", cascade="all, delete-orphan")
    messages = db.relationship("Message", back_populates="room", cascade="all, delete-orphan")


