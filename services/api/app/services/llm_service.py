"""
LLM Service — adapter untuk OpenAI dan Ollama.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def generate_answer(
    question: str,
    context: str,
    system_prompt: Optional[str] = None,
) -> str:
    """
    Generate jawaban dari LLM berdasarkan pertanyaan dan konteks dokumen.
    Mendukung OpenAI dan Ollama.
    """
    from app.core.config import settings

    if not system_prompt:
        system_prompt = (
            "Kamu adalah asisten AI yang membantu menjawab pertanyaan "
            "berdasarkan dokumen yang diberikan. "
            "Jawab hanya berdasarkan konteks yang ada. "
            "Jika informasi tidak tersedia di konteks, katakan bahwa "
            "kamu tidak menemukan informasi tersebut di dokumen. "
            "Jawab dalam bahasa yang sama dengan pertanyaan."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Konteks dokumen:\n\n{context}\n\nPertanyaan: {question}",
        },
    ]

    if settings.llm_provider == "openai":
        return await _call_openai(messages, settings)
    elif settings.llm_provider == "local":
        return await _call_ollama(messages, settings)
    else:
        raise ValueError(f"LLM provider tidak dikenal: {settings.llm_provider}")


async def _call_openai(messages: list, settings) -> str:
    """Panggil OpenAI API."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

    response = await client.chat.completions.create(
        model=settings.openai_model or "gpt-4o-mini",
        messages=messages,
        max_tokens=2048,
        temperature=0.1,
    )
    return response.choices[0].message.content or ""


async def _call_ollama(messages: list, settings) -> str:
    """Panggil Ollama API native endpoint."""
    import httpx

    # Ollama native endpoint: /api/chat (bukan OpenAI-compatible /v1/chat/completions)
    base_url = settings.local_llm_base_url or "http://host.docker.internal:11434/v1"
    ollama_base = base_url.replace("/v1", "")
    model = settings.local_llm_model or "llama3.2"

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{ollama_base}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 2048,
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]
