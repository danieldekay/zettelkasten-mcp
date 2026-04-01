"""Tests for ZETTELKASTEN_WATCH_DIRS configuration parsing."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from zettelkasten_mcp.config import _parse_watch_dirs


class TestParseWatchDirs:
    """Tests for _parse_watch_dirs() function."""

    def test_empty_env_var_returns_empty_list(self):
        """When ZETTELKASTEN_WATCH_DIRS is not set, returns an empty list."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ZETTELKASTEN_WATCH_DIRS", None)
            result = _parse_watch_dirs()
        assert result == []

    def test_blank_env_var_returns_empty_list(self):
        """When ZETTELKASTEN_WATCH_DIRS is blank, returns an empty list."""
        with patch.dict(os.environ, {"ZETTELKASTEN_WATCH_DIRS": "   "}):
            result = _parse_watch_dirs()
        assert result == []

    def test_single_valid_path(self):
        """A single valid directory path is returned as a one-element list."""
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(os.environ, {"ZETTELKASTEN_WATCH_DIRS": d}):
                result = _parse_watch_dirs()
        assert len(result) == 1
        assert isinstance(result[0], Path)

    def test_multiple_valid_paths(self):
        """Comma-separated valid paths are returned as a list."""
        with tempfile.TemporaryDirectory() as d1:
            with tempfile.TemporaryDirectory() as d2:
                env_val = f"{d1},{d2}"
                with patch.dict(os.environ, {"ZETTELKASTEN_WATCH_DIRS": env_val}):
                    result = _parse_watch_dirs()
        assert len(result) == 2

    def test_nonexistent_path_is_skipped(self, caplog):
        """A non-existent path is skipped with a WARNING log."""
        nonexistent = "/this/path/does/not/exist/ever"
        with patch.dict(os.environ, {"ZETTELKASTEN_WATCH_DIRS": nonexistent}):
            with caplog.at_level("WARNING"):
                result = _parse_watch_dirs()
        assert result == []
        assert any("WARNING" in r.levelname or r.levelno >= 30 for r in caplog.records)

    def test_file_path_is_skipped(self, tmp_path, caplog):
        """A path pointing to a file (not a directory) is skipped with a WARNING."""
        f = tmp_path / "not_a_dir.md"
        f.write_text("hello")
        with patch.dict(os.environ, {"ZETTELKASTEN_WATCH_DIRS": str(f)}):
            with caplog.at_level("WARNING"):
                result = _parse_watch_dirs()
        assert result == []

    def test_mix_of_valid_and_invalid_paths(self, tmp_path, caplog):
        """Valid paths are returned; invalid ones are skipped with WARNINGs."""
        nonexistent = "/no/such/dir"
        env_val = f"{nonexistent},{tmp_path}"
        with patch.dict(os.environ, {"ZETTELKASTEN_WATCH_DIRS": env_val}):
            with caplog.at_level("WARNING"):
                result = _parse_watch_dirs()
        assert len(result) == 1
        assert result[0] == tmp_path

    def test_whitespace_around_paths_is_stripped(self, tmp_path):
        """Leading/trailing whitespace around paths is stripped."""
        env_val = f"  {tmp_path}  "
        with patch.dict(os.environ, {"ZETTELKASTEN_WATCH_DIRS": env_val}):
            result = _parse_watch_dirs()
        assert len(result) == 1
        assert result[0] == tmp_path
