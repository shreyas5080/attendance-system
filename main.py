from flask import Flask, render_template, request, url_for, session, redirect, flash
from models import add_stu, add_user, check_user, get_students
from functools import wraps
from DataBase import init_database
from datetime import date
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECURE_KEY", "dev-key")


# ---------------- LOGIN DECORATOR ----------------
def login_required(role=None):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("login"))

            if role and session.get("role") != role:
                return "Unauthorized", 403

            return f(*args, **kwargs)
        return decorated
    return wrapper


# ---------------- HOME ----------------
@app.route("/", methods=["GET", "POST"])
def home_page():
    if request.method == "POST":
        val = request.form.get("H")

        if val == "Login":
            return redirect(url_for("login"))
        elif val == "Register":
            return redirect(url_for("reg"))

    return render_template("home_page.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("user_name", "").strip()
        password = request.form.get("password", "")
        user_role = request.form.get("user_type", "")

        if check_user(username, password, user_role):
            session["user"] = username
            session["role"] = user_role

            if user_role == "student":
                return redirect(url_for("student_dashboard"))
            else:
                return redirect(url_for("lecturer_dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def reg():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("user_name", "").strip()
        password = request.form.get("password", "")
        user_role = "lecturer"

        if not name or not username or not password:
            return render_template("reg.html", error="All fields are required")

        if not add_user(name, username, password, user_role):
            return render_template("reg.html", error="User already exists")

        return redirect(url_for("login"))

    return render_template("reg.html")


# ---------------- STUDENT DASHBOARD ----------------
@app.route("/student")
@login_required("student")
def student_dashboard():
    conn = init_database()
    cur = conn.cursor(dictionary=True)
    user = session["user"]
    query ='''
    SELECT a.date, a.status
    FROM attendance a
    JOIN students s ON a.student_id = s.id
    JOIN users u ON s.user_id = u.id
    WHERE u.user_name = %s
    ORDER BY a.date DESC
    LIMIT 5
    '''
    cur.execute(query, (user,))
    stats = cur.fetchall()
    conn.close()
    return render_template("student.html", stats=stats, user=user)


# ---------------- lecturer DASHBOARD ----------------
@app.route("/lecturer")
@login_required("lecturer")
def lecturer_dashboard():
    conn = init_database()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS present FROM attendance
        WHERE date = CURDATE() AND status = 1
    """)
    present = cursor.fetchone()["present"]

    cursor.execute("""
        SELECT COUNT(*) as absent FROM attendance
        WHERE date = CURDATE() AND status = 0
    """)
    absent = cursor.fetchone()["absent"]

    cursor.execute("""
        SELECT students.name, attendance.date, attendance.status
        FROM attendance
        JOIN students ON students.id = attendance.student_id
        ORDER BY attendance.date DESC
        LIMIT 5
    """)
    records = cursor.fetchall()

    conn.close()

    return render_template(
        "lecturer.html",
        user=session["user"],
        current_date=date.today(),
        total_students=total_students,
        present=present,
        absent=absent,
        records=records
    )


# ---------------- ADD STUDENT ----------------
@app.route("/lecturer/add_student", methods=["GET", "POST"])
@login_required("lecturer")
def add_student():
    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()

        if not student_name:
            return render_template("add_student.html", error="Student name is required")

        # auto-generate credentials
        name = " ".join(student_name.split())

        username, password = add_stu(name)

        return render_template(
            "add_student.html",
            generated_user=username,
            generated_password=password
        )

    return render_template("add_student.html")


#--------------ATTENDANCE----------------
@app.route("/lecturer/attendance")
@login_required("lecturer")
def attendance():
    students = get_students()
    return render_template("attendance.html", students=students)


@app.route("/lecturer/attendance", methods=["POST"])
@login_required("lecturer")
def mark_attentance():
    student_id = request.form.get("student_id")
    status = request.form.get("status")

    if status not in {"0", "1"}:
        flash("Invalid attendance status.", "error")
        return redirect(url_for("attendance"))

    conn = init_database()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO attendance (student_id, date, status)
        VALUES (%s, CURDATE(), %s)
        ON DUPLICATE KEY UPDATE status=%s
    """, (student_id, status, status))

    conn.commit()
    conn.close()

    return redirect(url_for("attendance"))

#-----------------REPORT-----------------
@app.route("/lecturer/report")
@login_required("lecturer")
def report():
    conn = init_database()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT 
            s.id, s.name, 
            COUNT(a.id) AS total_days, 
            SUM(CASE WHEN a.status = 1 THEN 1 ELSE 0 END) AS present_days,
            IFNULL(ROUND((SUM(CASE WHEN a.status = 1 THEN 1 ELSE 0 END) / COUNT(a.id)) * 100, 2), 0) AS percentage
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id
        GROUP BY s.id
    """
    cursor.execute(query)
    reports = cursor.fetchall()
    conn.close()
    
    return render_template("report.html", reports=reports)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- RUN ----------------
if __name__ == "__main__":
    init_database()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
