"""Service for indexing external Markdown files from watch directories."""

import datetime
import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import frontmatter

from zettelkasten_mcp.models.schema import (
    Link,
    LinkType,
    Note,
    NoteType,
    Tag,
    link_type_registry,
)

if TYPE_CHECKING:
    from zettelkasten_mcp.storage.note_repository import NoteRepository

logger = logging.getLogger(__name__)


def _generate_external_id(absolute_path: Path) -> str:
    """Generate a stable ID for a watch-folder file with no frontmatter id.

    Uses a SHA-256 hash of the absolute path so the ID is deterministic
    across re-scans even if the file content changes.

    Args:
        absolute_path: Absolute path to the Markdown file.

    Returns:
        ID string of the form ``ext-<first 12 hex chars of sha256>``.
    """
    digest = hashlib.sha256(str(absolute_path.resolve()).encode()).hexdigest()
    return f"ext-{digest[:12]}"


def _parse_external_note(file_path: Path) -> Note:  # noqa: PLR0912, PLR0915
    """Parse a single Markdown file from a watch folder into a ``Note``.

    Files with compatible YAML frontmatter (containing at least ``id`` or
    ``title``) are treated as full notes.  Files without frontmatter are
    treated as lightweight stubs with an auto-generated ID.

    Args:
        file_path: Absolute path to the Markdown file.

    Returns:
        A ``Note`` with ``is_readonly=True`` and ``source_path`` set.

    Raises:
        Exception: Any parse error (caller logs and skips).
    """
    raw = file_path.read_text(encoding="utf-8")
    post = frontmatter.loads(raw)
    meta = post.metadata

    # --- ID ---
    note_id = str(meta.get("id", "")).strip() or _generate_external_id(file_path)

    # --- Title ---
    title = str(meta.get("title", "")).strip()
    if not title:
        # Try to find first heading in content
        for line in post.content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                break
    if not title:
        title = file_path.stem

    # --- Note type ---
    note_type_str = meta.get("type", NoteType.PERMANENT.value)
    try:
        note_type = NoteType(note_type_str)
    except ValueError:
        note_type = NoteType.PERMANENT

    # --- Tags ---
    tags_raw = meta.get("tags", "")
    if isinstance(tags_raw, str):
        tag_names = [t.strip() for t in tags_raw.split(",") if t.strip()]
    elif isinstance(tags_raw, list):
        tag_names = [str(t).strip() for t in tags_raw if str(t).strip()]
    else:
        tag_names = []
    tags = [Tag(name=n) for n in tag_names]

    # --- Links (parse ## Links section if present) ---
    links: list[Link] = []
    in_links_section = False
    for raw_line in post.content.split("\n"):
        line = raw_line.strip()
        if line.startswith("## Links"):
            in_links_section = True
            continue
        if in_links_section and line.startswith("## "):
            in_links_section = False
            continue
        if in_links_section and line.startswith("- ") and "[[" in line:
            try:
                parts = line.split("[[", 1)
                link_type_str = parts[0].strip().lstrip("- ").strip()
                id_and_desc = parts[1].split("]]", 1)
                target_id = id_and_desc[0].strip()
                description: str | None = (
                    id_and_desc[1].strip() if len(id_and_desc) > 1 else None
                ) or None
                # Fall back to reference for unknown link types
                # (check registry which includes custom types)
                if not link_type_registry.is_valid(link_type_str):
                    link_type_str = LinkType.REFERENCE.value
                links.append(
                    Link(
                        source_id=note_id,
                        target_id=target_id,
                        link_type=link_type_str,
                        description=description,
                        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
                    ),
                )
            except Exception:  # noqa: BLE001
                logger.debug(
                    "Could not parse link line in %s: %s",
                    file_path,
                    line,
                )

    # --- Timestamps ---
    created_str = meta.get("created") or meta.get("date")
    if isinstance(created_str, str):
        try:
            created_at: datetime.datetime = datetime.datetime.fromisoformat(created_str)
        except ValueError:
            created_at = datetime.datetime.now(tz=datetime.timezone.utc)
    elif isinstance(created_str, datetime.datetime):
        created_at = created_str
    else:
        stat = file_path.stat()
        created_at = datetime.datetime.fromtimestamp(
            stat.st_ctime,
            tz=datetime.timezone.utc,
        )

    updated_str = meta.get("updated")
    if isinstance(updated_str, str):
        try:
            updated_at: datetime.datetime = datetime.datetime.fromisoformat(updated_str)
        except ValueError:
            updated_at = created_at
    elif isinstance(updated_str, datetime.datetime):
        updated_at = updated_str
    else:
        stat = file_path.stat()
        updated_at = datetime.datetime.fromtimestamp(
            stat.st_mtime,
            tz=datetime.timezone.utc,
        )

    return Note(
        id=note_id,
        title=title,
        content=post.content,
        note_type=note_type,
        tags=tags,
        links=links,
        created_at=created_at,
        updated_at=updated_at,
        is_readonly=True,
        source_path=str(file_path.resolve()),
    )


class WatchFolderService:
    """Indexes external Markdown directories as read-only reference notes.

    On server startup and on demand (via ``sync_all``), it scans every
    configured watch directory recursively for ``.md`` files, parses their
    YAML frontmatter, and upserts them into the SQLite index with
    ``is_readonly=True``.

    Primary (writable) notes in ``ZETTELKASTEN_NOTES_DIR`` are never
    touched by this service.
    """

    def __init__(
        self,
        watch_dirs: list[Path],
        repository: "NoteRepository",
    ) -> None:
        """Initialise the service.

        Args:
            watch_dirs: Directories to scan.  Empty list disables the feature.
            repository: Active ``NoteRepository`` used for DB indexing.
        """
        self.watch_dirs = watch_dirs
        self.repository = repository

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan_directory(self, path: Path) -> list[Note]:
        """Recursively scan *path* for Markdown files and return parsed Notes.

        Files with parse errors are logged at WARNING level and skipped.

        Args:
            path: Directory to scan (must exist).

        Returns:
            List of ``Note`` objects (all have ``is_readonly=True``).
        """
        notes: list[Note] = []
        for md_file in sorted(path.rglob("*.md")):
            if not md_file.is_file():
                continue
            try:
                note = _parse_external_note(md_file)
                notes.append(note)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Watch folder: failed to parse %s — %s",
                    md_file,
                    exc,
                )
        return notes

    def sync_all(self) -> dict[str, Any]:
        """Re-scan all watch directories and refresh the SQLite index.

        Drops all existing ``is_readonly=True`` entries from the DB, then
        re-ingests every Markdown file found in the configured watch dirs.

        Returns:
            Summary dict with keys:
            - ``scanned``: total ``.md`` files encountered
            - ``added``: notes successfully indexed
            - ``removed``: stale entries removed from DB
            - ``errors``: list of ``(path, error_message)`` tuples
        """
        if not self.watch_dirs:
            logger.debug("WatchFolderService.sync_all: no watch dirs configured")
            return {"scanned": 0, "added": 0, "removed": 0, "errors": []}

        # --- Collect the IDs currently in the DB before dropping ---
        previous_ids = self._get_readonly_ids()

        # --- Drop all existing watch-folder rows from the DB ---
        self._drop_readonly_entries()

        # --- Re-scan and ingest ---
        scanned = 0
        added = 0
        new_ids: set[str] = set()
        errors: list[tuple[str, str]] = []

        for watch_dir in self.watch_dirs:
            if not watch_dir.is_dir():
                logger.warning(
                    "WatchFolderService: watch directory no longer exists: %s",
                    watch_dir,
                )
                continue
            for md_file in sorted(watch_dir.rglob("*.md")):
                if not md_file.is_file():
                    continue
                scanned += 1
                try:
                    note = _parse_external_note(md_file)
                    self.repository._index_note(note)  # noqa: SLF001
                    new_ids.add(note.id)
                    added += 1
                    logger.debug(
                        "Watch folder indexed: %s → %s",
                        md_file,
                        note.id,
                    )
                except Exception as exc:  # noqa: BLE001
                    err_msg = str(exc)
                    errors.append((str(md_file), err_msg))
                    logger.warning(
                        "Watch folder: failed to index %s — %s",
                        md_file,
                        err_msg,
                    )

        # Stale entries are those that existed before but are no longer present
        # in the watch directories (deleted or moved files). This count helps
        # users understand how many external notes were removed from the index.
        removed = len(previous_ids - new_ids)

        logger.info(
            "WatchFolderService sync: scanned=%d added=%d removed=%d errors=%d",
            scanned,
            added,
            removed,
            len(errors),
        )
        return {
            "scanned": scanned,
            "added": added,
            "removed": removed,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_readonly_ids(self) -> set[str]:
        """Return the set of IDs for all current read-only notes in the DB."""
        from sqlalchemy import select  # noqa: PLC0415

        from zettelkasten_mcp.models.db_models import DBNote  # noqa: PLC0415

        with self.repository.session_factory() as session:
            ids = session.scalars(
                select(DBNote.id).where(DBNote.is_readonly.is_(True)),
            ).all()
        return set(ids)

    def _drop_readonly_entries(self) -> int:
        """Delete all is_readonly=True rows and their outgoing links from the DB.

        Only links *originating* from read-only notes are removed; incoming
        links from primary notes to external notes are left intact so the
        graph is not silently broken.

        Returns:
            Number of note rows removed.
        """
        from sqlalchemy import select, text  # noqa: PLC0415

        from zettelkasten_mcp.models.db_models import DBNote  # noqa: PLC0415

        removed = 0
        with self.repository.session_factory() as session:
            readonly_notes = session.scalars(
                select(DBNote).where(DBNote.is_readonly.is_(True)),
            ).all()
            for db_note in readonly_notes:
                note_id = db_note.id
                # Only remove links where this read-only note is the *source*
                session.execute(
                    text("DELETE FROM links WHERE source_id = :id"),
                    {"id": note_id},
                )
                session.execute(
                    text("DELETE FROM note_tags WHERE note_id = :id"),
                    {"id": note_id},
                )
                session.execute(
                    text("DELETE FROM notes_fts WHERE id = :id"),
                    {"id": note_id},
                )
                session.execute(
                    text("DELETE FROM notes WHERE id = :id"),
                    {"id": note_id},
                )
                removed += 1
            session.commit()
        return removed
