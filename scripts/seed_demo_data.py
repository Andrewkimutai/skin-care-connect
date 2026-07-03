"""
seed_demo_data.py
Creates a fresh local database with demo accounts so you (or anyone cloning
the repo) can log in and try every role immediately.

Usage:
    python scripts/seed_demo_data.py

CHANGE THESE PASSWORDS before deploying anywhere public-facing.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from database import init_db, create_user
from auth import hash_password

DEMO_ACCOUNTS = [
    ("demo_admin", "ChangeMe123!", "admin@example.com", "admin"),
    ("demo_dermatologist", "ChangeMe123!", "dermatologist@example.com", "dermatologist"),
    ("demo_patient", "ChangeMe123!", "patient@example.com", "user"),
]


def main():
    init_db()
    for username, password, email, role in DEMO_ACCOUNTS:
        password_hash, password_salt = hash_password(password)
        created = create_user(username, password_hash, password_salt, email, role)
        status = "created" if created else "already exists, skipped"
        print(f"[{role:14s}] {username:20s} -> {status}")
    print("\nDemo credentials (change before any public deployment):")
    for username, password, _, role in DEMO_ACCOUNTS:
        print(f"  {role:14s} | user: {username:20s} | pass: {password}")


if __name__ == "__main__":
    main()
