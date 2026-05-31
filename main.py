from datetime import date, datetime, timedelta
from functools import wraps
import hmac
import os
import secrets

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from mysql.connector import Error as MySQLError

try:
    from authlib.integrations.flask_client import OAuth
except ImportError:
    OAuth = None

from DataBase import check_database_health
from models import (
    add_stu,
    add_user,
    check_user,
    get_attendance_reports,
    get_dashboard_summary,
    get_or_create_google_user,
    get_recent_records,
    get_student_dashboard,
    get_students_for_attendance,
    is_valid_email,
    request_student_signup_otp,
    verify_student_signup_otp,
    mark_attendance,
    today_iso,
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECURE_KEY", "dev-key")
app.permanent_session_lifetime = timedelta(hours=8)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    or os.getenv("APP_ENV", "").lower() == "production",
)

google_oauth = None
if OAuth and os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
    oauth = OAuth(app)
    google_oauth = oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


app.jinja_env.globals["csrf_token"] = csrf_token


@app.context_processor
def inject_template_flags():
    return {
        "google_oauth_enabled": google_oauth is not None,
        "app_name": "Attendly",
    }


@app.before_request
def protect_forms():
    if request.method != "POST":
        return None

    expected = session.get("_csrf_token")
    submitted = request.form.get("csrf_token")
    if not expected or not submitted or not hmac.compare_digest(expected, submitted):
        return render_template(
            "error.html",
            title="Security check failed",
            message="The form session expired. Please go back and try again.",
        ), 400

    return None


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


def start_session(username, role):
    session.clear()
    session.permanent = True
    session["user"] = username
    session["role"] = role
    csrf_token()


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


@app.route("/")
def home_page():
    return render_template("home_page.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_id = request.form.get("login_id", "").strip()
        password = request.form.get("password", "")
        user_role = request.form.get("user_type", "")

        if check_user(login_id, password, user_role):
            start_session(login_id, user_role)

            if user_role == "student":
                return redirect(url_for("student_dashboard"))
            return redirect(url_for("lecturer_dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/auth/google")
def google_login():
    if not google_oauth:
        return render_template(
            "error.html",
            title="Google sign-in is not configured",
            message="Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in production to enable Google OAuth.",
        ), 503

    redirect_uri = url_for("google_callback", _external=True)
    return google_oauth.authorize_redirect(redirect_uri)


@app.route("/auth/google/callback")
def google_callback():
    if not google_oauth:
        return redirect(url_for("login"))

    token = google_oauth.authorize_access_token()
    userinfo = token.get("userinfo") or google_oauth.userinfo()
    email = userinfo.get("email")
    name = userinfo.get("name") or userinfo.get("given_name")
    subject = userinfo.get("sub")

    if not email or not subject:
        return render_template(
            "error.html",
            title="Google sign-in failed",
            message="Google did not return a verified account profile.",
        ), 400

    username, role = get_or_create_google_user(email, name, subject)
    start_session(username, role)

    if role == "lecturer":
        return redirect(url_for("lecturer_dashboard"))
    return redirect(url_for("student_dashboard"))


@app.route("/register", methods=["GET", "POST"])
def reg():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        username = request.form.get("user_name", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not username or not password:
            return render_template("reg.html", error="All fields are required")

        if not is_valid_email(email):
            return render_template("reg.html", error="Enter a valid email address")

        if len(password) < 8:
            return render_template("reg.html", error="Password must be at least 8 characters")

        if not add_user(name, username, password, "lecturer", email=email):
            return render_template("reg.html", error="User already exists")

        flash("Lecturer account created. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("reg.html")


@app.route("/student/signup", methods=["GET", "POST"])
def student_signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return render_template("student_signup.html", error="All fields are required")

        if not is_valid_email(email):
            return render_template("student_signup.html", error="Enter a valid email address")

        if len(password) < 8:
            return render_template("student_signup.html", error="Password must be at least 8 characters")

        ok, message, pending_email = request_student_signup_otp(name, email, password)
        if not ok:
            return render_template("student_signup.html", error=message)

        flash(message, "success")
        return redirect(url_for("verify_student_otp", email=pending_email))

    return render_template("student_signup.html")


@app.route("/student/verify", methods=["GET", "POST"])
def verify_student_otp():
    email = request.values.get("email", "").strip()

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        otp = request.form.get("otp", "").strip()

        if not email or not otp:
            return render_template("verify_otp.html", email=email, error="Email and OTP are required")

        ok, result = verify_student_signup_otp(email, otp)
        if not ok:
            return render_template("verify_otp.html", email=email, error=result)

        start_session(result, "student")
        return redirect(url_for("student_dashboard"))

    return render_template("verify_otp.html", email=email)


@app.route("/student")
@login_required("student")
def student_dashboard():
    summary, stats = get_student_dashboard(session["user"])
    return render_template(
        "student.html",
        stats=stats,
        summary=summary,
        user=session["user"],
        active_page="student_dashboard",
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
        active_page="dashboard",
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
            active_page="students",
        )

    return render_template("add_student.html", active_page="students")


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
        active_page="attendance",
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
        active_page="report",
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
