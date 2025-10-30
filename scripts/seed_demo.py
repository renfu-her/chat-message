"""Seed demo data via console.

Run: python scripts/seed_demo.py
"""

from datetime import datetime

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.room import Room
from app.models.membership import RoomMembership
from app.models.message import Message


def main():
    app = create_app()
    with app.app_context():
        db.create_all()

        # Admin seeded via app factory, ensure exists now
        admin = User.query.filter_by(email="admin@example.com").first()

        demo_users = [
            {"name": "Alice", "email": "alice@example.com", "password": "alicepass"},
            {"name": "Bob", "email": "bob@example.com", "password": "bobpass"},
        ]

        created_users = []
        for data in demo_users:
            user = User.query.filter_by(email=data["email"]).first()
            if not user:
                user = User(name=data["name"], email=data["email"], role="member")
                user.set_password(data["password"])
                db.session.add(user)
                db.session.commit()
                print(f"Created user {data['email']}")
            created_users.append(user)

        rooms = Room.query.order_by(Room.id).all()
        if rooms:
            target_room = rooms[0]
        else:
            target_room = Room(name="Demo Room", created_by=admin.id if admin else created_users[0].id)
            db.session.add(target_room)
            db.session.commit()
            print("Created Demo Room")

        for user in created_users:
            membership = RoomMembership.query.filter_by(user_id=user.id, room_id=target_room.id).first()
            if not membership:
                db.session.add(RoomMembership(user_id=user.id, room_id=target_room.id, joined_at=datetime.utcnow()))
        db.session.commit()

        if not Message.query.filter_by(room_id=target_room.id).first():
            for user in created_users:
                msg = Message(room_id=target_room.id, user_id=user.id, content=f"Hello from {user.name}")
                db.session.add(msg)
            db.session.commit()
            print("Added demo messages")

        print("Seed complete.")


if __name__ == "__main__":
    main()


