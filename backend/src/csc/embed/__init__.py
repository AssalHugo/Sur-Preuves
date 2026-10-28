"""Embedding module for semantic search and retrieval."""

from csc.embed.embedder import (
    DEFAULT_DIMENSION,
    DEFAULT_MODEL,
    DEV_DIMENSION,
    DEV_MODEL,
    CpuEmbedder,
    embed,
)

__all__ = [
    "CpuEmbedder",
    "DEFAULT_DIMENSION",
    "DEFAULT_MODEL",
    "DEV_DIMENSION",
    "DEV_MODEL",
    "embed",
]
