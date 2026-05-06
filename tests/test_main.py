# tests/test_main.py
"""Tests for the main module entry point."""

import sys
from unittest.mock import MagicMock, patch


class TestParseArgs:
    """Tests for parse_args."""

    def test_defaults(self):
        from zettelkasten_mcp.main import parse_args  # noqa: PLC0415

        with patch.object(sys, "argv", ["prog"]):
            args = parse_args()
        assert args.log_level is None
        assert args.notes_dir is None
        assert args.database_path is None
        assert args.config is None

    def test_config_arg(self, tmp_path):
        from zettelkasten_mcp.main import parse_args  # noqa: PLC0415

        cfg_path = str(tmp_path / "config.toml")
        with patch.object(sys, "argv", ["prog", "--config", cfg_path]):
            args = parse_args()
        assert args.config == cfg_path

    def test_custom_args(self, tmp_path):
        from zettelkasten_mcp.main import parse_args  # noqa: PLC0415

        db_path = str(tmp_path / "db.sqlite")
        notes_path = str(tmp_path / "notes")
        with patch.object(
            sys,
            "argv",
            [
                "prog",
                "--notes-dir",
                notes_path,
                "--database-path",
                db_path,
                "--log-level",
                "DEBUG",
            ],
        ):
            args = parse_args()
        assert args.notes_dir == notes_path
        assert args.database_path == db_path
        assert args.log_level == "DEBUG"


class TestUpdateConfig:
    """Tests for update_config."""

    def test_updates_notes_dir(self, tmp_path):
        from argparse import Namespace  # noqa: PLC0415

        from zettelkasten_mcp.main import update_config  # noqa: PLC0415

        args = Namespace(notes_dir=str(tmp_path / "notes"), database_path=None, log_level=None, config=None)
        update_config(args)

    def test_no_update_when_none(self):
        from argparse import Namespace  # noqa: PLC0415

        from zettelkasten_mcp.main import update_config  # noqa: PLC0415

        args = Namespace(notes_dir=None, database_path=None, log_level=None, config=None)
        update_config(args)

    def test_load_toml(self, tmp_path):
        """TOML values should override env defaults when --config is provided."""
        from argparse import Namespace  # noqa: PLC0415

        from zettelkasten_mcp.config import config  # noqa: PLC0415
        from zettelkasten_mcp.main import update_config  # noqa: PLC0415

        notes_dir = tmp_path / "mynotes"
        notes_dir.mkdir()
        db_path = tmp_path / "my.db"
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text(
            f'[storage]\nnotes_dir = "{notes_dir}"\ndatabase_path = "{db_path}"\n'
            '[server]\nlog_level = "DEBUG"\n'
        )

        args = Namespace(notes_dir=None, database_path=None, log_level=None, config=str(cfg_file))
        update_config(args)

        assert config.notes_dir == notes_dir
        assert config.database_path == db_path
        assert config.log_level == "DEBUG"


class TestMain:
    """Tests for the main() function."""

    def test_main_starts_server(self, tmp_path):
        from zettelkasten_mcp.main import main  # noqa: PLC0415

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
                    "--notes-dir",
                    str(notes_dir),
                    "--database-path",
                    str(db_path),
                    "--log-level",
                    "WARNING",
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
        from zettelkasten_mcp.main import main  # noqa: PLC0415

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
                    "--notes-dir",
                    str(notes_dir),
                    "--database-path",
                    str(db_path),
                ],
            ),
            patch("zettelkasten_mcp.main.init_db", side_effect=Exception("DB error")),
            patch("sys.exit") as mock_exit,
        ):
            main()

        mock_exit.assert_called_with(1)

    def test_main_exits_on_server_error(self, tmp_path):
        from zettelkasten_mcp.main import main  # noqa: PLC0415

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
                    "--notes-dir",
                    str(notes_dir),
                    "--database-path",
                    str(db_path),
                ],
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
