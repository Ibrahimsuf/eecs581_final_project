from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sock import Sock
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import time
import json
import os
import sys
from uuid import uuid4

import ku_jobs_scraper
from davidsscraper import scrape_remoteok
import database_helpers as dbh

# ---------------------------------------------------------
# APP SETUP
# ---------------------------------------------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# Profile photo folder
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

sock = Sock(app)
_db_conn = dbh.setup_db()
dbh.close_db(_db_conn)

# ---------------------------------------------------------
# LOGIN MANAGER SETUP
# ---------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ---------------------------------------------------------
# USER MODEL + HELPERS
# ---------------------------------------------------------
def get_user_by_username(username):
    conn = sqlite3.connect("users.db")
    row = conn.execute(
        "SELECT id, username, password_hash FROM users WHERE username=?",
        (username,),
    ).fetchone()
    conn.close()
    return row


def get_user_by_id(uid):
    conn = sqlite3.connect("users.db")
    row = conn.execute(
        "SELECT id, username, password_hash FROM users WHERE id=?",
        (uid,),
    ).fetchone()
    conn.close()
    return row


class User(UserMixin):
    def __init__(self, uid, username, password_hash):
        self.id = uid
        self.username = username
        self.password_hash = password_hash


@login_manager.user_loader
def load_user(user_id):
    row = get_user_by_id(user_id)
    return User(*row) if row else None


def _derive_job_identifier(job: dict) -> str:
    for key in ("id", "job_id", "url", "uuid", "slug", "name", "title"):
        value = job.get(key)
        if value:
            return str(value)
    return uuid4().hex


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

@app.route("/")
@login_required
def index():
    return render_template("index.html")


# ------------------ LOGIN ------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        row = get_user_by_username(username)
        if row:
            uid, uname, pwhash = row
            if check_password_hash(pwhash, password):
                user = User(uid, uname, pwhash)
                login_user(user)
                return redirect(url_for("index"))

        return "Invalid credentials", 401

    return render_template("login.html")


# ------------------ REGISTER ------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("users.db")
        cur = conn.cursor()

        exists = cur.execute(
            "SELECT 1 FROM users WHERE username=?", (username,)
        ).fetchone()
        if exists:
            return "Username already taken", 400

        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")


# ------------------ LOGOUT ------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------------------------------------------------
# JOB SEARCH
# ---------------------------------------------------------
@app.route("/get_jobs", methods=["POST"])
@login_required
def get_jobs():
    skills = request.form["skills"]

    out = []

    # ------------------------
    # KU job scraper
    # ------------------------
    session = ku_jobs_scraper.get_session()
    try:
        html = ku_jobs_scraper.fetch_html_text(session, ku_jobs_scraper.LIST_URL)
        jobs = ku_jobs_scraper.parse_listings_table(html)

        for job in jobs:
            j = job.to_api_format()

            # Normalize title
            j["title"] = (
                j.get("title")
                or j.get("name")
                or j.get("role")
                or j.get("position")
                or j.get("job_title")
                or "Untitled Role"
            )

            out.append(j)

    except Exception as e:
        print(f"Error fetching KU jobs: {e}", file=sys.stderr)

    # ------------------------
    # RemoteOK scraper
    # ------------------------
    remote_jobs = scrape_remoteok()
    if remote_jobs:
        for job in remote_jobs:

            # Normalize title
            job["title"] = (
                job.get("title")
                or job.get("name")
                or job.get("role")
                or job.get("position")
                or job.get("job_title")
                or "Untitled Role"
            )

            out.append(job)

    # ------------------------
    # Return final results
    # ------------------------
    return jsonify({
        "message": f"Received skills: {skills}",
        "jobs": out
    })



# ---------------------------------------------------------
# PROFILE PAGE + API
# ---------------------------------------------------------
@app.route("/profile")
@login_required
def profile_page():
    return render_template("profile.html")


@app.route("/api/profile", methods=["GET", "POST"])
@login_required
def api_profile():
    conn = dbh.get_db_connection()
    try:
        user_key = current_user.username

        if request.method == "GET":
            profile = dbh.get_user_profile(conn, user_key)
            return jsonify(profile)

        data = request.get_json(silent=True) or request.form
        name = (data.get("name") or "").strip()
        info = (data.get("info") or "").strip()
        soft_skills = (data.get("soft_skills") or "").strip()

        dbh.save_user_profile(
            conn,
            user_key,
            name=name,
            info=info,
            soft_skills=soft_skills,
            photo_path=None,
        )
        profile = dbh.get_user_profile(conn, user_key)
        return jsonify(profile)
    finally:
        dbh.close_db(conn)


@app.route("/api/profile/photo", methods=["POST"])
@login_required
def upload_profile_photo():
    if "photo" not in request.files:
        return jsonify({"error": "no_file"}), 400

    file = request.files["photo"]
    if not file.filename:
        return jsonify({"error": "empty_filename"}), 400

    allowed = {"png", "jpg", "jpeg", "gif"}
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        return jsonify({"error": "invalid_type"}), 400

    filename = f"profile_photo.{ext}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    rel_path = f"uploads/{filename}"

    conn = dbh.get_db_connection()
    try:
        dbh.update_profile_photo(conn, current_user.username, rel_path)
        profile = dbh.get_user_profile(conn, current_user.username)
    finally:
        dbh.close_db(conn)

    return jsonify(profile)


# ---------------------------------------------------------
# WEBSOCKET
# ---------------------------------------------------------
@sock.route("/job_socket")
@login_required
def websocket(ws):
    job_counter = 1

    # initial batch
    batch = [
        {
            "id": str(job_counter),
            "name": "Software Engineer",
            "short_description": "Build and maintain web applications.",
            "skills": ["python", "flask", "sql"],
        },
        {
            "id": str(job_counter + 1),
            "name": "Data Scientist",
            "short_description": "Analyze datasets and build models.",
            "skills": ["python", "pandas", "ml"],
        },
    ]
    job_counter += 2
    ws.send(json.dumps({"type": "jobs", "data": batch}))

    last_sent = time.time()
    while True:
        if time.time() - last_sent >= 8:
            job = {
                "id": str(job_counter),
                "name": f"Sample Job {job_counter}",
                "short_description": "Auto-generated job.",
                "skills": ["example", "sample"],
            }
            job_counter += 1
            ws.send(json.dumps({"type": "jobs", "data": [job]}))
            last_sent = time.time()


# ---------------------------------------------------------
# EXTRA PAGES
# ---------------------------------------------------------
@app.route("/job_updates")
@login_required
def job_updates():
    return render_template("job_updates.html")


@app.route("/save_job", methods=["POST"])
@login_required
def save_job():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_payload"}), 400

    job_id = _derive_job_identifier(payload)
    saved_id = f"{current_user.username}:{job_id}"

    try:
        serialized = json.dumps(payload, separators=(",", ":"))
        job_clean = json.loads(serialized)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "unserializable_job"}), 400

    conn = dbh.get_db_connection()
    try:
        dbh.upsert_saved_job(conn, saved_id, current_user.username, job_clean)
    finally:
        dbh.close_db(conn)

    return jsonify({"ok": True, "saved_id": saved_id})


@app.route("/saved_jobs", methods=["GET"])
@login_required
def saved_jobs():
    conn = dbh.get_db_connection()
    try:
        jobs = dbh.fetch_saved_jobs(conn, current_user.username, limit=200)
    finally:
        dbh.close_db(conn)
    return jsonify({"ok": True, "data": jobs})


# ---------------------------------------------------------
# RUN APP
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
