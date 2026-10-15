"""
Script untuk membuat user admin pertama.
Jalankan dari dalam container:
  docker compose exec api python infra/scripts/seed_admin.py

Atau dari host (dengan venv aktif):
  python infra/scripts/seed_admin.py
"""
import asyncio
import os
import sys

# Tambah root project ke path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Set env minimal jika belum ada
os.environ.setdefault("APP_ENV", "development")

import bcrypt
import uuid
from datetime import datetime, timezone


async def create_admin():
    from app.core.config import settings
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import text

    email = "admin@example.com"
    password = "Admin123!"

    # Hash password
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()

    db_url = settings.database_url.get_secret_value()
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        # Cek apakah user sudah ada
        result = await conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": email}
        )
        existing = result.fetchone()

        if existing:
            print(f"User '{email}' sudah ada, skip.")
        else:
            await conn.execute(
                text("""
                    INSERT INTO users (id, email, hashed_password, full_name, role, is_active, created_at, updated_at)
                    VALUES (:id, :email, :hashed_password, :full_name, :role, :is_active, :created_at, :updated_at)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "email": email,
                    "hashed_password": hashed,
                    "full_name": "Admin",
                    "role": "admin",
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            print(f"✅ User admin dibuat:")
            print(f"   Email    : {email}")
            print(f"   Password : {password}")
            print(f"   Role     : admin")
            print()
            print("⚠️  Ganti password setelah login pertama!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin())
