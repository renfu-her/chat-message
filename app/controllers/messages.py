from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required
from ..models.message import Message


bp = Blueprint("messages", __name__)


@bp.get("/rooms/<int:room_id>/messages")
@login_required
def get_messages(room_id: int):
    try:
        limit = max(1, min(int(request.args.get("limit", 50)), 200))
    except ValueError:
        limit = 50
    before_str = request.args.get("before")
    query = Message.query.filter_by(room_id=room_id)
    if before_str:
        try:
            before_dt = datetime.fromisoformat(before_str)
            query = query.filter(Message.created_at < before_dt)
        except ValueError:
            pass
    msgs = query.order_by(Message.created_at.desc()).limit(limit).all()
    return jsonify([
        {
            "id": m.id,
            "room_id": m.room_id,
            "user_id": m.user_id,
            "author_name": getattr(m.author, "name", None),
            "author_image": getattr(m.author, "image", None),
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in reversed(msgs)
    ])


