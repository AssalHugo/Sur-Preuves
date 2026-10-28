"""Prompt template management with YAML frontmatter and Jinja2 rendering."""

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel, Field

from csc.config import settings
from csc.llm.exceptions import ImplicitCacheViolationError, PromptNotFoundError

# Regex for frontmatter: starting with ---, ending with ---
_FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class PromptMetadata(BaseModel):
    """Metadata extracted from prompt frontmatter."""

    id: str
    version: str = "1.0.0"
    description: str = ""
    role: str = "extraction"
    min_prefix_tokens: int = Field(
        default=50, description="Minimum static prefix tokens before variables"
    )


class PromptTemplate:
    """Parsed prompt template with metadata, sha, and Jinja2 environment."""

    def __init__(
        self,
        metadata: PromptMetadata,
        raw_body: str,
        sha256: str,
        path: Path,
    ) -> None:
        self.metadata = metadata
        self.raw_body = raw_body
        self.sha256 = sha256
        self.path = path
        self._jinja_env = Environment(undefined=StrictUndefined, autoescape=False)
        self._template = self._jinja_env.from_string(raw_body)

    def validate_cache_prefix(self) -> None:
        """Verify that dynamic variables do not appear in the initial prefix of the prompt.

        Implicit caching requires a stable prefix for Gemini to cache the preamble across calls.
        """
        match = re.search(r"(\{\{|\{%)", self.raw_body)
        first_tag_pos = match.start() if match else len(self.raw_body)

        # Approximate token count by word splitting (~0.75 tokens per word or 4 chars/token)
        prefix = self.raw_body[:first_tag_pos]
        prefix_words = prefix.split()
        estimated_prefix_tokens = len(prefix_words)

        if estimated_prefix_tokens < self.metadata.min_prefix_tokens:
            raise ImplicitCacheViolationError(
                f"Prompt '{self.metadata.id}' places dynamic variables after only "
                f"{estimated_prefix_tokens} tokens "
                f"(minimum required: {self.metadata.min_prefix_tokens}). "
                "Move static instructions, methodology and schemas before variables."
            )

    def render(self, variables: dict[str, Any]) -> str:
        """Render the Jinja2 template with provided variables."""
        return self._template.render(**variables)


class PromptManager:
    """Loads and renders prompt files from the prompts/ directory."""

    def __init__(self, prompts_dir: Path | None = None) -> None:
        self.prompts_dir = prompts_dir or settings.prompts_dir
        self._cache: dict[str, PromptTemplate] = {}

    def _resolve_prompts_dir(self) -> Path:
        target = self.prompts_dir
        if not target.is_absolute():
            root = Path(__file__).resolve().parents[4]
            if (root / target).exists():
                return root / target
        return target

    def get_template(self, prompt_id: str) -> PromptTemplate:
        """Load and cache a prompt template by ID."""
        if prompt_id in self._cache:
            return self._cache[prompt_id]

        prompts_dir = self._resolve_prompts_dir()
        candidate = prompts_dir / f"{prompt_id}.md"
        if not candidate.exists():
            # Try without extension or with .jinja2
            alt = prompts_dir / f"{prompt_id}"
            if alt.exists():
                candidate = alt
            else:
                alt2 = prompts_dir / f"{prompt_id}.jinja2"
                if alt2.exists():
                    candidate = alt2
                else:
                    raise PromptNotFoundError(
                        f"Prompt template '{prompt_id}' not found in {prompts_dir}."
                    )

        content = candidate.read_text(encoding="utf-8")
        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

        match = _FRONTMATTER_PATTERN.match(content)
        if match:
            frontmatter_raw = match.group(1)
            raw_body = content[match.end() :]
            meta_dict = yaml.safe_load(frontmatter_raw) or {}
            if "id" not in meta_dict:
                meta_dict["id"] = prompt_id
            metadata = PromptMetadata(**meta_dict)
        else:
            metadata = PromptMetadata(id=prompt_id)
            raw_body = content

        template = PromptTemplate(
            metadata=metadata,
            raw_body=raw_body,
            sha256=sha256,
            path=candidate,
        )
        self._cache[prompt_id] = template
        return template

    def render(self, prompt_id: str, variables: dict[str, Any]) -> tuple[str, str, str]:
        """Render prompt and return (rendered_text, version, sha256)."""
        template = self.get_template(prompt_id)
        rendered = template.render(variables)
        return rendered, template.metadata.version, template.sha256


prompt_manager = PromptManager()
