import sqlite3
from typing import List, Dict, Optional

DB_PATH = 'app.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def mark_applied(user_id: int, job_id: int, notes: Optional[str] = None) -> None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT OR IGNORE INTO applied_jobs (user_id, job_id, notes) VALUES (?,?,?)', (user_id, job_id, notes))
    cur.execute('UPDATE applied_jobs SET notes = ? WHERE user_id = ? AND job_id = ?', (notes, user_id, job_id))
    conn.commit()
    conn.close()

def unmark_applied(user_id: int, job_id: int) -> None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM applied_jobs WHERE user_id = ? AND job_id = ?', (user_id, job_id))
    conn.commit()
    conn.close()

def get_user_applied_jobs(user_id: int) -> List[Dict]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT aj.id as id, aj.user_id as user_id, aj.job_id as job_id, aj.notes as notes, aj.applied_at as applied_at, j.title as title, j.company as company FROM applied_jobs aj LEFT JOIN jobs j ON aj.job_id = j.id WHERE aj.user_id = ? ORDER BY aj.applied_at DESC', (user_id,))
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({k: r[k] for k in r.keys()})
    return result

def is_job_applied_by_user(user_id: int, job_id: int) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM applied_jobs WHERE user_id = ? AND job_id = ? LIMIT 1', (user_id, job_id))
    exists = cur.fetchone() is not None
    conn.close()
    return exists
