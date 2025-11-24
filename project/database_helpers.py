import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "jobs.db"


def get_db_connection():
    """Return a SQLite connection with foreign keys enforced."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def setup_db():
    conn = get_db_connection()
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
        name TEXT NOT NULL UNIQUE
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
    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_job_skills_pair
        ON job_skills(job_id, skill_id)
    """)
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_job_skills_job
        ON job_skills(job_id)
    """)
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_job_skills_skill
        ON job_skills(skill_id)
    """)

    # --- NEW: user_profile table (per-user rows) ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_profile (
        user TEXT PRIMARY KEY,
        name TEXT,
        info TEXT,
        soft_skills TEXT,
        photo_path TEXT
    )
    """)

    # If the table was created with the legacy integer id column, migrate it.
    profile_cols = [row[1] for row in cur.execute("PRAGMA table_info(user_profile)").fetchall()]
    if "user" not in profile_cols and "id" in profile_cols:
        cur.execute("ALTER TABLE user_profile RENAME TO user_profile_legacy")
        cur.execute("""
        CREATE TABLE user_profile (
            user TEXT PRIMARY KEY,
            name TEXT,
            info TEXT,
            soft_skills TEXT,
            photo_path TEXT
        )
        """)
        cur.execute(
            """
            INSERT OR IGNORE INTO user_profile (user, name, info, soft_skills, photo_path)
            SELECT 'default', name, info, soft_skills, photo_path
            FROM user_profile_legacy
            WHERE id = 1
            """
        )
        cur.execute("DROP TABLE user_profile_legacy")

    # --- NEW: saved jobs table ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS saved_jobs (
        id TEXT PRIMARY KEY,
        user TEXT NOT NULL,
        job_json TEXT NOT NULL,
        saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_saved_jobs_user
        ON saved_jobs(user)
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
    cur.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (skill_name,))
    skill_row = cur.execute("SELECT id FROM skills WHERE name = ?", (skill_name,)).fetchone()
    if not skill_row:
        raise RuntimeError("Failed to resolve skill id for name: %s" % skill_name)
    skill_id = skill_row[0]
    cur.execute(
        "INSERT OR IGNORE INTO job_skills (job_id, skill_id) VALUES (?, ?)",
        (job_id, skill_id)
    )
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

def get_user_profile(conn, user):
    """Return the profile for the given user, creating a blank one if needed."""
    cur = conn.cursor()
    row = cur.execute(
        "SELECT user, name, info, soft_skills, photo_path FROM user_profile WHERE user = ?",
        (user,)
    ).fetchone()

    if row is None:
        cur.execute(
            "INSERT INTO user_profile (user, name, info, soft_skills, photo_path) VALUES (?, '', '', '', '')",
            (user,)
        )
        conn.commit()
        return {
            "user": user,
            "name": "",
            "info": "",
            "soft_skills": "",
            "photo_path": ""
        }

    return {
        "user": row[0],
        "name": row[1] or "",
        "info": row[2] or "",
        "soft_skills": row[3] or "",
        "photo_path": row[4] or ""
    }


def save_user_profile(conn, user, name, info, soft_skills, photo_path=None):
    """Update name/info/soft_skills for the given user."""
    current = get_user_profile(conn, user)
    new_photo_path = photo_path if photo_path is not None else current["photo_path"]

    cur = conn.cursor()
    cur.execute(
        """
        UPDATE user_profile
        SET name = ?, info = ?, soft_skills = ?, photo_path = ?
        WHERE user = ?
        """,
        (name, info, soft_skills, new_photo_path, user)
    )
    conn.commit()


def update_profile_photo(conn, user, photo_path):
    """Update only the photo_path for the given user."""
    _ = get_user_profile(conn, user)

    cur = conn.cursor()
    cur.execute(
        """
        UPDATE user_profile
        SET photo_path = ?
        WHERE user = ?
        """,
        (photo_path, user)
    )
    conn.commit()


# ----------------saved jobs helper functions ----------------

def upsert_saved_job(conn, saved_id, user, job_dict):
    payload = json.dumps(job_dict, separators=(",", ":"))
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO saved_jobs (id, user, job_json)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            user = excluded.user,
            job_json = excluded.job_json,
            saved_at = CURRENT_TIMESTAMP
        """,
        (saved_id, user, payload)
    )
    conn.commit()


def fetch_saved_jobs(conn, user, limit=100):
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT job_json FROM saved_jobs
        WHERE user = ?
        ORDER BY saved_at DESC
        LIMIT ?
        """,
        (user, limit)
    ).fetchall()
    return [json.loads(row[0]) for row in rows]


def delete_saved_job(conn, saved_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM saved_jobs WHERE id = ?", (saved_id,))
    conn.commit()


def reassign_saved_jobs(conn, old_user, new_user):
    if not old_user or not new_user or old_user == new_user:
        return
    cur = conn.cursor()
    cur.execute(
        "UPDATE saved_jobs SET user = ? WHERE user = ?",
        (new_user, old_user)
    )
    conn.commit()
