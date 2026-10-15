"""Test embedding adapter dari dalam container."""
import asyncio
import os
import sys

# Setup env minimal
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-32-characters-long!!")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-32-chars-long!")
os.environ.setdefault("POSTGRES_DB", "ai_chatbot")
os.environ.setdefault("POSTGRES_USER", "ai_chatbot_app")
os.environ.setdefault("POSTGRES_PASSWORD", "Admin123!")

async def main():
    from app.core.config import settings
    print(f"embedding_provider : {settings.embedding_provider}")
    print(f"embedding_model    : {settings.embedding_model}")
    print(f"embedding_dimension: {settings.embedding_dimension}")
    print(f"local_llm_base_url : {settings.local_llm_base_url}")

    from app.services.ingestion.embedder import get_embedding_adapter
    adapter = get_embedding_adapter()
    print(f"adapter type  : {type(adapter).__name__}")
    print(f"adapter model : {adapter.model_name}")

    print("\nMencoba embed teks 'halo dunia'...")
    try:
        result = await adapter.embed_texts(["halo dunia"])
        print(f"Berhasil! Dimensi: {len(result[0])}")
    except Exception as e:
        print(f"Gagal: {type(e).__name__}: {e}")

asyncio.run(main())
