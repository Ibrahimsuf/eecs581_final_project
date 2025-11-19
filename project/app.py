from flask import Flask, render_template, request, jsonify
from flask_sock import Sock
import time
import json
import sys

import ku_jobs_scraper
from davidsscraper import scrape_remoteok

app = Flask(__name__)
sock = Sock(app)

# -----------------------------------------------------------
# Matching Logic
# -----------------------------------------------------------
def analyze_match(description, hard_skills, soft_skills):
    desc = description.lower()

    hard_found = [h for h in hard_skills if h in desc]
    soft_found = [s for s in soft_skills if s in desc]

    score = len(hard_found) * 2 + len(soft_found)

    return {
        "hard_found": hard_found,
        "soft_found": soft_found,
        "score": score
    }


# -----------------------------------------------------------
# HOME PAGE
# -----------------------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')


# -----------------------------------------------------------
# UPDATED SEARCH ENDPOINT WITH HARD + SOFT SKILL SUPPORT
# -----------------------------------------------------------
@app.route('/get_jobs', methods=['POST'])
def get_jobs():

    # ========== READ SKILLS ==========
    data = request.get_json(silent=True) or {}

    hard_skills_raw = data.get("hardSkills", "")
    soft_skills_raw = data.get("softSkills", "")


    hard_skills = [s.strip().lower() for s in hard_skills_raw.split(",") if s.strip()]
    soft_skills = [s.strip().lower() for s in soft_skills_raw.split(",") if s.strip()]

    # Must provide hard skills
    if not hard_skills:
        return jsonify({"error": "Hard skills are required"}), 400

    all_jobs = []

    # ========== KU SCRAPER ==========
    session = ku_jobs_scraper.get_session()
    try:
        html = ku_jobs_scraper.fetch_html_text(session, ku_jobs_scraper.LIST_URL)
        ku_jobs = ku_jobs_scraper.parse_listings_table(html)

        for job in ku_jobs:
            j = job.to_api_format()
            all_jobs.append(j)

    except Exception as e:
        print(f"Error fetching KU jobs: {e}", file=sys.stderr)

    # ========== REMOTEOK SCRAPER ==========
    try:
        remote_jobs = scrape_remoteok()
        if remote_jobs:
            for job in remote_jobs:
                all_jobs.append(job)
    except Exception as e:
        print("RemoteOK error:", e, file=sys.stderr)


    # ========== APPLY MATCHING ==========
    processed = []
    for job in all_jobs:

        desc = job.get("description", "") or job.get("short_description", "")

        analysis = analyze_match(desc, hard_skills, soft_skills)

        job["hard_matches"] = analysis["hard_found"]
        job["soft_matches"] = analysis["soft_found"]
        job["match_score"] = analysis["score"]

        processed.append(job)

    # Sort by weighted score
    processed.sort(key=lambda j: j["match_score"], reverse=True)

    return jsonify({
        "jobs": processed,
        "hardSkills": hard_skills,
        "softSkills": soft_skills
    })


# -----------------------------------------------------------
# WEBSOCKET HANDLER (unchanged)
# -----------------------------------------------------------
@sock.route('/job_socket')
def websocket(ws):
    job_counter = 1

    # initial jobs
    batch = [
        {"id": str(job_counter), "name": "Software Engineer",
         "short_description": "Build and maintain web apps.",
         "skills": ["python", "flask", "sql"]},

        {"id": str(job_counter + 1), "name": "Data Scientist",
         "short_description": "Analyze datasets and build ML models.",
         "skills": ["python", "pandas", "ml"]}
    ]
    job_counter += 2
    ws.send(json.dumps({"type": "jobs", "data": batch}))

    last_sent = time.time()

    while True:
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


@app.route("/job_updates")
def job_updates():
    return render_template("job_updates.html")


# -----------------------------------------------------------
# Run App
# -----------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
