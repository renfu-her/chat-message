from flask import Blueprint, render_template, send_from_directory, current_app, jsonify
from flask_login import login_required
import os


bp = Blueprint("main", __name__)


@bp.get("/")
@login_required
def index():
    return render_template("index.html")


@bp.get("/rooms/join/<room_no>")
@login_required
def join_room_page(room_no: str):
    """Render the join room page"""
    return render_template("rooms/join.html")


@bp.get("/assets/uploads/<filename>")
def uploaded_file(filename):
    """Serve uploaded images from assets/uploads"""
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    filepath = os.path.join(upload_folder, filename)
    
    # Check if file exists
    if not os.path.exists(filepath):
        current_app.logger.warning(f"Image not found: {filepath}")
        return jsonify({"error": "Image not found"}), 404
    
    # Security: ensure filename doesn't contain path traversal
    if os.path.dirname(os.path.abspath(filepath)) != os.path.abspath(upload_folder):
        current_app.logger.warning(f"Path traversal attempt: {filename}")
        return jsonify({"error": "Invalid filename"}), 400
    
    return send_from_directory(upload_folder, filename)


