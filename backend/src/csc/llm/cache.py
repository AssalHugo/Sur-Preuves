"""Local LLM disk cache for reproducible and zero-cost re-execution."""

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from csc.config import settings


class CachedResponse(BaseModel):
    """Cached response metadata and textual output."""

    raw_output: str
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    latency_ms: int = 0


class LocalLlmCache:
    """Stores and retrieves LLM generation results keyed by sha, model, params and variables."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or settings.llm_cache_dir

    def _resolve_dir(self) -> Path:
        target = self.cache_dir
        if not target.is_absolute():
            root = Path(__file__).resolve().parents[4]
            target = root / target
        target.mkdir(parents=True, exist_ok=True)
        return target

    def compute_key(
        self,
        prompt_sha: str,
        model: str,
        params: dict[str, Any],
        variables: dict[str, Any],
    ) -> str:
        """Compute deterministic SHA-256 cache key."""
        payload = {
            "prompt_sha": prompt_sha,
            "model": model,
            "params": params,
            "variables": variables,
        }
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self, key: str) -> CachedResponse | None:
        """Retrieve cached output if present on disk."""
        target_dir = self._resolve_dir()
        path = target_dir / f"{key}.json"
        if not path.exists():
            return None
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            return CachedResponse(**data)
        except Exception:
            return None

    def set(
        self,
        key: str,
        raw_output: str,
        input_tokens: int = 0,
        cached_tokens: int = 0,
        output_tokens: int = 0,
        thinking_tokens: int = 0,
        latency_ms: int = 0,
    ) -> None:
        """Persist output to disk cache."""
        target_dir = self._resolve_dir()
        path = target_dir / f"{key}.json"
        cached = CachedResponse(
            raw_output=raw_output,
            input_tokens=input_tokens,
            cached_tokens=cached_tokens,
            output_tokens=output_tokens,
            thinking_tokens=thinking_tokens,
            latency_ms=latency_ms,
        )
        try:
            path.write_text(cached.model_dump_json(indent=2), encoding="utf-8")
        except Exception:
            pass

    def clear(self) -> None:
        """Clear all cached entries."""
        target_dir = self._resolve_dir()
        for f in target_dir.glob("*.json"):
            try:
                f.unlink()
            except Exception:
                pass


local_cache = LocalLlmCache()
