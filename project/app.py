from flask import Flask, render_template, request, jsonify
from flask_sock import Sock
import time
import asyncio
import json
import sys
import threading
import os

import ku_jobs_scraper
from davidsscraper import scrape_remoteok
import database_helpers as dbh  # NEW: for profile persistence

app = Flask(__name__)

# Folder for profile photos
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

sock = Sock(app)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/get_jobs", methods=["POST"])
def get_jobs():
    skills = request.form["skills"]

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

    return jsonify({
        "message": f"Received skills: {skills}",
        "jobs": out
    })


# ---------------- PROFILE PAGES / APIS ----------------

@app.route("/profile", methods=["GET"])
def profile_page():
    """Render the profile page."""
    return render_template("profile.html")


@app.route("/api/profile", methods=["GET", "POST"])
def api_profile():
    """
    GET  -> return current profile as JSON
    POST -> update name, info, soft_skills (photo handled separately)
    """
    conn = dbh.setup_db()

    if request.method == "GET":
        profile = dbh.get_user_profile(conn)
        dbh.close_db(conn)
        return jsonify(profile)

    # POST: update profile
    data = request.get_json(silent=True) or request.form

    name = (data.get("name") or "").strip()
    info = (data.get("info") or "").strip()
    soft_skills = (data.get("soft_skills") or "").strip()

    # photo_path=None -> don't overwrite existing photo unless explicitly changed
    dbh.save_user_profile(conn, name=name, info=info, soft_skills=soft_skills, photo_path=None)
    profile = dbh.get_user_profile(conn)
    dbh.close_db(conn)
    return jsonify(profile)


@app.route("/api/profile/photo", methods=["POST"])
def upload_profile_photo():
    """
    Handle profile photo upload.
    Expects form-data with field name "photo".
    Saves to static/uploads/profile_photo.<ext> and updates DB.
    """
    if "photo" not in request.files:
        return jsonify({"error": "no_file"}), 400

    file = request.files["photo"]
    if file.filename == "":
        return jsonify({"error": "empty_filename"}), 400

    # Basic extension check
    allowed = {"png", "jpg", "jpeg", "gif"}
    if "." in file.filename:
        ext = file.filename.rsplit(".", 1)[1].lower()
    else:
        ext = ""
    if ext not in allowed:
        return jsonify({"error": "invalid_type"}), 400

    # Always use the same filename (overwrite old photo)
    filename = f"profile_photo.{ext}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    rel_path = f"uploads/{filename}"  # stored in DB

    conn = dbh.setup_db()
    dbh.update_profile_photo(conn, rel_path)
    profile = dbh.get_user_profile(conn)
    dbh.close_db(conn)

    return jsonify(profile)


# ---------------- EXISTING WEBSOCKET STUFF ----------------

@sock.route("/job_socket")
def websocket(ws):
    job_counter = 1

    # send initial batch
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

    # main loop handles both incoming and timed sends
    while True:
        # periodically send job updates
        if time.time() - last_sent >= 8:
            job = {
                "id": str(job_counter),
                "name": f"Sample Job {job_counter}",
                "short_description": "Auto-generated job from server.",
                "skills": ["example", "sample"],
            }
            job_counter += 1
            ws.send(json.dumps({"type": "jobs", "data": [job]}))
            last_sent = time.time()


@app.route("/job_updates", methods=["GET"])
def job_updates():
    return render_template("job_updates.html")


if __name__ == "__main__":
    app.run(debug=True)
