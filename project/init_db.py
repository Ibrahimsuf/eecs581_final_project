import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect("users.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
)
""")

# Example user
c.execute(
    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
    ("test", generate_password_hash("password123"))
)

conn.commit()
conn.close()
