from datetime import date, datetime
from functools import wraps
import os

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from mysql.connector import Error as MySQLError

from DataBase import check_database_health
from models import (
    add_stu,
    add_user,
    check_user,
    get_attendance_reports,
    get_dashboard_summary,
    get_recent_records,
    get_student_dashboard,
    get_students_for_attendance,
    mark_attendance,
    today_iso,
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECURE_KEY", "dev-key")


def login_required(role=None):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("login"))

            if role and session.get("role") != role:
                return render_template(
                    "error.html",
                    title="Access denied",
                    message="You do not have permission to view this page.",
                ), 403

            return f(*args, **kwargs)

        return decorated

    return wrapper


def valid_date(value, fallback=None):
    if not value:
        return fallback or today_iso()

    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        flash("Invalid date selected. Showing today's records instead.", "error")
        return fallback or today_iso()


@app.errorhandler(MySQLError)
def handle_database_error(error):
    app.logger.exception("Database error: %s", error)
    return render_template(
        "error.html",
        title="Database unavailable",
        message="The app could not connect to the database. Check production environment variables and try again.",
    ), 503


@app.route("/health")
def health_check():
    ok, message = check_database_health()
    status = 200 if ok else 503
    return jsonify({
        "app": "running",
        "database": "connected" if ok else "error",
        "detail": message,
    }), status


@app.route("/", methods=["GET", "POST"])
def home_page():
    if request.method == "POST":
        val = request.form.get("H")

        if val == "Login":
            return redirect(url_for("login"))
        if val == "Register":
            return redirect(url_for("reg"))

    return render_template("home_page.html")


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
            return redirect(url_for("lecturer_dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def reg():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("user_name", "").strip()
        password = request.form.get("password", "")
        user_role = "lecturer"

        if not name or not username or not password:
            return render_template("reg.html", error="All fields are required")

        if len(password) < 6:
            return render_template("reg.html", error="Password must be at least 6 characters")

        if not add_user(name, username, password, user_role):
            return render_template("reg.html", error="User already exists")

        flash("Account created. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("reg.html")


@app.route("/student")
@login_required("student")
def student_dashboard():
    summary, stats = get_student_dashboard(session["user"])
    return render_template(
        "student.html",
        stats=stats,
        summary=summary,
        user=session["user"],
    )


@app.route("/lecturer")
@login_required("lecturer")
def lecturer_dashboard():
    selected_date = valid_date(request.args.get("date"), today_iso())
    summary = get_dashboard_summary(selected_date)
    records = get_recent_records()

    return render_template(
        "lecturer.html",
        user=session["user"],
        current_date=date.today(),
        selected_date=selected_date,
        summary=summary,
        records=records,
    )


@app.route("/lecturer/add_student", methods=["GET", "POST"])
@login_required("lecturer")
def add_student():
    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()

        if not student_name:
            return render_template("add_student.html", error="Student name is required")

        name = " ".join(student_name.split())
        username, password = add_stu(name)

        return render_template(
            "add_student.html",
            generated_user=username,
            generated_password=password,
        )

    return render_template("add_student.html")


@app.route("/lecturer/attendance")
@login_required("lecturer")
def attendance():
    selected_date = valid_date(request.args.get("date"), today_iso())
    students = get_students_for_attendance(selected_date)
    summary = get_dashboard_summary(selected_date)
    return render_template(
        "attendance.html",
        students=students,
        summary=summary,
        selected_date=selected_date,
    )


@app.route("/lecturer/attendance", methods=["POST"])
@login_required("lecturer")
def mark_attentance():
    student_id = request.form.get("student_id")
    status = request.form.get("status")
    attendance_date = valid_date(request.form.get("attendance_date"), today_iso())

    if not student_id:
        flash("Student is required.", "error")
        return redirect(url_for("attendance", date=attendance_date))

    if status not in {"0", "1"}:
        flash("Invalid attendance status.", "error")
        return redirect(url_for("attendance", date=attendance_date))

    mark_attendance(student_id, status, attendance_date)
    flash("Attendance updated.", "success")
    return redirect(url_for("attendance", date=attendance_date))


@app.route("/lecturer/report")
@login_required("lecturer")
def report():
    start_date = request.args.get("start_date") or None
    end_date = request.args.get("end_date") or None

    if start_date:
        start_date = valid_date(start_date, None)
    if end_date:
        end_date = valid_date(end_date, None)

    reports = get_attendance_reports(start_date, end_date)
    total_classes = sum(row["total_days"] or 0 for row in reports)
    total_present = sum(row["present_days"] or 0 for row in reports)
    average_percentage = round(
        sum(float(row["percentage"] or 0) for row in reports) / len(reports),
        2,
    ) if reports else 0

    return render_template(
        "report.html",
        reports=reports,
        start_date=start_date,
        end_date=end_date,
        total_classes=total_classes,
        total_present=total_present,
        average_percentage=average_percentage,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
