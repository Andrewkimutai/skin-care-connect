"""
auth.py
Password hashing helpers.

The original prototype used a raw, unsalted SHA-256 hash. That's fine for a
coursework demo but not something you want sitting in a public repo, so this
upgrades to a per-user random salt + PBKDF2-HMAC-SHA256 with a meaningful
iteration count, using only the standard library (no extra dependency).
"""
import hashlib
import hmac
import os

PBKDF2_ITERATIONS = 260_000


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Return (hash_hex, salt_hex) for a plaintext password."""
    salt_bytes = bytes.fromhex(salt) if salt else os.urandom(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt_bytes, PBKDF2_ITERATIONS
    )
    return derived.hex(), salt_bytes.hex()


def verify_password(stored_hash: str, stored_salt: str, provided_password: str) -> bool:
    """Constant-time check of a plaintext password against a stored hash."""
    if not stored_salt:
        # Legacy unsalted SHA-256 hash from the original prototype.
        legacy_hash = hashlib.sha256(provided_password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy_hash, stored_hash)
    candidate_hash, _ = hash_password(provided_password, stored_salt)
    return hmac.compare_digest(candidate_hash, stored_hash)
