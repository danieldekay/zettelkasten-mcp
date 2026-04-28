"""Configuration module for the Zettelkasten MCP server."""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

class ZettelkastenConfig(BaseModel):
    """Configuration for the Zettelkasten server."""
    # Base directory for the project
    base_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("ZETTELKASTEN_BASE_DIR", "."))
    )
    # Storage configuration
    notes_dir: Path = Field(
        default_factory=lambda: Path(
            os.getenv("ZETTELKASTEN_NOTES_DIR", "data/notes")
        )
    )
    # Database configuration
    database_path: Path = Field(
        default_factory=lambda: Path(
            os.getenv("ZETTELKASTEN_DATABASE_PATH", "data/db/zettelkasten.db")
        )
    )
    # Server configuration
    server_name: str = Field(
        default=os.getenv("ZETTELKASTEN_SERVER_NAME", "zettelkasten-mcp")
    )
    server_version: str = Field(default="1.2.1")
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
        )
    )
    # FTS5 Full-Text Search configuration
    use_fts5_search: bool = Field(
        default=os.getenv("USE_FTS5_SEARCH", "true").lower() == "true",
    )
    # LLM Summary Generation Configuration
    llm_enable_summaries: bool = Field(
        default=os.getenv("LLM_ENABLE_SUMMARIES", "false").lower() == "true",
    )
    azure_openai_endpoint: str = Field(
        default=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    )
    azure_openai_api_version: str = Field(
        default=os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
    )
    llm_model: str = Field(
        default=os.getenv("LLM_MODEL", "gpt-4o"),
    )
    llm_temperature: float = Field(
        default=float(os.getenv("LLM_TEMPERATURE", "0.1")),
    )
    llm_max_tokens: int = Field(
        default=int(os.getenv("LLM_MAX_TOKENS", "300")),
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
