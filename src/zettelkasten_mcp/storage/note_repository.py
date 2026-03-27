"""Repository for note storage and retrieval."""

import datetime
import logging
import threading
from pathlib import Path
from typing import Any

import frontmatter
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import joinedload

from zettelkasten_mcp.config import config
from zettelkasten_mcp.models.db_models import (
    DBLink,
    DBNote,
    DBTag,
    get_session_factory,
    init_db,
)
from zettelkasten_mcp.models.schema import (
    Link,
    LinkType,
    Note,
    NoteType,
    Tag,
    link_type_registry,
)
from zettelkasten_mcp.storage.base import Repository

logger = logging.getLogger(__name__)


class NoteRepository(Repository[Note]):
    """Repository for note storage and retrieval.
    This implements a dual storage approach:
    1. Notes are stored as Markdown files on disk for human readability and editing
    2. MySQL database is used for indexing and efficient querying
    The file system is the source of truth - database is rebuilt from files if needed.
    """

    def __init__(self, notes_dir: Path | None = None) -> None:
        """Initialize the repository."""
        self.notes_dir = (
            config.get_absolute_path(notes_dir)
            if notes_dir
            else config.get_absolute_path(config.notes_dir)
        )

        # Ensure directories exist
        self.notes_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self.engine = init_db()
        self.session_factory = get_session_factory(self.engine)

        # File access lock
        self.file_lock = threading.RLock()

        # Tracks whether the SQLite index is usable at runtime
        self._db_available: bool = True

        # Check if FTS5 table exists and warn if missing
        if not self._check_fts5_table_exists():
            logger.warning(
                "FTS5 full-text search table not found. "
                "Run rebuild_index() to enable fast search capabilities.",
            )

    def _check_fts5_table_exists(self) -> bool:
        """Check if the FTS5 virtual table exists.

        Returns:
            bool: True if notes_fts table exists, False otherwise
        """
        try:
            with self.session_factory() as session:
                result = session.execute(
                    text(
                        "SELECT name FROM sqlite_master "
                        "WHERE type='table' AND name='notes_fts'",
                    ),
                )
                return result.fetchone() is not None
        except Exception:
            logger.exception("Error checking FTS5 table existence")
            return False

    def _create_fts5_table(self, session: Any) -> None:
        """Create the FTS5 virtual table for full-text search.

        Args:
            session: Active database session

        Note:
            Creates a virtual table with columns:
            - id (UNINDEXED): Note ID for retrieval
            - title: Searchable note title
            - content: Searchable note content
            Uses unicode61 tokenizer for multilingual support (German + English)
        """
        try:
            # Drop existing table if it exists (idempotent)
            session.execute(text("DROP TABLE IF EXISTS notes_fts"))

            # Create FTS5 virtual table
            session.execute(
                text("""
                CREATE VIRTUAL TABLE notes_fts USING fts5(
                    id UNINDEXED,
                    title,
                    content,
                    tokenize='unicode61'
                )
            """),
            )

            logger.info("FTS5 table created successfully")
        except Exception:
            logger.exception("Error creating FTS5 table")
            raise

    def rebuild_index_if_needed(self) -> None:
        """Rebuild the database index from files if needed."""
        # Count notes in database
        with self.session_factory() as session:
            db_count = session.scalar(select(text("COUNT(*)")).select_from(DBNote))

        # Count note files
        file_count = len(list(self.notes_dir.glob("*.md")))

        # Rebuild if counts don't match
        if db_count != file_count:
            self.rebuild_index()

    def rebuild_index(self) -> None:
        """Rebuild the database index from all markdown files.

        This includes:
        - Clearing all tables (notes, links, note_tags)
        - Recreating FTS5 full-text search table
        - Re-indexing all markdown files from disk
        """
        logger.info("Starting index rebuild...")

        # Clear the database first
        with self.session_factory() as session:
            # Delete all records from link table
            session.execute(text("DELETE FROM links"))
            # Delete all records from note_tags table
            session.execute(text("DELETE FROM note_tags"))
            # Delete all records from notes table
            session.execute(text("DELETE FROM notes"))

            # Create/recreate FTS5 table
            logger.info("Creating FTS5 table...")
            self._create_fts5_table(session)

            # Commit changes
            session.commit()

        logger.info("Tables cleared and FTS5 table created")

        # Read all markdown files
        note_files = list(self.notes_dir.glob("*.md"))
        logger.info("Found %s markdown files to index", len(note_files))

        # Process files in batches to avoid memory issues
        batch_size = 100
        for i in range(0, len(note_files), batch_size):
            batch = note_files[i : i + batch_size]
            notes = []

            # Read files
            for file_path in batch:
                try:
                    with file_path.open(encoding="utf-8") as f:
                        content = f.read()
                    note = self._parse_note_from_markdown(content)
                    notes.append(note)
                except Exception:  # noqa: PERF203
                    logger.exception("Error processing file %s", file_path)

            # Index notes
            for note in notes:
                self._index_note(note)

        logger.info("Index rebuild complete: %s notes indexed", len(note_files))

    def _parse_note_from_markdown(self, content: str) -> Note:  # noqa: PLR0912
        """Parse a note from markdown content."""
        # Parse frontmatter
        post = frontmatter.loads(content)
        metadata = post.metadata

        # Extract ID from metadata or filename
        note_id = metadata.get("id")
        if not note_id:
            msg = "Note ID missing from frontmatter"
            raise ValueError(msg)

        # Extract title from metadata or first heading
        title = metadata.get("title")
        if not title:
            # Try to extract from content
            lines = post.content.strip().split("\n")
            for line in lines:
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        if not title:
            msg = "Note title missing from frontmatter or content"
            raise ValueError(msg)

        # Extract note type
        note_type_str = metadata.get("type", NoteType.PERMANENT.value)
        try:
            note_type = NoteType(note_type_str)
        except ValueError:
            note_type = NoteType.PERMANENT

        # Extract tags
        tags_str = metadata.get("tags", "")
        if isinstance(tags_str, str):
            tag_names = [t.strip() for t in tags_str.split(",") if t.strip()]
        elif isinstance(tags_str, list):
            tag_names = [str(t).strip() for t in tags_str if str(t).strip()]
        else:
            tag_names = []
        tags = [Tag(name=name) for name in tag_names]

        # Extract links
        links = []
        links_section = False
        for raw_line in post.content.split("\n"):
            line = raw_line.strip()
            # Check if we're in the links section
            if line.startswith("## Links"):
                links_section = True
                continue
            if links_section and line.startswith("## "):
                # We've reached the next section
                links_section = False
                continue
            if links_section and line.startswith("- "):
                # Parse link line
                try:
                    # Example format: - reference [[202101010000]] Optional description
                    line_content = line.strip()
                    if "[[" in line_content and "]]" in line_content:
                        # Split the line at the [[ delimiter
                        parts = line_content.split("[[", 1)
                        # Extract the link type from before [[
                        link_type_str = parts[0].strip()
                        # Remove the leading "- " from the link type string
                        if link_type_str.startswith("- "):
                            link_type_str = link_type_str[2:].strip()
                        # Extract target ID and description
                        id_and_description = parts[1].split("]]", 1)
                        target_id = id_and_description[0].strip()
                        description = None
                        if len(id_and_description) > 1:
                            description = id_and_description[1].strip()
                        # Validate link type using registry (supports custom types)
                        if not link_type_registry.is_valid(link_type_str):
                            # Unknown type — treat as reference
                            link_type_str = LinkType.REFERENCE.value
                        links.append(
                            Link(
                                source_id=str(note_id),
                                target_id=target_id,
                                link_type=link_type_str,
                                description=description,
                                created_at=datetime.datetime.now(
                                    tz=datetime.timezone.utc,
                                ),
                            ),
                        )
                except Exception:
                    logger.exception("Error parsing link: %s", line)

        # Extract timestamps
        created_str = metadata.get("created")
        created_at = (
            datetime.datetime.fromisoformat(str(created_str))
            if created_str
            else datetime.datetime.now(tz=datetime.timezone.utc)
        )
        updated_str = metadata.get("updated")
        updated_at = (
            datetime.datetime.fromisoformat(str(updated_str))
            if updated_str
            else created_at
        )

        # Create note object
        return Note(
            id=str(note_id),
            title=str(title),
            content=post.content,
            note_type=note_type,
            tags=tags,
            links=links,
            created_at=created_at,
            updated_at=updated_at,
            metadata={
                k: v
                for k, v in metadata.items()
                if k not in ["id", "title", "type", "tags", "created", "updated"]
            },
        )

    def _index_note(self, note: Note) -> None:
        """Index a note in the database."""
        with self.session_factory() as session:
            # Create or update note
            db_note = session.scalar(select(DBNote).where(DBNote.id == note.id))
            if db_note:
                # Update existing note
                db_note.title = note.title
                db_note.content = note.content
                db_note.note_type = note.note_type.value
                db_note.updated_at = note.updated_at
                # Clear existing links and tags to rebuild them
                session.execute(
                    text("DELETE FROM links WHERE source_id = :note_id"),
                    {"note_id": note.id},
                )
                session.execute(
                    text("DELETE FROM note_tags WHERE note_id = :note_id"),
                    {"note_id": note.id},
                )
            else:
                # Create new note
                db_note = DBNote(
                    id=note.id,
                    title=note.title,
                    content=note.content,
                    note_type=note.note_type.value,
                    created_at=note.created_at,
                    updated_at=note.updated_at,
                )
                session.add(db_note)

            session.flush()  # Flush to get the note ID

            # Add tags
            for tag in note.tags:
                # Check if tag exists
                db_tag = session.scalar(select(DBTag).where(DBTag.name == tag.name))
                if not db_tag:
                    db_tag = DBTag(name=tag.name)
                    session.add(db_tag)
                    session.flush()  # Flush to get the tag ID
                # Prevent duplicate tag associations
                if db_tag not in db_note.tags:
                    db_note.tags.append(db_tag)

            # Add links
            for link in note.links:
                # Check if this link already exists in the database
                existing_link = session.scalar(
                    select(DBLink).where(
                        (DBLink.source_id == link.source_id)
                        & (DBLink.target_id == link.target_id)
                        & (DBLink.link_type == link.link_type),
                    ),
                )

                if not existing_link:
                    db_link = DBLink(
                        source_id=link.source_id,
                        target_id=link.target_id,
                        link_type=link.link_type,
                        description=link.description,
                        created_at=link.created_at,
                    )
                    session.add(db_link)

            # Sync to FTS5 table for full-text search
            self._sync_note_to_fts5(session, note)

            # Commit changes
            session.commit()

    def _sync_note_to_fts5(self, session: Any, note: Note) -> None:
        """Synchronize a note to the FTS5 full-text search table.

        Args:
            session: Active database session
            note: Note object to sync

        Note:
            Uses DELETE + INSERT strategy (simpler than UPDATE for FTS5)
        """
        try:
            # Delete existing FTS5 entry if it exists
            session.execute(
                text("DELETE FROM notes_fts WHERE id = :id"),
                {"id": note.id},
            )

            # Insert into FTS5 table
            session.execute(
                text("""
                    INSERT INTO notes_fts (id, title, content)
                    VALUES (:id, :title, :content)
                """),
                {
                    "id": note.id,
                    "title": note.title,
                    "content": note.content,
                },
            )

            logger.debug("Synced note %s to FTS5 table", note.id)

        except Exception as e:  # noqa: BLE001
            # Don't fail the entire indexing if FTS5 sync fails
            logger.warning("Failed to sync note %s to FTS5: %s", note.id, e)

    def _note_to_markdown(self, note: Note) -> str:
        """Convert a note to markdown with frontmatter."""
        # Create frontmatter
        metadata = {
            "id": note.id,
            "title": note.title,
            "type": note.note_type.value,
            "tags": [tag.name for tag in note.tags],
            "created": note.created_at.isoformat(),
            "updated": note.updated_at.isoformat(),
        }
        # Add any custom metadata
        metadata.update(note.metadata)

        # Check if content already starts with the title
        title_heading = f"# {note.title}"
        if note.content.strip().startswith(title_heading):
            content = note.content
        else:
            content = f"{title_heading}\n\n{note.content}"

        # Remove existing Links section(s)
        content_parts = []
        skip_section = False
        for line in content.split("\n"):
            if line.strip() == "## Links":
                skip_section = True
                continue
            if skip_section and line.startswith("## "):
                skip_section = False

            if not skip_section:
                content_parts.append(line)

        # Reconstruct the content without the Links sections
        content = "\n".join(content_parts).rstrip()

        # Add links section (with deduplication)
        if note.links:
            unique_links = {}  # Use dict to deduplicate
            for link in note.links:
                key = f"{link.target_id}:{link.link_type}"
                unique_links[key] = link
            content += "\n\n## Links\n"
            for link in unique_links.values():
                desc = f" {link.description}" if link.description else ""
                content += f"- {link.link_type} [[{link.target_id}]]{desc}\n"

        # Create markdown with frontmatter
        post = frontmatter.Post(content, **metadata)
        return str(frontmatter.dumps(post))

    def create(self, note: Note) -> Note:
        """Create a new note."""
        # Ensure the note has an ID
        if not note.id:
            from zettelkasten_mcp.models.schema import generate_id  # noqa: PLC0415

            note.id = generate_id()

        # Convert note to markdown
        markdown = self._note_to_markdown(note)

        # Write to file
        file_path = self.notes_dir / f"{note.id}.md"
        try:
            with self.file_lock, file_path.open("w", encoding="utf-8") as f:
                f.write(markdown)
        except OSError as e:
            msg = f"Failed to write note to {file_path}: {e}"
            raise OSError(msg) from e

        # Index in database (non-fatal: filesystem write already succeeded)
        try:
            self._index_note(note)
        except Exception:  # noqa: BLE001
            self._db_available = False
            logger.warning(
                "Failed to index note %s in database; filesystem write succeeded",
                note.id,
            )
        return note

    def _read_from_markdown(self, note_id: str) -> "Note | None":
        """Load a note directly from its Markdown file (bypasses the DB index).

        Args:
            note_id: ID of the note to load.

        Returns:
            Parsed Note or None if the file does not exist.
        """
        file_path = self.notes_dir / f"{note_id}.md"
        if not file_path.exists():
            return None
        try:
            with file_path.open(encoding="utf-8") as f:
                content = f.read()
            return self._parse_note_from_markdown(content)
        except Exception as e:
            msg = f"Failed to read note {note_id}: {e}"
            raise OSError(msg) from e

    def get(self, id: str) -> "Note | None":  # noqa: A002
        """Get a note by ID.

        Args:
            id: The ISO 8601 formatted identifier of the note

        Returns:
            Note object if found, None otherwise
        """
        return self._read_from_markdown(id)

    def get_by_title(self, title: str) -> Note | None:
        """Get a note by title."""
        with self.session_factory() as session:
            db_note = session.scalar(select(DBNote).where(DBNote.title == title))
            if not db_note:
                return None
            return self.get(db_note.id)

    def get_all(self) -> list[Note]:
        """Get all notes.

        Falls back to a filesystem glob if the database index is unavailable.
        """
        if not self._db_available:
            logger.warning(
                "Database index unavailable; falling back to filesystem glob for get_all()",  # noqa: E501
            )
            notes = []
            for md_file in sorted(self.notes_dir.glob("*.md")):
                try:
                    note = self._read_from_markdown(md_file.stem)
                    if note:
                        notes.append(note)
                except Exception:  # noqa: PERF203
                    logger.exception("Error loading note from %s", md_file)
            return notes

        try:
            with self.session_factory() as session:
                # Get all notes with eager loading of tags and links
                query = select(DBNote).options(
                    joinedload(DBNote.tags),
                    joinedload(DBNote.outgoing_links),
                    joinedload(DBNote.incoming_links),
                )
                result = session.execute(query)
                # Apply unique() to handle the duplicate rows from eager loading
                db_notes = result.unique().scalars().all()

                # Process notes in batches to reduce memory usage
                batch_size = 50
                all_notes = []
                note_ids = [note.id for note in db_notes]
                for i in range(0, len(note_ids), batch_size):
                    batch_ids = note_ids[i : i + batch_size]
                    note_batch = []
                    for note_id in batch_ids:
                        try:
                            note = self.get(note_id)
                            if note:
                                note_batch.append(note)
                        except Exception:  # noqa: PERF203
                            logger.exception("Error loading note %s", note_id)
                    all_notes.extend(note_batch)
                return all_notes
        except Exception:  # noqa: BLE001
            self._db_available = False
            logger.warning(
                "Database unavailable in get_all(); falling back to filesystem glob",
            )
            return self.get_all()  # recursive — _db_available is now False

    def update(self, note: Note) -> Note:
        """Update a note."""
        # Check if note exists
        existing_note = self.get(note.id)
        if not existing_note:
            msg = f"Note with ID {note.id} does not exist"
            raise ValueError(msg)

        # Update timestamp
        note.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)

        # Convert note to markdown
        markdown = self._note_to_markdown(note)

        # Write to file
        file_path = self.notes_dir / f"{note.id}.md"
        try:
            with self.file_lock, file_path.open("w", encoding="utf-8") as f:
                f.write(markdown)
        except OSError as e:
            msg = f"Failed to write note to {file_path}: {e}"
            raise OSError(msg) from e

        try:
            # Re-index in database
            with self.session_factory() as session:
                # Get the existing note from the database
                db_note = session.scalar(select(DBNote).where(DBNote.id == note.id))
                if db_note:
                    # Update the note fields
                    db_note.title = note.title
                    db_note.content = note.content
                    db_note.note_type = note.note_type.value
                    db_note.updated_at = note.updated_at

                    # Clear existing tags
                    db_note.tags = []

                    # Add tags
                    for tag in note.tags:
                        # Check if tag exists
                        db_tag = session.scalar(
                            select(DBTag).where(DBTag.name == tag.name),
                        )
                        if not db_tag:
                            db_tag = DBTag(name=tag.name)
                            session.add(db_tag)
                            session.flush()
                        db_note.tags.append(db_tag)

                    # For links, we'll delete existing links and add the new ones
                    session.execute(
                        text("DELETE FROM links WHERE source_id = :note_id"),
                        {"note_id": note.id},
                    )

                    # Add new links
                    for link in note.links:
                        db_link = DBLink(
                            source_id=link.source_id,
                            target_id=link.target_id,
                            link_type=link.link_type,
                            description=link.description,
                            created_at=link.created_at,
                        )
                        session.add(db_link)

                    # Sync to FTS5 table
                    self._sync_note_to_fts5(session, note)

                    session.commit()
                else:
                    # Unusual case: create a new database record
                    self._index_note(note)
        except Exception:  # noqa: BLE001
            self._db_available = False
            logger.warning(
                "Failed to update note %s in database index; "
                "filesystem write succeeded",
                note.id,
            )

        return note

    def delete(self, id: str) -> None:  # noqa: A002
        """Delete a note by ID."""
        # Check if note exists
        file_path = self.notes_dir / f"{id}.md"
        if not file_path.exists():
            msg = f"Note with ID {id} does not exist"
            raise ValueError(msg)

        # Delete from file system
        try:
            with self.file_lock:
                file_path.unlink()
        except OSError as e:
            msg = f"Failed to delete note {id}: {e}"
            raise OSError(msg) from e

        # Delete from database
        with self.session_factory() as session:
            # Delete note and its relationships
            session.execute(
                text("DELETE FROM links WHERE source_id = :id OR target_id = :id"),
                {"id": id},
            )
            session.execute(
                text("DELETE FROM note_tags WHERE note_id = :id"),
                {"id": id},
            )
            session.execute(
                text("DELETE FROM notes WHERE id = :id"),
                {"id": id},
            )

            # Delete from FTS5 table
            try:
                session.execute(
                    text("DELETE FROM notes_fts WHERE id = :id"),
                    {"id": id},
                )
                logger.debug("Deleted note %s from FTS5 table", id)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to delete note %s from FTS5: %s", id, e)

            session.commit()

    def search_by_fts5(
        self,
        query: str,
        limit: int = 100,
        title_weight: float = 10.0,
        content_weight: float = 1.0,
    ) -> list[tuple[str, float, str]]:
        """Search notes using FTS5 full-text search.

        Args:
            query: Search query (supports FTS5 syntax)
            limit: Maximum number of results (default: 100)
            title_weight: BM25 weight for title field (default: 10.0)
            content_weight: BM25 weight for content field (default: 1.0)

        Returns:
            List of tuples: (note_id, bm25_score, snippet)

        FTS5 Query Syntax Examples:
            - Simple: "machine learning"
            - Phrase: '"machine learning"'
            - Boolean: "machine AND learning"
            - Prefix: "machin* learn*"
            - Column-specific: "title:machine content:learning"

        Note:
            BM25 scores are negative (more negative = better match)
            Snippet includes highlighted matches with context
        """
        try:
            with self.session_factory() as session:
                result = session.execute(
                    text(r"""
                    SELECT
                        id,
                        bm25(notes_fts, :title_weight, :content_weight) as score,
                        -- snippet: col 1=content, <b></b>=highlight markers;
                        -- length 64 gives concise context (not rendered HTML).
                        snippet(notes_fts, 1, '<b>', '</b>', '...', 64) as snippet
                    FROM notes_fts
                    WHERE notes_fts MATCH :query
                    ORDER BY score
                    LIMIT :limit
                """),
                    {
                        "query": query,
                        "limit": limit,
                        "title_weight": title_weight,
                        "content_weight": content_weight,
                    },
                )

                results = [(row.id, row.score, row.snippet) for row in result]

                logger.debug(
                    "FTS5 search for %r returned %s results",
                    query,
                    len(results),
                )
                return results

        except Exception:
            logger.exception("FTS5 search failed for query %r", query)
            # Return empty list on error (graceful degradation)
            return []

    def search(self, **kwargs: Any) -> list[Note]:
        """Search for notes based on criteria."""
        with self.session_factory() as session:
            query = select(DBNote).options(
                joinedload(DBNote.tags),
                joinedload(DBNote.outgoing_links),
                joinedload(DBNote.incoming_links),
            )
            # Process search criteria
            if "content" in kwargs:
                search_term = kwargs["content"]
                # Search in both content and title since content might include the title
                query = query.where(
                    or_(
                        DBNote.content.like(f"%{search_term}%"),
                        DBNote.title.like(f"%{search_term}%"),
                    ),
                )
            if "title" in kwargs:
                search_title = kwargs["title"]
                # Use case-insensitive search with func.lower()
                query = query.where(
                    func.lower(DBNote.title).like(f"%{search_title.lower()}%"),
                )
            if "note_type" in kwargs:
                note_type = (
                    kwargs["note_type"].value
                    if isinstance(kwargs["note_type"], NoteType)
                    else kwargs["note_type"]
                )
                query = query.where(DBNote.note_type == note_type)
            if "tag" in kwargs:
                tag_name = kwargs["tag"]
                query = query.join(DBNote.tags).where(DBTag.name == tag_name)
            if "tags" in kwargs:
                tag_names = kwargs["tags"]
                if isinstance(tag_names, list):
                    query = query.join(DBNote.tags).where(DBTag.name.in_(tag_names))
            if "linked_to" in kwargs:
                target_id = kwargs["linked_to"]
                query = query.join(DBNote.outgoing_links).where(
                    DBLink.target_id == target_id,
                )
            if "linked_from" in kwargs:
                source_id = kwargs["linked_from"]
                query = query.join(DBNote.incoming_links).where(
                    DBLink.source_id == source_id,
                )
            if "created_after" in kwargs:
                query = query.where(DBNote.created_at >= kwargs["created_after"])
            if "created_before" in kwargs:
                query = query.where(DBNote.created_at <= kwargs["created_before"])
            if "updated_after" in kwargs:
                query = query.where(DBNote.updated_at >= kwargs["updated_after"])
            if "updated_before" in kwargs:
                query = query.where(DBNote.updated_at <= kwargs["updated_before"])
            # Execute query and apply unique() to handle duplicates from joins
            result = session.execute(query)
            db_notes = result.unique().scalars().all()
        # Load notes from file system
        notes = []
        for db_note in db_notes:
            note = self.get(db_note.id)
            if note:
                notes.append(note)
        return notes

    def find_by_tag(self, tag: str | Tag) -> list[Note]:
        """Find notes by tag."""
        tag_name = tag.name if isinstance(tag, Tag) else tag
        return self.search(tag=tag_name)

    def find_linked_notes(
        self,
        note_id: str,
        direction: str = "outgoing",
    ) -> list[Note]:
        """Find notes linked to/from this note."""
        with self.session_factory() as session:
            if direction == "outgoing":
                # Find notes that this note links to
                query = (
                    select(DBNote)
                    .join(DBLink, DBNote.id == DBLink.target_id)
                    .where(DBLink.source_id == note_id)
                    .options(
                        joinedload(DBNote.tags),
                        joinedload(DBNote.outgoing_links),
                        joinedload(DBNote.incoming_links),
                    )
                )
            elif direction == "incoming":
                # Find notes that link to this note
                query = (
                    select(DBNote)
                    .join(DBLink, DBNote.id == DBLink.source_id)
                    .where(DBLink.target_id == note_id)
                    .options(
                        joinedload(DBNote.tags),
                        joinedload(DBNote.outgoing_links),
                        joinedload(DBNote.incoming_links),
                    )
                )
            elif direction == "both":
                # Find both directions
                query = (
                    select(DBNote)
                    .join(
                        DBLink,
                        or_(
                            and_(
                                DBNote.id == DBLink.target_id,
                                DBLink.source_id == note_id,
                            ),
                            and_(
                                DBNote.id == DBLink.source_id,
                                DBLink.target_id == note_id,
                            ),
                        ),
                    )
                    .options(
                        joinedload(DBNote.tags),
                        joinedload(DBNote.outgoing_links),
                        joinedload(DBNote.incoming_links),
                    )
                )
            else:
                msg = (
                    f"Invalid direction: {direction}. "
                    "Use 'outgoing', 'incoming', or 'both'"
                )
                raise ValueError(
                    msg,
                )

            result = session.execute(query)
            # Apply unique() to handle the duplicate rows from eager loading
            db_notes = result.unique().scalars().all()

            # Convert to model Notes
            notes = []
            for db_note in db_notes:
                note = self.get(db_note.id)
                if note:
                    notes.append(note)
            return notes

    def get_all_tags(self) -> list[Tag]:
        """Get all tags in the system."""
        with self.session_factory() as session:
            result = session.execute(select(DBTag))
            db_tags = result.scalars().all()
        return [Tag(name=tag.name) for tag in db_tags]

    def get_tags_with_counts(self) -> list[tuple[str, int]]:
        """Get all tags with their note counts, sorted alphabetically."""
        with self.session_factory() as session:
            result = session.execute(
                text("""
                SELECT t.name, COUNT(nt.note_id) as count
                FROM tags t
                LEFT JOIN note_tags nt ON t.id = nt.tag_id
                GROUP BY t.id, t.name
                ORDER BY t.name
            """),
            )
            return [(row.name, row.count) for row in result]

    def find_in_timerange(
        self,
        start: datetime.datetime,
        end: datetime.datetime,
        date_field: str = "created_at",
        note_type: str | None = None,
        include_linked: bool = False,
    ) -> list[Note]:
        """Find notes within a date range using a DB index query.

        Args:
            start: Start of the date range (inclusive).
            end: End of the date range (inclusive).
            date_field: ``"created_at"`` (default) or ``"updated_at"``.
            note_type: Optional note type filter (e.g. ``"permanent"``).
            include_linked: When True, also fetch notes linked from the primary
                result set (one extra IN clause, no recursion).

        Returns:
            List of Note objects sorted by the selected date field (descending).

        Raises:
            ValueError: If ``date_field`` is not ``"created_at"`` or
                ``"updated_at"``.
        """
        if date_field not in ("created_at", "updated_at"):
            msg = f"date_field must be 'created_at' or 'updated_at', got '{date_field}'"
            raise ValueError(msg)

        col = DBNote.created_at if date_field == "created_at" else DBNote.updated_at

        with self.session_factory() as session:
            stmt = (
                select(DBNote)
                .where(col >= start, col <= end)
                .options(
                    joinedload(DBNote.tags),
                    joinedload(DBNote.outgoing_links),
                )
            )
            if note_type:
                stmt = stmt.where(DBNote.note_type == note_type)

            db_notes = session.execute(stmt).unique().scalars().all()
            primary_ids = [n.id for n in db_notes]

            linked_ids: list[str] = []
            if include_linked and primary_ids:
                linked_stmt = (
                    select(DBNote.id)
                    .join(DBLink, DBNote.id == DBLink.target_id)
                    .where(
                        DBLink.source_id.in_(primary_ids),
                        DBNote.id.notin_(primary_ids),
                    )
                )
                linked_ids = list(session.execute(linked_stmt).scalars().all())

        notes = []
        for note_id in primary_ids:
            note = self.get(note_id)
            if note:
                notes.append(note)

        seen = set(primary_ids)
        for note_id in linked_ids:
            if note_id not in seen:
                note = self.get(note_id)
                if note:
                    notes.append(note)
                    seen.add(note_id)

        def _naive(dt: datetime.datetime | None) -> datetime.datetime:
            if dt is None:
                return datetime.datetime.min  # noqa: DTZ901
            return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt

        sort_key = (
            (lambda n: _naive(n.created_at))
            if date_field == "created_at"
            else (lambda n: _naive(n.updated_at))
        )
        notes.sort(key=sort_key, reverse=True)
        return notes

    def create_batch(self, notes: list[Note]) -> list[Note]:
        """Create multiple notes atomically in one transaction.

        Writes all Markdown files first, then commits all DB records in one
        session.commit(). On any failure, already-written files are deleted
        and the exception is re-raised so the caller can handle rollback.

        Args:
            notes: List of Note objects to create. IDs are generated if absent.

        Returns:
            List of created Note objects with IDs populated.

        Raises:
            ValueError: If any note fails validation before any writes occur.
            OSError: If a file cannot be written.
            Exception: On DB error; written files are cleaned up before re-raise.
        """
        from zettelkasten_mcp.models.schema import generate_id  # noqa: PLC0415

        # Assign IDs and validate before any IO
        for note in notes:
            if not note.id:
                note.id = generate_id()
            if not note.title:
                msg = f"Note at index {notes.index(note)} has an empty title"
                raise ValueError(msg)
            if not note.content:
                msg = f"Note at index {notes.index(note)} has empty content"
                raise ValueError(msg)

        written_paths: list[Path] = []
        try:
            # Write all files first
            for note in notes:
                markdown = self._note_to_markdown(note)
                file_path = self.notes_dir / f"{note.id}.md"
                with self.file_lock, file_path.open("w", encoding="utf-8") as f:
                    f.write(markdown)
                written_paths.append(file_path)

            # Commit all DB records in one transaction
            with self.session_factory() as session:
                for note in notes:
                    db_note = DBNote(
                        id=note.id,
                        title=note.title,
                        content=note.content,
                        note_type=note.note_type.value,
                        created_at=note.created_at,
                        updated_at=note.updated_at,
                    )
                    session.add(db_note)
                    session.flush()

                    for tag in note.tags:
                        db_tag = session.scalar(
                            select(DBTag).where(DBTag.name == tag.name),
                        )
                        if not db_tag:
                            db_tag = DBTag(name=tag.name)
                            session.add(db_tag)
                            session.flush()
                        if db_tag not in db_note.tags:
                            db_note.tags.append(db_tag)

                    for link in note.links:
                        db_link = DBLink(
                            source_id=link.source_id,
                            target_id=link.target_id,
                            link_type=link.link_type,
                            description=link.description,
                            created_at=link.created_at,
                        )
                        session.add(db_link)

                    self._sync_note_to_fts5(session, note)

                session.commit()
        except Exception:
            # Clean up written files on any failure
            for path in written_paths:
                try:
                    path.unlink(missing_ok=True)
                except OSError:  # noqa: PERF203
                    logger.warning(
                        "Could not remove partial file %s during rollback",
                        path,
                    )
            raise

        return notes

    def create_links_batch(self, source_id: str, links: list[dict]) -> int:
        """Create multiple links from source_id in one transaction.

        Args:
            source_id: ID of the source note for all links.
            links: List of dicts with keys ``target_id``, ``link_type``,
                and optional ``description``.

        Returns:
            Number of links created.

        Raises:
            ValueError: If any link_type is invalid.
            Exception: On DB error (full rollback via session context manager).
        """
        db_links = []
        for i, link_def in enumerate(links):
            raw_type = link_def.get("link_type", LinkType.REFERENCE.value)
            if not link_type_registry.is_valid(raw_type):
                msg = (
                    f"Link at index {i} has invalid link_type '{raw_type}'. "
                    f"Valid types: {', '.join(link_type_registry.all_types())}"
                )
                raise ValueError(msg)
            db_links.append(
                DBLink(
                    source_id=source_id,
                    target_id=link_def["target_id"],
                    link_type=raw_type,
                    description=link_def.get("description"),
                    created_at=link_def.get(
                        "created_at",
                        datetime.datetime.now(datetime.timezone.utc),
                    ),
                ),
            )

        with self.session_factory() as session:
            for db_link in db_links:
                session.add(db_link)
            session.commit()

        return len(db_links)
