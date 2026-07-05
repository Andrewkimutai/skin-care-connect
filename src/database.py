"""
database.py
Data access layer for Skin Care Connect, backed by SQLAlchemy so the exact
same code runs against SQLite (local dev, zero setup) or PostgreSQL
(production — e.g. Render Postgres).

Which one you get is controlled entirely by the DATABASE_URL environment
variable:

    - Not set               -> SQLite file at ./data/app.db
    - postgres://...        -> normalized to postgresql+psycopg2:// and used
    - postgresql://...      -> used as-is (driver added if missing)

All function signatures and return shapes are unchanged from the original
sqlite3 version, so app.py did not need any changes for this migration.
"""
import os
import json
from pathlib import Path

from sqlalchemy import (
    create_engine, text, MetaData, Table, Column, Integer, String, Text,
    Float, Boolean, DateTime, ForeignKey, func,
)

BASE_DIR = Path(__file__).resolve().parent.parent


def _normalize_database_url(url: str) -> str:
    """Render (and other Heroku-style platforms) hand out URLs prefixed with
    'postgres://', but SQLAlchemy 2.x / psycopg2 expect 'postgresql://'."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


_raw_url = os.environ.get("DATABASE_URL")
if _raw_url:
    DATABASE_URL = _normalize_database_url(_raw_url)
    IS_POSTGRES = True
else:
    sqlite_path = os.environ.get("DATABASE_PATH", str(BASE_DIR / "data" / "app.db"))
    Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{sqlite_path}"
    IS_POSTGRES = False

# pool_pre_ping avoids "server closed the connection unexpectedly" errors
# from Postgres providers (including Render) that silently drop idle
# connections. pool_recycle proactively refreshes connections before that
# can happen.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    connect_args={"check_same_thread": False} if not IS_POSTGRES else {},
)

metadata = MetaData()

users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(150), unique=True, nullable=False),
    Column("password_hash", String(255), nullable=False),
    Column("password_salt", String(255), nullable=False, server_default=""),
    Column("email", String(255), unique=True),
    Column("role", String(30), server_default="user"),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

predictions = Table(
    "predictions", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("image_filename", String(500), nullable=False),
    Column("predicted_class", String(100), nullable=False),
    Column("confidence", Float, nullable=False),
    Column("all_probabilities", Text, nullable=False),
    Column("recommendation", Text, nullable=False),
    Column("needs_appointment", Boolean, nullable=False),
    Column("timestamp", DateTime(timezone=True), server_default=func.now()),
)

appointments = Table(
    "appointments", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("prediction_id", Integer, ForeignKey("predictions.id")),
    Column("scheduled_date", DateTime(timezone=True), nullable=False),
    Column("status", String(30), server_default="pending"),
    Column("notes", Text),
    Column("notes_from_dermatologist", Text, server_default=""),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)


def init_db():
    metadata.create_all(engine)


def get_user_by_username(username):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, username, password_hash, password_salt, role "
                 "FROM users WHERE username = :username"),
            {"username": username},
        ).fetchone()
        return tuple(row) if row else None


def create_user(username, password_hash, password_salt, email=None, role='user'):
    with engine.begin() as conn:
        try:
            conn.execute(
                users.insert().values(
                    username=username, password_hash=password_hash,
                    password_salt=password_salt, email=email, role=role,
                )
            )
            return True
        except Exception:
            return False


def save_prediction_result(user_id, image_filename, result):
    with engine.begin() as conn:
        inserted = conn.execute(
            predictions.insert().values(
                user_id=user_id,
                image_filename=image_filename,
                predicted_class=result['predicted_class'],
                confidence=result['confidence'],
                all_probabilities=json.dumps(result['all_predictions']),
                recommendation=result['recommendation'],
                needs_appointment=result['needs_appointment'],
            ).returning(predictions.c.id)
        )
        return inserted.scalar_one()


def book_appointment(user_id, prediction_id, scheduled_datetime, notes=""):
    with engine.begin() as conn:
        conn.execute(
            appointments.insert().values(
                user_id=user_id, prediction_id=prediction_id,
                scheduled_date=scheduled_datetime, notes=notes, status='pending',
            )
        )


def get_user_appointments(user_id):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT a.id, a.scheduled_date, a.status, a.notes, a.notes_from_dermatologist,
                       p.predicted_class, p.confidence, p.timestamp as prediction_time
                FROM appointments a
                LEFT JOIN predictions p ON a.prediction_id = p.id
                WHERE a.user_id = :user_id
                ORDER BY a.scheduled_date ASC
            """),
            {"user_id": user_id},
        ).fetchall()
        return [tuple(r) for r in rows]


def get_all_appointments():
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT a.id, u.username as patient_username, a.scheduled_date, a.status,
                       a.notes, a.notes_from_dermatologist, p.predicted_class, p.confidence,
                       p.timestamp as prediction_time
                FROM appointments a
                JOIN users u ON a.user_id = u.id
                LEFT JOIN predictions p ON a.prediction_id = p.id
                ORDER BY a.scheduled_date ASC
            """)
        ).fetchall()
        return [tuple(r) for r in rows]


def update_appointment_status_and_notes(appointment_id, new_status, dermatologist_notes):
    if new_status not in ('pending', 'confirmed', 'cancelled'):
        return False
    with engine.begin() as conn:
        try:
            conn.execute(
                appointments.update()
                .where(appointments.c.id == appointment_id)
                .values(status=new_status, notes_from_dermatologist=dermatologist_notes)
            )
            return True
        except Exception:
            return False


def get_all_users():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC")
        ).fetchall()
        return [tuple(r) for r in rows]


def update_user_role(user_id, new_role):
    if new_role not in ('user', 'dermatologist', 'admin'):
        return False
    with engine.begin() as conn:
        try:
            conn.execute(
                users.update().where(users.c.id == user_id).values(role=new_role)
            )
            return True
        except Exception:
            return False


def delete_user(user_id):
    with engine.begin() as conn:
        try:
            conn.execute(users.delete().where(users.c.id == user_id))
            return True
        except Exception:
            return False


def get_user_predictions(user_id):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, image_filename, predicted_class, confidence, recommendation,
                       needs_appointment, timestamp
                FROM predictions
                WHERE user_id = :user_id
                ORDER BY timestamp DESC
            """),
            {"user_id": user_id},
        ).fetchall()
        return [tuple(r) for r in rows]


def count_users():
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM users")).scalar()


def bootstrap_admin_from_env():
    """
    Creates a single admin account from environment variables, but only if
    the users table is completely empty. This exists so a fresh deployment
    (e.g. on a Render free-tier instance with no shell access) still ends up
    with a way to log in — set ADMIN_USERNAME / ADMIN_PASSWORD / ADMIN_EMAIL
    as environment variables in the Render dashboard and this runs once on
    the app's first startup.

    Intentionally does nothing if ADMIN_PASSWORD isn't set, and does nothing
    once any user already exists — so it can't be used to reset or hijack
    an existing account.
    """
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_password:
        return None
    if count_users() > 0:
        return None

    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")

    # Imported here (not at module top) to avoid a circular import, since
    # auth.py doesn't need anything from database.py.
    from auth import hash_password
    password_hash, password_salt = hash_password(admin_password)
    created = create_user(admin_username, password_hash, password_salt, admin_email, "admin")
    return admin_username if created else None


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DATABASE_URL} (postgres={IS_POSTGRES})")
