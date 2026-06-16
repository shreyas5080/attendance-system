# Attendly - Student Attendance Management System

A production-ready Flask attendance app with lecturer dashboards, student self-signup, email OTP validation, Google OAuth, date-based attendance, and reporting.

## Features

- Lecturer and student login with username or email
- Google OAuth login through Authlib
- Student self-signup with hashed email OTP validation
- Lecturer-created managed student credentials
- Date-based attendance marking
- Present, absent, and unmarked summaries
- Student dashboard with attendance percentage
- Date-range reports with eligibility status
- Health endpoint at `/health`
- Secure session cookie settings and CSRF-protected forms
- Shared production UI system and SVG logo

## Environment Variables

Create a `.env` file:

```env
SECURE_KEY=change_this_secret_key
APP_ENV=production
SESSION_COOKIE_SECURE=true

DB_HOST=your_database_host
DB_PORT=your_database_port
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_NAME=my_database
DB_SSL_CA=/etc/ssl/certs/ca-certificates.crt

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=your_email@example.com
```

For Google OAuth, add this authorized redirect URI in Google Cloud:

```text
https://your-production-domain/auth/google/callback
```

For local testing:

```text
http://127.0.0.1:5000/auth/google/callback
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Open:

```text
http://127.0.0.1:5000/
```

## Database

The app keeps the original tables and adds production auth fields automatically when the first auth/database action runs.

Base schema:

```sql
CREATE TABLE users(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    user_name VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    user_role ENUM('lecturer','student'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE students(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200),
    user_id INT UNIQUE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE attendance(
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    date DATE,
    status BOOLEAN DEFAULT 0,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE(student_id, date)
);
```

Optional manual migration is available at:

```text
migrations/001_auth_and_otp.sql
```

## Production Notes

- Set `SECURE_KEY` to a long random value.
- Set `SESSION_COOKIE_SECURE=true` when serving over HTTPS.
- Configure SMTP before enabling production OTP signup.
- Configure Google OAuth credentials before showing Google login to users.
- Check `/health` after deploy to confirm the app and database are reachable.

## 📄 LICENSE

This project available under the MIT License

---
**Last Updated**: 16 june 2026
