"""
Storage Service — Enkripsi file menggunakan AES-256-GCM.

Format file terenkripsi (binary):
  [4 bytes: magic "ACMV"] [1 byte: version] [12 bytes: nonce] [ciphertext + 16 bytes GCM tag]

Alasan desain:
- AES-256-GCM memberikan authenticated encryption — deteksi jika ciphertext dimodifikasi
- Nonce unik per file mencegah reuse
- Magic bytes memudahkan identifikasi format
- Kunci disimpan di environment variable, TIDAK di dalam file atau database
"""
from __future__ import annotations

import logging
import os
import struct
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Magic identifier untuk format file terenkripsi
_MAGIC = b"ACMV"
_VERSION = 1
_NONCE_SIZE = 12  # 96-bit nonce untuk GCM
_HEADER_SIZE = len(_MAGIC) + 1 + _NONCE_SIZE  # 17 bytes


class StorageService:
    """
    Layanan penyimpanan file dengan enkripsi AES-256-GCM.

    Jika ENCRYPTION_KEY tidak diset, file disimpan tanpa enkripsi
    dengan peringatan log. Ini memudahkan development lokal.
    """

    def __init__(self, upload_dir: str, encryption_key: Optional[str] = None) -> None:
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self._key: Optional[bytes] = None
        self._encryption_enabled = False

        if encryption_key:
            key_bytes = self._load_key(encryption_key)
            if key_bytes:
                self._key = key_bytes
                self._encryption_enabled = True
                logger.info("StorageService: enkripsi AES-256-GCM aktif")
            else:
                logger.warning(
                    "StorageService: ENCRYPTION_KEY tidak valid, "
                    "file disimpan tanpa enkripsi"
                )
        else:
            logger.warning(
                "StorageService: ENCRYPTION_KEY tidak diset, "
                "file disimpan tanpa enkripsi. "
                "Set ENCRYPTION_KEY di .env untuk enkripsi production."
            )

    @property
    def encryption_enabled(self) -> bool:
        return self._encryption_enabled

    def _load_key(self, key_str: str) -> Optional[bytes]:
        """
        Load kunci dari string base64 atau hex.
        Kunci harus tepat 32 bytes (256 bit).
        """
        import base64

        # Coba base64
        try:
            key = base64.b64decode(key_str)
            if len(key) == 32:
                return key
        except Exception:
            pass

        # Coba hex
        try:
            key = bytes.fromhex(key_str)
            if len(key) == 32:
                return key
        except Exception:
            pass

        logger.error(
            "ENCRYPTION_KEY harus berupa base64 atau hex dari 32 bytes (256 bit). "
            "Generate dengan: python -c \"import secrets,base64; "
            "print(base64.b64encode(secrets.token_bytes(32)).decode())\""
        )
        return None

    async def save(self, content: bytes, filename: str) -> Path:
        """
        Simpan file ke disk. Enkripsi jika kunci tersedia.
        Return path file yang disimpan.
        """
        file_path = self.upload_dir / filename

        if self._encryption_enabled and self._key:
            data = self._encrypt(content)
        else:
            data = content

        import aiofiles
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(data)

        logger.debug(
            "File disimpan: %s (encrypted=%s, size=%d bytes)",
            filename, self._encryption_enabled, len(data),
        )
        return file_path

    async def read(self, file_path: Path) -> bytes:
        """
        Baca file dari disk. Dekripsi jika file terenkripsi.
        Raise ValueError jika dekripsi gagal (file dimodifikasi).
        """
        import aiofiles
        async with aiofiles.open(file_path, "rb") as f:
            data = await f.read()

        # Deteksi apakah file terenkripsi berdasarkan magic bytes
        if data[:4] == _MAGIC:
            if not self._encryption_enabled or not self._key:
                raise ValueError(
                    "File terenkripsi tapi ENCRYPTION_KEY tidak tersedia"
                )
            return self._decrypt(data)

        # File tidak terenkripsi — kembalikan langsung
        return data

    async def delete(self, file_path: Path) -> None:
        """Hapus file dari disk secara aman."""
        if file_path.exists():
            # Overwrite sebelum hapus untuk mengurangi risiko recovery
            try:
                size = file_path.stat().st_size
                import aiofiles
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(os.urandom(min(size, 4096)))
            except Exception:
                pass  # Jika overwrite gagal, tetap hapus
            file_path.unlink(missing_ok=True)
            logger.debug("File dihapus: %s", file_path.name)

    def _encrypt(self, plaintext: bytes) -> bytes:
        """
        Enkripsi menggunakan AES-256-GCM.
        Format output: magic(4) + version(1) + nonce(12) + ciphertext+tag
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = os.urandom(_NONCE_SIZE)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # Header: magic + version + nonce
        header = _MAGIC + struct.pack("B", _VERSION) + nonce
        return header + ciphertext

    def _decrypt(self, data: bytes) -> bytes:
        """
        Dekripsi data terenkripsi.
        Raise InvalidTag jika data dimodifikasi (authenticated encryption).
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.exceptions import InvalidTag

        if len(data) < _HEADER_SIZE + 16:  # minimum: header + GCM tag
            raise ValueError("File terlalu kecil untuk format enkripsi yang valid")

        # Parse header
        magic = data[:4]
        if magic != _MAGIC:
            raise ValueError("Magic bytes tidak cocok — bukan file terenkripsi ACMV")

        version = struct.unpack("B", data[4:5])[0]
        if version != _VERSION:
            raise ValueError(f"Versi format tidak didukung: {version}")

        nonce = data[5 : 5 + _NONCE_SIZE]
        ciphertext = data[_HEADER_SIZE:]

        aesgcm = AESGCM(self._key)
        try:
            return aesgcm.decrypt(nonce, ciphertext, None)
        except InvalidTag:
            raise ValueError(
                "Dekripsi gagal — file mungkin dimodifikasi atau kunci salah"
            )


# ── Singleton factory ───────────────────────────────────────────────────────

_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Return singleton StorageService."""
    global _storage_service
    if _storage_service is None:
        from app.core.config import settings
        enc_key = settings.encryption_key.get_secret_value() if settings.encryption_key else None
        _storage_service = StorageService(
            upload_dir=settings.upload_dir,
            encryption_key=enc_key,
        )
    return _storage_service
