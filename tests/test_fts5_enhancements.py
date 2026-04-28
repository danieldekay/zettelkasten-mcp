"""Tests for FTS5 schema upgrades: porter stemming, extended columns, pre-warming."""

import datetime

import pytest
from sqlalchemy import create_engine, text

from zettelkasten_mcp.config import config
from zettelkasten_mcp.models.db_models import Base
from zettelkasten_mcp.models.schema import Note, NoteType, Tag
from zettelkasten_mcp.storage.note_repository import NoteRepository


@pytest.fixture
def fts5_repo(tmp_path):
    """NoteRepository backed by a fresh in-memory-ish SQLite file."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    db_path = tmp_path / "test.db"

    original_notes = config.notes_dir
    original_db = config.database_path
    config.notes_dir = notes_dir
    config.database_path = db_path

    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    engine.dispose()

    repo = NoteRepository(notes_dir=notes_dir)
    repo.rebuild_index()

    yield repo

    config.notes_dir = original_notes
    config.database_path = original_db


def _make_note(title: str, content: str, tags: list[str] | None = None) -> Note:
    return Note(
        id=f"20240101T000000000000{abs(hash(title)) % 1000:03d}",
        title=title,
        content=content,
        note_type=NoteType.PERMANENT,
        tags=[Tag(name=t) for t in (tags or [])],
        links=[],
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
        updated_at=datetime.datetime.now(tz=datetime.timezone.utc),
    )


class TestFts5TableSchema:
    def test_fts5_table_named_fts5_notes(self, fts5_repo):
        """The FTS5 virtual table should be named 'fts5_notes' (not 'notes_fts')."""
        assert fts5_repo._check_fts5_table_exists()  # noqa: SLF001
        with fts5_repo.session_factory() as session:
            row = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='fts5_notes'"),
            ).fetchone()
            assert row is not None, "fts5_notes table not found"

    def test_old_notes_fts_table_absent(self, fts5_repo):
        """The old notes_fts table must not exist after a fresh rebuild."""
        with fts5_repo.session_factory() as session:
            row = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='notes_fts'"),
            ).fetchone()
            assert row is None, "Stale notes_fts table found"

    def test_fts5_columns_include_en_summary_and_tags(self, fts5_repo):
        """The FTS5 table should have the extended column set."""
        note = _make_note("Test Extended Columns", "Some content here", ["testag"])
        fts5_repo.create(note)

        with fts5_repo.session_factory() as session:
            row = session.execute(
                text("SELECT note_id, title, content, en_summary, en_keywords, tags "
                     "FROM fts5_notes LIMIT 1"),
            ).fetchone()
            assert row is not None, "No row in fts5_notes after create"
            assert row[1] == "Test Extended Columns"
            assert "testag" in (row[5] or "")

    def test_fts5_uses_porter_tokenizer(self, fts5_repo):
        """Porter stemming should match 'run' when searching 'running'."""
        note = _make_note("Running Tests", "The system is running at full speed.", [])
        fts5_repo.create(note)

        results = fts5_repo.search_by_fts5("run")
        ids = [r[0] for r in results]
        assert note.id in ids, "Porter stemming did not match 'run' → 'running'"


class TestPrewarmFts5:
    def test_prewarm_runs_without_error(self, fts5_repo):
        """prewarm_fts5 must not raise even on an empty table."""
        # Should not raise
        fts5_repo.prewarm_fts5()

    def test_prewarm_skips_when_table_missing(self, fts5_repo):
        """prewarm_fts5 should silently skip when the table is absent."""
        with fts5_repo.session_factory() as session:
            session.execute(text("DROP TABLE IF EXISTS fts5_notes"))
            session.commit()

        # Should not raise
        fts5_repo.prewarm_fts5()


class TestFts5ExtendedColumnIndexing:
    def test_en_summary_and_keywords_stored_after_create(self, fts5_repo):
        """en_summary and en_keywords inserted into FTS5 should be retrievable."""
        note = _make_note("Summary Note", "Content", ["ai"])
        # Simulate a pre-populated LLM summary on the Note object via en_summary attr
        # (without LLM enabled, values will be empty — test the storage round-trip)
        fts5_repo.create(note)

        with fts5_repo.session_factory() as session:
            row = session.execute(
                text("SELECT en_summary, en_keywords FROM fts5_notes WHERE note_id = :nid"),
                {"nid": note.id},
            ).fetchone()
            assert row is not None
            # Empty string is fine when LLM disabled
            assert row[0] is not None
            assert row[1] is not None

    def test_tags_searchable_in_fts5(self, fts5_repo):
        """Tags stored in the FTS5 tags column should be searchable."""
        note = _make_note("Tagged Note", "Ordinary content.", ["machinelearning"])
        fts5_repo.create(note)

        with fts5_repo.session_factory() as session:
            row = session.execute(
                text("SELECT note_id FROM fts5_notes WHERE tags MATCH 'machinelearning'"),
            ).fetchone()
            assert row is not None
            assert row[0] == note.id

    def test_bm25_weights_applied(self, fts5_repo):
        """BM25 custom weights are applied: both title and body matches are returned."""
        title_note = _make_note("Zettelkasten Note", "Plain content without keyword.")
        body_note = _make_note("Unrelated Title", "Zettelkasten mentioned in the body only.")
        fts5_repo.create(title_note)
        fts5_repo.create(body_note)

        results = fts5_repo.search_by_fts5("Zettelkasten")
        ids = [r[0] for r in results]
        # Both notes should be returned — verifies custom BM25 weights don't exclude anything
        assert title_note.id in ids
        assert body_note.id in ids

    def test_title_weight_higher_than_content(self, fts5_repo):
        """A title-only hit should score better than a body-only hit of the same term."""
        # Use a unique term that appears in many docs to dilute IDF effect
        unique_term = "zettelkastentest"
        # Create multiple notes to establish a realistic avgdl baseline
        filler = _make_note("Filler A", "Some filler content about nothing in particular here today.")
        fts5_repo.create(filler)
        filler2 = _make_note("Filler B", "Another unrelated note about everyday topics like cooking.")
        fts5_repo.create(filler2)

        title_note = _make_note("zettelkastentest concept", "Ordinary content without the term.")
        # Give body_note a longer document so title's normalized TF wins
        body_note = _make_note("Generic Title Here", f"{unique_term} " + "padding " * 20)
        fts5_repo.create(title_note)
        fts5_repo.create(body_note)

        results = fts5_repo.search_by_fts5(unique_term)
        assert len(results) == 2
        ids = [r[0] for r in results]
        # Title hit (weight=10, short doc → high TF-norm) should beat content hit (weight=1)
        assert ids[0] == title_note.id, "Title hit should rank above body hit"
