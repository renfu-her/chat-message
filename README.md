# Flask Chat (MySQL + Flask-SocketIO)

Requirements: Python 3.12, MySQL server with database `chat-python` (user `root`, empty password).

## Setup

1. Create and activate venv
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows Git Bash
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Environment (optional)
- Create `.env` with `SECRET_KEY=your-secret`
- To override DB URL: `DATABASE_URL=mysql+pymysql://root:@localhost/chat-python?charset=utf8mb4`

4. Run
```bash
python wsgi.py
```
- Visit http://localhost:5000/
- Login via API: `POST /auth/login` with `{ "email":"admin@example.com", "password":"admin123" }`

5. (Optional) Seed demo data via console
```bash
python scripts/seed_demo.py
```
This creates example member accounts (`alice@example.com`, `bob@example.com`) with sample messages.

## API
- POST `/auth/login`, POST `/auth/logout`, GET `/auth/me`
- GET `/rooms`, POST `/rooms/<id>/join`, POST `/rooms/<id>/leave`
- GET `/rooms/<id>/messages?before=<iso>&limit=50`
- Admin: POST `/admin/rooms`, PUT `/admin/rooms/<id>`, DELETE `/admin/rooms/<id>`

## Socket.IO (/chat)
- join_room { room_id }
- leave_room { room_id }
- send_message { room_id, content }
- typing { room_id, is_typing }
- admin_broadcast { content } (admin only)

Notes:
- First run seeds an admin user and `general` room automatically.
- For production, replace eventlet with a production server and configure CORS/session.

