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
        if not path.is_absolute():
            logger.warning(
                "ZETTELKASTEN_WATCH_DIRS: relative path given, resolving to "
                "absolute: %s",
                path,
            )
        try:
            resolved = path.resolve()
        except OSError as exc:  # pragma: no cover - extremely rare filesystem error
            logger.warning(
                "ZETTELKASTEN_WATCH_DIRS: failed to resolve path, skipping: %s (%s)",
                path,
                exc,
            )
            continue
        if not resolved.exists():
            logger.warning(
                "ZETTELKASTEN_WATCH_DIRS: path does not exist, skipping: %s",
                resolved,
            )
        elif not resolved.is_dir():
            logger.warning(
                "ZETTELKASTEN_WATCH_DIRS: path is not a directory, skipping: %s",
                resolved,
            )
        else:
            valid.append(resolved)
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
    log_level: str = Field(
        default=os.getenv("ZETTELKASTEN_LOG_LEVEL", "INFO"),
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
    # LLM summary generation (Azure OpenAI) — disabled by default
    llm_enable_summaries: bool = Field(
        default=os.getenv("LLM_ENABLE_SUMMARIES", "false").lower() == "true",
    )
    azure_openai_endpoint: str = Field(
        default=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    )
    azure_openai_api_version: str = Field(
        default=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )
    llm_model: str = Field(
        default=os.getenv("LLM_MODEL", "gpt-4o"),
    )
    llm_temperature: float = Field(
        default=float(os.getenv("LLM_TEMPERATURE", "0.2")),
    )
    llm_max_tokens: int = Field(
        default=int(os.getenv("LLM_MAX_TOKENS", "512")),
    )
    # Self-healing index: auto-rebuild when drift exceeds this percent (0 = disabled)
    auto_rebuild_threshold: int = Field(
        default=int(os.getenv("ZETTELKASTEN_AUTO_REBUILD_THRESHOLD", "5")),
    )
    # Tag syntax enforcement: when True, reject non-canonical tags instead of
    # normalising them silently.
    strict_tag_syntax: bool = Field(
        default=os.getenv("ZETTELKASTEN_STRICT_TAGS", "false").lower() == "true",
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

    def _apply_storage_section(self, s: dict) -> None:
        if "notes_dir" in s:
            self.notes_dir = Path(s["notes_dir"])
        if "database_path" in s:
            self.database_path = Path(s["database_path"])

    def _apply_server_section(self, s: dict) -> None:
        if "name" in s:
            self.server_name = str(s["name"])
        if "log_level" in s:
            self.log_level = str(s["log_level"])

    def _apply_watch_section(self, s: dict) -> None:
        if "dirs" not in s:
            return
        valid: list[Path] = []
        for entry in s["dirs"]:
            p = Path(str(entry)).resolve()
            if not p.exists():
                logger.warning(
                    "config.toml watch.dirs: path not found, skipping: %s", p
                )
            elif not p.is_dir():
                logger.warning(
                    "config.toml watch.dirs: not a directory, skipping: %s", p
                )
            else:
                valid.append(p)
        self.watch_dirs = valid

    def _apply_search_section(self, s: dict) -> None:
        if "use_fts5" in s:
            self.use_fts5_search = bool(s["use_fts5"])

    def _apply_index_section(self, s: dict) -> None:
        if "auto_rebuild_threshold" in s:
            self.auto_rebuild_threshold = int(s["auto_rebuild_threshold"])

    def _apply_tags_section(self, s: dict) -> None:
        if "strict" in s:
            self.strict_tag_syntax = bool(s["strict"])

    def _apply_llm_section(self, s: dict) -> None:
        if "enable_summaries" in s:
            self.llm_enable_summaries = bool(s["enable_summaries"])
        if "azure_endpoint" in s:
            self.azure_openai_endpoint = str(s["azure_endpoint"])
        if "azure_api_version" in s:
            self.azure_openai_api_version = str(s["azure_api_version"])
        if "model" in s:
            self.llm_model = str(s["model"])
        if "temperature" in s:
            self.llm_temperature = float(s["temperature"])
        if "max_tokens" in s:
            self.llm_max_tokens = int(s["max_tokens"])

    def load_toml(self, path: Path) -> None:
        """Apply settings from a TOML config file, overriding current values.

        Only keys present in the file are applied; absent keys keep their
        current values (env-var defaults or previous settings).

        Priority after this call: env-var defaults < TOML file < CLI flags.

        Args:
            path: Path to the TOML configuration file.

        Raises:
            FileNotFoundError: If the config file does not exist.
            ValueError: If the TOML file cannot be parsed.
        """
        import sys  # noqa: PLC0415
        if sys.version_info >= (3, 11):
            import tomllib  # noqa: PLC0415
        else:
            import tomli as tomllib  # type: ignore[no-redef]  # noqa: PLC0415

        try:
            with path.open("rb") as fh:
                data = tomllib.load(fh)
        except FileNotFoundError:
            raise
        except Exception as exc:
            msg = f"Failed to parse TOML config at {path}: {exc}"
            raise ValueError(msg) from exc

        self._apply_storage_section(data.get("storage", {}))
        self._apply_server_section(data.get("server", {}))
        self._apply_watch_section(data.get("watch", {}))
        self._apply_search_section(data.get("search", {}))
        self._apply_index_section(data.get("index", {}))
        self._apply_tags_section(data.get("tags", {}))
        self._apply_llm_section(data.get("llm", {}))

    def get_db_url(self) -> str:
        """Get the database URL for SQLite."""
        db_path = self.get_absolute_path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"


# Create a global config instance
config = ZettelkastenConfig()
