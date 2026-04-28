"""Tests for the FTS5 auto-OR fallback in SearchService."""

import datetime
from unittest.mock import MagicMock

from zettelkasten_mcp.models.schema import Note, NoteType
from zettelkasten_mcp.services.search_service import SearchResult, SearchService


def _make_note(note_id: str, title: str, content: str) -> Note:
    return Note(
        id=note_id,
        title=title,
        content=content,
        note_type=NoteType.PERMANENT,
        tags=[],
        links=[],
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
        updated_at=datetime.datetime.now(tz=datetime.timezone.utc),
    )


class TestAutoOrFallback:
    """Verify _search_combined_fts5 triggers OR retry when the initial query returns nothing."""

    def _make_service(self, fts5_side_effects):
        """Return a SearchService whose repository.search_by_fts5 uses the given side effects."""
        service = MagicMock(spec=SearchService)
        service.zettel_service = MagicMock()
        service.zettel_service.repository = MagicMock()
        service.zettel_service.repository.search_by_fts5 = MagicMock(
            side_effect=fts5_side_effects,
        )
        service.zettel_service.get_note = MagicMock(return_value=None)
        # Delegate to the real implementation
        service._search_combined_fts5 = (  # noqa: SLF001
            SearchService._search_combined_fts5.__get__(service)  # noqa: SLF001
        )
        return service

    def test_or_fallback_triggered_when_strict_returns_empty(self):
        """When AND search returns nothing and query is multi-word, OR retry fires."""
        note = _make_note("note1", "Partial Match", "Content about something")
        # First call (AND) → empty; second call (OR) → one result
        service = self._make_service([[], [("note1", -0.5, "snippet")]])
        service.zettel_service.get_note.return_value = note

        results = service._search_combined_fts5("partial match")  # noqa: SLF001

        assert service.zettel_service.repository.search_by_fts5.call_count == 2
        assert len(results) == 1
        assert results[0].fallback_applied is True

    def test_or_fallback_not_triggered_for_single_word(self):
        """Single-word queries must not trigger the OR retry even when results are empty."""
        service = self._make_service([[]])

        results = service._search_combined_fts5("python")  # noqa: SLF001

        assert service.zettel_service.repository.search_by_fts5.call_count == 1
        assert results == []

    def test_or_fallback_not_triggered_when_strict_returns_results(self):
        """If AND search already returned results, the fallback must not fire."""
        note = _make_note("note1", "Direct Hit", "Content")
        service = self._make_service([[("note1", -0.8, "Direct Hit snippet")]])
        service.zettel_service.get_note.return_value = note

        results = service._search_combined_fts5("direct hit")  # noqa: SLF001

        assert service.zettel_service.repository.search_by_fts5.call_count == 1
        assert len(results) == 1
        assert results[0].fallback_applied is False

    def test_fallback_applied_false_on_successful_strict_search(self):
        """All results from a successful strict search must have fallback_applied=False."""
        note = _make_note("note1", "Title", "Content")
        service = self._make_service([[("note1", -0.9, "snippet")]])
        service.zettel_service.get_note.return_value = note

        results = service._search_combined_fts5("machine learning")  # noqa: SLF001

        # Two words but strict search returned results — no fallback
        assert service.zettel_service.repository.search_by_fts5.call_count == 1
        assert results[0].fallback_applied is False

    def test_or_query_joins_words_correctly(self):
        """The OR retry query should join each word with ' OR '."""
        service = self._make_service([[], []])

        service._search_combined_fts5("word1 word2 word3")  # noqa: SLF001

        calls = service.zettel_service.repository.search_by_fts5.call_args_list
        assert calls[1][1]["query"] == "word1 OR word2 OR word3" or \
               calls[1][0][0] == "word1 OR word2 OR word3"

    def test_fallback_result_is_empty_when_or_also_returns_nothing(self):
        """If both strict and OR return empty, the final result should be empty."""
        service = self._make_service([[], []])

        results = service._search_combined_fts5("foo bar")  # noqa: SLF001

        assert results == []
        assert service.zettel_service.repository.search_by_fts5.call_count == 2


class TestSearchResultDataclass:
    def test_fallback_applied_defaults_to_false(self):
        """SearchResult.fallback_applied should default to False."""
        note = _make_note("n1", "T", "C")
        result = SearchResult(note=note, score=1.0, matched_terms=set(), matched_context="")
        assert result.fallback_applied is False

    def test_fallback_applied_can_be_true(self):
        """SearchResult.fallback_applied can be set to True explicitly."""
        note = _make_note("n1", "T", "C")
        result = SearchResult(
            note=note, score=1.0, matched_terms=set(), matched_context="", fallback_applied=True,
        )
        assert result.fallback_applied is True
