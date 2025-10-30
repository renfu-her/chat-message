from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db
from ..models.user import User


bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    login_user(user)
    return jsonify({"ok": True, "user": {"id": user.id, "email": user.email, "role": user.role}})


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"ok": True})


@bp.get("/me")
def me():
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False})
    return jsonify(
        {
            "authenticated": True,
            "user": {"id": current_user.id, "email": current_user.email, "role": current_user.role},
        }
    )


