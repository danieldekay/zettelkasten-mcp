"""Tests for SummaryCacheService and calculate_content_hash."""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from zettelkasten_mcp.models.db_models import Base, DBNote, DBNoteSummaryCache
from zettelkasten_mcp.services.summary_cache_service import (
    SummaryCacheService,
    calculate_content_hash,
)


@pytest.fixture
def db_session(tmp_path):
    """In-memory SQLite database for cache tests."""
    db_path = tmp_path / "cache_test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()
    engine.dispose()


def _insert_note(session: Session, note_id: str = "note1") -> DBNote:
    """Insert a minimal DBNote so FK constraints pass."""
    db_note = DBNote(
        id=note_id,
        title="Test Note",
        content="Test content",
        note_type="permanent",
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
        updated_at=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    session.add(db_note)
    session.flush()
    return db_note


class TestCalculateContentHash:
    def test_hash_is_deterministic(self):
        h1 = calculate_content_hash("Title", "Content", ["a", "b"])
        h2 = calculate_content_hash("Title", "Content", ["a", "b"])
        assert h1 == h2

    def test_hash_is_stable_regardless_of_tag_order(self):
        """Tags should be sorted before hashing."""
        h1 = calculate_content_hash("T", "C", ["z", "a", "m"])
        h2 = calculate_content_hash("T", "C", ["a", "m", "z"])
        assert h1 == h2

    def test_hash_differs_on_title_change(self):
        h1 = calculate_content_hash("Title A", "Content", [])
        h2 = calculate_content_hash("Title B", "Content", [])
        assert h1 != h2

    def test_hash_differs_on_content_change(self):
        h1 = calculate_content_hash("Title", "Content A", [])
        h2 = calculate_content_hash("Title", "Content B", [])
        assert h1 != h2

    def test_hash_differs_on_tag_change(self):
        h1 = calculate_content_hash("T", "C", ["ai"])
        h2 = calculate_content_hash("T", "C", ["ml"])
        assert h1 != h2

    def test_hash_is_64_char_hex(self):
        h = calculate_content_hash("Title", "Content", [])
        assert len(h) == 64
        int(h, 16)  # should not raise

    def test_none_tags_treated_as_empty(self):
        h1 = calculate_content_hash("T", "C", None)
        h2 = calculate_content_hash("T", "C", [])
        assert h1 == h2


class TestSummaryCacheService:
    def test_get_from_cache_returns_none_when_empty(self, db_session):
        svc = SummaryCacheService()
        _insert_note(db_session)
        result = svc.get_from_cache(db_session, "note1", "abc123")
        assert result is None

    def test_save_then_get_from_cache_returns_data(self, db_session):
        _insert_note(db_session)
        svc = SummaryCacheService()
        content_hash = calculate_content_hash("Title", "Content", [])
        summary_data = {"summary": "An English summary.", "keywords": ["alpha", "beta"]}

        svc.save_to_cache(db_session, "note1", content_hash, summary_data, "gpt-4")
        db_session.flush()

        result = svc.get_from_cache(db_session, "note1", content_hash)
        assert result is not None
        assert result["summary"] == "An English summary."
        assert result["keywords"] == ["alpha", "beta"]

    def test_cache_miss_on_stale_hash(self, db_session):
        """A hash mismatch should be treated as a cache miss."""
        _insert_note(db_session)
        svc = SummaryCacheService()
        old_hash = "old" * 16
        new_hash = "new" * 16
        svc.save_to_cache(db_session, "note1", old_hash,
                          {"summary": "Old", "keywords": []}, "gpt-4")
        db_session.flush()

        result = svc.get_from_cache(db_session, "note1", new_hash)
        assert result is None

    def test_save_overwrites_existing_entry(self, db_session):
        """Calling save_to_cache twice for the same note should overwrite, not duplicate."""
        _insert_note(db_session)
        svc = SummaryCacheService()
        h = calculate_content_hash("T", "C", [])

        svc.save_to_cache(db_session, "note1", h,
                          {"summary": "First", "keywords": ["x"]}, "gpt-4")
        db_session.flush()
        svc.save_to_cache(db_session, "note1", h,
                          {"summary": "Updated", "keywords": ["y"]}, "gpt-4")
        db_session.flush()

        result = svc.get_from_cache(db_session, "note1", h)
        assert result is not None
        assert result["summary"] == "Updated"
        # Only one row per note
        count = db_session.query(DBNoteSummaryCache).filter_by(note_id="note1").count()
        assert count == 1

    def test_cache_survives_across_sessions(self, tmp_path):
        """Cache entry persisted in one session should be readable in another."""
        db_path = tmp_path / "persist.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)

        svc = SummaryCacheService()
        h = calculate_content_hash("Persistent", "Content", [])

        with session_factory() as s1:
            _insert_note(s1, "note_p")
            svc.save_to_cache(s1, "note_p", h, {"summary": "Persisted", "keywords": []}, "gpt-4")
            s1.commit()

        with session_factory() as s2:
            result = svc.get_from_cache(s2, "note_p", h)
            assert result is not None
            assert result["summary"] == "Persisted"

        engine.dispose()
