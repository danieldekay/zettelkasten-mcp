"""Summary cache service for persisting LLM-generated note summaries.

The cache (``note_summary_cache`` table) survives ``rebuild_index()`` so that
expensive LLM calls are only made once per unique note content.  A SHA-256
hash of the note's key fields (title + content + sorted tags) is the cache
key, so stale entries are ignored when content changes.
"""

import datetime
import hashlib
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from zettelkasten_mcp.models.db_models import DBNoteSummaryCache

logger = logging.getLogger(__name__)


def calculate_content_hash(
    title: str, content: str, tags: list[str] | None = None
) -> str:
    """Compute a deterministic SHA-256 hash of a note's key fields.

    Tags are sorted before hashing to ensure the hash is stable regardless of
    the order in which tags were attached to the note.
    """
    sorted_tags = sorted(tags or [])
    payload = f"{title}|||{content}|||{'|'.join(sorted_tags)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class SummaryCacheService:
    """Manages the ``note_summary_cache`` table for LLM summary persistence."""

    def get_from_cache(
        self,
        session: Session,
        note_id: str,
        content_hash: str,
    ) -> dict[str, Any] | None:
        """Return a cached summary if the content hash matches, else None.

        Args:
            session: Active SQLAlchemy session.
            note_id: The note's ID.
            content_hash: Hash of the note's current content (see
                :func:`calculate_content_hash`).

        Returns:
            Dict with ``summary`` and ``keywords`` if a valid cache entry
            exists, or ``None``.
        """
        try:
            entry: DBNoteSummaryCache | None = session.get(DBNoteSummaryCache, note_id)
            if entry is None:
                return None
            if entry.content_hash != content_hash:
                # Content has changed — cached value is stale
                logger.debug("Cache miss (hash mismatch) for note %s", note_id)
                return None

            keywords = json.loads(str(entry.en_keywords)) if entry.en_keywords else []
            logger.debug("Cache hit for note %s", note_id)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Failed to read summary cache for note %s", note_id, exc_info=True
            )
            return None
        else:
            return {"summary": entry.en_summary, "keywords": keywords}

    def save_to_cache(
        self,
        session: Session,
        note_id: str,
        content_hash: str,
        summary_dict: dict[str, Any],
        llm_model: str,
    ) -> None:
        """Persist an LLM-generated summary to the cache.

        Uses INSERT-OR-REPLACE semantics: an existing entry for the same
        ``note_id`` is overwritten.

        Args:
            session: Active SQLAlchemy session.
            note_id: The note's ID.
            content_hash: Hash used to detect future content changes.
            summary_dict: Dict with ``summary`` (str) and ``keywords`` (list[str]).
            llm_model: Model name used for generation (for audit/debug).
        """
        try:
            keywords_json = json.dumps(summary_dict.get("keywords", []))
            entry: DBNoteSummaryCache | None = session.get(DBNoteSummaryCache, note_id)
            if entry is None:
                entry = DBNoteSummaryCache(note_id=note_id)
                session.add(entry)

            entry.content_hash = content_hash  # type: ignore[assignment]
            entry.en_summary = summary_dict.get("summary", "")  # type: ignore[assignment]
            entry.en_keywords = keywords_json  # type: ignore[assignment]
            entry.generated_at = datetime.datetime.now(tz=datetime.timezone.utc)  # type: ignore[assignment]
            entry.llm_model = llm_model  # type: ignore[assignment]

            logger.debug("Saved summary cache entry for note %s", note_id)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Failed to save summary cache for note %s", note_id, exc_info=True
            )
