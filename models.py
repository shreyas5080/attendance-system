from datetime import date
import secrets
import string

from werkzeug.security import check_password_hash, generate_password_hash

from DataBase import init_database


def today_iso():
    return date.today().isoformat()


def generate_username(name, length=4):
    characters = string.ascii_lowercase + string.digits
    random_part = "".join(secrets.choice(characters) for _ in range(length))
    return f"{name.lower().replace(' ', '')}@{random_part}"


def generate_password(length=10):
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(characters) for _ in range(length))


def generate_unique_username(cur, name):
    while True:
        username = generate_username(name)
        cur.execute("SELECT id FROM users WHERE user_name=%s", (username,))
        if not cur.fetchone():
            return username


def add_user(name, username, password, role):
    conn = init_database()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE user_name=%s", (username,))
        if cur.fetchone():
            return False

        hashed = generate_password_hash(password)

        cur.execute("""
            INSERT INTO users(name, user_name, password, user_role)
            VALUES(%s, %s, %s, %s)
        """, (name, username, hashed, role))

        conn.commit()
        return True
    finally:
        conn.close()


def check_user(username, password, role):
    conn = init_database()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, password FROM users
            WHERE user_name=%s AND user_role=%s
        """, (username, role))

        user = cur.fetchone()
        if user and check_password_hash(user[1], password):
            return user[0]

        return None
    finally:
        conn.close()


def add_stu(name):
    conn = init_database()
    cur = conn.cursor()
    try:
        username = generate_unique_username(cur, name).lower()
        password = generate_password()
        hashed = generate_password_hash(password)

        cur.execute("""
            INSERT INTO users(name, user_name, password, user_role)
            VALUES(%s, %s, %s, 'student')
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


def get_students():
    conn = init_database()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT s.id, s.name, u.user_name
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
            SELECT s.id, s.name, u.user_name, a.status
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
            WHERE u.user_name = %s
        """, (username,))
        summary = cur.fetchone()

        cur.execute("""
            SELECT a.date, a.status
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            JOIN users u ON s.user_id = u.id
            WHERE u.user_name = %s
            ORDER BY a.date DESC
            LIMIT 10
        """, (username,))
        recent = cur.fetchall()

        return summary, recent
    finally:
        conn.close()
