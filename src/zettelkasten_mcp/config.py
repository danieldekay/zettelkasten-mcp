"""Configuration module for the Zettelkasten MCP server."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def _parse_watch_dirs() -> list[Path]:
    """Parse and validate watch directories from ZETTELKASTEN_WATCH_DIRS env var.

    Returns:
        List of valid, existing directory Paths. Invalid paths are skipped
        with a WARNING log entry.
    """
    raw = os.getenv("ZETTELKASTEN_WATCH_DIRS", "").strip()
    if not raw:
        return []
    valid: list[Path] = []
    for entry in raw.split(","):
        entry = entry.strip()  # noqa: PLW2901
        if not entry:
            continue
        path = Path(entry)
        if not path.exists():
            logger.warning(
                "ZETTELKASTEN_WATCH_DIRS: path does not exist, skipping: %s", path,
            )
        elif not path.is_dir():
            logger.warning(
                "ZETTELKASTEN_WATCH_DIRS: path is not a directory, skipping: %s", path,
            )
        else:
            valid.append(path)
    return valid


class ZettelkastenConfig(BaseModel):
    """Configuration for the Zettelkasten server."""

    # Base directory for the project
    base_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("ZETTELKASTEN_BASE_DIR", ".")),
    )
    # Storage configuration
    notes_dir: Path = Field(
        default_factory=lambda: Path(
            os.getenv("ZETTELKASTEN_NOTES_DIR", "data/notes"),
        ),
    )
    # Database configuration
    database_path: Path = Field(
        default_factory=lambda: Path(
            os.getenv("ZETTELKASTEN_DATABASE_PATH", "data/db/zettelkasten.db"),
        ),
    )
    # Server configuration
    server_name: str = Field(
        default=os.getenv("ZETTELKASTEN_SERVER_NAME", "zettelkasten-mcp"),
    )
    server_version: str = Field(default="1.3.0")
    # Date format for ID generation (using ISO format for timestamps)
    id_date_format: str = Field(default="%Y%m%dT%H%M%S")
    # Default note template
    default_note_template: str = Field(
        default=(
            "# {title}\n\n"
            "## Metadata\n"
            "- Created: {created_at}\n"
            "- Tags: {tags}\n\n"
            "## Content\n\n"
            "{content}\n\n"
            "## Links\n"
            "{links}\n"
        ),
    )
    # FTS5 Full-Text Search configuration
    use_fts5_search: bool = Field(
        default=os.getenv("USE_FTS5_SEARCH", "true").lower() == "true",
    )
    # Self-healing index: auto-rebuild when drift exceeds this percent (0 = disabled)
    auto_rebuild_threshold: int = Field(
        default=int(os.getenv("ZETTELKASTEN_AUTO_REBUILD_THRESHOLD", "5")),
    )
    # Project-scoped custom link types config
    custom_link_types_path: Path = Field(
        default_factory=lambda: Path(
            os.getenv(
                "ZETTELKASTEN_CUSTOM_LINK_TYPES_PATH",
                "openspec/config.yaml",
            ),
        ),
    )
    # Watch folders: additional read-only Markdown directories to index
    watch_dirs: list[Path] = Field(
        default_factory=_parse_watch_dirs,
        description=(
            "Extra directories scanned for read-only reference notes. "
            "Set via ZETTELKASTEN_WATCH_DIRS (comma-separated paths)."
        ),
    )

    def get_absolute_path(self, path: Path) -> Path:
        """Convert a relative path to an absolute path based on base_dir."""
        if path.is_absolute():
            return path
        return self.base_dir / path

    def get_db_url(self) -> str:
        """Get the database URL for SQLite."""
        db_path = self.get_absolute_path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"


# Create a global config instance
config = ZettelkastenConfig()
