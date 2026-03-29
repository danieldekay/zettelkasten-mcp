"""Data models for the Zettelkasten MCP server."""

import datetime
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# Thread-safe counter for uniqueness
_id_lock = threading.Lock()
_last_timestamp = 0
_counter = 0


def generate_id() -> str:
    """Generate an ISO 8601 compliant timestamp-based ID with guaranteed uniqueness
    (pseudo-nanosecond precision).

    Returns:
        A string in format "YYYYMMDDTHHMMSSssssssccc" where:
        - YYYYMMDD is the date
        - T is the ISO 8601 date/time separator
        - HHMMSS is the time (hours, minutes, seconds)
        - ssssss is the 6-digit microsecond component (from time.time())
        - ccc is a 3-digit counter for uniqueness within the same microsecond

    The format follows ISO 8601 basic format with extended precision,
    allowing up to 1 billion unique IDs per second.
    """
    global _last_timestamp, _counter  # noqa: PLW0603

    with _id_lock:
        # Get current timestamp with microsecond precision
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        # Create a timestamp in microseconds
        current_timestamp = int(now.timestamp() * 1_000_000)

        # If multiple IDs generated in same microsecond, increment counter
        if current_timestamp == _last_timestamp:
            _counter += 1
        else:
            _last_timestamp = current_timestamp
            _counter = 0

        # Ensure counter doesn't overflow our 3 digits
        _counter %= 1000

        # Format as ISO 8601 basic format with microseconds and counter
        date_time = now.strftime("%Y%m%dT%H%M%S")
        microseconds = now.microsecond

        return f"{date_time}{microseconds:06d}{_counter:03d}"


class LinkType(str, Enum):
    """Built-in link type constants (preserved for backward compatibility)."""

    REFERENCE = "reference"
    EXTENDS = "extends"
    EXTENDED_BY = "extended_by"
    REFINES = "refines"
    REFINED_BY = "refined_by"
    CONTRADICTS = "contradicts"
    CONTRADICTED_BY = "contradicted_by"
    QUESTIONS = "questions"
    QUESTIONED_BY = "questioned_by"
    SUPPORTS = "supports"
    SUPPORTED_BY = "supported_by"
    RELATED = "related"


@dataclass
class LinkTypeDef:
    """Definition of a link type (built-in or custom)."""

    name: str
    inverse: str
    symmetric: bool


class LinkTypeRegistry:
    """Registry of all valid link types (built-in + project-local custom)."""

    _built_in: dict[str, LinkTypeDef] = field(default_factory=dict)
    _custom: dict[str, LinkTypeDef] = field(default_factory=dict)

    def __init__(self) -> None:
        def _lt(name: str, inverse: str, symmetric: bool) -> LinkTypeDef:
            return LinkTypeDef(name=name, inverse=inverse, symmetric=symmetric)

        self._built_in: dict[str, LinkTypeDef] = {
            "reference": _lt("reference", "reference", symmetric=True),
            "extends": _lt("extends", "extended_by", symmetric=False),
            "extended_by": _lt("extended_by", "extends", symmetric=False),
            "refines": _lt("refines", "refined_by", symmetric=False),
            "refined_by": _lt("refined_by", "refines", symmetric=False),
            "contradicts": _lt("contradicts", "contradicted_by", symmetric=False),
            "contradicted_by": _lt("contradicted_by", "contradicts", symmetric=False),
            "questions": _lt("questions", "questioned_by", symmetric=False),
            "questioned_by": _lt("questioned_by", "questions", symmetric=False),
            "supports": _lt("supports", "supported_by", symmetric=False),
            "supported_by": _lt("supported_by", "supports", symmetric=False),
            "related": _lt("related", "related", symmetric=True),
        }
        self._custom: dict[str, LinkTypeDef] = {}

    def is_valid(self, name: str) -> bool:
        """Return True if `name` is a registered link type."""
        return name in self._built_in or name in self._custom

    def register(self, name: str, inverse: str, symmetric: bool) -> None:
        """Register a custom link type.

        Args:
            name: Unique type name (e.g. ``"implements"``)
            inverse: Inverse type name (same as ``name`` for symmetric types)
            description: Optional human-readable description
            symmetric: Whether the relationship is symmetric

        Raises:
            ValueError: If the type name already exists (built-in or custom)
        """
        if name in self._built_in:
            msg = f"'{name}' is a built-in link type and cannot be overridden"
            raise ValueError(msg)
        if name in self._custom:
            msg = f"Custom link type '{name}' is already registered"
            raise ValueError(msg)

        defn = LinkTypeDef(name=name, inverse=inverse, symmetric=symmetric)
        self._custom[name] = defn
        # Register inverse if different
        if inverse != name and inverse not in self._built_in and inverse not in self._custom:  # noqa: E501
            self._custom[inverse] = LinkTypeDef(
                name=inverse, inverse=name, symmetric=symmetric,
            )

    def get_inverse(self, name: str) -> str:
        """Return the inverse type name for `name`."""
        defn = self._built_in.get(name) or self._custom.get(name)
        return defn.inverse if defn else name

    def all_types(self) -> list[str]:
        """Return all registered type names."""
        return sorted(list(self._built_in.keys()) + list(self._custom.keys()))

    def custom_types(self) -> list[LinkTypeDef]:
        """Return only the custom (non-built-in) type definitions."""
        return list(self._custom.values())

    def load_from_yaml(self, path: "Path") -> None:  # noqa: F821
        """Load custom link types from a YAML config file."""
        if not path.exists():
            return
        try:
            with path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            for entry in data.get("custom_link_types", []):
                name = entry.get("name", "")
                inverse = entry.get("inverse", name)
                symmetric = bool(entry.get("symmetric", False))
                if name and not self.is_valid(name):
                    defn = LinkTypeDef(name=name, inverse=inverse, symmetric=symmetric)
                    self._custom[name] = defn
                    if inverse != name and not self.is_valid(inverse):
                        self._custom[inverse] = LinkTypeDef(
                            name=inverse, inverse=name, symmetric=symmetric,
                        )
        except Exception:  # noqa: BLE001
            logger.debug("Failed to load custom link types from %s", path)


# Module-level registry singleton
link_type_registry = LinkTypeRegistry()


class Link(BaseModel):
    """A link between two notes."""

    source_id: str = Field(..., description="ID of the source note")
    target_id: str = Field(..., description="ID of the target note")
    link_type: str = Field(default="reference", description="Type of link")
    description: str | None = Field(
        default=None,
        description="Optional description of the link",
    )
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc),
        description="When the link was created",
    )

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
        "frozen": True,  # Links are immutable
    }

    @field_validator("link_type")
    @classmethod
    def validate_link_type(cls, v: str) -> str:
        """Validate that link_type is in the registry."""
        # Coerce LinkType enum values to their string form
        if isinstance(v, LinkType):
            return v.value
        if not link_type_registry.is_valid(v):
            msg = (
                f"Invalid link type '{v}'. "
                f"Valid types: {', '.join(link_type_registry.all_types())}"
            )
            raise ValueError(msg)
        return v


class NoteType(str, Enum):
    """Types of notes in a Zettelkasten."""

    FLEETING = "fleeting"  # Quick, temporary notes
    LITERATURE = "literature"  # Notes from reading material
    PERMANENT = "permanent"  # Permanent, well-formulated notes
    STRUCTURE = "structure"  # Structure/index notes that organize other notes
    HUB = "hub"  # Hub notes that serve as entry points


class Tag(BaseModel):
    """A tag for categorizing notes."""

    name: str = Field(..., description="Tag name")

    model_config = {
        "validate_assignment": True,
        "frozen": True,
    }

    def __str__(self) -> str:
        """Return string representation of tag."""
        return self.name


class Note(BaseModel):
    """A Zettelkasten note."""

    id: str = Field(default_factory=generate_id, description="Unique ID of the note")
    title: str = Field(..., description="Title of the note")
    content: str = Field(..., description="Content of the note")
    note_type: NoteType = Field(default=NoteType.PERMANENT, description="Type of note")
    tags: list[Tag] = Field(default_factory=list, description="Tags for categorization")
    links: list[Link] = Field(default_factory=list, description="Links to other notes")
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc),
        description="When the note was created",
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc),
        description="When the note was last updated",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the note",
    )
    is_readonly: bool = Field(
        default=False,
        description="True if this note is an external watch-folder reference (read-only)",
    )
    source_path: str | None = Field(
        default=None,
        description="Absolute path to the source file for read-only external notes",
    )

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
    }

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate that the title is not empty."""
        if not v.strip():
            msg = "Title cannot be empty"
            raise ValueError(msg)
        return v

    def add_tag(self, tag: str | Tag) -> None:
        """Add a tag to the note."""
        if isinstance(tag, str):
            tag = Tag(name=tag)
        # Check if tag already exists
        tag_names = {t.name for t in self.tags}
        if tag.name not in tag_names:
            self.tags.append(tag)
            self.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)

    def remove_tag(self, tag: str | Tag) -> None:
        """Remove a tag from the note."""
        tag_name = tag.name if isinstance(tag, Tag) else tag
        self.tags = [t for t in self.tags if t.name != tag_name]
        self.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)

    def add_link(
        self,
        target_id: str,
        link_type: LinkType | str = LinkType.REFERENCE,
        description: str | None = None,
    ) -> None:
        """Add a link to another note."""
        # Normalise to string
        lt_str = link_type.value if isinstance(link_type, LinkType) else str(link_type)
        # Check if link already exists
        for link in self.links:
            if link.target_id == target_id and link.link_type == lt_str:
                return  # Link already exists
        link = Link(
            source_id=self.id,
            target_id=target_id,
            link_type=lt_str,
            description=description,
        )
        self.links.append(link)
        self.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)

    def remove_link(self, target_id: str, link_type: LinkType | str | None = None) -> None:  # noqa: E501
        """Remove a link to another note."""
        if link_type is not None:
            lt_str = link_type.value if isinstance(link_type, LinkType) else str(link_type)  # noqa: E501
            self.links = [
                link
                for link in self.links
                if not (link.target_id == target_id and link.link_type == lt_str)
            ]
        else:
            self.links = [link for link in self.links if link.target_id != target_id]
        self.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)

    def get_linked_note_ids(self) -> set[str]:
        """Get all note IDs that this note links to."""
        return {link.target_id for link in self.links}

    def to_markdown(self) -> str:
        """Convert the note to a markdown formatted string."""
        from zettelkasten_mcp.config import config  # noqa: PLC0415

        # Format tags
        tags_str = ", ".join([tag.name for tag in self.tags])
        # Format links
        links_str = ""
        if self.links:
            links_str = "\n".join(
                [
                    f"- [{link.link_type}] [[{link.target_id}]] {link.description or ''}"  # noqa: E501
                    for link in self.links
                ],
            )
        # Apply template
        return config.default_note_template.format(
            title=self.title,
            content=self.content,
            created_at=self.created_at.isoformat(),
            tags=tags_str,
            links=links_str,
        )
