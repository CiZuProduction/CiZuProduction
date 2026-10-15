"""
Adapter untuk embedding model.
Mendukung OpenAI dan stub lokal untuk development tanpa API key.
"""
from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class EmbeddingAdapter(Protocol):
    """Interface embedding — semua provider harus implement ini."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return list of embedding vectors, satu per teks."""
        ...

    @property
    def model_name(self) -> str:
        """Nama model yang digunakan."""
        ...

    @property
    def dimension(self) -> int:
        """Dimensi vektor output."""
        ...


class OpenAIEmbeddingAdapter:
    """Embedding menggunakan OpenAI API."""

    def __init__(self, model: str, dimension: int, api_key: str) -> None:
        self._model = model
        self._dimension = dimension
        self._api_key = api_key

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed batch teks menggunakan OpenAI API."""
        if not texts:
            return []

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key)

        # Batch maksimum 100 teks per request
        all_embeddings: list[list[float]] = []
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            # Truncate teks yang terlalu panjang (max 8191 token untuk text-embedding-3-small)
            batch = [t[:32000] for t in batch]

            try:
                response = await client.embeddings.create(
                    model=self._model,
                    input=batch,
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                logger.debug("Embedded %d teks (batch %d)", len(batch), i // batch_size + 1)
            except Exception as e:
                logger.error("OpenAI embedding error: %s", e)
                raise

        return all_embeddings


class StubEmbeddingAdapter:
    """
    Stub embedding untuk development tanpa API key.
    Menghasilkan vektor random — TIDAK untuk production.
    """

    def __init__(self, dimension: int = 1536) -> None:
        self._dimension = dimension
        logger.warning(
            "StubEmbeddingAdapter aktif — menggunakan vektor random. "
            "Set OPENAI_API_KEY untuk embedding nyata."
        )

    @property
    def model_name(self) -> str:
        return "stub-random"

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        import random
        import math

        result = []
        for _ in texts:
            # Buat vektor random yang ternormalisasi
            vec = [random.gauss(0, 1) for _ in range(self._dimension)]
            magnitude = math.sqrt(sum(x * x for x in vec))
            normalized = [x / magnitude for x in vec]
            result.append(normalized)
        return result


class OllamaEmbeddingAdapter:
    """Embedding menggunakan Ollama yang berjalan di host lokal."""

    def __init__(self, model: str, dimension: int, base_url: str) -> None:
        self._model = model
        self._dimension = dimension
        self._base_url = base_url.rstrip("/")

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed teks menggunakan Ollama API."""
        if not texts:
            return []

        import httpx

        all_embeddings: list[list[float]] = []

        async with httpx.AsyncClient(timeout=60.0) as client:
            for text in texts:
                try:
                    # Coba endpoint baru dulu (/api/embed), fallback ke lama (/api/embeddings)
                    for endpoint in ["/api/embed", "/api/embeddings"]:
                        try:
                            payload = (
                                {"model": self._model, "input": text}
                                if endpoint == "/api/embed"
                                else {"model": self._model, "prompt": text}
                            )
                            response = await client.post(
                                f"{self._base_url}{endpoint}",
                                json=payload,
                            )
                            if response.status_code == 404:
                                continue
                            response.raise_for_status()
                            data = response.json()
                            # /api/embed returns {"embeddings": [[...]]}
                            # /api/embeddings returns {"embedding": [...]}
                            embedding = (
                                data["embeddings"][0]
                                if "embeddings" in data
                                else data["embedding"]
                            )
                            all_embeddings.append(embedding)
                            break
                        except httpx.HTTPStatusError as e:
                            if e.response.status_code == 404:
                                continue
                            raise
                except Exception as e:
                    logger.error("Ollama embedding error: %s", e)
                    raise

        return all_embeddings


def get_embedding_adapter() -> EmbeddingAdapter:
    """
    Factory — pilih adapter berdasarkan konfigurasi.
    Fallback ke stub jika tidak ada provider yang dikonfigurasi.
    """
    from app.core.config import settings

    if settings.embedding_provider == "openai":
        api_key = settings.openai_api_key
        if api_key:
            logger.info("Menggunakan OpenAI embedding: %s", settings.embedding_model)
            return OpenAIEmbeddingAdapter(
                model=settings.embedding_model,
                dimension=settings.embedding_dimension,
                api_key=api_key.get_secret_value(),
            )
        else:
            logger.warning("OPENAI_API_KEY tidak diset, fallback ke stub embedding")
            return StubEmbeddingAdapter(dimension=settings.embedding_dimension)

    if settings.embedding_provider == "ollama":
        base_url = settings.local_llm_base_url or "http://host.docker.internal:11434"
        # Ollama embedding pakai endpoint berbeda dari LLM
        ollama_base = base_url.replace("/v1", "")
        logger.info("Menggunakan Ollama embedding: %s @ %s", settings.embedding_model, ollama_base)
        return OllamaEmbeddingAdapter(
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
            base_url=ollama_base,
        )

    # Default fallback
    return StubEmbeddingAdapter(dimension=settings.embedding_dimension)
