
from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from ..extensions import db
from ..models.room import Room
from ..models.membership import RoomMembership
from ..models.user import User
from ..extensions import socketio
from ..services.socketio import _room_key


bp = Blueprint("rooms", __name__)


def _require_admin():
    if not current_user.is_authenticated or current_user.role != "admin":
        return jsonify({"error": "Admin required"}), 403
    return None


def _require_room_owner(room: Room):
    if not current_user.is_authenticated:
        return jsonify({"error": "需要登入"}), 401
    if room.created_by != current_user.id and current_user.role != "admin":
        return jsonify({"error": "只有房間創建者可以操作"}), 403
    return None


def _require_room_member(room: Room):
    if not current_user.is_authenticated:
        return jsonify({"error": "需要登入"}), 401
    # Check if user is a member of the room
    membership = RoomMembership.query.filter_by(user_id=current_user.id, room_id=room.id).first()
    if not membership and current_user.role != "admin":
        return jsonify({"error": "只有房間成員可以操作"}), 403
    return None


@bp.get("/rooms")
@login_required
def list_rooms():
    rooms = Room.query.filter_by(is_active=True).order_by(Room.name.asc()).all()
    # Get user's memberships
    user_memberships = {m.room_id for m in RoomMembership.query.filter_by(user_id=current_user.id).all()}
    return jsonify([
        {
            "id": r.id,
            "name": r.name,
            "created_by": r.created_by,
            "created_at": r.created_at.isoformat(),
            "is_member": r.id in user_memberships
        }
        for r in rooms
    ])


@bp.post("/rooms/<int:room_id>/join")
@login_required
def join_room_api(room_id: int):
    room = Room.query.get_or_404(room_id)
    if not room.is_active:
        return jsonify({"error": "房間已關閉"}), 400
    exists = RoomMembership.query.filter_by(user_id=current_user.id, room_id=room.id).first()
    if exists:
        return jsonify({"ok": True, "joined": True})
    m = RoomMembership(user_id=current_user.id, room_id=room.id)
    db.session.add(m)
    db.session.commit()
    return jsonify({"ok": True, "joined": True})


@bp.post("/rooms/<int:room_id>/leave")
@login_required
def leave_room_api(room_id: int):
    m = RoomMembership.query.filter_by(user_id=current_user.id, room_id=room_id).first()
    if m:
        db.session.delete(m)
        db.session.commit()
    return jsonify({"ok": True, "left": True})


@bp.get("/members")
@login_required
def list_members():
    members = User.query.filter_by(role="member").order_by(User.name.asc()).all()
    from ..services.socketio import online_users
    online_user_ids = set(online_users.keys())
    return jsonify([
        {
            "id": m.id,
            "name": m.name,
            "email": m.email,
            "image": m.image,
            "created_at": m.created_at.isoformat(),
            "online": m.id in online_user_ids,
        }
        for m in members
    ])


# User room management endpoints
@bp.post("/rooms")
@login_required
def create_room():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    if Room.query.filter_by(name=name).first():
        return jsonify({"error": "name exists"}), 409
    room = Room(name=name, created_by=current_user.id)
    db.session.add(room)
    db.session.commit()
    return jsonify({"id": room.id, "name": room.name}), 201


@bp.put("/rooms/<int:room_id>")
@login_required
def update_room(room_id: int):
    room = Room.query.get_or_404(room_id)
    err = _require_room_owner(room)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    if Room.query.filter(Room.id != room.id, Room.name == name).first():
        return jsonify({"error": "name exists"}), 409
    room.name = name
    db.session.commit()
    return jsonify({"id": room.id, "name": room.name})


@bp.post("/rooms/<int:room_id>/close")
@login_required
def close_room(room_id: int):
    room = Room.query.get_or_404(room_id)
    err = _require_room_member(room)
    if err:
        return err
    room.is_active = False
    db.session.commit()
    # Emit close event to clients in this room
    rk = _room_key(room_id)
    socketio.emit("room_closed", {"room_id": room_id}, room=rk, namespace="/chat")
    socketio.close_room(rk, namespace="/chat")
    return jsonify({"ok": True, "room_closed": room_id})


@bp.delete("/rooms/<int:room_id>")
@login_required
def delete_room(room_id: int):
    room = Room.query.get_or_404(room_id)
    err = _require_room_member(room)
    if err:
        return err
    # Emit deletion event to clients in this room before closing
    rk = _room_key(room_id)
    socketio.emit("room_deleted", {"room_id": room_id}, room=rk, namespace="/chat")
    # Delete from DB
    db.session.delete(room)
    db.session.commit()
    # Force clients out of the room on server side
    socketio.close_room(rk, namespace="/chat")
    return jsonify({"ok": True, "room_deleted": room_id})


# Admin endpoints


