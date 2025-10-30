from flask import Blueprint, request, jsonify, render_template
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db
from ..models.user import User


bp = Blueprint("auth", __name__, url_prefix="/auth")
@bp.get("/login")
def login_view():
    return render_template("auth/login.html")



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


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()

    if not email or not password or not name:
        return jsonify({"error": "Name, email and password required"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    try:
        user = User(email=email, role="member", name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # assign primary key
        new_id = user.id
        db.session.commit()
        # verify persisted
        persisted = User.query.get(new_id)
        if not persisted:
            raise RuntimeError("User not persisted after commit")
        login_user(user)
        return (
            jsonify({
                "ok": True,
                "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role},
            }),
            201,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Register failed", "detail": str(e)}), 500


