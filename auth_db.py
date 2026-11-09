
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "users.db")


def get_connection():
    return sqlite3.connect(DATABASE)


def create_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            student_id TEXT UNIQUE,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def register_user(name, student_id, email, password, role="student"):
    conn = get_connection()
    try:
        hashed_password = generate_password_hash(password)
        conn.execute("""
            INSERT INTO users
            (name, student_id, email, password, role)
            VALUES (?, ?, ?, ?, ?)
        """, (name, student_id, email, hashed_password, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def login_user(email, password, role):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    user = conn.execute(
        "SELECT * FROM users WHERE email = ? AND role = ?",
        (email, role)
    ).fetchone()
    conn.close()

    if user and check_password_hash(user["password"], password):
        return dict(user)
    return None


create_table()
