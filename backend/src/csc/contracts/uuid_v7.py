"""Générateur d'identifiants uniques UUIDv7 conformes RFC 9562.

Les UUIDv7 garantissent un tri chronologique (ordonnancement monotone par milliseconde)
et sont adaptés pour les identifiants stables exposés dans les URL publiques.
"""

from __future__ import annotations

import os
import threading
import time
import uuid


class _UUID7Generator:
    """Générateur thread-safe d'UUIDv7 avec compteur monotone."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_ms = 0
        self._seq = 0

    def generate(self) -> uuid.UUID:
        with self._lock:
            ns = time.time_ns()
            ms = ns // 1_000_000

            if ms > self._last_ms:
                self._last_ms = ms
                self._seq = int.from_bytes(os.urandom(2), "big") & 0x0FFF
            else:
                self._seq = (self._seq + 1) & 0x0FFF
                ms = self._last_ms

            seq = self._seq
            last_ms = ms

        rand_b = os.urandom(8)

        # Octets 0 à 5 : timestamp 48 bits (millisecondes depuis epoch)
        b0 = (last_ms >> 40) & 0xFF
        b1 = (last_ms >> 32) & 0xFF
        b2 = (last_ms >> 24) & 0xFF
        b3 = (last_ms >> 16) & 0xFF
        b4 = (last_ms >> 8) & 0xFF
        b5 = last_ms & 0xFF

        # Octets 6 et 7 : 4 bits version (0b0111 = 7) + 12 bits sequence
        b6 = 0x70 | ((seq >> 8) & 0x0F)
        b7 = seq & 0xFF

        # Octet 8 : 2 bits variant (0b10 = RFC 4122/9562) + 6 bits rand_b
        b8 = 0x80 | (rand_b[0] & 0x3F)

        raw_bytes = bytes([b0, b1, b2, b3, b4, b5, b6, b7, b8]) + rand_b[1:8]
        return uuid.UUID(bytes=raw_bytes)


_default_gen = _UUID7Generator()


def uuid7() -> uuid.UUID:
    """Génère une instance UUID version 7."""
    return _default_gen.generate()


def uuid7_str() -> str:
    """Génère un UUIDv7 sous forme de chaîne de caractères normalisée."""
    return str(_default_gen.generate())
