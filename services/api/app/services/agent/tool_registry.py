"""
Tool Registry — daftar tools yang boleh digunakan oleh agent.
Setiap tool memiliki nama, deskripsi, schema input, dan timeout.
Agent TIDAK boleh mengakses tool di luar registry ini.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict
    timeout_seconds: int = 30
    max_calls_per_request: int = 3


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: Optional[str] = None


class ToolRegistry:
    """
    Registry tool yang diizinkan untuk agent.
    Implementasi allowlist — hanya tool yang terdaftar yang bisa dipanggil.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._call_counts: dict[str, int] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Daftarkan tool default yang diizinkan."""

        self.register(ToolDefinition(
            name="search_documents",
            description="Cari informasi relevan dari dokumen yang diupload pengguna",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Query pencarian"},
                    "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
                },
                "required": ["query"],
            },
            timeout_seconds=30,
            max_calls_per_request=3,
        ))

        self.register(ToolDefinition(
            name="get_document_summary",
            description="Dapatkan ringkasan dokumen berdasarkan ID",
            input_schema={
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"},
                },
                "required": ["document_id"],
            },
            timeout_seconds=15,
            max_calls_per_request=2,
        ))

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool
        logger.debug("Tool terdaftar: %s", tool.name)

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def is_allowed(self, name: str) -> bool:
        return name in self._tools

    def can_call(self, name: str, request_id: str) -> bool:
        """Cek apakah tool masih bisa dipanggil (belum melewati batas)."""
        key = f"{request_id}:{name}"
        tool = self.get(name)
        if not tool:
            return False
        count = self._call_counts.get(key, 0)
        return count < tool.max_calls_per_request

    def record_call(self, name: str, request_id: str) -> None:
        key = f"{request_id}:{name}"
        self._call_counts[key] = self._call_counts.get(key, 0) + 1

    def reset_counts(self, request_id: str) -> None:
        keys_to_delete = [k for k in self._call_counts if k.startswith(f"{request_id}:")]
        for k in keys_to_delete:
            del self._call_counts[k]

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())


# Singleton registry
_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _registry
