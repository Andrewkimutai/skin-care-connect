"""
database.py
SQLite data access layer for Skin Care Connect.

The DB path is resolved relative to this file (not the current working
directory) so the app behaves the same whether it's launched from the repo
root, from src/, or from a Render container. It can be overridden with the
DATABASE_PATH environment variable.
"""
import os
import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "data" / "app.db"))

# Make sure the folder that will hold app.db actually exists (Render's
# filesystem starts empty on every deploy).
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    """Context-managed connection so we never leak open handles."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL DEFAULT '',
                email TEXT UNIQUE,
                role TEXT DEFAULT 'user',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                image_filename TEXT NOT NULL,
                predicted_class TEXT NOT NULL,
                confidence REAL NOT NULL,
                all_probabilities TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                needs_appointment BOOLEAN NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                prediction_id INTEGER,
                scheduled_date DATETIME NOT NULL,
                status TEXT DEFAULT 'pending',
                notes TEXT,
                notes_from_dermatologist TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (prediction_id) REFERENCES predictions (id)
            )
        ''')

        # Lightweight migration: add password_salt if an old DB is present.
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        if "password_salt" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN password_salt TEXT NOT NULL DEFAULT ''")


def get_user_by_username(username):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, username, password_hash, password_salt, role FROM users WHERE username = ?',
            (username,)
        )
        return cursor.fetchone()


def create_user(username, password_hash, password_salt, email=None, role='user'):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO users (username, password_hash, password_salt, email, role) '
                'VALUES (?, ?, ?, ?, ?)',
                (username, password_hash, password_salt, email, role)
            )
            return True
        except sqlite3.IntegrityError:
            return False


def save_prediction_result(user_id, image_filename, result):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO predictions (user_id, image_filename, predicted_class, confidence,
                                      all_probabilities, recommendation, needs_appointment)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, image_filename, result['predicted_class'], result['confidence'],
            json.dumps(result['all_predictions']), result['recommendation'], result['needs_appointment']
        ))
        return cursor.lastrowid


def book_appointment(user_id, prediction_id, scheduled_datetime, notes=""):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO appointments (user_id, prediction_id, scheduled_date, notes, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, prediction_id, scheduled_datetime, notes, 'pending'))


def get_user_appointments(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, a.scheduled_date, a.status, a.notes, a.notes_from_dermatologist,
                   p.predicted_class, p.confidence, p.timestamp as prediction_time
            FROM appointments a
            LEFT JOIN predictions p ON a.prediction_id = p.id
            WHERE a.user_id = ?
            ORDER BY a.scheduled_date ASC
        ''', (user_id,))
        return cursor.fetchall()


def get_all_appointments():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, u.username as patient_username, a.scheduled_date, a.status,
                   a.notes, a.notes_from_dermatologist, p.predicted_class, p.confidence,
                   p.timestamp as prediction_time
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            LEFT JOIN predictions p ON a.prediction_id = p.id
            ORDER BY a.scheduled_date ASC
        ''')
        return cursor.fetchall()


def update_appointment_status_and_notes(appointment_id, new_status, dermatologist_notes):
    if new_status not in ('pending', 'confirmed', 'cancelled'):
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                'UPDATE appointments SET status = ?, notes_from_dermatologist = ? WHERE id = ?',
                (new_status, dermatologist_notes, appointment_id)
            )
            return True
        except sqlite3.Error:
            return False


def get_all_users():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC')
        return cursor.fetchall()


def update_user_role(user_id, new_role):
    if new_role not in ('user', 'dermatologist', 'admin'):
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
            return True
        except sqlite3.Error:
            return False


def delete_user(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            return True
        except sqlite3.Error:
            return False


def get_user_predictions(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, image_filename, predicted_class, confidence, recommendation,
                   needs_appointment, timestamp
            FROM predictions
            WHERE user_id = ?
            ORDER BY timestamp DESC
        ''', (user_id,))
        return cursor.fetchall()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
