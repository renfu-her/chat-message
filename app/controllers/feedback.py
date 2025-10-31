from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from flask_mail import Message
from ..extensions import db, mail
from ..models.feedback import Feedback


bp = Blueprint("feedback", __name__, url_prefix="/feedback")


@bp.post("")
def submit_feedback():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()

    # Validation
    if not name:
        return jsonify({"error": "姓名為必填"}), 400
    if not email:
        return jsonify({"error": "Email 為必填"}), 400
    if not subject:
        return jsonify({"error": "主題為必填"}), 400
    if not message:
        return jsonify({"error": "訊息內容為必填"}), 400

    try:
        # Save to database
        feedback = Feedback(
            name=name,
            email=email,
            subject=subject,
            message=message,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        db.session.add(feedback)
        db.session.commit()

        # Send email notification
        try:
            msg = Message(
                subject=f"Feedback: {subject}",
                sender=current_app.config["MAIL_FROM"],
                recipients=[current_app.config["MAIL_TO"]],
                body=f"""收到新的意見回饋：

姓名: {name}
Email: {email}
主題: {subject}

訊息內容:
{message}

---
此信件由系統自動發送
"""
            )
            mail.send(msg)
        except Exception as e:
            # Log email error but don't fail the request
            current_app.logger.error(f"Failed to send feedback email: {str(e)}")

        return jsonify({"ok": True, "message": "意見回饋已送出"})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to save feedback: {str(e)}")
        return jsonify({"error": "提交失敗，請稍後再試"}), 500

