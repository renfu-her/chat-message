from . import db, datetime


class RoomMembership(db.Model):
    __tablename__ = "room_memberships"
    __table_args__ = (
        db.UniqueConstraint("user_id", "room_id", name="uq_user_room"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False, index=True)
    joined_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("memberships", cascade="all, delete-orphan"))
    room = db.relationship("Room", back_populates="memberships")


