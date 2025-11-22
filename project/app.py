from flask import Flask, render_template, request, jsonify, redirect, url_for, render_template_string
from flask_sock import Sock
import time
import asyncio
import json
import sys
import threading
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3

import ku_jobs_scraper
from davidsscraper import scrape_remoteok

app = Flask(__name__)
sock = Sock(app)
app.secret_key = 'supersecretkey'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

def get_user_by_username(username):
    conn = sqlite3.connect("users.db")
    row = conn.execute("SELECT id, username, password_hash FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return row

def get_user_by_id(uid):
    conn = sqlite3.connect("users.db")
    row = conn.execute("SELECT id, username, password_hash FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return row

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash


@login_manager.user_loader
def load_user(user_id):
    row = get_user_by_id(user_id)
    return User(*row) if row else None

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/get_jobs', methods=['POST'])
@login_required
def get_jobs():
    skills = request.form['skills']
    # For now, just test the connection

    # ku job scraper from main loop
    session = ku_jobs_scraper.get_session()
    jobs = []
    try:
        html = ku_jobs_scraper.fetch_html_text(session, ku_jobs_scraper.LIST_URL)
        jobs = ku_jobs_scraper.parse_listings_table(html)
    except Exception as e:
        print(f"Error fetching list page: {e}", file=sys.stderr)

    out = []
    for job in jobs:
        out.append(job.to_api_format())

    # using davidsscraper.py for second scraper
    jobs = scrape_remoteok()
    if jobs is None:
        return jsonify({"message": "Error fetching jobs from remoteok"})
    for job in jobs:
        out.append(job)

    # return jsonify({"message": f"Received skills: {skills}"})
    # print(out)
    return jsonify({
        "message": f"Received skills: {skills}",
        "jobs": out
    })

@sock.route('/job_socket')
@login_required
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
@login_required
def job_updates():
    return render_template("job_updates.html")


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



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("users.db")
        c = conn.cursor()

        exists = c.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
        if exists:
            return "Username already taken", 400

        c.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password))
        )
        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


if __name__ == '__main__':
    app.run(debug=True)
