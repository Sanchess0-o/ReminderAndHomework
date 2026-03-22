import os
import sqlite3
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "homework.db")


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name    TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS homeworks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                subject_id  INTEGER NOT NULL,
                description TEXT    NOT NULL,
                deadline    TEXT    NOT NULL,
                done        INTEGER DEFAULT 0,
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            )
        """)
        conn.commit()


def get_subjects(user_id: int) -> list:
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute(
            "SELECT id, name FROM subjects WHERE user_id = ? ORDER BY name",
            (user_id,)
        ).fetchall()


def add_subject(user_id: int, name: str) -> int:
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.execute(
            "INSERT INTO subjects (user_id, name) VALUES (?, ?)", (user_id, name)
        )
        conn.commit()
        return cur.lastrowid


def delete_subject(subject_id: int, user_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "DELETE FROM subjects WHERE id = ? AND user_id = ?", (subject_id, user_id)
        )
        conn.commit()


def add_homework(user_id: int, subject_id: int, description: str, deadline: str) -> int:
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.execute(
            "INSERT INTO homeworks (user_id, subject_id, description, deadline) VALUES (?, ?, ?, ?)",
            (user_id, subject_id, description, deadline)
        )
        conn.commit()
        return cur.lastrowid


def get_homeworks(user_id: int) -> list:
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("""
            SELECT h.id, s.name, h.description, h.deadline
            FROM homeworks h
            JOIN subjects s ON h.subject_id = s.id
            WHERE h.user_id = ? AND h.done = 0
            ORDER BY h.deadline
        """, (user_id,)).fetchall()


def mark_done(hw_id: int, user_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "UPDATE homeworks SET done = 1 WHERE id = ? AND user_id = ?", (hw_id, user_id)
        )
        conn.commit()


def delete_homework(hw_id: int, user_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "DELETE FROM homeworks WHERE id = ? AND user_id = ?", (hw_id, user_id)
        )
        conn.commit()


def get_homeworks_due_tomorrow() -> list:
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("""
            SELECT h.user_id, s.name, h.description, h.deadline
            FROM homeworks h
            JOIN subjects s ON h.subject_id = s.id
            WHERE h.deadline = ? AND h.done = 0
        """, (tomorrow,)).fetchall()