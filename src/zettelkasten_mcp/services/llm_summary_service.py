"""LLM-powered summary generation service for Zettelkasten notes.

Generates English summaries and search keywords for notes written in any
language, enabling cross-language search via the FTS5 en_summary and
en_keywords columns.

Requires Azure OpenAI credentials (Azure CLI auth).  If the endpoint is
not configured or the API call fails the service returns ``None`` — LLM
failures never block note creation or updates.
"""

import json
import logging
from typing import Any

from zettelkasten_mcp.config import config

logger = logging.getLogger(__name__)

_SUMMARY_PROMPT = """\
Generate an English summary and keyword list for the following note.

Title: {title}
Content: {content}
Tags: {tags}

Requirements:
- summary: 80-150 words in English, capturing the key ideas
- keywords: 5-10 single lowercase words (no hyphens), optimised for full-text search

Respond with valid JSON only, no markdown fences:
{{"summary": "...", "keywords": ["word1", "word2", ...]}}"""


class LLMSummaryService:
    """Service for generating LLM summaries of notes via Azure OpenAI."""

    def __init__(self) -> None:
        """Initialise the service; client is created lazily on first use."""
        self._client: Any = None

    def is_enabled(self) -> bool:
        """Return True if LLM summaries are configured and enabled."""
        return bool(config.llm_enable_summaries and config.azure_openai_endpoint)

    def _get_client(self) -> Any | None:
        """Return (and lazily initialise) the Azure OpenAI client."""
        if self._client is not None:
            return self._client
        if not self.is_enabled():
            return None
        try:
            from azure.identity import (  # type: ignore[import-untyped]  # noqa: PLC0415
                DefaultAzureCredential,
                get_bearer_token_provider,
            )
            from openai import (  # noqa: PLC0415
                AzureOpenAI,  # type: ignore[import-untyped]
            )

            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default",
            )
            self._client = AzureOpenAI(
                azure_endpoint=config.azure_openai_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=config.azure_openai_api_version,
            )
            logger.info(
                "Azure OpenAI client initialised (endpoint: %s)",
                config.azure_openai_endpoint,
            )
        except ImportError:
            logger.warning(
                "openai / azure-identity packages not installed; "
                "LLM summaries disabled. Install with: uv add openai azure-identity"
            )
        except Exception:
            logger.exception("Failed to initialise Azure OpenAI client")
        return self._client

    def generate_summary(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Generate an English summary and keywords for a note.

        Args:
            title: Note title.
            content: Note content (Markdown).
            tags: Optional list of tag names.

        Returns:
            Dict with ``summary`` (str) and ``keywords`` (list[str]), or
            ``None`` if generation failed or is disabled.
        """
        if not self.is_enabled():
            return None

        client = self._get_client()
        if client is None:
            return None

        # Truncate very long content to stay within token budget
        max_content_chars = 4000
        truncated = content[:max_content_chars]
        if len(content) > max_content_chars:
            truncated += "\n[... truncated ...]"

        prompt = _SUMMARY_PROMPT.format(
            title=title,
            content=truncated,
            tags=", ".join(tags or []),
        )

        try:
            response = client.chat.completions.create(
                model=config.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.llm_temperature,
                max_tokens=config.llm_max_tokens,
            )
            raw = response.choices[0].message.content or ""
            data = json.loads(raw.strip())

            summary = str(data.get("summary", "")).strip()
            keywords = [str(k).lower().strip() for k in data.get("keywords", []) if k]

            if not summary:
                logger.warning("LLM returned empty summary for note '%s'", title)
                return None

            logger.debug(
                "Generated summary for '%s' (%d keywords)",
                title,
                len(keywords),
            )

        except json.JSONDecodeError as exc:
            logger.warning(
                "Failed to parse LLM JSON response for note '%s': %s",
                title,
                exc,
            )
            return None
        except Exception:  # noqa: BLE001
            logger.warning(
                "LLM summary generation failed for note '%s'"
                " (will retry on next rebuild)",
                title,
                exc_info=True,
            )
            return None
        else:
            return {"summary": summary, "keywords": keywords}
