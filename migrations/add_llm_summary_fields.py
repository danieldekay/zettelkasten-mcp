"""Migration: Add LLM summary fields and upgrade FTS5 schema.

Run this script once against an existing Zettelkasten database to apply the
v1.2 schema changes:

    uv run python migrations/add_llm_summary_fields.py

Changes applied (all idempotent):
1. Add LLM summary columns to ``notes`` table.
2. Create ``note_summary_cache`` table (if not already present).
3. Add ``idx_notes_content_hash`` index (if not already present).
4. Drop the old ``notes_fts`` FTS5 table and create the new ``fts5_notes``
   table with Porter stemming and extended columns.

After migration, run ``rebuild_index()`` (or the MCP ``zk_rebuild_index``
tool) so that all existing notes are re-indexed into the new FTS5 schema.
"""

import logging
import sys
from pathlib import Path

# Allow running as a script without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from zettelkasten_mcp.config import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_migration() -> None:
    """Apply all schema changes for v1.2."""
    engine = create_engine(config.get_db_url())

    with engine.connect() as conn:
        # 1. Add new columns to notes (idempotent via OperationalError catch)
        new_columns = [
            "ALTER TABLE notes ADD COLUMN en_summary TEXT",
            "ALTER TABLE notes ADD COLUMN en_keywords TEXT",
            "ALTER TABLE notes ADD COLUMN content_hash VARCHAR(64)",
            "ALTER TABLE notes ADD COLUMN summary_generated_at DATETIME",
            "ALTER TABLE notes ADD COLUMN llm_model VARCHAR(50)",
        ]
        for stmt in new_columns:
            try:
                conn.execute(text(stmt))
                conn.commit()
                logger.info("Applied: %s", stmt)
            except OperationalError as exc:  # noqa: PERF203
                if "duplicate column name" in str(exc).lower():
                    logger.debug("Already exists, skipping: %s", stmt)
                    conn.rollback()
                else:
                    conn.rollback()
                    raise

        # 2. Create note_summary_cache table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS note_summary_cache (
                note_id VARCHAR(255) PRIMARY KEY
                    REFERENCES notes(id) ON DELETE CASCADE,
                content_hash VARCHAR(64) NOT NULL,
                en_summary TEXT NOT NULL,
                en_keywords TEXT NOT NULL,
                generated_at DATETIME NOT NULL,
                llm_model VARCHAR(50) NOT NULL
            )
        """))
        conn.commit()
        logger.info("Ensured note_summary_cache table exists")

        # 3. Add content_hash index (idempotent)
        try:
            conn.execute(text(
                "CREATE INDEX idx_notes_content_hash ON notes(content_hash)",
            ))
            conn.commit()
            logger.info("Created index idx_notes_content_hash")
        except OperationalError as exc:
            if "already exists" in str(exc).lower():
                logger.debug("Index idx_notes_content_hash already exists, skipping")
                conn.rollback()
            else:
                conn.rollback()
                raise

        # 4. Replace old FTS5 table with new schema
        # Drop both old and new names so the next create is always fresh
        conn.execute(text("DROP TABLE IF EXISTS notes_fts"))
        conn.execute(text("DROP TABLE IF EXISTS fts5_notes"))
        conn.execute(text("""
            CREATE VIRTUAL TABLE fts5_notes USING fts5(
                note_id UNINDEXED,
                title,
                content,
                en_summary,
                en_keywords,
                tags,
                tokenize='porter unicode61'
            )
        """))
        conn.commit()
        logger.info("Recreated FTS5 table as fts5_notes (porter unicode61)")

    logger.info(
        "Migration complete. Run rebuild_index() to populate the new FTS5 table.",
    )


if __name__ == "__main__":
    run_migration()
