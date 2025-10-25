from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_jobs', methods=['POST'])
def get_jobs():
    skills = request.form['skills']
    # For now, just test the connection
    return jsonify({"message": f"Received skills: {skills}"})

if __name__ == '__main__':
    app.run(debug=True)
