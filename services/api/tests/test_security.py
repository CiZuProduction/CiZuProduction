"""
Unit test untuk modul security: hashing password dan JWT.
Menggunakan bcrypt langsung, bukan passlib.
"""
import os

import pytest

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-32-characters-long!!")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("DATABASE_URL_DOCKER", "postgresql+psycopg://test:test@postgres:5432/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-32-chars-long!")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("EMBEDDING_MODEL", "text-embedding-3-small")
os.environ.setdefault("EMBEDDING_DIMENSION", "1536")

from app.core.security import (  # noqa: E402
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("secretpassword")
        assert hashed != "secretpassword"

    def test_verify_correct_password(self):
        plain = "mypassword123"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_different_hashes_for_same_password(self):
        """bcrypt menghasilkan salt unik setiap kali."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2
        assert verify_password("same", h1)
        assert verify_password("same", h2)


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token("user-123")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"

    def test_extra_claims(self):
        token = create_access_token("user-456", extra_claims={"role": "admin"})
        payload = decode_access_token(token)
        assert payload["role"] == "admin"

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError):
            decode_access_token("invalid.token.here")

    def test_tampered_token_raises(self):
        token = create_access_token("user-789")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(ValueError):
            decode_access_token(tampered)
