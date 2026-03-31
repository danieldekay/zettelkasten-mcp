#!/usr/bin/env python
"""Main entry point for the Zettelkasten MCP server."""

import argparse
import logging
import os
import sys
from pathlib import Path

from zettelkasten_mcp.config import config
from zettelkasten_mcp.models.db_models import init_db
from zettelkasten_mcp.models.schema import link_type_registry
from zettelkasten_mcp.server.mcp_server import ZettelkastenMcpServer
from zettelkasten_mcp.utils import setup_logging


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Zettelkasten MCP Server")
    parser.add_argument(
        "--notes-dir",
        help="Directory for storing note files",
        type=str,
        default=os.environ.get("ZETTELKASTEN_NOTES_DIR"),
    )
    parser.add_argument(
        "--database-path",
        help="SQLite database file path",
        type=str,
        default=os.environ.get("ZETTELKASTEN_DATABASE_PATH"),
    )
    parser.add_argument(
        "--log-level",
        help="Logging level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.environ.get("ZETTELKASTEN_LOG_LEVEL", "INFO"),
    )
    return parser.parse_args()


def update_config(args: argparse.Namespace) -> None:
    """Update the global config with command line arguments."""
    if args.notes_dir:
        config.notes_dir = Path(args.notes_dir)
    if args.database_path:
        config.database_path = Path(args.database_path)


def _run_drift_check(logger: logging.Logger) -> None:
    """Check filesystem vs DB drift and auto-rebuild if threshold exceeded."""
    from sqlalchemy import func, select  # noqa: PLC0415

    from zettelkasten_mcp.models.db_models import (  # noqa: PLC0415
        DBNote,
        get_session_factory,
    )
    from zettelkasten_mcp.storage.note_repository import NoteRepository  # noqa: PLC0415

    try:
        notes_dir = config.get_absolute_path(config.notes_dir)
        fs_count = len(list(notes_dir.glob("*.md")))

        engine = init_db()
        session_factory = get_session_factory(engine)
        with session_factory() as session:
            db_count = session.scalar(select(func.count(DBNote.id))) or 0

        if fs_count == 0:
            return

        drift_pct = abs(fs_count - db_count) / max(fs_count, 1) * 100
        threshold = config.auto_rebuild_threshold

        if threshold > 0 and drift_pct > threshold:
            logger.info(
                "Auto-rebuild triggered: %.1f%% drift detected (%d/%d notes indexed)",
                drift_pct,
                db_count,
                fs_count,
            )
            repo = NoteRepository()
            repo.rebuild_index()
        elif drift_pct > 0:
            logger.warning(
                "Index drift %.1f%% detected (%d/%d notes) - run zk_rebuild_index",
                drift_pct,
                db_count,
                fs_count,
            )
    except Exception:  # noqa: BLE001
        logger.warning("Drift check failed; continuing without auto-rebuild")


def main() -> None:
    """Run the Zettelkasten MCP server."""
    # Parse arguments and update config
    args = parse_args()
    update_config(args)

    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # Ensure database directory exists
    db_dir = config.get_absolute_path(config.database_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    # Initialize database schema
    try:
        logger.info("Using SQLite database: %s", config.get_db_url())
        init_db()
    except Exception:
        logger.exception("Failed to initialize database")
        sys.exit(1)

    # Load custom link types from project config
    custom_types_path = config.get_absolute_path(config.custom_link_types_path)
    link_type_registry.load_from_yaml(custom_types_path)
    logger.debug("Custom link types loaded from %s", custom_types_path)

    # Self-healing index drift check
    if config.auto_rebuild_threshold >= 0:
        _run_drift_check(logger)

    # Index watch folders (external read-only Markdown directories)
    if config.watch_dirs:
        from zettelkasten_mcp.services.watch_folder_service import (  # noqa: PLC0415
            WatchFolderService,
        )
        from zettelkasten_mcp.storage.note_repository import (  # noqa: PLC0415
            NoteRepository,
        )

        try:
            repo = NoteRepository()
            wfs = WatchFolderService(watch_dirs=config.watch_dirs, repository=repo)
            summary = wfs.sync_all()
            logger.info(
                "Watch folder indexing: scanned=%d added=%d removed=%d errors=%d",
                summary["scanned"],
                summary["added"],
                summary["removed"],
                len(summary["errors"]),
            )
        except Exception:  # noqa: BLE001
            logger.warning("Watch folder indexing failed; continuing without it")

    # Create and run the MCP server
    try:
        logger.info("Starting Zettelkasten MCP server")
        server = ZettelkastenMcpServer()
        server.run()
    except Exception:
        logger.exception("Error running server")
        sys.exit(1)


if __name__ == "__main__":
    main()
