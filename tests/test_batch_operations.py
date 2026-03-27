"""Tests for batch operations, note verification, and index health dashboard."""

import time

import pytest

from zettelkasten_mcp.models.schema import NoteType

# ---------------------------------------------------------------------------
# 1. Batch Note Creation
# ---------------------------------------------------------------------------


class TestCreateNotesBatch:
    """Tests for ZettelService.create_notes_batch and NoteRepository.create_batch."""

    def test_success_creates_all_notes(self, zettel_service, test_config):
        """All notes are written to filesystem and indexed."""
        notes_data = [
            {"title": f"Batch Note {i}", "content": f"Content for note {i}"}
            for i in range(15)
        ]
        result = zettel_service.create_notes_batch(notes_data)

        assert result["created"] == 15
        assert len(result["note_ids"]) == 15
        assert result["failed"] == 0
        assert result["errors"] == []

        notes_dir = test_config.get_absolute_path(test_config.notes_dir)
        for note_id in result["note_ids"]:
            assert (notes_dir / f"{note_id}.md").exists(), (
                f"File for {note_id} not found on disk"
            )

    def test_success_notes_indexed_in_db(self, zettel_service):
        """All batch-created notes are retrievable from DB."""
        notes_data = [
            {"title": f"Indexed Note {i}", "content": f"DB content {i}"}
            for i in range(5)
        ]
        result = zettel_service.create_notes_batch(notes_data)

        for note_id in result["note_ids"]:
            retrieved = zettel_service.get_note(note_id)
            assert retrieved is not None
            assert retrieved.id == note_id

    def test_tags_and_type_preserved(self, zettel_service):
        """Tags and note_type from the input are persisted correctly."""
        result = zettel_service.create_notes_batch(
            [
                {
                    "title": "Tagged Note",
                    "content": "Has tags",
                    "note_type": "literature",
                    "tags": ["alpha", "beta"],
                },
            ],
        )
        note_id = result["note_ids"][0]
        note = zettel_service.get_note(note_id)
        assert note.note_type == NoteType.LITERATURE
        assert {t.name for t in note.tags} == {"alpha", "beta"}

    def test_validation_failure_empty_title_rejects_all(
        self,
        zettel_service,
        test_config,
    ):
        """Empty title in any note: full rejection, zero writes."""
        notes_data = [
            {"title": "Good Note", "content": "Fine"},
            {"title": "", "content": "Bad - no title"},
            {"title": "Another Good", "content": "Fine too"},
        ]
        with pytest.raises(ValueError, match="empty title"):
            zettel_service.create_notes_batch(notes_data)

        notes_dir = test_config.get_absolute_path(test_config.notes_dir)
        assert list(notes_dir.glob("*.md")) == [], (
            "No files should exist after rollback"
        )

    def test_validation_failure_empty_content_rejects_all(
        self,
        zettel_service,
        test_config,
    ):
        """Empty content in any note: full rejection, zero writes."""
        notes_data = [
            {"title": "Note A", "content": ""},
            {"title": "Note B", "content": "OK"},
        ]
        with pytest.raises(ValueError, match="empty content"):
            zettel_service.create_notes_batch(notes_data)

        notes_dir = test_config.get_absolute_path(test_config.notes_dir)
        assert list(notes_dir.glob("*.md")) == []

    def test_invalid_note_type_rejects_all(self, zettel_service):
        """Invalid note_type before writes causes ValueError."""
        notes_data = [
            {"title": "Note A", "content": "Content", "note_type": "not_a_type"},
        ]
        with pytest.raises(ValueError, match="invalid note_type"):
            zettel_service.create_notes_batch(notes_data)

    def test_repository_create_batch_db_error_cleans_files(
        self,
        zettel_service,
        test_config,
        monkeypatch,
    ):
        """If DB commit fails, any written files are deleted (rollback)."""

        call_count = [0]

        class _FailingSession:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                pass

            def add(self, obj):
                pass

            def flush(self):
                pass

            def commit(self):
                call_count[0] += 1
                err = "Simulated DB error"
                raise RuntimeError(err)

            def scalar(self, *_args, **_kwargs):
                return None

            def rollback(self):
                pass

        monkeypatch.setattr(
            zettel_service.repository,
            "session_factory",
            lambda: _FailingSession(),
        )

        notes_data = [
            {"title": f"Note {i}", "content": f"Content {i}"} for i in range(3)
        ]
        with pytest.raises(RuntimeError, match="Simulated DB error"):
            zettel_service.create_notes_batch(notes_data)

        notes_dir = test_config.get_absolute_path(test_config.notes_dir)
        assert list(notes_dir.glob("*.md")) == [], "Files must be removed on DB failure"

    def test_performance_batch_vs_individual(self, zettel_service):
        """Batch creation must be faster than equivalent individual calls."""
        n = 50
        notes_data = [
            {"title": f"Perf Batch {i}", "content": f"Content {i}"} for i in range(n)
        ]

        t0 = time.perf_counter()
        zettel_service.create_notes_batch(notes_data)
        batch_duration = time.perf_counter() - t0

        individual_notes = [
            {"title": f"Perf Solo {i}", "content": f"Solo content {i}"}
            for i in range(n)
        ]
        t1 = time.perf_counter()
        for nd in individual_notes:
            zettel_service.create_note(title=nd["title"], content=nd["content"])
        individual_duration = time.perf_counter() - t1

        assert batch_duration < individual_duration, (
            f"Batch ({batch_duration:.3f}s) was not faster "
            f"than individual ({individual_duration:.3f}s)"
        )


# ---------------------------------------------------------------------------
# 2. Batch Link Creation
# ---------------------------------------------------------------------------


class TestCreateLinksBatch:
    """Tests for ZettelService.create_links_batch and NoteRepository.create_links_batch."""  # noqa: E501

    def _make_notes(self, zettel_service, count: int) -> list[str]:
        """Helper: create `count` notes and return their IDs."""
        result = zettel_service.create_notes_batch(
            [
                {"title": f"Link Test Note {i}", "content": f"Content {i}"}
                for i in range(count)
            ],
        )
        return result["note_ids"]

    def test_success_all_links_created(self, zettel_service):
        """All links in the batch are persisted."""
        ids = self._make_notes(zettel_service, 21)
        source_id = ids[0]
        links = [
            {"source_id": source_id, "target_id": ids[i + 1], "link_type": "reference"}
            for i in range(20)
        ]
        result = zettel_service.create_links_batch(links)
        assert result == {"created": 20, "failed": 0, "errors": []}

        source_note = zettel_service.get_note(source_id)
        assert len(source_note.links) == 20

    def test_invalid_link_type_rejects_all(self, zettel_service):
        """Any invalid link_type causes full rejection before writes."""
        ids = self._make_notes(zettel_service, 3)
        links = [
            {"source_id": ids[0], "target_id": ids[1], "link_type": "reference"},
            {"source_id": ids[0], "target_id": ids[2], "link_type": "not_a_type"},
        ]
        with pytest.raises(ValueError, match="invalid link_type"):
            zettel_service.create_links_batch(links)

    def test_missing_target_note_rejects_all(self, zettel_service):
        """A link to a non-existent target note causes full rejection."""
        ids = self._make_notes(zettel_service, 2)
        links = [
            {"source_id": ids[0], "target_id": ids[1], "link_type": "reference"},
            {
                "source_id": ids[0],
                "target_id": "nonexistent_id_xyz",
                "link_type": "extends",
            },
        ]
        with pytest.raises(ValueError, match="not found"):
            zettel_service.create_links_batch(links)

    def test_missing_source_id_raises(self, zettel_service):
        """A link dict without source_id raises ValueError."""
        ids = self._make_notes(zettel_service, 2)
        with pytest.raises(ValueError, match="source_id"):
            zettel_service.create_links_batch(
                [{"target_id": ids[1], "link_type": "reference"}],
            )

    def test_missing_target_id_raises(self, zettel_service):
        """A link dict without target_id raises ValueError."""
        ids = self._make_notes(zettel_service, 2)
        with pytest.raises(ValueError, match="target_id"):
            zettel_service.create_links_batch(
                [{"source_id": ids[0], "link_type": "reference"}],
            )

    def test_performance_batch_vs_individual(self, zettel_service):
        """Batch link creation must be faster than 20 individual create_link calls."""
        ids = self._make_notes(zettel_service, 41)
        source_id_batch = ids[0]
        source_id_solo = ids[21]

        links_batch = [
            {
                "source_id": source_id_batch,
                "target_id": ids[i + 1],
                "link_type": "reference",
            }
            for i in range(20)
        ]
        t0 = time.perf_counter()
        zettel_service.create_links_batch(links_batch)
        batch_duration = time.perf_counter() - t0

        from zettelkasten_mcp.models.schema import LinkType  # noqa: PLC0415

        t1 = time.perf_counter()
        for i in range(20):
            zettel_service.create_link(
                source_id=source_id_solo,
                target_id=ids[i + 1],
                link_type=LinkType.REFERENCE,
            )
        individual_duration = time.perf_counter() - t1

        assert batch_duration < individual_duration, (
            f"Batch ({batch_duration:.3f}s) was not faster "
            f"than individual ({individual_duration:.3f}s)"
        )


# ---------------------------------------------------------------------------
# 3. Note Verification
# ---------------------------------------------------------------------------


class TestVerifyNote:
    """Tests for ZettelService.verify_note."""

    def test_fully_indexed_note(self, zettel_service):
        """A freshly created note reports file_exists=True, db_indexed=True."""
        note = zettel_service.create_note(title="Verify Me", content="Some content")
        result = zettel_service.verify_note(note.id)

        assert result["file_exists"] is True
        assert result["db_indexed"] is True
        assert "hint" not in result or result.get("hint") is None

    def test_link_and_tag_counts(self, zettel_service):
        """verify_note returns correct link_count and tag_count."""
        note_a = zettel_service.create_note(
            title="Source",
            content="Source content",
            tags=["x", "y"],
        )
        note_b = zettel_service.create_note(title="Target", content="Target content")
        from zettelkasten_mcp.models.schema import LinkType  # noqa: PLC0415

        zettel_service.create_link(note_a.id, note_b.id, LinkType.REFERENCE)

        result = zettel_service.verify_note(note_a.id)
        assert result["tag_count"] == 2
        assert result["link_count"] == 1

    def test_file_exists_but_not_indexed(self, zettel_service, test_config):
        """Note file on disk but missing from DB returns hint to rebuild."""

        from zettelkasten_mcp.models.schema import Note, NoteType  # noqa: PLC0415

        note_id = "20260101T120000000000000"
        note = Note(
            id=note_id,
            title="Orphan File",
            content="# Orphan File\n\nContent",
            note_type=NoteType.PERMANENT,
        )
        markdown = zettel_service.repository._note_to_markdown(note)  # noqa: SLF001
        notes_dir = test_config.get_absolute_path(test_config.notes_dir)
        (notes_dir / f"{note_id}.md").write_text(markdown, encoding="utf-8")

        result = zettel_service.verify_note(note_id)
        assert result["file_exists"] is True
        assert result["db_indexed"] is False
        assert "hint" in result
        assert "zk_rebuild_index" in result["hint"]

    def test_note_not_found_anywhere(self, zettel_service):
        """Non-existent note ID returns file_exists=False, db_indexed=False."""
        result = zettel_service.verify_note("totally_nonexistent_id_000")
        assert result["file_exists"] is False
        assert result["db_indexed"] is False
        assert result["link_count"] == 0
        assert result["tag_count"] == 0


# ---------------------------------------------------------------------------
# 4. Index Health Dashboard
# ---------------------------------------------------------------------------


class TestGetIndexStatus:
    """Tests for ZettelService.get_index_status."""

    def test_healthy_system(self, zettel_service):
        """No orphans reported when all notes are properly indexed."""
        zettel_service.create_notes_batch(
            [
                {"title": f"Health Note {i}", "content": f"Content {i}"}
                for i in range(5)
            ],
        )
        result = zettel_service.get_index_status()

        assert result["total_notes_filesystem"] == 5
        assert result["total_notes_indexed"] == 5
        assert result["orphaned_files"] == 0
        assert result["orphaned_db_records"] == 0
        assert result["orphaned_file_paths"] == []
        assert result["orphaned_db_ids"] == []

    def test_orphaned_files_detected(self, zettel_service, test_config):
        """Files present on disk but not in DB are counted as orphaned_files."""
        from zettelkasten_mcp.models.schema import Note, NoteType  # noqa: PLC0415

        notes_dir = test_config.get_absolute_path(test_config.notes_dir)

        orphan_ids = []
        for i in range(3):
            note_id = f"20260101T00000{i}000000000"
            note = Note(
                id=note_id,
                title=f"Orphan {i}",
                content=f"# Orphan {i}\n\nContent",
                note_type=NoteType.PERMANENT,
            )
            markdown = zettel_service.repository._note_to_markdown(note)  # noqa: SLF001
            (notes_dir / f"{note_id}.md").write_text(markdown, encoding="utf-8")
            orphan_ids.append(note_id)

        result = zettel_service.get_index_status()
        assert result["orphaned_files"] == 3
        for oid in orphan_ids:
            assert any(oid in p for p in result["orphaned_file_paths"])

    def test_stale_db_records_detected(self, zettel_service, test_config):
        """DB records with no corresponding file are counted as orphaned_db_records."""
        batch_result = zettel_service.create_notes_batch(
            [{"title": f"Stale {i}", "content": f"Content {i}"} for i in range(2)],
        )
        notes_dir = test_config.get_absolute_path(test_config.notes_dir)
        for note_id in batch_result["note_ids"]:
            (notes_dir / f"{note_id}.md").unlink()

        result = zettel_service.get_index_status()
        assert result["orphaned_db_records"] == 2
        for note_id in batch_result["note_ids"]:
            assert note_id in result["orphaned_db_ids"]

    def test_database_size_reported(self, zettel_service):
        """database_size_mb is a non-negative float."""
        zettel_service.create_note(title="Size Test", content="Some content")
        result = zettel_service.get_index_status()
        assert isinstance(result["database_size_mb"], float)
        assert result["database_size_mb"] >= 0.0
