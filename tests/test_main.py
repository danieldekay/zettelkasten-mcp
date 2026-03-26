# tests/test_main.py
"""Tests for the main module entry point."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestParseArgs:
    """Tests for parse_args."""

    def test_defaults(self):
        from zettelkasten_mcp.main import parse_args

        with patch.object(sys, "argv", ["prog"]):
            args = parse_args()
        assert args.log_level == "INFO"

    def test_custom_args(self, tmp_path):
        from zettelkasten_mcp.main import parse_args

        db_path = str(tmp_path / "db.sqlite")
        notes_path = str(tmp_path / "notes")
        with patch.object(
            sys,
            "argv",
            [
                "prog",
                "--notes-dir", notes_path,
                "--database-path", db_path,
                "--log-level", "DEBUG",
            ],
        ):
            args = parse_args()
        assert args.notes_dir == notes_path
        assert args.database_path == db_path
        assert args.log_level == "DEBUG"


class TestUpdateConfig:
    """Tests for update_config."""

    def test_updates_notes_dir(self, tmp_path):
        from argparse import Namespace

        from zettelkasten_mcp.main import update_config

        args = Namespace(notes_dir=str(tmp_path / "notes"), database_path=None)
        update_config(args)

    def test_no_update_when_none(self):
        from argparse import Namespace

        from zettelkasten_mcp.main import update_config

        args = Namespace(notes_dir=None, database_path=None)
        update_config(args)


class TestMain:
    """Tests for the main() function."""

    def test_main_starts_server(self, tmp_path):
        from zettelkasten_mcp.main import main

        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        db_path = tmp_path / "db" / "zk.db"
        db_path.parent.mkdir()

        with (
            patch.object(
                sys,
                "argv",
                [
                    "prog",
                    "--notes-dir", str(notes_dir),
                    "--database-path", str(db_path),
                    "--log-level", "WARNING",
                ],
            ),
            patch("zettelkasten_mcp.main.init_db"),
            patch("zettelkasten_mcp.main.ZettelkastenMcpServer") as mock_server_cls,
        ):
            mock_server = MagicMock()
            mock_server_cls.return_value = mock_server
            main()

        mock_server.run.assert_called_once()

    def test_main_exits_on_db_error(self, tmp_path):
        from zettelkasten_mcp.main import main

        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        db_path = tmp_path / "db" / "zk.db"
        db_path.parent.mkdir()

        with (
            patch.object(
                sys,
                "argv",
                ["prog", "--notes-dir", str(notes_dir), "--database-path", str(db_path)],
            ),
            patch("zettelkasten_mcp.main.init_db", side_effect=Exception("DB error")),
            patch("sys.exit") as mock_exit,
        ):
            main()

        mock_exit.assert_called_with(1)

    def test_main_exits_on_server_error(self, tmp_path):
        from zettelkasten_mcp.main import main

        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        db_path = tmp_path / "db" / "zk.db"
        db_path.parent.mkdir()

        with (
            patch.object(
                sys,
                "argv",
                ["prog", "--notes-dir", str(notes_dir), "--database-path", str(db_path)],
            ),
            patch("zettelkasten_mcp.main.init_db"),
            patch(
                "zettelkasten_mcp.main.ZettelkastenMcpServer",
                side_effect=Exception("Server error"),
            ),
            patch("sys.exit") as mock_exit,
        ):
            main()

        mock_exit.assert_called_with(1)
