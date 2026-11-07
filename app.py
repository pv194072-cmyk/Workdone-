import os
import sqlite3
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "workdone.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("WORKDONE_SECRET", "change-this-secret-before-deployment")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()

def init_db():
    connection = sqlite3.connect(DATABASE)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('applicant','board')),
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        education TEXT,
        experience TEXT,
        skills TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        skills TEXT NOT NULL,
        location TEXT,
        created_by INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(created_by) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        applicant_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'Submitted',
        applied_at TEXT NOT NULL,
        UNIQUE(job_id, applicant_id),
        FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
        FOREIGN KEY(applicant_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        interview_type TEXT NOT NULL CHECK(interview_type IN ('Online','Offline')),
        scheduled_at TEXT NOT NULL,
        details TEXT,
        created_by INTEGER NOT NULL,
        FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE,
        FOREIGN KEY(created_by) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS support_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    connection.commit()
    connection.close()

def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in first.", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("You do not have permission to open that page.", "danger")
                return redirect(url_for("home"))
            return view(*args, **kwargs)
        return wrapped
    return decorator

@app.route("/")
def home():
    jobs = db().execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 6").fetchall()
    return render_template("index.html", jobs=jobs)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "applicant")
        invite = request.form.get("invite_code", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name and email, and use a password of at least 8 characters.", "danger")
            return render_template("register.html")
        if role not in ("applicant", "board"):
            flash("Invalid account type.", "danger")
            return render_template("register.html")
        if role == "board":
            expected = os.environ.get("WORKDONE_BOARD_INVITE", "")
            if not expected or invite != expected:
                flash("A valid board invitation code is required. Ask the site administrator.", "danger")
                return render_template("register.html")
        try:
            connection = db()
            cursor = connection.execute(
                "INSERT INTO users(name,email,phone,password_hash,role,created_at) VALUES(?,?,?,?,?,?)",
                (name, email, phone, generate_password_hash(password), role, datetime.utcnow().isoformat())
            )
            user_id = cursor.lastrowid
            if role == "applicant":
                connection.execute("INSERT INTO profiles(user_id,education,experience,skills) VALUES(?,?,?,?)",
                                   (user_id, "", "", ""))
            connection.commit()
            session.clear()
            session.update(user_id=user_id, name=name, role=role)
            flash("Your account has been created.", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=user["id"], name=user["name"], role=user["role"])
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.", "success")
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required()
def dashboard():
    if session["role"] == "board":
        return redirect(url_for("board_dashboard"))
    return redirect(url_for("applicant_dashboard"))

@app.route("/applicant")
@login_required("applicant")
def applicant_dashboard():
    connection = db()
    profile = connection.execute("SELECT * FROM profiles WHERE user_id=?", (session["user_id"],)).fetchone()
    applications = connection.execute("""
        SELECT applications.*, jobs.title, jobs.location FROM applications
        JOIN jobs ON jobs.id=applications.job_id
        WHERE applicant_id=? ORDER BY applications.id DESC
    """, (session["user_id"],)).fetchall()
    interviews = connection.execute("""
        SELECT interviews.*, jobs.title FROM interviews
        JOIN applications ON applications.id=interviews.application_id
        JOIN jobs ON jobs.id=applications.job_id
        WHERE applications.applicant_id=? ORDER BY interviews.scheduled_at
    """, (session["user_id"],)).fetchall()
    return render_template("applicant.html", profile=profile, applications=applications, interviews=interviews)

@app.route("/profile", methods=["POST"])
@login_required("applicant")
def update_profile():
    education = request.form.get("education", "").strip()
    experience = request.form.get("experience", "").strip()
    skills = request.form.get("skills", "").strip()
    db().execute("UPDATE profiles SET education=?, experience=?, skills=? WHERE user_id=?",
                 (education, experience, skills, session["user_id"]))
    db().commit()
    flash("Your profile has been updated.", "success")
    return redirect(url_for("applicant_dashboard"))

@app.route("/jobs")
def jobs():
    all_jobs = db().execute("SELECT jobs.*, users.name AS recruiter FROM jobs JOIN users ON users.id=jobs.created_by ORDER BY jobs.id DESC").fetchall()
    return render_template("jobs.html", jobs=all_jobs)

@app.route("/apply/<int:job_id>", methods=["POST"])
@login_required("applicant")
def apply(job_id):
    try:
        db().execute("INSERT INTO applications(job_id,applicant_id,applied_at) VALUES(?,?,?)",
                     (job_id, session["user_id"], datetime.utcnow().isoformat()))
        db().commit()
        flash("Application submitted successfully.", "success")
    except sqlite3.IntegrityError:
        flash("You have already applied for this job, or the job is no longer available.", "warning")
    return redirect(url_for("jobs"))

@app.route("/board")
@login_required("board")
def board_dashboard():
    connection = db()
    jobs_list = connection.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    applicants = connection.execute("""
        SELECT applications.id AS application_id, applications.status, applications.applied_at,
               users.id AS user_id, users.name, users.email, users.phone, jobs.title,
               profiles.education, profiles.experience, profiles.skills
        FROM applications
        JOIN users ON users.id=applications.applicant_id
        JOIN jobs ON jobs.id=applications.job_id
        LEFT JOIN profiles ON profiles.user_id=users.id
        ORDER BY applications.id DESC
    """).fetchall()
    return render_template("board.html", jobs=jobs_list, applicants=applicants)

@app.route("/board/jobs", methods=["POST"])
@login_required("board")
def create_job():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    skills = request.form.get("skills", "").strip()
    location = request.form.get("location", "").strip()
    if not title or not description or not skills:
        flash("Job title, description and technical skills are required.", "danger")
    else:
        db().execute("INSERT INTO jobs(title,description,skills,location,created_by,created_at) VALUES(?,?,?,?,?,?)",
                     (title, description, skills, location, session["user_id"], datetime.utcnow().isoformat()))
        db().commit()
        flash("Technical job opening published.", "success")
    return redirect(url_for("board_dashboard"))

@app.route("/board/application/<int:application_id>/status", methods=["POST"])
@login_required("board")
def update_application(application_id):
    status = request.form.get("status")
    if status not in ("Submitted", "Shortlisted", "Rejected", "Interview"):
        flash("Invalid application status.", "danger")
    else:
        db().execute("UPDATE applications SET status=? WHERE id=?", (status, application_id))
        db().commit()
        flash("Application status updated.", "success")
    return redirect(url_for("board_dashboard"))

@app.route("/board/application/<int:application_id>/interview", methods=["POST"])
@login_required("board")
def schedule_interview(application_id):
    interview_type = request.form.get("interview_type")
    scheduled_at = request.form.get("scheduled_at", "").strip()
    details = request.form.get("details", "").strip()
    exists = db().execute("SELECT id FROM applications WHERE id=?", (application_id,)).fetchone()
    if not exists or interview_type not in ("Online", "Offline") or not scheduled_at:
        flash("Please provide a valid interview type and date/time.", "danger")
    else:
        db().execute("INSERT INTO interviews(application_id,interview_type,scheduled_at,details,created_by) VALUES(?,?,?,?,?)",
                     (application_id, interview_type, scheduled_at, details, session["user_id"]))
        db().execute("UPDATE applications SET status='Interview' WHERE id=?", (application_id,))
        db().commit()
        flash("Interview invitation created.", "success")
    return redirect(url_for("board_dashboard"))

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if name and email and message:
            db().execute("INSERT INTO support_messages(name,email,message,created_at) VALUES(?,?,?,?)",
                         (name, email, message, datetime.utcnow().isoformat()))
            db().commit()
            flash("Thanks! Your message has been sent to the support inbox.", "success")
            return redirect(url_for("contact"))
        flash("Please complete all fields.", "danger")
    return render_template("contact.html")

@app.errorhandler(413)
def too_large(error):
    flash("That upload is too large.", "danger")
    return redirect(url_for("contact"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
