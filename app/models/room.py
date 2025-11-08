from . import db, datetime
import bcrypt
import random
import string
try:
    from uuid7 import uuid7
except ImportError:
    # Fallback: simple UUID7-like generator using timestamp + random
    import time
    def uuid7():
        """Simple UUID7-like generator (timestamp + random)"""
        timestamp_ms = int(time.time() * 1000)
        random_part = random.randint(0, 0xFFFFFFFFFFFF)
        return f"{timestamp_ms:013x}-{random_part:012x}"


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    room_no = db.Column(db.String(50), unique=True, nullable=True, index=True)  # UUID7 + random text
    room_type = db.Column(db.String(20), nullable=False, default='public')  # 'public' or 'private'
    password_hash = db.Column(db.String(255), nullable=True)  # For private rooms
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)  # Room active status
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    creator = db.relationship("User", back_populates="rooms_created")
    memberships = db.relationship("RoomMembership", back_populates="room", cascade="all, delete-orphan")
    messages = db.relationship("Message", back_populates="room", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """Set password for private room"""
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def check_password(self, password: str) -> bool:
        """Check password for private room"""
        if not self.password_hash:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))
        except ValueError:
            return False

    def get_invitation_link(self) -> str:
        """Get invitation link for this room"""
        if not self.room_no:
            return ""
        return f"/rooms/join/{self.room_no}"


def generate_room_no(db_session) -> str:
    """Generate a unique room_no: random shuffled prefix + UUID7 portion
    Args:
        db_session: SQLAlchemy session to check uniqueness
    """
    max_attempts = 10
    for _ in range(max_attempts):
        # Generate random alphanumeric prefix (6-8 characters, shuffled)
        prefix_length = random.randint(6, 8)
        chars = string.ascii_letters + string.digits
        prefix = ''.join(random.sample(chars, prefix_length))
        
        # Generate UUID7 and take a portion
        uuid7_value = str(uuid7())
        # Take last 5-6 characters from UUID7 (after removing hyphens)
        uuid7_clean = uuid7_value.replace('-', '')
        uuid7_suffix = uuid7_clean[-6:]
        
        # Combine: prefix + uuid7_suffix
        room_no = prefix + uuid7_suffix
        
        # Check uniqueness using provided session
        existing = db_session.query(Room).filter_by(room_no=room_no).first()
        if not existing:
            return room_no
    
    # Fallback: if all attempts fail, use timestamp-based approach
    import time
    timestamp = int(time.time())
    random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    fallback_no = f"{random_suffix}{timestamp % 100000}"
    
    # Check fallback uniqueness
    existing = db_session.query(Room).filter_by(room_no=fallback_no).first()
    if existing:
        # Last resort: add more randomness
        import uuid as uuid_lib
        return f"{random_suffix}{uuid_lib.uuid4().hex[:6]}"
    
    return fallback_no


