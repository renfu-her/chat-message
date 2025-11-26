from flask import request
from flask_login import current_user
from flask_socketio import Namespace, emit, join_room as sio_join_room, leave_room as sio_leave_room, disconnect

from ..extensions import socketio, db
from ..models.message import Message


ROOM_KEY_PREFIX = "room:"
# Track online users: {user_id: {name, email, ...}}
online_users = {}


def _room_key(room_id: int) -> str:
    return f"{ROOM_KEY_PREFIX}{room_id}"


class ChatNamespace(Namespace):
    def on_connect(self):
        # Session-based auth; reject unauthenticated
        try:
            if not current_user.is_authenticated:
                return False
        except Exception as e:
            # Log any errors accessing current_user (e.g., session issues)
            import logging
            logging.getLogger(__name__).error(f"Socket.IO connect error: {e}", exc_info=True)
            return False
        # Add to online users
        online_users[current_user.id] = {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role,
        }
        # Send current online users list to the newly connected user (includes self)
        emit("online_users", {"users": list(online_users.values())})
        # Broadcast user online status to other users (exclude self)
        emit("user_online", {"user_id": current_user.id, "name": current_user.name}, broadcast=True, include_self=False)
        # Send ready event to confirm connection
        emit("ready", {"user_id": current_user.id, "role": current_user.role})
        return True

    def on_disconnect(self):
        # Remove from online users
        if current_user.is_authenticated:
            user_id = current_user.id
            if user_id in online_users:
                del online_users[user_id]
            # Broadcast user offline status
            emit("user_offline", {"user_id": user_id}, broadcast=True)
        return

    def on_join_room(self, data):
        room_id = int(data.get("room_id"))
        sio_join_room(_room_key(room_id))
        emit("user_joined", {"room_id": room_id, "user_id": current_user.id}, room=_room_key(room_id))

    def on_leave_room(self, data):
        room_id = int(data.get("room_id"))
        sio_leave_room(_room_key(room_id))
        emit("user_left", {"room_id": room_id, "user_id": current_user.id}, room=_room_key(room_id))

    def on_send_message(self, data):
        room_id = int(data.get("room_id"))
        content = (data.get("content") or "").strip()
        if not content:
            return
        msg = Message(room_id=room_id, user_id=current_user.id, content=content)
        db.session.add(msg)
        db.session.commit()
        payload = {
            "id": msg.id,
            "room_id": room_id,
            "user_id": current_user.id,
            "author_name": getattr(current_user, "name", None),
            "author_image": getattr(current_user, "image", None),
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }
        emit("new_message", payload, room=_room_key(room_id))

    def on_typing(self, data):
        room_id = int(data.get("room_id"))
        is_typing = bool(data.get("is_typing"))
        emit(
            "user_typing",
            {"room_id": room_id, "user_id": current_user.id, "is_typing": is_typing},
            room=_room_key(room_id),
            include_self=False,
        )

    def on_admin_broadcast(self, data):
        if current_user.role != "admin":
            return
        content = (data.get("content") or "").strip()
        if not content:
            return
        emit("admin_broadcast", {"content": content, "user_id": current_user.id}, broadcast=True)


def register_socketio_namespaces():
    socketio.on_namespace(ChatNamespace("/chat"))
    
    # Add global error handler for connection errors
    @socketio.on_error_default
    def default_error_handler(e):
        import logging
        logging.getLogger(__name__).error(f"Socket.IO error: {e}", exc_info=True)
        return False


