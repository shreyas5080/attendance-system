from datetime import date, datetime, timedelta
import re
import secrets
import string

from werkzeug.security import check_password_hash, generate_password_hash

from DataBase import ensure_auth_schema, init_database
from mail_service import send_otp_email

OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 5

_schema_ready = False


def ensure_schema_ready():
    global _schema_ready
    if not _schema_ready:
        ensure_auth_schema()
        _schema_ready = True


def today_iso():
    return date.today().isoformat()


def normalize_email(email):
    return (email or "").strip().lower()


def is_valid_email(email):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalize_email(email)))


def generate_username(name, length=4):
    characters = string.ascii_lowercase + string.digits
    random_part = "".join(secrets.choice(characters) for _ in range(length))
    return f"{name.lower().replace(' ', '')}@{random_part}"


def generate_email_username(email):
    return normalize_email(email)


def generate_password(length=10):
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(characters) for _ in range(length))


def generate_otp():
    return "".join(secrets.choice(string.digits) for _ in range(6))


def generate_unique_username(cur, name):
    while True:
        username = generate_username(name)
        cur.execute("SELECT id FROM users WHERE user_name=%s", (username,))
        if not cur.fetchone():
            return username


def user_exists(cur, username=None, email=None):
    if email:
        cur.execute("SELECT id FROM users WHERE email=%s OR user_name=%s", (email, email))
        if cur.fetchone():
            return True

    if username:
        cur.execute("SELECT id FROM users WHERE user_name=%s", (username,))
        if cur.fetchone():
            return True

    return False


def add_user(name, username, password, role, email=None):
    ensure_schema_ready()
    email = normalize_email(email)
    conn = init_database()
    cur = conn.cursor()
    try:
        if user_exists(cur, username=username, email=email):
            return False

        hashed = generate_password_hash(password)

        cur.execute("""
            INSERT INTO users(
                name, user_name, email, password, user_role,
                auth_provider, is_verified
            )
            VALUES(%s, %s, %s, %s, %s, 'password', 1)
        """, (name, username, email or None, hashed, role))

        conn.commit()
        return True
    finally:
        conn.close()


def check_user(login_id, password, role):
    ensure_schema_ready()
    login_id = (login_id or "").strip()
    conn = init_database()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, password
            FROM users
            WHERE (user_name=%s OR email=%s)
                AND user_role=%s
                AND is_verified=1
        """, (login_id, login_id.lower(), role))

        user = cur.fetchone()
        if user and check_password_hash(user[1], password):
            cur.execute("UPDATE users SET last_login_at=NOW() WHERE id=%s", (user[0],))
            conn.commit()
            return user[0]

        return None
    finally:
        conn.close()


def add_stu(name):
    ensure_schema_ready()
    conn = init_database()
    cur = conn.cursor()
    try:
        username = generate_unique_username(cur, name).lower()
        password = generate_password()
        hashed = generate_password_hash(password)

        cur.execute("""
            INSERT INTO users(
                name, user_name, password, user_role,
                auth_provider, is_verified
            )
            VALUES(%s, %s, %s, 'student', 'password', 1)
        """, (name, username, hashed))

        user_id = cur.lastrowid

        cur.execute("""
            INSERT INTO students(name, user_id)
            VALUES(%s, %s)
        """, (name, user_id))

        conn.commit()
        return username, password
    finally:
        conn.close()


def request_student_signup_otp(name, email, password):
    ensure_schema_ready()
    email = normalize_email(email)
    username = generate_email_username(email)
    otp = generate_otp()
    otp_hash = generate_password_hash(otp)
    password_hash = generate_password_hash(password)
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    conn = init_database()
    cur = conn.cursor()
    try:
        if user_exists(cur, username=username, email=email):
            return False, "An account already exists for this email.", None

        cur.execute("""
            INSERT INTO otp_verifications(
                name, email, user_name, password_hash, otp_hash, expires_at, attempts
            )
            VALUES(%s, %s, %s, %s, %s, %s, 0)
            ON DUPLICATE KEY UPDATE
                name=VALUES(name),
                user_name=VALUES(user_name),
                password_hash=VALUES(password_hash),
                otp_hash=VALUES(otp_hash),
                expires_at=VALUES(expires_at),
                attempts=0,
                consumed_at=NULL
        """, (name, email, username, password_hash, otp_hash, expires_at))

        conn.commit()
    finally:
        conn.close()

    sent, message = send_otp_email(email, otp)
    if not sent:
        return False, message, None

    return True, message, email


def verify_student_signup_otp(email, otp):
    ensure_schema_ready()
    email = normalize_email(email)
    conn = init_database()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT *
            FROM otp_verifications
            WHERE email=%s AND consumed_at IS NULL
            LIMIT 1
        """, (email,))
        pending = cur.fetchone()

        if not pending:
            return False, "No pending verification was found."

        if pending["expires_at"] < datetime.utcnow():
            return False, "This OTP has expired. Please request a new one."

        if pending["attempts"] >= MAX_OTP_ATTEMPTS:
            return False, "Too many attempts. Please request a new OTP."

        if not check_password_hash(pending["otp_hash"], otp):
            cur.execute("""
                UPDATE otp_verifications
                SET attempts = attempts + 1
                WHERE id=%s
            """, (pending["id"],))
            conn.commit()
            return False, "Invalid OTP."

        if user_exists(cur, username=pending["user_name"], email=email):
            return False, "An account already exists for this email."

        cur.execute("""
            INSERT INTO users(
                name, user_name, email, password, user_role,
                auth_provider, is_verified
            )
            VALUES(%s, %s, %s, %s, 'student', 'password', 1)
        """, (
            pending["name"],
            pending["user_name"],
            pending["email"],
            pending["password_hash"],
        ))
        user_id = cur.lastrowid

        cur.execute("""
            INSERT INTO students(name, user_id)
            VALUES(%s, %s)
        """, (pending["name"], user_id))

        cur.execute("""
            UPDATE otp_verifications
            SET consumed_at=NOW()
            WHERE id=%s
        """, (pending["id"],))

        conn.commit()
        return True, pending["user_name"]
    finally:
        conn.close()


def get_or_create_google_user(email, name, oauth_subject):
    ensure_schema_ready()
    email = normalize_email(email)
    username = generate_email_username(email)
    display_name = name or email.split("@")[0]
    conn = init_database()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, user_name, user_role
            FROM users
            WHERE auth_provider='google' AND oauth_subject=%s
            LIMIT 1
        """, (oauth_subject,))
        user = cur.fetchone()

        if not user:
            cur.execute("""
                SELECT id, user_name, user_role
                FROM users
                WHERE email=%s OR user_name=%s
                LIMIT 1
            """, (email, email))
            user = cur.fetchone()

        if user:
            cur.execute("""
                UPDATE users
                SET email=%s,
                    auth_provider='google',
                    oauth_subject=%s,
                    is_verified=1,
                    last_login_at=NOW()
                WHERE id=%s
            """, (email, oauth_subject, user["id"]))

            if user["user_role"] == "student":
                cur.execute("SELECT id FROM students WHERE user_id=%s", (user["id"],))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO students(name, user_id)
                        VALUES(%s, %s)
                    """, (display_name, user["id"]))

            conn.commit()
            return user["user_name"], user["user_role"]

        fallback_hash = generate_password_hash(secrets.token_urlsafe(32))
        cur.execute("""
            INSERT INTO users(
                name, user_name, email, password, user_role,
                auth_provider, oauth_subject, is_verified, last_login_at
            )
            VALUES(%s, %s, %s, %s, 'student', 'google', %s, 1, NOW())
        """, (display_name, username, email, fallback_hash, oauth_subject))
        user_id = cur.lastrowid

        cur.execute("""
            INSERT INTO students(name, user_id)
            VALUES(%s, %s)
        """, (display_name, user_id))

        conn.commit()
        return username, "student"
    finally:
        conn.close()


def get_students():
    conn = init_database()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT s.id, s.name, u.user_name, u.email
            FROM students s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.name
        """)
        return cur.fetchall()
    finally:
        conn.close()


def get_dashboard_summary(attendance_date=None):
    attendance_date = attendance_date or today_iso()
    conn = init_database()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT COUNT(*) AS total FROM students")
        total_students = cur.fetchone()["total"]

        cur.execute("""
            SELECT
                SUM(CASE WHEN a.status = 1 THEN 1 ELSE 0 END) AS present,
                SUM(CASE WHEN a.status = 0 THEN 1 ELSE 0 END) AS absent,
                COUNT(a.id) AS marked
            FROM students s
            LEFT JOIN attendance a
                ON a.student_id = s.id AND a.date = %s
        """, (attendance_date,))
        summary = cur.fetchone()

        present = summary["present"] or 0
        absent = summary["absent"] or 0
        marked = summary["marked"] or 0
        unmarked = max(total_students - marked, 0)
        attendance_rate = round((present / total_students) * 100, 2) if total_students else 0

        return {
            "date": attendance_date,
            "total_students": total_students,
            "present": present,
            "absent": absent,
            "marked": marked,
            "unmarked": unmarked,
            "attendance_rate": attendance_rate,
        }
    finally:
        conn.close()


def get_recent_records(limit=8):
    conn = init_database()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT s.name, attendance.date, attendance.status
            FROM attendance
            JOIN students s ON s.id = attendance.student_id
            ORDER BY attendance.date DESC, attendance.id DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()
    finally:
        conn.close()


def get_students_for_attendance(attendance_date=None):
    attendance_date = attendance_date or today_iso()
    conn = init_database()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT s.id, s.name, u.user_name, u.email, a.status
            FROM students s
            JOIN users u ON s.user_id = u.id
            LEFT JOIN attendance a
                ON a.student_id = s.id AND a.date = %s
            ORDER BY s.name
        """, (attendance_date,))
        return cur.fetchall()
    finally:
        conn.close()


def mark_attendance(student_id, status, attendance_date=None):
    attendance_date = attendance_date or today_iso()
    conn = init_database()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO attendance (student_id, date, status)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE status=%s
        """, (student_id, attendance_date, status, status))

        conn.commit()
    finally:
        conn.close()


def get_attendance_reports(start_date=None, end_date=None):
    join_filters = []
    params = []

    if start_date:
        join_filters.append("a.date >= %s")
        params.append(start_date)
    if end_date:
        join_filters.append("a.date <= %s")
        params.append(end_date)

    date_filter = ""
    if join_filters:
        date_filter = " AND " + " AND ".join(join_filters)

    conn = init_database()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(f"""
            SELECT
                s.id,
                s.name,
                COUNT(a.id) AS total_days,
                IFNULL(SUM(CASE WHEN a.status = 1 THEN 1 ELSE 0 END), 0) AS present_days,
                IFNULL(SUM(CASE WHEN a.status = 0 THEN 1 ELSE 0 END), 0) AS absent_days,
                IFNULL(
                    ROUND(
                        (SUM(CASE WHEN a.status = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(a.id), 0)) * 100,
                        2
                    ),
                    0
                ) AS percentage
            FROM students s
            LEFT JOIN attendance a ON s.id = a.student_id{date_filter}
            GROUP BY s.id, s.name
            ORDER BY percentage DESC, s.name
        """, params)
        return cur.fetchall()
    finally:
        conn.close()


def get_student_dashboard(username):
    conn = init_database()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT
                COUNT(a.id) AS total_days,
                IFNULL(SUM(CASE WHEN a.status = 1 THEN 1 ELSE 0 END), 0) AS present_days,
                IFNULL(SUM(CASE WHEN a.status = 0 THEN 1 ELSE 0 END), 0) AS absent_days,
                IFNULL(
                    ROUND(
                        (SUM(CASE WHEN a.status = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(a.id), 0)) * 100,
                        2
                    ),
                    0
                ) AS percentage
            FROM users u
            JOIN students s ON s.user_id = u.id
            LEFT JOIN attendance a ON a.student_id = s.id
            WHERE u.user_name = %s OR u.email = %s
        """, (username, username))
        summary = cur.fetchone()

        cur.execute("""
            SELECT a.date, a.status
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            JOIN users u ON s.user_id = u.id
            WHERE u.user_name = %s OR u.email = %s
            ORDER BY a.date DESC
            LIMIT 10
        """, (username, username))
        recent = cur.fetchall()

        return summary, recent
    finally:
        conn.close()
