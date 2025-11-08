from flask import Flask, render_template, request, jsonify
from flask_sock import Sock
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
    while True:
        data = ws.receive()
        if data is None:
            break
        ws.send(f"Echo: {data}")

if __name__ == '__main__':
    app.run(debug=True)
