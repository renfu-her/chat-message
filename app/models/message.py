from . import db, datetime


class Message(db.Model):
    __tablename__ = "messages"
    __table_args__ = (
        db.Index("ix_room_created", "room_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    room = db.relationship("Room", back_populates="messages")
    author = db.relationship("User", back_populates="messages")


