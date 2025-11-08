from flask import Flask, render_template, request, jsonify
from flask_sock import Sock
import time
import asyncio
import json
import threading
app = Flask(__name__)
sock = Sock(app)
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_jobs', methods=['POST'])
def get_jobs():
    skills = request.form['skills']
    # For now, just test the connection
    return jsonify({"message": f"Received skills: {skills}"})

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
    app.run(debug=True)
