from flask import Blueprint, request, jsonify, render_template, send_from_directory, current_app
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename
import os
from PIL import Image
try:
    from uuid7 import uuid7
except ImportError:
    # Fallback: simple UUID7-like generator using timestamp + random
    import time
    import random
    def uuid7():
        """Simple UUID7-like generator (timestamp + random)"""
        timestamp_ms = int(time.time() * 1000)
        random_part = random.randint(0, 0xFFFFFFFFFFFF)
        return f"{timestamp_ms:013x}-{random_part:012x}"
from ..extensions import db
from ..models.user import User


bp = Blueprint("auth", __name__, url_prefix="/auth")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


@bp.get("/login")
def login_view():
    return render_template("auth/login.html")


@bp.get("/profile")
@login_required
def profile_view():
    return render_template("auth/profile.html")


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email 和密碼為必填"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "帳號或密碼錯誤"}), 401

    login_user(user)
    return jsonify({"ok": True, "user": {"id": user.id, "email": user.email, "name": user.name, "image": user.image, "role": user.role}})


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
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "name": current_user.name,
                "image": current_user.image,
                "role": current_user.role,
            },
        }
    )


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()

    if not email or not password or not name:
        return jsonify({"error": "姓名、Email 和密碼為必填"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email 重覆"}), 409

    try:
        user = User(email=email, role="member", name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        persisted = User.query.filter_by(email=email).first()
        if not persisted:
            raise RuntimeError("User not persisted after commit")
        login_user(persisted)
        return (
            jsonify({
                "ok": True,
                "user": {
                    "id": persisted.id,
                    "email": persisted.email,
                    "name": persisted.name,
                    "image": persisted.image,
                    "role": persisted.role,
                },
            }),
            201,
        )
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Email 重覆"}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "註冊失敗", "detail": str(e)}), 500


@bp.post("/profile/upload")
@login_required
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "沒有選擇檔案"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "沒有選擇檔案"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "檔案格式不支援，僅支援 PNG, JPG, JPEG, GIF"}), 400
    
    try:
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)
        
        # Generate UUID7 for filename
        uuid7_value = uuid7()
        filename = f"{uuid7_value}.webp"
        filepath = os.path.join(upload_folder, filename)
        
        # Open and convert image to WebP
        image = Image.open(file.stream)
        # Convert RGBA to RGB if necessary (WebP doesn't support RGBA in all cases)
        if image.mode in ('RGBA', 'LA', 'P'):
            # Create a white background
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = rgb_image
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Save as WebP with quality optimization
        image.save(filepath, 'WEBP', quality=85, method=6)
        
        # Verify file was saved
        if not os.path.exists(filepath):
            raise RuntimeError(f"File was not saved: {filepath}")
        
        current_app.logger.info(f"Image saved: {filepath}, size: {os.path.getsize(filepath)} bytes")
        
        # Update user image
        old_image = current_user.image
        current_user.image = filename
        db.session.commit()
        
        # Delete old image if exists
        if old_image:
            old_filepath = os.path.join(upload_folder, old_image)
            if os.path.exists(old_filepath):
                try:
                    os.remove(old_filepath)
                    current_app.logger.info(f"Deleted old image: {old_filepath}")
                except Exception as e:
                    current_app.logger.warning(f"Failed to delete old image: {e}")
        
        return jsonify({"ok": True, "image": filename})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to upload image: {str(e)}")
        return jsonify({"error": "上傳失敗", "detail": str(e)}), 500


@bp.put("/profile")
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    password = data.get("password") or ""
    
    if not name:
        return jsonify({"error": "姓名為必填"}), 400
    
    try:
        user = current_user
        user.name = name
        
        if password:
            user.set_password(password)
        
        db.session.commit()
        return jsonify({
            "ok": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "image": user.image,
                "role": user.role,
            },
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "更新失敗", "detail": str(e)}), 500


