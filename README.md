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

3. Database Setup

   **3.1. Create MySQL Database**
   
   Connect to MySQL and create the database:
   ```bash
   mysql -u root -p
   ```
   
   Then in MySQL console:
   ```sql
   CREATE DATABASE `chat-python` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
   
   Or if you prefer a different database name, update the `DB_NAME` in `.env` file (see step 3.2).
   
   **3.2. Environment Configuration**
Create `.env` file in project root:
```bash
# Flask Secret Key
SECRET_KEY=your-secret-key-here

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=chat-python

# Optional: Override DATABASE_URL directly (takes precedence over above DB_* vars)
# DATABASE_URL=mysql+pymysql://root:@localhost/chat-python?charset=utf8mb4

# Session Security (for production)
SESSION_COOKIE_SECURE=false

# Email Configuration (for feedback notifications)
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password
MAIL_FROM=noreply@example.com
MAIL_TO=admin@example.com
```

If `.env` file is not provided, defaults will be used:
- DB_HOST=localhost
- DB_PORT=3306
- DB_USER=root
- DB_PASSWORD=(empty)
- DB_NAME=chat-python
- MAIL_SERVER=localhost
- MAIL_PORT=587
- MAIL_USE_TLS=true
- MAIL_FROM=noreply@example.com
- MAIL_TO=admin@example.com

4. Initialize Database Tables

   When you first run the application, it will automatically:
   - Create all database tables (`users`, `rooms`, `room_memberships`, `messages`, `feedbacks`) using SQLAlchemy models
   - Add missing columns if tables already exist (auto-migration)
   - Seed an admin user (`admin@example.com` / `admin123`) and default rooms
   
   **No manual migration needed** - tables are created automatically via `db.create_all()` on startup.

5. Run

   **Development Mode (Recommended):**
   ```bash
   python wsgi.py
   ```
   - Visit http://localhost:5000/
   - Login via API: `POST /auth/login` with `{ "email":"admin@example.com", "password":"admin123" }`
   
   **Production Mode (uWSGI):**
   ```bash
   uwsgi --ini uwsgi.ini
   ```
   Or with custom settings:
   ```bash
   uwsgi --module wsgi:application --http 0.0.0.0:5000 --threads 10 --enable-threads
   ```

6. (Optional) Seed demo data via console
```bash
python scripts/seed_demo.py
```
This creates example member accounts (`alice@example.com`, `bob@example.com`) with sample messages.

## API

### Authentication
- POST `/auth/login`, POST `/auth/logout`, GET `/auth/me`

### Rooms
- GET `/rooms`, POST `/rooms/<id>/join`, POST `/rooms/<id>/leave`
- GET `/rooms/<id>/messages?before=<iso>&limit=50`
- Admin: POST `/admin/rooms`, PUT `/admin/rooms/<id>`, DELETE `/admin/rooms/<id>`

### Feedback
- POST `/feedback` - Submit feedback form
  - Body: `{ "name": "string", "email": "string", "subject": "string", "message": "string" }`
  - Saves to database and sends email notification

## Socket.IO (/chat)
- join_room { room_id }
- leave_room { room_id }
- send_message { room_id, content }
- typing { room_id, is_typing }
- admin_broadcast { content } (admin only)

## Database Schema

The application uses the following tables:
- `users` - User accounts (email, password_hash, name, role, image)
- `rooms` - Chat rooms (name, created_by, is_active)
- `room_memberships` - User-room relationships (user_id, room_id, joined_at)
- `messages` - Chat messages (room_id, author_id, content, created_at)
- `feedbacks` - User feedback submissions (name, email, subject, message, user_id, created_at)

All tables are created automatically on first run via SQLAlchemy's `db.create_all()`.

## Deployment Notes

### Development
- Run `python wsgi.py` for development server with Socket.IO support
- Uses eventlet for async Socket.IO handling

### Production (uWSGI)
- Configuration file: `uwsgi.ini`
- Flask-SocketIO uses threading mode, so uWSGI should use threads (not gevent/async)
- Command: `uwsgi --ini uwsgi.ini`
- Ensure `wsgi.py` exports `application` variable for uWSGI

### Troubleshooting uWSGI
If you see "no python application found":
1. Check that `wsgi.py` has `application = app` exported
2. Verify uWSGI config: `module = wsgi:application`
3. Check logs: `/tmp/uwsgi.log` or stdout/stderr
4. Ensure Python path is correct: `pythonpath = %d` in uwsgi.ini

## Features

### Feedback System
- Users can submit feedback via the "Feedback" button in the top navigation bar
- Feedback is saved to the database and automatically sent via email to the configured `MAIL_TO` address
- If the user is logged in, their `user_id` is automatically associated with the feedback
- Email configuration is optional - if email fails, feedback is still saved to the database

### Email Configuration
To enable email notifications for feedback:
1. Configure SMTP settings in `.env` file (see Environment Configuration above)
2. Ensure `MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD` are set correctly
3. Set `MAIL_TO` to the email address where feedback notifications should be sent

If email is not configured or fails, feedback submissions will still be saved to the database.

## Notes
- First run seeds an admin user (`admin@example.com` / `admin123`) and default rooms automatically.
- Table structure is automatically created - no manual SQL scripts needed.
- For production, configure CORS and session security settings in `.env`.
- Feedback email notifications require proper SMTP configuration in `.env`.

