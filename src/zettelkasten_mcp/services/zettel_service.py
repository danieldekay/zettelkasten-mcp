"""Service layer for Zettelkasten operations."""

import datetime
import logging
from typing import Any

from zettelkasten_mcp.models.schema import (
    LinkType,
    Note,
    NoteType,
    Tag,
    link_type_registry,
)
from zettelkasten_mcp.storage.note_repository import NoteRepository

logger = logging.getLogger(__name__)


class ZettelService:
    """Service for managing Zettelkasten notes."""

    def __init__(self, repository: NoteRepository | None = None) -> None:
        """Initialize the service."""
        self.repository = repository or NoteRepository()

    def initialize(self) -> None:
        """Initialize the service and dependencies."""
        # Nothing to do here for synchronous implementation
        # The repository is initialized in its constructor

    def create_note(
        self,
        title: str,
        content: str,
        note_type: NoteType = NoteType.PERMANENT,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Note:
        """Create a new note."""
        if not title:
            msg = "Title is required"
            raise ValueError(msg)
        if not content:
            msg = "Content is required"
            raise ValueError(msg)

        # Create note object
        note = Note(
            title=title,
            content=content,
            note_type=note_type,
            tags=[Tag(name=tag) for tag in (tags or [])],
            metadata=metadata or {},
        )

        # Save to repository
        return self.repository.create(note)

    def get_note(self, note_id: str) -> Note | None:
        """Retrieve a note by ID."""
        return self.repository.get(note_id)

    def get_note_by_title(self, title: str) -> Note | None:
        """Retrieve a note by title."""
        return self.repository.get_by_title(title)

    def update_note(
        self,
        note_id: str,
        title: str | None = None,
        content: str | None = None,
        note_type: NoteType | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Note:
        """Update an existing note."""
        note = self.repository.get(note_id)
        if not note:
            msg = f"Note with ID {note_id} not found"
            raise ValueError(msg)

        if note.is_readonly:
            msg = (
                f"Cannot modify read-only external note '{note_id}' "
                f"(source: {note.source_path}). "
                "Edit the source file directly or use zk_sync_watch_folders to refresh."
            )
            raise PermissionError(msg)

        # Update fields
        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if note_type is not None:
            note.note_type = note_type
        if tags is not None:
            note.tags = [Tag(name=tag) for tag in tags]
        if metadata is not None:
            note.metadata = metadata

        note.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)

        # Save to repository
        return self.repository.update(note)

    def delete_note(self, note_id: str) -> None:
        """Delete a note."""
        note = self.repository.get(note_id)
        if note and note.is_readonly:
            msg = (
                f"Cannot delete read-only external note '{note_id}' "
                f"(source: {note.source_path}). "
                "Remove the source file and run zk_sync_watch_folders to deindex it."
            )
            raise PermissionError(msg)
        self.repository.delete(note_id)

    def get_all_notes(self) -> list[Note]:
        """Get all notes."""
        return self.repository.get_all()

    def search_notes(self, **kwargs: Any) -> list[Note]:
        """Search for notes based on criteria."""
        return self.repository.search(**kwargs)

    def get_notes_by_tag(self, tag: str) -> list[Note]:
        """Get notes by tag."""
        return self.repository.find_by_tag(tag)

    def add_tag_to_note(self, note_id: str, tag: str) -> Note:
        """Add a tag to a note."""
        note = self.repository.get(note_id)
        if not note:
            msg = f"Note with ID {note_id} not found"
            raise ValueError(msg)
        note.add_tag(tag)
        return self.repository.update(note)

    def remove_tag_from_note(self, note_id: str, tag: str) -> Note:
        """Remove a tag from a note."""
        note = self.repository.get(note_id)
        if not note:
            msg = f"Note with ID {note_id} not found"
            raise ValueError(msg)
        note.remove_tag(tag)
        return self.repository.update(note)

    def get_all_tags(self) -> list[Tag]:
        """Get all tags in the system."""
        return self.repository.get_all_tags()

    def get_all_tags_with_counts(self) -> list[tuple[str, int]]:
        """Get all tags with their usage counts."""
        return self.repository.get_tags_with_counts()

    def create_link(
        self,
        source_id: str,
        target_id: str,
        link_type: LinkType | str = LinkType.REFERENCE,
        description: str | None = None,
        bidirectional: bool = False,
        bidirectional_type: LinkType | str | None = None,
    ) -> tuple[Note, Note | None]:
        """Create a link between notes with proper bidirectional semantics."""
        # Normalise link_type to string
        lt = link_type.value if isinstance(link_type, LinkType) else str(link_type)

        source_note = self.repository.get(source_id)
        if not source_note:
            msg = f"Source note with ID {source_id} not found"
            raise ValueError(msg)
        target_note = self.repository.get(target_id)
        if not target_note:
            msg = f"Target note with ID {target_id} not found"
            raise ValueError(msg)

        # Check if this link already exists before attempting to add it
        for link in source_note.links:
            if link.target_id == target_id and link.link_type == lt:
                # Link already exists, no need to add it again
                if not bidirectional:
                    return source_note, None
                break
        else:
            # Only add the link if it doesn't exist
            source_note.add_link(target_id, lt, description)
            source_note = self.repository.update(source_note)

        # If bidirectional, add link from target to source with appropriate semantics
        reverse_note = None
        if bidirectional:
            # Cannot write a reverse link back to a read-only (watch-folder) note
            if target_note.is_readonly:
                logger.warning(
                    "Skipping reverse link: target '%s' is a read-only external note "
                    "(source: %s). Only the forward link was created.",
                    target_id,
                    target_note.source_path,
                )
                return source_note, None

            if bidirectional_type is None:
                bd_str = link_type_registry.get_inverse(lt)
            else:
                bd_str = (
                    bidirectional_type.value
                    if isinstance(bidirectional_type, LinkType)
                    else str(bidirectional_type)
                )

            # Check if the reverse link already exists before adding it
            for link in target_note.links:
                if link.target_id == source_id and link.link_type == bd_str:
                    # Reverse link already exists, no need to add it again
                    return source_note, target_note

            # Only add the reverse link if it doesn't exist
            target_note.add_link(source_id, bd_str, description)
            reverse_note = self.repository.update(target_note)

        return source_note, reverse_note

    def remove_link(
        self,
        source_id: str,
        target_id: str,
        link_type: LinkType | str | None = None,
        bidirectional: bool = False,
    ) -> tuple[Note, Note | None]:
        """Remove a link between notes."""
        source_note = self.repository.get(source_id)
        if not source_note:
            msg = f"Source note with ID {source_id} not found"
            raise ValueError(msg)

        # Remove link from source to target
        source_note.remove_link(target_id, link_type)
        source_note = self.repository.update(source_note)

        # If bidirectional, remove link from target to source
        reverse_note = None
        if bidirectional:
            target_note = self.repository.get(target_id)
            if target_note:
                target_note.remove_link(source_id, link_type)
                reverse_note = self.repository.update(target_note)

        return source_note, reverse_note

    def get_linked_notes(
        self,
        note_id: str,
        direction: str = "outgoing",
    ) -> list[Note]:
        """Get notes linked to/from a note."""
        note = self.repository.get(note_id)
        if not note:
            msg = f"Note with ID {note_id} not found"
            raise ValueError(msg)
        return self.repository.find_linked_notes(note_id, direction)

    def rebuild_index(self) -> None:
        """Rebuild the database index from files."""
        self.repository.rebuild_index()

    def export_note(self, note_id: str, fmt: str = "markdown") -> str:
        """Export a note in the specified format."""
        note = self.repository.get(note_id)
        if not note:
            msg = f"Note with ID {note_id} not found"
            raise ValueError(msg)

        if fmt.lower() == "markdown":
            return note.to_markdown()
        msg = f"Unsupported export format: {fmt}"
        raise ValueError(msg)

    def find_similar_notes(
        self,
        note_id: str,
        threshold: float = 0.5,
    ) -> list[tuple[Note, float]]:
        """Find notes similar to the given note based on shared tags and links."""
        note = self.repository.get(note_id)
        if not note:
            msg = f"Note with ID {note_id} not found"
            raise ValueError(msg)

        # Get all notes
        all_notes = self.repository.get_all()
        results = []

        # Set of this note's tags and links
        note_tags = {tag.name for tag in note.tags}
        note_links = {link.target_id for link in note.links}

        # Add notes linked to this note
        incoming_notes = self.repository.find_linked_notes(note_id, "incoming")
        note_incoming = {n.id for n in incoming_notes}

        # For each note, calculate similarity
        for other_note in all_notes:
            if other_note.id == note_id:
                continue

            # Calculate tag overlap
            other_tags = {tag.name for tag in other_note.tags}
            tag_overlap = len(note_tags.intersection(other_tags))

            # Calculate link overlap (outgoing)
            other_links = {link.target_id for link in other_note.links}
            link_overlap = len(note_links.intersection(other_links))

            # Check if other note links to this note
            incoming_overlap = 1 if other_note.id in note_incoming else 0

            # Check if this note links to other note
            outgoing_overlap = 1 if other_note.id in note_links else 0

            # Calculate similarity score
            # Weight: 40% tags, 20% outgoing links, 20% incoming links,
            # 20% direct connections
            total_possible = (
                max(len(note_tags), len(other_tags)) * 0.4
                + max(len(note_links), len(other_links)) * 0.2
                + 1 * 0.2  # Possible incoming link
                + 1 * 0.2  # Possible outgoing link
            )

            # Avoid division by zero
            if total_possible == 0:
                similarity = 0.0
            else:
                similarity = (
                    (tag_overlap * 0.4)
                    + (link_overlap * 0.2)
                    + (incoming_overlap * 0.2)
                    + (outgoing_overlap * 0.2)
                ) / total_possible

            if similarity >= threshold:
                results.append((other_note, similarity))

        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def register_link_type(
        self,
        name: str,
        inverse: str | None = None,
        symmetric: bool = False,
    ) -> dict:
        """Register a custom project-scoped link type.

        Args:
            name: Unique type name (e.g. ``"implements"``)
            inverse: Inverse type name (defaults to ``name`` if symmetric,
                else ``"<name>_by"``)
            symmetric: Whether the relationship is symmetric

        Returns:
            Dict with ``registered``, ``inverse``, ``symmetric`` keys.

        Raises:
            ValueError: If the type name is empty or already registered.
        """
        import yaml  # noqa: PLC0415

        from zettelkasten_mcp.config import config  # noqa: PLC0415

        name = name.strip().lower()
        if not name:
            msg = "Link type name cannot be empty"
            raise ValueError(msg)

        inv = name if symmetric else (
            inverse.strip().lower() if inverse else f"{name}_by"
        )

        # Registers in module-level registry (raises on duplicate)
        link_type_registry.register(name, inv, symmetric)

        # Persist to openspec/config.yaml
        config_path = config.get_absolute_path(config.custom_link_types_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        if config_path.exists():
            with config_path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        else:
            data = {}

        entries = data.get("custom_link_types", [])
        entries.append({"name": name, "inverse": inv, "symmetric": symmetric})
        data["custom_link_types"] = entries

        with config_path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, default_flow_style=False, allow_unicode=True)

        return {"registered": name, "inverse": inv, "symmetric": symmetric}

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    def create_notes_batch(self, notes: list[dict]) -> dict:
        """Create multiple notes in one atomic transaction.

        Args:
            notes: List of note dicts. Each dict may contain:
                - title (required)
                - content (required)
                - note_type (optional, default "permanent")
                - tags (optional, list[str])
                - metadata (optional, dict)

        Returns:
            Dict with keys ``created``, ``note_ids``, ``failed``, ``errors``.

        Raises:
            ValueError: If any note fails validation before any writes.
        """
        note_objects: list[Note] = []
        for i, note_def in enumerate(notes):
            title = note_def.get("title", "")
            content = note_def.get("content", "")
            if not title:
                msg = f"Note at index {i} has an empty title"
                raise ValueError(msg)
            if not content:
                msg = f"Note at index {i} has empty content"
                raise ValueError(msg)

            raw_type = note_def.get("note_type", NoteType.PERMANENT.value)
            try:
                note_type = NoteType(raw_type)
            except ValueError:
                msg = (
                    f"Note at index {i} has invalid note_type '{raw_type}'. "
                    f"Valid types: {', '.join(t.value for t in NoteType)}"
                )
                raise ValueError(msg)  # noqa: B904

            tag_list = note_def.get("tags") or []
            metadata = note_def.get("metadata") or {}

            note_objects.append(
                Note(
                    title=title,
                    content=content,
                    note_type=note_type,
                    tags=[Tag(name=t) for t in tag_list],
                    metadata=metadata,
                ),
            )

        created = self.repository.create_batch(note_objects)
        return {
            "created": len(created),
            "note_ids": [n.id for n in created],
            "failed": 0,
            "errors": [],
        }

    def create_links_batch(self, links: list[dict]) -> dict:
        """Create multiple semantic links atomically.

        Args:
            links: List of link dicts. Each dict must contain:
                - source_id
                - target_id
                - link_type (optional, default "reference")
                - description (optional)

        Returns:
            Dict with keys ``created``, ``failed``, ``errors``.

        Raises:
            ValueError: If any source/target note does not exist or link_type
                is invalid.
        """
        # Validate all link types and target notes before any writes
        for i, link_def in enumerate(links):
            source_id = link_def.get("source_id", "")
            target_id = link_def.get("target_id", "")

            if not source_id:
                msg = f"Link at index {i} is missing source_id"
                raise ValueError(msg)
            if not target_id:
                msg = f"Link at index {i} is missing target_id"
                raise ValueError(msg)

            raw_type = link_def.get("link_type", LinkType.REFERENCE.value)
            if not link_type_registry.is_valid(raw_type):
                msg = (
                    f"Link at index {i} has invalid link_type '{raw_type}'. "
                    f"Valid types: {', '.join(link_type_registry.all_types())}"
                )
                raise ValueError(msg)

            if not self.repository.get(target_id):
                msg = f"Link at index {i}: target note '{target_id}' not found"
                raise ValueError(msg)

        # Group by source and update each source note (file + DB)
        from collections import defaultdict  # noqa: PLC0415

        grouped: dict[str, list[dict]] = defaultdict(list)
        for link_def in links:
            grouped[link_def["source_id"]].append(link_def)

        total_created = 0
        for source_id, source_links in grouped.items():
            source_note = self.repository.get(source_id)
            if not source_note:
                msg = f"Source note '{source_id}' not found"
                raise ValueError(msg)

            for link_def in source_links:
                source_note.add_link(
                    link_def["target_id"],
                    link_def.get("link_type", LinkType.REFERENCE.value),
                    link_def.get("description"),
                )
            self.repository.update(source_note)
            total_created += len(source_links)

        return {"created": total_created, "failed": 0, "errors": []}

    # ------------------------------------------------------------------
    # Verification and health
    # ------------------------------------------------------------------

    def verify_note(self, note_id: str) -> dict:
        """Verify that a note is consistent between filesystem and DB index.

        Args:
            note_id: ID of the note to check.

        Returns:
            Dict with keys ``note_id``, ``file_exists``, ``db_indexed``,
            ``link_count``, ``tag_count``, and optionally ``hint``.
        """
        from sqlalchemy import func, select  # noqa: PLC0415
        from sqlalchemy import text as _text  # noqa: PLC0415

        from zettelkasten_mcp.models.db_models import DBLink, DBNote  # noqa: PLC0415

        notes_dir = self.repository.notes_dir
        file_path = notes_dir / f"{note_id}.md"
        file_exists = file_path.exists()

        link_count = 0
        tag_count = 0
        db_indexed = False

        with self.repository.session_factory() as session:
            db_note = session.scalar(select(DBNote).where(DBNote.id == note_id))
            if db_note is not None:
                db_indexed = True
                link_count = (
                    session.scalar(
                        select(func.count(DBLink.id)).where(
                            DBLink.source_id == note_id,
                        ),
                    )
                    or 0
                )
                tag_count = (
                    session.scalar(
                        _text("SELECT COUNT(*) FROM note_tags WHERE note_id = :nid"),
                        {"nid": note_id},
                    )
                    or 0
                )

        result: dict = {
            "note_id": note_id,
            "file_exists": file_exists,
            "db_indexed": db_indexed,
            "link_count": link_count,
            "tag_count": tag_count,
        }

        if file_exists and not db_indexed:
            result["hint"] = "Run zk_rebuild_index to sync"

        return result

    def get_index_status(self) -> dict:
        """Return a health summary comparing filesystem vs. database index.

        Returns:
            Dict with keys:
            - ``total_notes_filesystem``
            - ``total_notes_indexed``
            - ``orphaned_files`` (count of files not in DB)
            - ``orphaned_db_records`` (count of DB entries with no file)
            - ``orphaned_file_paths`` (list of paths)
            - ``orphaned_db_ids`` (list of IDs)
            - ``database_size_mb``
        """
        from sqlalchemy import select  # noqa: PLC0415

        from zettelkasten_mcp.config import config  # noqa: PLC0415
        from zettelkasten_mcp.models.db_models import DBNote  # noqa: PLC0415

        notes_dir = self.repository.notes_dir
        filesystem_ids = {p.stem for p in notes_dir.glob("*.md")}

        with self.repository.session_factory() as session:
            rows = session.execute(select(DBNote.id)).scalars().all()
        db_ids = set(rows)

        orphaned_file_ids = filesystem_ids - db_ids
        orphaned_db_ids = db_ids - filesystem_ids

        db_abs_path = config.get_absolute_path(config.database_path)
        try:
            db_size_bytes = db_abs_path.stat().st_size
            db_size_mb = round(db_size_bytes / (1024 * 1024), 3)
        except OSError:
            db_size_mb = 0.0

        return {
            "total_notes_filesystem": len(filesystem_ids),
            "total_notes_indexed": len(db_ids),
            "orphaned_files": len(orphaned_file_ids),
            "orphaned_db_records": len(orphaned_db_ids),
            "orphaned_file_paths": sorted(
                str(notes_dir / f"{fid}.md") for fid in orphaned_file_ids
            ),
            "orphaned_db_ids": sorted(orphaned_db_ids),
            "database_size_mb": db_size_mb,
        }

    def find_notes_in_timerange(
        self,
        start_date: str,
        end_date: str,
        date_field: str = "created_at",
        include_linked: bool = False,
        note_type: str | None = None,
    ) -> dict:
        """Find notes within an ISO 8601 date range.

        Args:
            start_date: ISO 8601 start date string (e.g. ``"2026-01-01"`` or
                ``"2026-01-01T00:00:00"``).
            end_date: ISO 8601 end date string (inclusive end of range).
            date_field: ``"created_at"`` (default) or ``"updated_at"``.
            include_linked: When True, also return notes linked from the primary
                result set (neighbours, no recursion).
            note_type: Optional note type filter (e.g. ``"permanent"``).

        Returns:
            Dict with ``count``, ``notes`` (list of Note objects), and ``date_field``.

        Raises:
            ValueError: If either date string is not valid ISO 8601.
        """
        try:
            start_dt = datetime.datetime.fromisoformat(start_date)
        except (ValueError, TypeError) as exc:
            msg = (
                f"Invalid start_date '{start_date}'. "
                "Expected ISO 8601 format, e.g. '2026-01-01' or '2026-01-01T00:00:00'."
            )
            raise ValueError(msg) from exc

        try:
            end_dt = datetime.datetime.fromisoformat(end_date)
        except (ValueError, TypeError) as exc:
            msg = (
                f"Invalid end_date '{end_date}'. "
                "Expected ISO 8601 format, e.g. '2026-01-31' or '2026-01-31T23:59:59'."
            )
            raise ValueError(msg) from exc

        # Expand bare date strings to cover the full day for end_date
        if "T" not in end_date and len(end_date) == 10:  # noqa: PLR2004
            end_dt = end_dt.replace(hour=23, minute=59, second=59)

        if date_field not in ("created_at", "updated_at"):
            msg = f"date_field must be 'created_at' or 'updated_at', got '{date_field}'"
            raise ValueError(msg)

        notes = self.repository.find_in_timerange(
            start=start_dt,
            end=end_dt,
            date_field=date_field,
            note_type=note_type,
            include_linked=include_linked,
        )
        return {"count": len(notes), "notes": notes, "date_field": date_field}
