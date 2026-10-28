"""Tests for CPU text embeddings using fastembed."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from csc.embed.embedder import (
    DEV_DIMENSION,
    DEV_MODEL,
    CpuEmbedder,
)


def test_bge_small_en_prohibited() -> None:
    """Model bge-small-en is English-only and must be rejected at initialization."""
    with pytest.raises(ValueError) as exc_info:
        CpuEmbedder(model_name="BAAI/bge-small-en-v1.5")
    assert "prohibited" in str(exc_info.value)


def test_query_and_passages_mandatory_prefixes() -> None:
    """e5 models require 'query: ' and 'passage: ' prefixes."""
    embedder = CpuEmbedder(model_name=DEV_MODEL)

    mock_model = MagicMock()
    # Mock returning 384-dim dummy vector
    mock_model.embed.side_effect = lambda texts, **kwargs: [[0.05] * DEV_DIMENSION for _ in texts]
    embedder._model = mock_model

    # 1. Query prefix
    vec = embedder.query("politique de transition énergétique")
    assert len(vec) == DEV_DIMENSION
    call_args = mock_model.embed.call_args[0][0]
    assert call_args[0] == "query: politique de transition énergétique"

    # Already prefixed query should not be double prefixed
    embedder.query("query: déjà préfixé")
    call_args2 = mock_model.embed.call_args[0][0]
    assert call_args2[0] == "query: déjà préfixé"

    # 2. Passages prefix
    passages = ["Extrait du rapport GIEC", "Amendement législatif"]
    res = embedder.passages(passages)
    assert len(res) == 2
    assert len(res[0]) == DEV_DIMENSION
    p_args = mock_model.embed.call_args[0][0]
    assert p_args == ["passage: Extrait du rapport GIEC", "passage: Amendement législatif"]


def test_check_dimension_consistency() -> None:
    """Model output dimension must match expected database vector schema."""
    embedder = CpuEmbedder(model_name=DEV_MODEL)
    mock_model = MagicMock()
    mock_model.embed.return_value = [[0.1] * DEV_DIMENSION]
    embedder._model = mock_model

    # Matches dev dimension 384
    assert embedder.check_dimension(expected_dimension=DEV_DIMENSION) is True

    # Fails against production dimension 1024
    with pytest.raises(ValueError) as exc_info:
        embedder.check_dimension(expected_dimension=1024)
    assert "Embedding dimension mismatch" in str(exc_info.value)


def test_embedding_1000_passages_cpu() -> None:
    """Embedding 1,000 passages with MiniLM runs in batches of 64 on CPU with 384-dim output."""
    embedder = CpuEmbedder(model_name=DEV_MODEL, batch_size=64)

    mock_model = MagicMock()
    # Simulates batch generation
    mock_model.embed.side_effect = lambda texts, **kwargs: [[0.01] * DEV_DIMENSION for _ in texts]
    embedder._model = mock_model

    corpus = [f"Passage scientifique numéro {i} sur les politiques publiques." for i in range(1000)]
    vectors = embedder.passages(corpus)

    assert len(vectors) == 1000
    assert len(vectors[0]) == DEV_DIMENSION
    # Check that embed was called with parallel=0 (all cores) and batch_size=64
    _, kwargs = mock_model.embed.call_args
    assert kwargs.get("batch_size") == 64
    assert kwargs.get("parallel") == 0


def test_embed_passages_resumable(tmp_path: Path) -> None:
    """Resumable embedding must persist checkpoints and resume without recomputing."""
    embedder = CpuEmbedder(model_name=DEV_MODEL, batch_size=10)

    mock_model = MagicMock()
    mock_model.embed.side_effect = lambda texts, **kwargs: [[0.02] * DEV_DIMENSION for _ in texts]
    embedder._model = mock_model

    checkpoint = tmp_path / "embed_ckpt.json"
    corpus = [f"Passage {i}" for i in range(25)]

    # 1. Run first 10 items then simulate interruption
    initial_vectors = embedder.embed_passages_resumable(corpus[:10], checkpoint_path=checkpoint)
    assert len(initial_vectors) == 10
    assert checkpoint.exists()

    # 2. Resume full 25 items: it should read the first 10 from checkpoint and process remaining 15
    resumed_vectors = embedder.embed_passages_resumable(corpus, checkpoint_path=checkpoint)
    assert len(resumed_vectors) == 25

    final_ckpt = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert final_ckpt["processed_count"] == 25
