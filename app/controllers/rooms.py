from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from ..extensions import db
from ..models.room import Room
from ..models.membership import RoomMembership
from ..extensions import socketio
from ..services.socketio import _room_key


bp = Blueprint("rooms", __name__)


def _require_admin():
    if not current_user.is_authenticated or current_user.role != "admin":
        return jsonify({"error": "Admin required"}), 403
    return None


@bp.get("/rooms")
@login_required
def list_rooms():
    rooms = Room.query.order_by(Room.name.asc()).all()
    return jsonify([
        {"id": r.id, "name": r.name, "created_by": r.created_by, "created_at": r.created_at.isoformat()}
        for r in rooms
    ])


@bp.post("/rooms/<int:room_id>/join")
@login_required
def join_room_api(room_id: int):
    room = Room.query.get_or_404(room_id)
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


# Admin endpoints
@bp.post("/admin/rooms")
@login_required
def admin_create_room():
    err = _require_admin()
    if err:
        return err
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


@bp.put("/admin/rooms/<int:room_id>")
@login_required
def admin_update_room(room_id: int):
    err = _require_admin()
    if err:
        return err
    room = Room.query.get_or_404(room_id)
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    if Room.query.filter(Room.id != room.id, Room.name == name).first():
        return jsonify({"error": "name exists"}), 409
    room.name = name
    db.session.commit()
    return jsonify({"id": room.id, "name": room.name})


@bp.delete("/admin/rooms/<int:room_id>")
@login_required
def admin_delete_room(room_id: int):
    err = _require_admin()
    if err:
        return err
    room = Room.query.get_or_404(room_id)
    # Emit deletion event to clients in this room before closing
    rk = _room_key(room_id)
    socketio.emit("room_deleted", {"room_id": room_id}, room=rk, namespace="/chat")
    # Delete from DB
    db.session.delete(room)
    db.session.commit()
    # Force clients out of the room on server side
    socketio.close_room(rk, namespace="/chat")
    return jsonify({"ok": True, "room_deleted": room_id})


