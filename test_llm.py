"""Test LLM call ke Ollama dari dalam container."""
import asyncio
import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-32-characters-long!!")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-32-chars-long!")
os.environ.setdefault("POSTGRES_DB", "ai_chatbot")
os.environ.setdefault("POSTGRES_USER", "ai_chatbot_app")
os.environ.setdefault("POSTGRES_PASSWORD", "Admin123!")

async def main():
    from app.core.config import settings
    print(f"llm_provider      : {settings.llm_provider}")
    print(f"local_llm_base_url: {settings.local_llm_base_url}")
    print(f"local_llm_model   : {settings.local_llm_model}")

    print("\nTest LLM call...")
    try:
        from app.services.llm_service import generate_answer
        answer = await generate_answer(
            question="Berapa total server?",
            context="Total Server: 187. Power On: 151. Power Off: 36.",
        )
        print(f"Berhasil! Jawaban: {answer[:200]}")
    except Exception as e:
        print(f"Gagal: {type(e).__name__}: {e}")

asyncio.run(main())
