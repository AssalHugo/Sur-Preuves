"""Local CPU embedding service using fastembed (ONNX Runtime)."""

import json
import logging
from pathlib import Path
from typing import Any

from csc.config import settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "intfloat/multilingual-e5-large"
DEV_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_DIMENSION = 1024
DEV_DIMENSION = 384


class CpuEmbedder:
    """CPU-bound text embedding generator with mandatory e5 prefixing and checkpointing."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        cache_dir: Path | None = None,
        threads: int = 0,
        batch_size: int = 64,
    ) -> None:
        if "bge-small-en" in model_name:
            raise ValueError(
                "Model 'bge-small-en' is English-only and prohibited. "
                "Use multilingual-e5-large or MiniLM."
            )
        self.model_name = model_name
        self.cache_dir = cache_dir or settings.models_cache_dir
        self.threads = threads
        self.batch_size = batch_size
        self._model: Any = None

    def _resolve_cache_dir(self) -> Path:
        target = self.cache_dir
        if not target.is_absolute():
            root = Path(__file__).resolve().parents[4]
            target = root / target
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _get_model(self) -> Any:
        if self._model is None:
            from fastembed import TextEmbedding

            cache_path = str(self._resolve_cache_dir())
            logger.info(
                "Loading fastembed model '%s' on CPU (cache: %s)...", self.model_name, cache_path
            )
            self._model = TextEmbedding(
                model_name=self.model_name,
                cache_dir=cache_path,
                threads=self.threads if self.threads > 0 else None,
            )
        return self._model

    def query(self, text: str) -> list[float]:
        """Embed a single search query with mandatory 'query: ' prefix."""
        prefixed = text if text.startswith("query: ") else f"query: {text}"
        model = self._get_model()
        vectors = list(model.embed([prefixed]))
        first_vec: Any = vectors[0]
        return [float(x) for x in first_vec]

    def passages(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple document passages with mandatory 'passage: ' prefix."""
        if not texts:
            return []

        prefixed_texts = [t if t.startswith("passage: ") else f"passage: {t}" for t in texts]
        model = self._get_model()
        raw_vectors = model.embed(
            prefixed_texts,
            batch_size=self.batch_size,
            parallel=self.threads,
        )
        return [[float(x) for x in vec] for vec in raw_vectors]

    def check_dimension(self, expected_dimension: int = DEFAULT_DIMENSION) -> bool:
        """Validate that the embedding model dimension matches the database schema column."""
        probe = self.query("dimension_check")
        dim = len(probe)
        if dim != expected_dimension:
            raise ValueError(
                f"Embedding dimension mismatch: model '{self.model_name}' produces "
                f"{dim} dimensions, but schema requires {expected_dimension}."
            )
        return True

    def embed_passages_resumable(
        self,
        texts: list[str],
        checkpoint_path: Path | None = None,
        batch_size: int | None = None,
    ) -> list[list[float]]:
        """Embed passages in batches with resumption support in case of interruption."""
        if not texts:
            return []

        bs = batch_size or self.batch_size
        results: list[list[float]] = []
        start_idx = 0

        # Load checkpoint if available
        if checkpoint_path and checkpoint_path.exists():
            try:
                data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                saved_vectors = data.get("vectors", [])
                if len(saved_vectors) <= len(texts):
                    results = saved_vectors
                    start_idx = len(results)
                    logger.info("Resuming embedding from item index %d/%d", start_idx, len(texts))
            except Exception as e:
                logger.warning("Failed to read checkpoint %s: %s", checkpoint_path, e)

        for i in range(start_idx, len(texts), bs):
            chunk = texts[i : i + bs]
            chunk_vectors = self.passages(chunk)
            results.extend(chunk_vectors)

            # Save checkpoint atomically
            if checkpoint_path is not None:
                try:
                    payload = {"vectors": results, "processed_count": len(results)}
                    tmp_ckpt = checkpoint_path.with_suffix(f"{checkpoint_path.suffix}.tmp")
                    tmp_ckpt.write_text(json.dumps(payload), encoding="utf-8")
                    tmp_ckpt.replace(checkpoint_path)
                except Exception as e:
                    logger.warning("Failed to write checkpoint %s: %s", checkpoint_path, e)

        return results


embed = CpuEmbedder()
