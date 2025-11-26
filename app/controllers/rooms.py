
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from ..extensions import db
from ..models.room import Room, generate_room_no
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
        return jsonify({"error": "Login required"}), 401
    if room.created_by != current_user.id and current_user.role != "admin":
        return jsonify({"error": "Only room creator can perform this action"}), 403
    return None


def _require_room_member(room: Room):
    if not current_user.is_authenticated:
        return jsonify({"error": "Login required"}), 401
    # Check if user is a member of the room
    membership = RoomMembership.query.filter_by(user_id=current_user.id, room_id=room.id).first()
    if not membership and current_user.role != "admin":
        return jsonify({"error": "Only room members can perform this action"}), 403
    return None


@bp.get("/rooms")
@login_required
def list_rooms():
    try:
        # Filter rooms based on privacy:
        # - Public rooms: visible to all authenticated users
        # - Private rooms: visible to creator, admins, and members who joined via invitation
        if current_user.role == "admin":
            # Admins can see all rooms
            rooms = Room.query.filter_by(is_active=True).order_by(Room.name.asc()).all()
        else:
            # Get user's memberships to include private rooms they joined
            user_memberships = {m.room_id for m in RoomMembership.query.filter_by(user_id=current_user.id).all()}
            
            # Regular users: public rooms + private rooms they created + private rooms they joined
            # Build query conditions
            conditions = [
                Room.room_type == 'public',
                Room.created_by == current_user.id
            ]
            
            # Add condition for private rooms user joined
            if user_memberships:
                conditions.append(
                    db.and_(
                        Room.room_type == 'private',
                        Room.id.in_(list(user_memberships))
                    )
                )
            
            rooms = Room.query.filter(
                Room.is_active == True,
                db.or_(*conditions)
            ).order_by(Room.name.asc()).all()
        
        # Get user's memberships (re-fetch for response)
        user_memberships = {m.room_id for m in RoomMembership.query.filter_by(user_id=current_user.id).all()}
        return jsonify([
            {
                "id": r.id,
                "name": r.name,
                "room_no": r.room_no or "",  # Handle None values
                "room_type": r.room_type or "public",
                "created_by": r.created_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "is_member": r.id in user_memberships,
                "is_creator": r.created_by == current_user.id,
                "invitation_link": r.get_invitation_link() if r.room_no else ""
            }
            for r in rooms
        ])
    except Exception as e:
        current_app.logger.error(f"Error in /rooms: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


@bp.post("/rooms/<int:room_id>/join")
@login_required
def join_room_api(room_id: int):
    room = Room.query.get_or_404(room_id)
    if not room.is_active:
        return jsonify({"error": "Room is closed"}), 400
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
    try:
        members = User.query.filter_by(role="member").order_by(User.name.asc()).all()
        from ..services.socketio import online_users
        online_user_ids = set(online_users.keys())
        return jsonify([
            {
                "id": m.id,
                "name": m.name or "",
                "email": m.email or "",
                "image": m.image or None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "online": m.id in online_user_ids,
            }
            for m in members
        ])
    except Exception as e:
        current_app.logger.error(f"Error in /members: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


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
    
    room_type = data.get("room_type", "public")
    if room_type not in ["public", "private"]:
        return jsonify({"error": "room_type must be 'public' or 'private'"}), 400
    
    password = data.get("password", "").strip()
    
    # Generate room_no
    room_no = generate_room_no(db.session)
    
    room = Room(
        name=name,
        room_no=room_no,
        room_type=room_type,
        created_by=current_user.id
    )
    
    # Set password if provided for private room
    if room_type == "private" and password:
        room.set_password(password)
    
    db.session.add(room)
    db.session.commit()
    
    return jsonify({
        "id": room.id,
        "name": room.name,
        "room_no": room.room_no,
        "room_type": room.room_type,
        "invitation_link": room.get_invitation_link()
    }), 201


@bp.put("/rooms/<int:room_id>")
@login_required
def update_room(room_id: int):
    room = Room.query.get_or_404(room_id)
    err = _require_room_owner(room)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    
    # Update name if provided
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name required"}), 400
        if Room.query.filter(Room.id != room.id, Room.name == name).first():
            return jsonify({"error": "name exists"}), 409
        room.name = name
    
    # Update room_type if provided
    if "room_type" in data:
        room_type = data.get("room_type")
        if room_type not in ["public", "private"]:
            return jsonify({"error": "room_type must be 'public' or 'private'"}), 400
        room.room_type = room_type
        # Clear password if switching to public
        if room_type == "public":
            room.password_hash = None
    
    # Update password if provided
    if "password" in data:
        password = data.get("password", "").strip()
        if password:
            if room.room_type != "private":
                return jsonify({"error": "password can only be set for private rooms"}), 400
            room.set_password(password)
        elif room.room_type == "private":
            # Empty password means remove password protection
            room.password_hash = None
    
    db.session.commit()
    return jsonify({
        "id": room.id,
        "name": room.name,
        "room_no": room.room_no,
        "room_type": room.room_type,
        "invitation_link": room.get_invitation_link()
    })


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


# Room join by room_no endpoints
@bp.get("/rooms/info/<room_no>")
@login_required
def get_room_info(room_no: str):
    """Get room information by room_no"""
    room = Room.query.filter_by(room_no=room_no, is_active=True).first_or_404()
    
    # Check access permissions
    is_creator = room.created_by == current_user.id
    is_admin = current_user.role == "admin"
    is_member = RoomMembership.query.filter_by(user_id=current_user.id, room_id=room.id).first() is not None
    
    # For private rooms, only creator/admin can see full info
    if room.room_type == "private" and not (is_creator or is_admin):
        return jsonify({
            "id": room.id,
            "name": room.name,
            "room_no": room.room_no,
            "room_type": room.room_type,
            "requires_password": room.password_hash is not None,
            "is_member": is_member
        })
    
    return jsonify({
        "id": room.id,
        "name": room.name,
        "room_no": room.room_no,
        "room_type": room.room_type,
        "created_by": room.created_by,
        "created_at": room.created_at.isoformat(),
        "requires_password": room.password_hash is not None,
        "is_member": is_member,
        "is_creator": is_creator,
        "invitation_link": room.get_invitation_link()
    })


@bp.post("/rooms/join/<room_no>")
@login_required
def join_room_by_no(room_no: str):
    """Join a room by room_no (with password validation for private rooms)"""
    room = Room.query.filter_by(room_no=room_no, is_active=True).first_or_404()
    
    if not room.is_active:
        return jsonify({"error": "Room is closed"}), 400
    
    # Check if already a member
    existing_membership = RoomMembership.query.filter_by(user_id=current_user.id, room_id=room.id).first()
    if existing_membership:
        return jsonify({
            "ok": True,
            "joined": True,
            "room_id": room.id,
            "room_name": room.name
        })
    
    # For private rooms, validate password
    if room.room_type == "private":
        data = request.get_json(silent=True) or {}
        password = data.get("password", "").strip()
        
        # Check if password is required
        if room.password_hash:
            if not password:
                return jsonify({"error": "Password required for private room"}), 400
            if not room.check_password(password):
                return jsonify({"error": "Invalid password"}), 401
    
    # Add user to room
    membership = RoomMembership(user_id=current_user.id, room_id=room.id)
    db.session.add(membership)
    db.session.commit()
    
    return jsonify({
        "ok": True,
        "joined": True,
        "room_id": room.id,
        "room_name": room.name,
        "room_no": room.room_no,
        "room_type": room.room_type
    })


# Admin endpoints


