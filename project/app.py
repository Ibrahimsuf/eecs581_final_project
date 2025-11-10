from flask import Flask, render_template, request, jsonify, session
from flask_sock import Sock
import time
import asyncio
import json
import threading
import os
import sqlite3
import uuid

app = Flask(__name__)
sock = Sock(app)

# Basic secret key for session management (replace via env in prod)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

# SQLite database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "app.db")


def init_db():
    """Create the saved_jobs table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                name TEXT,
                short_description TEXT,
                skills TEXT, -- JSON string
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, job_id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_session_id() -> str:
    """Ensure an anonymous session id exists for the current user."""
    sid = session.get("sid")
    if not sid:
        sid = str(uuid.uuid4())
        session["sid"] = sid
    return sid


def save_job_to_db(payload: dict) -> tuple[bool, str]:
    """Insert a job row for the current session. Returns (created, message)."""
    required = ["id", "name"]
    for key in required:
        if key not in payload or not str(payload[key]).strip():
            return False, f"Missing required field: {key}"

    sid = get_session_id()
    job_id = str(payload.get("id"))
    name = str(payload.get("name", "")).strip()
    short_description = str(payload.get("short_description", ""))
    skills_val = payload.get("skills", [])
    # Store skills as JSON string for simplicity
    try:
        skills_json = json.dumps(skills_val)
    except Exception:
        skills_json = json.dumps([])

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT OR IGNORE INTO saved_jobs (session_id, job_id, name, short_description, skills)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sid, job_id, name, short_description, skills_json),
            )
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()

    # Check whether it was inserted or already existed
    # A second query to determine existence
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(1) FROM saved_jobs WHERE session_id = ? AND job_id = ?",
            (sid, job_id),
        )
        exists = bool(cur.fetchone()[0])
    finally:
        conn.close()

    if exists:
        # If INSERT OR IGNORE hit a duplicate, we still return exists=True with appropriate message
        return True, "Saved (or already saved)"
    return False, "Unable to save job"
@app.route('/')
def home():
    # Redirect users to the live job updates page for now
    return render_template('job_updates.html')

@app.route('/get_jobs', methods=['POST'])
def get_jobs():
    skills = request.form['skills']
    # For now, just test the connection
    return jsonify({"message": f"Received skills: {skills}"})


@app.route('/save_job', methods=['POST'])
def save_job():
    """Persist a job for the current anonymous session."""
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        payload = None
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "Invalid JSON payload"}), 400

    created, msg = save_job_to_db(payload)
    status = 200 if created else 400
    return jsonify({"ok": created, "message": msg}), status


@app.route('/saved_jobs', methods=['GET'])
def list_saved_jobs():
    """Return saved jobs for the current anonymous session."""
    sid = get_session_id()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT job_id, name, short_description, skills, saved_at FROM saved_jobs WHERE session_id = ? ORDER BY saved_at DESC",
            (sid,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    items = []
    for r in rows:
        try:
            skills = json.loads(r["skills"]) if r["skills"] else []
        except Exception:
            skills = []
        items.append(
            {
                "id": r["job_id"],
                "name": r["name"],
                "short_description": r["short_description"],
                "skills": skills,
                "saved_at": r["saved_at"],
            }
        )
    return jsonify({"ok": True, "data": items})

@sock.route('/job_socket')
def websocket(ws):
    job_counter = 1

    # send initial batch
    batch = [
        {"id": str(job_counter), "name": "Software Engineer",
         "short_description": "Build and maintain web applications.",
         "skills": ["python", "flask", "sql"]},
        {"id": str(job_counter + 1), "name": "Data Scientist",
         "short_description": "Analyze datasets and build models.",
         "skills": ["python", "pandas", "ml"]},
    ]
    job_counter += 2
    ws.send(json.dumps({"type": "jobs", "data": batch}))

    last_sent = time.time()

    # main loop handles both incoming and timed sends
    while True:
        # periodically send job updates
        if time.time() - last_sent >= 8:
            job = {
                "id": str(job_counter),
                "name": f"Sample Job {job_counter}",
                "short_description": "Auto-generated job from server.",
                "skills": ["example", "sample"]
            }
            job_counter += 1
            ws.send(json.dumps({"type": "jobs", "data": [job]}))
            last_sent = time.time()


@app.route("/job_updates", methods=["GET"])
def job_updates():
    return render_template("job_updates.html")

if __name__ == '__main__':
    # Ensure DB exists on startup
    init_db()
    app.run(debug=True)
