import sqlite3

def setup_db():
  conn = sqlite3.connect("jobs.db")
  cur = conn.cursor()
  # Create a table
  cur.execute("""
  CREATE TABLE IF NOT EXISTS jobs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      description TEXT
  )
  """)
  cur.execute("""
  CREATE TABLE IF NOT EXISTS skills (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name STRING NOT NULL
  )
  """)
  cur.execute("""
  CREATE TABLE IF NOT EXISTS job_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(id),
    FOREIGN KEY (skill_id) REFERENCES skills(id)
  )
  """)

  conn.commit()
  return conn

def add_job(conn, name, description):
  cur = conn.cursor()
  cur.execute("INSERT INTO jobs (name, description) VALUES (?, ?)", (name, description))
  conn.commit()

def add_skill_to_job(conn, skill_name, job_id):
  cur = conn.cursor()
  skill_id = cur.execute("SELECT id FROM skills WHERE name = ?", (skill_name,)).fetchone()
  # reset cursor for next query
  cur = conn.cursor()
  if skill_id is None:
    cur.execute("INSERT INTO skills (name) VALUES (?)", (skill_name,))
    skill_id = cur.lastrowid
  else:
    skill_id = skill_id[0]
  cur.execute("INSERT INTO job_skills (job_id, skill_id) VALUES (?, ?)", (job_id, skill_id, ))
  conn.commit()

def get_jobs(conn):
  cur = conn.cursor()
  return cur.execute("SELECT * FROM jobs").fetchall()

def get_skills_for_job(conn, job_id):
  cur = conn.cursor()
  return cur.execute("SELECT * FROM skills WHERE id IN (SELECT skill_id FROM job_skills WHERE job_id = ?)", (job_id,)).fetchall()

def get_job_for_skill(conn, skill_name):
  cur = conn.cursor()
  skill_id = cur.execute("SELECT id FROM skills WHERE name = ?", (skill_name, )).fetchone()
  if skill_id is None:
    print("No such skill")
    return []
  else:
    skill_id = skill_id[0]
  # reset cursor for next query
  cur = conn.cursor()
  return cur.execute("SELECT * FROM jobs WHERE id IN (SELECT job_id FROM job_skills WHERE skill_id = ?)", (skill_id,)).fetchall()

def get_job_id(conn, job_name):
  cur = conn.cursor()
  res = cur.execute("SELECT id FROM jobs WHERE name = ?", (job_name,)).fetchone()
  if res is None:
    return None
  else:
    return res[0]

def close_db(conn):
  conn.close()