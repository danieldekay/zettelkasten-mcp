"""MCP server implementation for the Zettelkasten."""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, TypedDict

from mcp.server.fastmcp import FastMCP
from sqlalchemy import exc as sqlalchemy_exc

from zettelkasten_mcp.config import config
from zettelkasten_mcp.models.schema import LinkType, NoteType
from zettelkasten_mcp.services.inference_service import InferenceService
from zettelkasten_mcp.services.search_service import SearchService
from zettelkasten_mcp.services.zettel_service import ZettelService

logger = logging.getLogger(__name__)

_SEARCH_PREVIEW_LEN = 150
_CONTENT_PREVIEW_LEN = 100


class ToolResponse(TypedDict, total=False):
    """Base type for all MCP tool responses. Every response MUST include `summary`."""

    summary: str


class ZettelkastenMcpServer:
    """MCP server for Zettelkasten."""

    def __init__(self) -> None:
        """Initialize the MCP server."""
        self.mcp = FastMCP(
            config.server_name,
            version=config.server_version,
        )
        # Services
        self.zettel_service = ZettelService()
        self.search_service = SearchService(self.zettel_service)
        # Initialize services
        self.initialize()
        # Register tools
        self._register_tools()
        self._register_resources()
        self._register_prompts()

    def initialize(self) -> None:
        """Initialize services."""
        self.zettel_service.initialize()
        self.search_service.initialize()
        logger.info("Zettelkasten MCP server initialized")

    def format_error_response(self, error: Exception) -> dict:
        """Format an error response as a structured dict.

        Args:
            error: The exception that occurred

        Returns:
            Structured error dict with error_type, message, and summary
        """
        error_id = str(uuid.uuid4())[:8]

        if isinstance(error, ValueError):
            logger.error("Validation error [%s]: %s", error_id, error)
            return {
                "error": True,
                "error_type": "validation_error",
                "message": str(error),
                "summary": f"Error: {error!s}",
            }
        if isinstance(error, (IOError, OSError)):
            logger.error("File system error [%s]: %s", error_id, error)
            return {
                "error": True,
                "error_type": "file_system_error",
                "message": str(error),
                "summary": f"Error: {error!s}",
            }
        logger.error("Unexpected error [%s]: %s", error_id, error)
        return {
            "error": True,
            "error_type": "internal_error",
            "message": str(error),
            "summary": f"Error: {error!s}",
        }

    def _note_to_dict(self, note: Any) -> dict:
        """Convert a Note to a full detail dict."""
        notes_dir = config.get_absolute_path(config.notes_dir)
        return {
            "note_id": note.id,
            "title": note.title,
            "note_type": note.note_type.value,
            "tags": [tag.name for tag in note.tags],
            "links": [
                {
                    "source_id": lnk.source_id,
                    "target_id": lnk.target_id,
                    "link_type": lnk.link_type.value,
                    "description": lnk.description,
                }
                for lnk in note.links
            ],
            "created_at": note.created_at.isoformat(),
            "updated_at": note.updated_at.isoformat(),
            "content": note.content,
            "metadata": note.metadata if note.metadata else {},
            "file_path": str(notes_dir / f"{note.id}.md"),
        }

    def _note_summary_dict(self, note: Any) -> dict:
        """Convert a Note to a brief summary dict for list results."""
        notes_dir = config.get_absolute_path(config.notes_dir)
        preview = note.content[:_CONTENT_PREVIEW_LEN].replace("\n", " ")
        if len(note.content) > _CONTENT_PREVIEW_LEN:
            preview += "..."
        return {
            "note_id": note.id,
            "title": note.title,
            "note_type": note.note_type.value,
            "tags": [tag.name for tag in note.tags],
            "created_at": note.created_at.isoformat(),
            "updated_at": note.updated_at.isoformat(),
            "preview": preview,
            "file_path": str(notes_dir / f"{note.id}.md"),
        }

    def _register_tools(self) -> None:  # noqa: PLR0915
        """Register MCP tools."""

        # Create a new note
        @self.mcp.tool(name="zk_create_note")
        def zk_create_note(
            title: str,
            content: str,
            note_type: str = "permanent",
            tags: str | None = None,
            metadata: str | dict | None = None,
        ) -> dict:
            """Create a new Zettelkasten note.
            Args:
                title: The title of the note
                content: The main content of the note
                note_type: Type of note (fleeting, literature, permanent,
                    structure, hub)
                tags: Comma-separated list of tags (optional)
                metadata: Metadata as a JSON string or dict (optional)

            Note: The created note will be stored as a markdown file at:
                  {notes_dir}/{note_id}.md
                  You can create a clickable file link using:
                  file://{absolute_path_to_notes_dir}/{note_id}.md
            """
            try:
                # Convert note_type string to enum
                try:
                    note_type_enum = NoteType(note_type.lower())
                except ValueError:
                    return {
                        "error": True,
                        "error_type": "validation_error",
                        "message": (
                            f"Invalid note type: {note_type}. Valid types are: "
                            f"{', '.join(t.value for t in NoteType)}"
                        ),
                        "summary": f"Invalid note type: {note_type}",
                    }

                # Convert tags string to list
                tag_list = []
                if tags:
                    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

                # Parse metadata JSON if provided
                metadata_dict: dict | None = None
                if metadata:
                    if isinstance(metadata, dict):
                        metadata_dict = metadata
                    else:
                        try:
                            metadata_dict = json.loads(metadata)
                            if not isinstance(metadata_dict, dict):
                                return {
                                    "error": True,
                                    "error_type": "invalid_metadata",
                                    "message": "metadata must be a JSON object",
                                    "summary": "Error: metadata must be a JSON object",
                                }
                        except json.JSONDecodeError as exc:
                            return {
                                "error": True,
                                "error_type": "invalid_metadata",
                                "message": f"Invalid metadata JSON: {exc}",
                                "summary": f"Error: Invalid metadata JSON: {exc}",
                            }

                # Create the note
                note = self.zettel_service.create_note(
                    title=title,
                    content=content,
                    note_type=note_type_enum,
                    tags=tag_list,
                    metadata=metadata_dict,
                )
                note_file_path = (
                    config.get_absolute_path(config.notes_dir) / f"{note.id}.md"
                )
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                result: dict = {
                    "note_id": note.id,
                    "file_path": str(note_file_path),
                    "summary": f"Note created: '{note.title}' ({note.id})",
                }
                if not self.zettel_service.repository._db_available:  # noqa: SLF001
                    result["warning"] = "Note saved to filesystem; DB index unavailable"
                return result

        # Get a note by ID or title
        @self.mcp.tool(name="zk_get_note")
        def zk_get_note(identifier: str) -> dict:
            """Retrieve a note by ID or title.
            Args:
                identifier: The ID or title of the note

            Note: The note is stored as a markdown file at:
                  {notes_dir}/{note_id}.md
                  You can create a clickable file link using:
                  file://{absolute_path_to_notes_dir}/{note_id}.md
            """
            try:
                identifier = str(identifier)
                # Try to get by ID first
                note = self.zettel_service.get_note(identifier)
                # If not found, try by title
                if not note:
                    note = self.zettel_service.get_note_by_title(identifier)
                if not note:
                    return {
                        "error": True,
                        "error_type": "not_found",
                        "message": f"Note not found: {identifier}",
                        "summary": f"Note not found: {identifier}",
                    }
                result = self._note_to_dict(note)
                result["summary"] = f"Note retrieved: '{note.title}' ({note.id})"
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                return result

        # Update a note
        @self.mcp.tool(name="zk_update_note")
        def zk_update_note(  # noqa: PLR0912
            note_id: str,
            title: str | None = None,
            content: str | None = None,
            note_type: str | None = None,
            tags: str | None = None,
            metadata: str | dict | None = None,
        ) -> dict:
            """Update an existing note.
            Args:
                note_id: The ID of the note to update
                title: New title (optional)
                content: New content (optional)
                note_type: New note type (optional)
                tags: New comma-separated list of tags (optional)
                metadata: Metadata as a JSON string or dict to replace note metadata (optional)
            """  # noqa: E501
            try:
                # Get the note
                note = self.zettel_service.get_note(str(note_id))
                if not note:
                    return {
                        "error": True,
                        "error_type": "not_found",
                        "message": f"Note not found: {note_id}",
                        "summary": f"Note not found: {note_id}",
                    }

                # Convert note_type string to enum if provided
                note_type_enum = None
                if note_type:
                    try:
                        note_type_enum = NoteType(note_type.lower())
                    except ValueError:
                        return {
                            "error": True,
                            "error_type": "validation_error",
                            "message": (
                                f"Invalid note type: {note_type}. Valid types are: "
                                f"{', '.join(t.value for t in NoteType)}"
                            ),
                            "summary": f"Invalid note type: {note_type}",
                        }

                # Convert tags string to list if provided
                tag_list = None
                if tags is not None:  # Allow empty string to clear tags
                    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

                # Parse metadata JSON if provided
                metadata_dict: dict | None = None
                if metadata:
                    if isinstance(metadata, dict):
                        metadata_dict = metadata
                    else:
                        try:
                            metadata_dict = json.loads(metadata)
                            if not isinstance(metadata_dict, dict):
                                return {
                                    "error": True,
                                    "error_type": "invalid_metadata",
                                    "message": "metadata must be a JSON object",
                                    "summary": "Error: metadata must be a JSON object",
                                }
                        except json.JSONDecodeError as exc:
                            return {
                                "error": True,
                                "error_type": "invalid_metadata",
                                "message": f"Invalid metadata JSON: {exc}",
                                "summary": f"Error: Invalid metadata JSON: {exc}",
                            }

                # Track which fields are being updated
                updated_fields = []
                if title is not None:
                    updated_fields.append("title")
                if content is not None:
                    updated_fields.append("content")
                if note_type_enum is not None:
                    updated_fields.append("note_type")
                if tag_list is not None:
                    updated_fields.append("tags")
                if metadata_dict is not None:
                    updated_fields.append("metadata")

                # Update the note
                updated_note = self.zettel_service.update_note(
                    note_id=note_id,
                    title=title,
                    content=content,
                    note_type=note_type_enum,
                    tags=tag_list,
                    metadata=metadata_dict,
                )
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                return {
                    "note_id": updated_note.id,
                    "updated_fields": updated_fields,
                    "summary": (
                        f"Note updated: '{updated_note.title}' ({updated_note.id})"
                    ),
                }

        # Delete a note
        @self.mcp.tool(name="zk_delete_note")
        def zk_delete_note(note_id: str) -> dict:
            """Delete a note.
            Args:
                note_id: The ID of the note to delete
            """
            try:
                # Check if note exists
                note = self.zettel_service.get_note(note_id)
                if not note:
                    return {
                        "error": True,
                        "error_type": "not_found",
                        "message": f"Note not found: {note_id}",
                        "summary": f"Note not found: {note_id}",
                    }

                title = note.title
                # Delete the note
                self.zettel_service.delete_note(str(note_id))
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                return {
                    "note_id": note_id,
                    "deleted": True,
                    "summary": f"Note deleted: '{title}' ({note_id})",
                }

        # Add a link between notes
        @self.mcp.tool(name="zk_create_link")
        def zk_create_link(
            source_id: str,
            target_id: str,
            link_type: str = "reference",
            description: str | None = None,
            bidirectional: bool = False,
        ) -> dict:
            """Create a link between two notes.
            Args:
                source_id: ID of the source note
                target_id: ID of the target note
                link_type: Type of link (reference, extends, refines, contradicts,
                    questions, supports, related)
                description: Optional description of the link
                bidirectional: Whether to create a link in both directions
            """
            try:
                # Convert link_type string to enum
                try:
                    str(source_id)
                    str(target_id)
                    link_type_enum = LinkType(link_type.lower())
                except ValueError:
                    return {
                        "error": True,
                        "error_type": "validation_error",
                        "message": (
                            f"Invalid link type: {link_type}. Valid types are: "
                            f"{', '.join(t.value for t in LinkType)}"
                        ),
                        "summary": f"Invalid link type: {link_type}",
                    }

                # Create the link
                _source_note, _target_note = self.zettel_service.create_link(
                    source_id=source_id,
                    target_id=target_id,
                    link_type=link_type_enum,
                    description=description,
                    bidirectional=bidirectional,
                )
            except (Exception, sqlalchemy_exc.IntegrityError) as e:  # noqa: BLE001
                if "UNIQUE constraint failed" in str(e):
                    return {
                        "error": True,
                        "error_type": "conflict",
                        "message": (
                            "A link of this type already exists between these notes."
                        ),
                        "summary": "Error: duplicate link",
                    }
                return self.format_error_response(e)
            else:
                direction_label = "Bidirectional link" if bidirectional else "Link"
                return {
                    "source_id": source_id,
                    "target_id": target_id,
                    "link_type": link_type,
                    "bidirectional": bidirectional,
                    "summary": (
                        f"{direction_label} created: "
                        f"{source_id} → {target_id} ({link_type})"
                    ),
                }

        self.zk_create_link = zk_create_link

        # Remove a link between notes
        @self.mcp.tool(name="zk_remove_link")
        def zk_remove_link(
            source_id: str,
            target_id: str,
            bidirectional: bool = False,
        ) -> dict:
            """Remove a link between two notes.
            Args:
                source_id: ID of the source note
                target_id: ID of the target note
                bidirectional: Whether to remove the link in both directions
            """
            try:
                # Remove the link
                _source_note, _target_note = self.zettel_service.remove_link(
                    source_id=str(source_id),
                    target_id=str(target_id),
                    bidirectional=bidirectional,
                )
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                direction_label = "Bidirectional link" if bidirectional else "Link"
                return {
                    "source_id": source_id,
                    "target_id": target_id,
                    "removed": True,
                    "bidirectional": bidirectional,
                    "summary": f"{direction_label} removed: {source_id} → {target_id}",
                }

        # Search for notes
        @self.mcp.tool(name="zk_search_notes")
        def zk_search_notes(
            query: str | None = None,
            tags: str | None = None,
            note_type: str | None = None,
            limit: int = 10,
        ) -> dict:
            """Search for notes by text, tags, or type.
            Args:
                query: Text to search for in titles and content
                tags: Comma-separated list of tags to filter by
                note_type: Type of note to filter by
                limit: Maximum number of results to return

            Note: Each result includes a file path where the note is stored as:
                  {notes_dir}/{note_id}.md
                  You can create a clickable file link using:
                  file://{absolute_path_to_notes_dir}/{note_id}.md
            """
            try:
                # Convert tags string to list if provided
                tag_list = None
                if tags:
                    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

                # Convert note_type string to enum if provided
                note_type_enum = None
                if note_type:
                    try:
                        note_type_enum = NoteType(note_type.lower())
                    except ValueError:
                        return {
                            "error": True,
                            "error_type": "validation_error",
                            "message": (
                                f"Invalid note type: {note_type}. Valid types are: "
                                f"{', '.join(t.value for t in NoteType)}"
                            ),
                            "summary": f"Invalid note type: {note_type}",
                        }

                # Perform search
                results = self.search_service.search_combined(
                    text=query,
                    tags=tag_list,
                    note_type=note_type_enum,
                )

                # Limit results
                results = results[:limit]
                note_dicts = [
                    {**self._note_summary_dict(r.note), "score": round(r.score, 4)}
                    for r in results
                ]
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                total = len(note_dicts)
                return {
                    "notes": note_dicts,
                    "total": total,
                    "query": query,
                    "summary": (
                        f"Found {total} matching notes"
                        if total
                        else "No matching notes found"
                    ),
                }

        # Get linked notes
        @self.mcp.tool(name="zk_get_linked_notes")
        def zk_get_linked_notes(
            note_id: str,
            direction: str = "both",
        ) -> dict:
            """Get notes linked to/from a note.
            Args:
                note_id: ID of the note
                direction: Direction of links (outgoing, incoming, both)

            Note: Each result includes a file path where the note is stored.
            """
            try:
                if direction not in ["outgoing", "incoming", "both"]:
                    return {
                        "error": True,
                        "error_type": "validation_error",
                        "message": (
                            f"Invalid direction: {direction}. "
                            "Use 'outgoing', 'incoming', or 'both'."
                        ),
                        "summary": f"Invalid direction: {direction}",
                    }
                # Get linked notes
                linked_notes = self.zettel_service.get_linked_notes(
                    str(note_id),
                    direction,
                )
                # Fetch source note once for link type lookup
                source_note = (
                    self.zettel_service.get_note(str(note_id))
                    if direction in ["outgoing", "both"]
                    else None
                )
                note_list = []
                for note in linked_notes:
                    entry = self._note_summary_dict(note)
                    link_type = None
                    link_description = None
                    if source_note:
                        for lnk in source_note.links:
                            if str(lnk.target_id) == str(note.id):
                                link_type = lnk.link_type
                                link_description = lnk.description
                                break
                    if link_type is None and direction in ["incoming", "both"]:
                        for lnk in note.links:
                            if str(lnk.target_id) == str(note_id):
                                link_type = lnk.link_type
                                link_description = lnk.description
                                break
                    entry["link_type"] = link_type
                    entry["link_description"] = link_description
                    note_list.append(entry)
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                total = len(note_list)
                return {
                    "note_id": note_id,
                    "direction": direction,
                    "notes": note_list,
                    "total": total,
                    "summary": (
                        f"Found {total} {direction} linked notes for {note_id}"
                        if total
                        else f"No {direction} links found for note {note_id}"
                    ),
                }

        self.zk_get_linked_notes = zk_get_linked_notes

        # Get all tags
        @self.mcp.tool(name="zk_get_all_tags")
        def zk_get_all_tags() -> dict:
            """Get all tags in the Zettelkasten with their usage counts."""
            try:
                tags_with_counts = self.zettel_service.get_all_tags_with_counts()
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                tag_list = [
                    {"name": name, "count": count} for name, count in tags_with_counts
                ]
                return {
                    "tags": tag_list,
                    "total": len(tag_list),
                    "summary": (
                        f"Found {len(tag_list)} tags" if tag_list else "No tags found"
                    ),
                }

        # Find similar notes
        @self.mcp.tool(name="zk_find_similar_notes")
        def zk_find_similar_notes(
            note_id: str,
            threshold: float = 0.3,
            limit: int = 5,
        ) -> dict:
            """Find notes similar to a given note.
            Args:
                note_id: ID of the reference note
                threshold: Similarity threshold (0.0-1.0)
                limit: Maximum number of results to return

            Note: Each result includes a file path where the note is stored as:
                  {notes_dir}/{note_id}.md
            """
            try:
                # Get similar notes
                similar_notes = self.zettel_service.find_similar_notes(
                    str(note_id),
                    threshold,
                )
                similar_notes = similar_notes[:limit]
                note_list = []
                for note, similarity in similar_notes:
                    entry = self._note_summary_dict(note)
                    entry["similarity"] = round(similarity, 4)
                    note_list.append(entry)
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                total = len(note_list)
                return {
                    "notes": note_list,
                    "total": total,
                    "summary": (
                        f"Found {total} similar notes for {note_id}"
                        if total
                        else (
                            f"No similar notes found for {note_id} "
                            f"with threshold {threshold}"
                        )
                    ),
                }

        # Find central notes
        @self.mcp.tool(name="zk_find_central_notes")
        def zk_find_central_notes(limit: int = 10) -> dict:
            """Find notes with the most connections (incoming + outgoing links).
            Notes are ranked by their total number of connections, determining
            their centrality in the knowledge network. Due to database constraints,
            only one link of each type is counted between any pair of notes.

            Args:
                limit: Maximum number of results to return (default: 10)

            Note: Each result includes a file path where the note is stored.
            """
            try:
                # Get central notes
                central_notes = self.search_service.find_central_notes(limit)
                note_list = []
                for note, connection_count in central_notes:
                    entry = self._note_summary_dict(note)
                    entry["connections"] = connection_count
                    note_list.append(entry)
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                return {
                    "notes": note_list,
                    "total": len(note_list),
                    "summary": (
                        f"Found {len(note_list)} central notes"
                        if note_list
                        else "No notes found with connections"
                    ),
                }

        # Find orphaned notes
        @self.mcp.tool(name="zk_find_orphaned_notes")
        def zk_find_orphaned_notes() -> dict:
            """Find notes with no connections to other notes.

            Note: Each result includes a file path where the note is stored.
            """
            try:
                # Get orphaned notes
                orphans = self.search_service.find_orphaned_notes()
                note_list = [self._note_summary_dict(note) for note in orphans]
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                return {
                    "notes": note_list,
                    "total": len(note_list),
                    "summary": (
                        f"Found {len(note_list)} orphaned notes"
                        if note_list
                        else "No orphaned notes found"
                    ),
                }

        # List notes by date range
        @self.mcp.tool(name="zk_list_notes_by_date")
        def zk_list_notes_by_date(
            start_date: str | None = None,
            end_date: str | None = None,
            use_updated: bool = False,
            limit: int = 10,
        ) -> dict:
            """List notes created or updated within a date range.
            Args:
                start_date: Start date in ISO format (YYYY-MM-DD)
                end_date: End date in ISO format (YYYY-MM-DD)
                use_updated: Whether to use updated_at instead of created_at
                limit: Maximum number of results to return

            Note: Each result includes a file path where the note is stored.
            """
            try:
                # Parse dates
                start_datetime = None
                if start_date:
                    start_datetime = datetime.fromisoformat(f"{start_date}T00:00:00")
                end_datetime = None
                if end_date:
                    end_datetime = datetime.fromisoformat(f"{end_date}T23:59:59")

                # Get notes
                notes = self.search_service.find_notes_by_date_range(
                    start_date=start_datetime,
                    end_date=end_datetime,
                    use_updated=use_updated,
                )

                # Limit results
                notes = notes[:limit]
                note_list = [self._note_summary_dict(note) for note in notes]
            except ValueError as e:
                # Special handling for date parsing errors
                logger.exception("Date parsing error")
                return {
                    "error": True,
                    "error_type": "validation_error",
                    "message": f"Error parsing date: {e!s}",
                    "summary": f"Error parsing date: {e!s}",
                }
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                total = len(note_list)
                date_type = "updated" if use_updated else "created"
                date_range = ""
                if start_date and end_date:
                    date_range = f" between {start_date} and {end_date}"
                elif start_date:
                    date_range = f" after {start_date}"
                elif end_date:
                    date_range = f" before {end_date}"
                return {
                    "notes": note_list,
                    "total": total,
                    "summary": (
                        f"Found {total} notes {date_type}{date_range}"
                        if total
                        else f"No notes found {date_type}{date_range}"
                    ),
                }

        # Rebuild the index
        @self.mcp.tool(name="zk_rebuild_index")
        def zk_rebuild_index() -> dict:
            """Rebuild the database index from files."""
            try:
                # Get count before rebuild
                note_count_before = len(self.zettel_service.get_all_notes())

                # Perform the rebuild
                self.zettel_service.rebuild_index()
                self.search_service.invalidate_tag_cache()

                # Get count after rebuild
                note_count_after = len(self.zettel_service.get_all_notes())
            except Exception as e:
                # Provide a detailed error message
                logger.exception("Failed to rebuild index")
                return self.format_error_response(e)
            else:
                return {
                    "notes_indexed": note_count_after,
                    "errors": [],
                    "summary": (
                        f"Index rebuilt: {note_count_after} notes "
                        f"(change: {note_count_after - note_count_before:+d})"
                    ),
                }

        # Custom link type registration
        @self.mcp.tool(name="zk_register_link_type")
        def zk_register_link_type(
            name: str,
            inverse: str | None = None,
            symmetric: bool = False,
        ) -> dict:
            """Register a custom project-scoped link type.

            Args:
                name: Unique type name (e.g. ``"implements"``)
                inverse: Inverse type name for asymmetric types
                    (e.g. ``"implemented_by"``). Ignored when
                    ``symmetric=True``.
                symmetric: Whether the relationship is symmetric
                    (e.g. ``"complements"``).

            Returns a dict with ``registered``, ``inverse``, ``symmetric``,
            and ``summary``. Returns an error if the type already exists.
            """
            try:
                result = self.zettel_service.register_link_type(
                    name=name,
                    inverse=inverse,
                    symmetric=symmetric,
                )
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                result["summary"] = (
                    f"Registered link type '{result['registered']}' "
                    f"(inverse: '{result['inverse']}', symmetric: {result['symmetric']})"  # noqa: E501
                )
                return result

        # Tag suggestions
        @self.mcp.tool(name="zk_suggest_tags")
        def zk_suggest_tags(content: str, limit: int = 10) -> dict:
            """Suggest existing tags for new content using TF-IDF.

            Args:
                content: The note content or title to match against.
                limit: Maximum number of tag suggestions to return (default 10).

            Returns a dict with ``suggestions`` (list of ``{"tag", "confidence"}``)
            and ``summary``.
            """
            try:
                suggestions = self.search_service.suggest_tags(content, limit=limit)
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                return {
                    "suggestions": suggestions,
                    "summary": f"{len(suggestions)} tag suggestion(s) found",
                }

        # Link type inference
        @self.mcp.tool(name="zk_suggest_link_type")
        def zk_suggest_link_type(source_id: str, target_id: str) -> dict:
            """Suggest a link type between two notes using heuristic inference.

            Args:
                source_id: The ID of the source note.
                target_id: The ID of the target note.

            Returns a dict with ``suggestions`` (list of
            ``{"link_type", "confidence"}``), ``low_confidence`` flag, and
            ``summary``.
            """
            try:
                source = self.zettel_service.get_note(source_id)
                target = self.zettel_service.get_note(target_id)
                if source is None or target is None:
                    return self.format_error_response(
                        ValueError("Source or target note not found")
                    )
                result = InferenceService().suggest_link_type(source, target)
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                top = (
                    result["suggestions"][0]["link_type"]
                    if result["suggestions"]
                    else "reference"
                )
                result["summary"] = f"Top suggestion: '{top}'" + (
                    " (low confidence)" if result["low_confidence"] else ""
                )
                return result

        # Temporal range query
        @self.mcp.tool(name="zk_find_notes_in_timerange")
        def zk_find_notes_in_timerange(
            start_date: str,
            end_date: str,
            date_field: str = "created_at",
            include_linked: bool = False,
            note_type: str | None = None,
            limit: int = 100,
        ) -> dict:
            """Find notes created or updated within an ISO 8601 date range.

            Uses a SQLite index for fast filtering — suitable for large collections.

            Args:
                start_date: ISO 8601 start date (e.g. ``"2026-01-01"``).
                end_date: ISO 8601 end date, inclusive (e.g. ``"2026-01-31"``).
                date_field: ``"created_at"`` (default) or ``"updated_at"``.
                include_linked: Also return notes linked from the primary
                    result set (neighbours, not recursive).
                note_type: Optional note type filter (e.g. ``"permanent"``).
                limit: Maximum number of notes to return (default 100).
            """
            try:
                result = self.zettel_service.find_notes_in_timerange(
                    start_date=start_date,
                    end_date=end_date,
                    date_field=date_field,
                    include_linked=include_linked,
                    note_type=note_type,
                )
                notes = result["notes"][:limit]
                note_list = [self._note_summary_dict(n) for n in notes]
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                count = len(note_list)
                return {
                    "count": count,
                    "notes": note_list,
                    "date_field": date_field,
                    "summary": (
                        f"Found {count} notes ({date_field} between "
                        f"{start_date} and {end_date})"
                        if count
                        else f"No notes found ({date_field} between "
                        f"{start_date} and {end_date})"
                    ),
                }

        # Tag co-occurrence cluster analysis
        @self.mcp.tool(name="zk_analyze_tag_clusters")
        def zk_analyze_tag_clusters(min_co_occurrence: int = 2) -> dict:
            """Identify tag groups that frequently co-appear on the same notes.

            Uses a SQL co-occurrence join and union-find clustering — no external
            graph libraries required.

            Args:
                min_co_occurrence: Minimum number of shared notes for a tag pair to
                    be included (default 2).
            """
            try:
                result = self.search_service.analyze_tag_clusters(
                    min_co_occurrence=min_co_occurrence,
                )
            except Exception as e:  # noqa: BLE001
                return self.format_error_response(e)
            else:
                cluster_count = len(result["clusters"])
                result["summary"] = (
                    f"Found {cluster_count} tag cluster(s) "
                    f"(min_co_occurrence={min_co_occurrence})"
                    if cluster_count
                    else "No tag clusters found at this threshold"
                )
                return result

    def _register_resources(self) -> None:
        """Register MCP resources."""
        # Currently, we don't define resources for the Zettelkasten server

    def _register_prompts(self) -> None:
        """Register MCP prompts."""
        # Currently, we don't define prompts for the Zettelkasten server

    def run(self) -> None:
        """Run the MCP server."""
        self.mcp.run()
