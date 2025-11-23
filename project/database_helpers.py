import sqlite3

def setup_db():
    conn = sqlite3.connect("jobs.db")
    cur = conn.cursor()

    # --- existing jobs/skills tables ---
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

    # --- NEW: user_profile table (single user row) ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY,
        name TEXT,
        info TEXT,
        soft_skills TEXT,
        photo_path TEXT
    )
    """)

    conn.commit()
    return conn


# ---------------- existing job helper functions ----------------

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
    cur.execute("INSERT INTO job_skills (job_id, skill_id) VALUES (?, ?)", (job_id, skill_id))
    conn.commit()

def get_jobs(conn):
    cur = conn.cursor()
    return cur.execute("SELECT * FROM jobs").fetchall()

def get_skills_for_job(conn, job_id):
    cur = conn.cursor()
    return cur.execute(
        "SELECT * FROM skills WHERE id IN (SELECT skill_id FROM job_skills WHERE job_id = ?)",
        (job_id,)
    ).fetchall()

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
    return cur.execute(
        "SELECT * FROM jobs WHERE id IN (SELECT job_id FROM job_skills WHERE skill_id = ?)",
        (skill_id,)
    ).fetchall()

def get_job_id(conn, job_name):
    cur = conn.cursor()
    res = cur.execute("SELECT id FROM jobs WHERE name = ?", (job_name,)).fetchone()
    if res is None:
        return None
    else:
        return res[0]

def close_db(conn):
    conn.close()


# ---------------- NEW: profile helper functions ----------------

def get_user_profile(conn):
    """
    Return the single user profile row as a dict.
    If it doesn't exist yet, create a blank one (id=1).
    """
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, name, info, soft_skills, photo_path FROM user_profile WHERE id = 1"
    ).fetchone()

    if row is None:
        # create default row
        cur.execute(
            "INSERT INTO user_profile (id, name, info, soft_skills, photo_path) VALUES (1, '', '', '', '')"
        )
        conn.commit()
        return {
            "id": 1,
            "name": "",
            "info": "",
            "soft_skills": "",
            "photo_path": ""
        }

    return {
        "id": row[0],
        "name": row[1] or "",
        "info": row[2] or "",
        "soft_skills": row[3] or "",
        "photo_path": row[4] or ""
    }


def save_user_profile(conn, name, info, soft_skills, photo_path=None):
    """
    Update name/info/soft_skills.
    If photo_path is None, keep the existing photo_path.
    """
    current = get_user_profile(conn)  # ensures row exists
    new_photo_path = photo_path if photo_path is not None else current["photo_path"]

    cur = conn.cursor()
    cur.execute(
        """
        UPDATE user_profile
        SET name = ?, info = ?, soft_skills = ?, photo_path = ?
        WHERE id = 1
        """,
        (name, info, soft_skills, new_photo_path)
    )
    conn.commit()


def update_profile_photo(conn, photo_path):
    """
    Update only the photo_path, preserving existing text fields.
    """
    current = get_user_profile(conn)  # ensures row exists

    cur = conn.cursor()
    cur.execute(
        """
        UPDATE user_profile
        SET photo_path = ?
        WHERE id = 1
        """,
        (photo_path,)
    )
    conn.commit()
