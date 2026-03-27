# tests/test_utils.py
"""Tests for the utility functions."""

import re
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from zettelkasten_mcp.utils import (
    format_note_for_display,
    generate_timestamp_id,
    parse_tags,
    setup_logging,
)


class TestGenerateTimestampId:
    """Tests for generate_timestamp_id."""

    def test_returns_string(self):
        id1 = generate_timestamp_id()
        assert isinstance(id1, str)

    def test_format_matches_pattern(self):
        id1 = generate_timestamp_id()
        assert re.match(r"^\d{8}T\d{6}\d{9}$", id1), f"Got: {id1}"

    def test_unique_ids(self):
        ids = {generate_timestamp_id() for _ in range(5)}
        assert len(ids) == 5


class TestParseTags:
    """Tests for parse_tags."""

    def test_empty_string(self):
        assert parse_tags("") == []

    def test_single_tag(self):
        assert parse_tags("python") == ["python"]

    def test_multiple_tags(self):
        result = parse_tags("python, ml, ai")
        assert result == ["python", "ml", "ai"]

    def test_strips_whitespace(self):
        result = parse_tags("  a  ,  b  ")
        assert result == ["a", "b"]

    def test_skips_empty_segments(self):
        result = parse_tags("a,,b")
        assert result == ["a", "b"]


class TestFormatNoteForDisplay:
    """Tests for format_note_for_display."""

    def _make_dt(self):
        return datetime(2024, 1, 15, 10, 30, 0)

    def test_basic_format(self):
        result = format_note_for_display(
            title="My Note",
            note_id="abc123",
            content="Some content",
            tags=["t1", "t2"],
            created_at=self._make_dt(),
            updated_at=self._make_dt(),
        )
        assert "# My Note" in result
        assert "abc123" in result
        assert "Some content" in result
        assert "t1, t2" in result

    def test_no_tags(self):
        result = format_note_for_display(
            title="T",
            note_id="id1",
            content="C",
            tags=[],
            created_at=self._make_dt(),
            updated_at=self._make_dt(),
        )
        assert "Tags:" not in result

    def test_with_links_no_description(self):
        mock_link = MagicMock()
        mock_link.link_type = "extends"
        mock_link.target_id = "target1"
        mock_link.description = None

        result = format_note_for_display(
            title="T",
            note_id="id1",
            content="C",
            tags=[],
            created_at=self._make_dt(),
            updated_at=self._make_dt(),
            links=[mock_link],
        )
        assert "## Links" in result
        assert "extends: target1" in result

    def test_with_links_with_description(self):
        mock_link = MagicMock()
        mock_link.link_type = "supports"
        mock_link.target_id = "target2"
        mock_link.description = "see also"

        result = format_note_for_display(
            title="T",
            note_id="id1",
            content="C",
            tags=[],
            created_at=self._make_dt(),
            updated_at=self._make_dt(),
            links=[mock_link],
        )
        assert "see also" in result

    def test_no_links(self):
        result = format_note_for_display(
            title="T",
            note_id="id1",
            content="C",
            tags=[],
            created_at=self._make_dt(),
            updated_at=self._make_dt(),
            links=None,
        )
        assert "## Links" not in result


class TestSetupLogging:
    """Tests for setup_logging."""

    def test_default_level_runs_without_error(self):
        setup_logging()

    def test_debug_level_runs_without_error(self):
        setup_logging(level="DEBUG")

    def test_invalid_level_defaults_to_info(self):
        setup_logging(level="NOTAREALLEVEL")

    def test_with_log_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "test.log")
            setup_logging(level="WARNING", log_file=log_path)


class TestConfig:
    """Tests for config utility methods."""

    def test_get_absolute_path_absolute_input(self, tmp_path):
        from zettelkasten_mcp.config import ZettelkastenConfig

        cfg = ZettelkastenConfig(base_dir=tmp_path)
        result = cfg.get_absolute_path(tmp_path / "subdir")
        assert result == tmp_path / "subdir"

    def test_get_absolute_path_relative_input(self, tmp_path):
        from pathlib import Path

        from zettelkasten_mcp.config import ZettelkastenConfig

        cfg = ZettelkastenConfig(base_dir=tmp_path)
        result = cfg.get_absolute_path(Path("data/notes"))
        assert result == tmp_path / "data" / "notes"
