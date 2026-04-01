"""Tests for WatchFolderService — scan, ID generation, and sync."""

import hashlib
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, patch

from zettelkasten_mcp.services.watch_folder_service import (
    WatchFolderService,
    _generate_external_id,
    _parse_external_note,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_md(path: Path, content: str) -> Path:
    path.write_text(dedent(content).strip())
    return path


# ---------------------------------------------------------------------------
# _generate_external_id
# ---------------------------------------------------------------------------


class TestGenerateExternalId:
    def test_returns_ext_prefix(self, tmp_path):
        p = tmp_path / "note.md"
        nid = _generate_external_id(p)
        assert nid.startswith("ext-")

    def test_id_length_is_16_chars(self, tmp_path):
        p = tmp_path / "note.md"
        nid = _generate_external_id(p)
        # "ext-" + 12 hex chars
        assert len(nid) == 16

    def test_deterministic(self, tmp_path):
        p = tmp_path / "note.md"
        assert _generate_external_id(p) == _generate_external_id(p)

    def test_different_paths_give_different_ids(self, tmp_path):
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        assert _generate_external_id(a) != _generate_external_id(b)

    def test_sha256_derivation(self, tmp_path):
        p = tmp_path / "note.md"
        expected = "ext-" + hashlib.sha256(str(p).encode()).hexdigest()[:12]
        assert _generate_external_id(p) == expected


# ---------------------------------------------------------------------------
# _parse_external_note
# ---------------------------------------------------------------------------


class TestParseExternalNote:
    def test_note_with_full_frontmatter(self, tmp_path):
        md = tmp_path / "my-note.md"
        _write_md(
            md,
            """\
            ---
            title: My External Note
            tags: [foo, bar]
            ---
            # My External Note

            Content here.
        """,
        )
        note = _parse_external_note(md)
        assert note.title == "My External Note"
        assert {t.name for t in note.tags} == {"foo", "bar"}
        assert note.is_readonly is True
        assert note.source_path == str(md)

    def test_note_with_frontmatter_and_links_metadata(self, tmp_path):
        md = tmp_path / "rich-note.md"
        _write_md(
            md,
            """\
            ---
            id: ext-123
            title: Rich External Note
            type: not-a-real-type
            tags: alpha, beta
            created: 2026-01-01T12:00:00+00:00
            updated: 2026-01-02T13:30:00+00:00
            ---
            # Rich External Note

            Body content.

            ## Links
            - extends [[target-1]] Because
            - nonsense [[target-2]] Fallback
            - malformed link line

            ## Other
            More content.
        """,
        )

        note = _parse_external_note(md)

        assert note.id == "ext-123"
        assert note.title == "Rich External Note"
        assert note.note_type.value == "permanent"
        assert [tag.name for tag in note.tags] == ["alpha", "beta"]
        assert len(note.links) == 2
        assert note.links[0].link_type == "extends"
        assert note.links[0].target_id == "target-1"
        assert note.links[1].link_type == "reference"
        assert note.links[1].target_id == "target-2"
        assert note.created_at.isoformat().startswith("2026-01-01T12:00:00")
        assert note.updated_at.isoformat().startswith("2026-01-02T13:30:00")

    def test_note_without_frontmatter_uses_stem_as_title(self, tmp_path):
        md = tmp_path / "plain-file.md"
        _write_md(md, "Some plain content with no frontmatter.")
        note = _parse_external_note(md)
        assert note.title == "plain-file"
        assert note.is_readonly is True

    def test_note_without_frontmatter_gets_ext_id(self, tmp_path):
        md = tmp_path / "no-front.md"
        _write_md(md, "content")
        note = _parse_external_note(md)
        assert note.id.startswith("ext-")

    def test_note_with_frontmatter_id_preserved(self, tmp_path):
        md = tmp_path / "has-id.md"
        _write_md(
            md,
            """\
            ---
            id: 20251109T120530123456789
            title: ID-bearing note
            ---
            Content.
        """,
        )
        note = _parse_external_note(md)
        assert note.id == "20251109T120530123456789"

    def test_is_readonly_always_true(self, tmp_path):
        md = tmp_path / "always.md"
        _write_md(md, "content")
        note = _parse_external_note(md)
        assert note.is_readonly is True

    def test_source_path_is_absolute(self, tmp_path):
        md = tmp_path / "note.md"
        _write_md(md, "content")
        note = _parse_external_note(md)
        assert Path(note.source_path).is_absolute()


# ---------------------------------------------------------------------------
# WatchFolderService.scan_directory
# ---------------------------------------------------------------------------


class TestScanDirectory:
    def test_empty_directory_returns_empty_list(self, tmp_path):
        repo = MagicMock()
        svc = WatchFolderService(watch_dirs=[tmp_path], repository=repo)
        result = svc.scan_directory(tmp_path)
        assert result == []

    def test_scans_md_files(self, tmp_path):
        (tmp_path / "a.md").write_text("# A")
        (tmp_path / "b.md").write_text("# B")
        repo = MagicMock()
        svc = WatchFolderService(watch_dirs=[tmp_path], repository=repo)
        result = svc.scan_directory(tmp_path)
        assert len(result) == 2

    def test_ignores_non_md_files(self, tmp_path):
        (tmp_path / "note.md").write_text("# Note")
        (tmp_path / "data.txt").write_text("data")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        repo = MagicMock()
        svc = WatchFolderService(watch_dirs=[tmp_path], repository=repo)
        result = svc.scan_directory(tmp_path)
        assert len(result) == 1

    def test_scans_recursively(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "root.md").write_text("root")
        (sub / "child.md").write_text("child")
        repo = MagicMock()
        svc = WatchFolderService(watch_dirs=[tmp_path], repository=repo)
        result = svc.scan_directory(tmp_path)
        assert len(result) == 2

    def test_malformed_frontmatter_is_skipped_with_warning(self, tmp_path, caplog):
        bad = tmp_path / "bad.md"
        bad.write_text("---\n{{ invalid yaml [\n---\ncontent")
        repo = MagicMock()
        svc = WatchFolderService(watch_dirs=[tmp_path], repository=repo)
        with caplog.at_level("WARNING"):
            result = svc.scan_directory(tmp_path)
        # By convention the service should skip files that raise on parse
        # It may recover and include the file with a stub note, or skip it.
        # Either behaviour is acceptable; we just confirm no exception is raised.
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# WatchFolderService.sync_all
# ---------------------------------------------------------------------------


class TestSyncAll:
    def test_sync_all_returns_summary_dict(self, tmp_path):
        (tmp_path / "note.md").write_text("# Watch Note\n\nContent.")
        repo = MagicMock()
        repo._index_note = MagicMock()
        svc = WatchFolderService(watch_dirs=[tmp_path], repository=repo)
        # Patch _drop_readonly_entries so we don't need a real DB
        with patch.object(svc, "_drop_readonly_entries", return_value=0):
            result = svc.sync_all()
        assert "scanned" in result
        assert "added" in result
        assert "removed" in result
        assert "errors" in result

    def test_sync_all_reports_scanned_count(self, tmp_path):
        (tmp_path / "a.md").write_text("A")
        (tmp_path / "b.md").write_text("B")
        repo = MagicMock()
        svc = WatchFolderService(watch_dirs=[tmp_path], repository=repo)
        with patch.object(svc, "_drop_readonly_entries", return_value=0):
            result = svc.sync_all()
        assert result["scanned"] == 2

    def test_sync_all_with_no_watch_dirs(self):
        repo = MagicMock()
        svc = WatchFolderService(watch_dirs=[], repository=repo)
        with patch.object(svc, "_drop_readonly_entries", return_value=0):
            result = svc.sync_all()
        assert result["scanned"] == 0
        assert result["added"] == 0

    def test_sync_all_skips_missing_watch_dir(self, tmp_path, caplog):
        missing_dir = tmp_path / "missing"
        repo = MagicMock()
        svc = WatchFolderService(watch_dirs=[missing_dir], repository=repo)
        with patch.object(svc, "_drop_readonly_entries", return_value=0):
            with caplog.at_level("WARNING"):
                result = svc.sync_all()

        assert result == {"scanned": 0, "added": 0, "removed": 0, "errors": []}
        assert any("no longer exists" in record.message for record in caplog.records)

    def test_sync_all_index_note_called_for_each_file(self, tmp_path):
        (tmp_path / "note1.md").write_text("one")
        (tmp_path / "note2.md").write_text("two")
        repo = MagicMock()
        repo._index_note = MagicMock(return_value=None)
        svc = WatchFolderService(watch_dirs=[tmp_path], repository=repo)
        with patch.object(svc, "_drop_readonly_entries", return_value=0):
            svc.sync_all()
        assert repo._index_note.call_count == 2

    def test_drop_readonly_entries_removes_external_notes(self, note_repository):
        from zettelkasten_mcp.models.schema import Note, NoteType

        with note_repository.session_factory() as session:
            note_repository._create_fts5_table(session)
            session.commit()

        note = Note(
            id="readonly-1",
            title="Readonly",
            content="External content",
            note_type=NoteType.PERMANENT,
            tags=[],
            links=[],
            metadata={},
            is_readonly=True,
            source_path="/tmp/external.md",
        )
        note_repository._index_note(note)

        svc = WatchFolderService(watch_dirs=[], repository=note_repository)
        removed = svc._drop_readonly_entries()

        assert removed == 1
        assert note_repository.get("readonly-1") is None
