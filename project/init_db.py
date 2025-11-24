import sqlite3
conn = sqlite3.connect('app.db')
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS applied_jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, job_id INTEGER NOT NULL, notes TEXT, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, job_id))')
conn.commit()
conn.close()
