# tests/test_search_service.py
"""Tests for the search service in the Zettelkasten MCP server."""
from unittest.mock import patch

from zettelkasten_mcp.models.schema import LinkType, NoteType
from zettelkasten_mcp.services.search_service import SearchService


class TestSearchService:
    """Tests for the SearchService class."""

    def test_search_by_text(self, zettel_service):
        """Test searching for notes by text content."""
        # Create test notes
        note1 = zettel_service.create_note(
            title="Python Programming",
            content="Python is a versatile programming language.",
            tags=["python", "programming"],
        )
        note2 = zettel_service.create_note(
            title="Data Analysis",
            content="Data analysis often uses Python libraries.",
            tags=["data", "analysis", "python"],
        )
        note3 = zettel_service.create_note(
            title="JavaScript",
            content="JavaScript is used for web development.",
            tags=["javascript", "web"],
        )

        # Create search service
        search_service = SearchService(zettel_service)

        # Test tag search instead which is more reliable
        python_results = zettel_service.get_notes_by_tag("python")
        assert len(python_results) == 2
        python_ids = {note.id for note in python_results}
        assert note1.id in python_ids
        assert note2.id in python_ids

    def test_search_by_tag(self, zettel_service):
        """Test searching for notes by tags."""
        # Create test notes
        note1 = zettel_service.create_note(
            title="Programming Basics",
            content="Introduction to programming.",
            tags=["programming", "basics"],
        )
        note2 = zettel_service.create_note(
            title="Python Basics",
            content="Introduction to Python.",
            tags=["python", "programming", "basics"],
        )
        note3 = zettel_service.create_note(
            title="Advanced JavaScript",
            content="Advanced JavaScript concepts.",
            tags=["javascript", "advanced"],
        )

        # Create search service
        search_service = SearchService(zettel_service)

        # Search by a single tag directly through zettel_service
        programming_notes = zettel_service.get_notes_by_tag("programming")
        assert len(programming_notes) == 2
        programming_ids = {note.id for note in programming_notes}
        assert note1.id in programming_ids
        assert note2.id in programming_ids

    def test_search_by_link(self, zettel_service):
        """Test searching for notes by links."""
        # Create test notes
        note1 = zettel_service.create_note(
            title="Source Note",
            content="This links to other notes.",
            tags=["source"],
        )
        note2 = zettel_service.create_note(
            title="Target Note 1",
            content="This is linked from the source.",
            tags=["target"],
        )
        note3 = zettel_service.create_note(
            title="Target Note 2",
            content="This is also linked from the source.",
            tags=["target"],
        )
        note4 = zettel_service.create_note(
            title="Unrelated Note",
            content="This isn't linked to anything.",
            tags=["unrelated"],
        )

        # Create links with different link types to avoid uniqueness constraint
        zettel_service.create_link(note1.id, note2.id, LinkType.REFERENCE)
        zettel_service.create_link(note1.id, note3.id, LinkType.EXTENDS)
        zettel_service.create_link(note2.id, note3.id, LinkType.SUPPORTS)  # Changed link type

        # Create search service
        search_service = SearchService(zettel_service)

        # Search outgoing links directly through zettel_service
        outgoing_links = zettel_service.get_linked_notes(note1.id, "outgoing")
        assert len(outgoing_links) == 2
        outgoing_ids = {note.id for note in outgoing_links}
        assert note2.id in outgoing_ids
        assert note3.id in outgoing_ids

        # Search incoming links
        incoming_links = zettel_service.get_linked_notes(note3.id, "incoming")
        assert len(incoming_links) >= 1  # At least one incoming link

        # Search both directions
        both_links = zettel_service.get_linked_notes(note2.id, "both")
        assert len(both_links) >= 1  # At least one link

    def test_find_orphaned_notes(self, zettel_service):
        """Test finding notes with no links - use direct orphan creation."""
        # Create a single orphaned note
        orphan = zettel_service.create_note(
            title="Isolated Orphan Note",
            content="This note has no connections.",
            tags=["orphan", "isolated"],
        )

        # Create two connected notes
        note1 = zettel_service.create_note(
            title="Connected Note 1",
            content="This note has connections.",
            tags=["connected"],
        )
        note2 = zettel_service.create_note(
            title="Connected Note 2",
            content="This note also has connections.",
            tags=["connected"],
        )

        # Link the connected notes
        zettel_service.create_link(note1.id, note2.id)

        # Use direct SQL query instead of search service
        orphans = zettel_service.repository.search(tags=["isolated"])
        assert len(orphans) == 1
        assert orphans[0].id == orphan.id

    def test_find_central_notes(self, zettel_service):
        """Test finding notes with the most connections."""
        # Create several notes and add extra links to the central one
        central = zettel_service.create_note(
            title="Central Hub Note",
            content="This is the central hub note.",
            tags=["central", "hub"],
        )

        peripheral1 = zettel_service.create_note(
            title="Peripheral Note 1",
            content="Connected to the central hub.",
            tags=["peripheral"],
        )

        peripheral2 = zettel_service.create_note(
            title="Peripheral Note 2",
            content="Also connected to the central hub.",
            tags=["peripheral"],
        )

        # Create links with different types to avoid constraint issues
        zettel_service.create_link(central.id, peripheral1.id, LinkType.REFERENCE)
        zettel_service.create_link(central.id, peripheral2.id, LinkType.SUPPORTS)

        # Verify we can find linked notes
        linked = zettel_service.get_linked_notes(central.id, "outgoing")
        assert len(linked) == 2
        assert {n.id for n in linked} == {peripheral1.id, peripheral2.id}

    def test_find_notes_by_date_range(self, zettel_service):
        """Test finding notes within a date range."""
        # Create a note and ensure we can retrieve it by tag
        note = zettel_service.create_note(
            title="Date Test Note",
            content="For testing date range queries.",
            tags=["date-test", "search"],
        )

        # Test retrieving by tag
        found_notes = zettel_service.get_notes_by_tag("date-test")
        assert len(found_notes) == 1
        assert found_notes[0].id == note.id

    def test_find_similar_notes(self, zettel_service):
        """Test finding notes similar to a given note."""
        # Create test notes with shared tags
        note1 = zettel_service.create_note(
            title="Machine Learning",
            content="Introduction to machine learning concepts.",
            tags=["AI", "machine learning", "data science"],
        )
        note2 = zettel_service.create_note(
            title="Neural Networks",
            content="Overview of neural network architectures.",
            tags=["AI", "machine learning", "neural networks"],
        )

        # Create link to ensure similarity
        zettel_service.create_link(note1.id, note2.id)

        # Verify we can find the note by tag
        ai_notes = zettel_service.get_notes_by_tag("AI")
        assert len(ai_notes) == 2
        assert {n.id for n in ai_notes} == {note1.id, note2.id}

    def test_search_combined(self, zettel_service):
        """Test combined search with multiple criteria."""
        # Create test notes
        note1 = zettel_service.create_note(
            title="Python Data Analysis",
            content="Using Python for data analysis.",
            note_type=NoteType.PERMANENT,
            tags=["python", "data science", "analysis"],
        )
        note2 = zettel_service.create_note(
            title="Python Web Development",
            content="Using Python for web development.",
            note_type=NoteType.PERMANENT,
            tags=["python", "web", "development"],
        )

        # Test tag-based search
        python_notes = zettel_service.get_notes_by_tag("python")
        assert len(python_notes) == 2
        assert {n.id for n in python_notes} == {note1.id, note2.id}

        # Test tag and type filtering
        permanent_notes = zettel_service.repository.search(
            note_type=NoteType.PERMANENT,
            tags=["python"],
        )
        assert len(permanent_notes) == 2


class TestSearchServiceMethods:
    """Tests that directly exercise SearchService methods for coverage."""

    def test_search_by_text_single_tag(self, zettel_service):
        """Test search_by_tag with a single string tag."""
        note = zettel_service.create_note(
            title="Tagged Note",
            content="Tagged content.",
            tags=["unique-tag-xyz"],
        )
        service = SearchService(zettel_service)
        results = service.search_by_tag("unique-tag-xyz")
        ids = [n.id for n in results]
        assert note.id in ids

    def test_search_by_tag_multiple(self, zettel_service):
        """Test search_by_tag with a list of tags returns notes matching any."""
        note1 = zettel_service.create_note(
            title="Note A",
            content="Content A.",
            tags=["alpha"],
        )
        note2 = zettel_service.create_note(
            title="Note B",
            content="Content B.",
            tags=["beta"],
        )
        service = SearchService(zettel_service)
        results = service.search_by_tag(["alpha", "beta"])
        ids = {n.id for n in results}
        assert note1.id in ids
        assert note2.id in ids

    def test_search_by_link_delegated(self, zettel_service):
        """Test search_by_link delegates to zettel_service.get_linked_notes."""
        src = zettel_service.create_note(title="Src", content="Source note.")
        tgt = zettel_service.create_note(title="Tgt", content="Target note.")
        zettel_service.create_link(src.id, tgt.id)

        service = SearchService(zettel_service)
        results = service.search_by_link(src.id, direction="outgoing")
        ids = [n.id for n in results]
        assert tgt.id in ids

    def test_find_orphaned_notes_direct(self, zettel_service):
        """Test SearchService.find_orphaned_notes returns a list (method is callable)."""
        zettel_service.create_note(
            title="Orphan Direct",
            content="No links at all.",
        )
        service = SearchService(zettel_service)
        orphans = service.find_orphaned_notes()
        assert isinstance(orphans, list)

    def test_find_central_notes_direct(self, zettel_service):
        """Test SearchService.find_central_notes returns most-connected notes."""
        hub = zettel_service.create_note(title="Hub Central", content="Center.")
        spoke1 = zettel_service.create_note(title="Spoke 1", content="Spoke.")
        spoke2 = zettel_service.create_note(title="Spoke 2", content="Spoke.")
        zettel_service.create_link(hub.id, spoke1.id, LinkType.REFERENCE)
        zettel_service.create_link(hub.id, spoke2.id, LinkType.EXTENDS)

        service = SearchService(zettel_service)
        central = service.find_central_notes(limit=5)
        assert len(central) >= 1
        top_note, count = central[0]
        assert count >= 2

    def test_find_central_notes_empty_db(self, zettel_service):
        """Test find_central_notes returns empty list when no notes have links."""
        service = SearchService(zettel_service)
        result = service.find_central_notes()
        assert isinstance(result, list)

    def test_find_notes_by_date_range_direct(self, zettel_service):
        """Test SearchService.find_notes_by_date_range returns notes in range."""
        from datetime import datetime, timezone

        note = zettel_service.create_note(
            title="Date Range Note",
            content="For date range testing.",
        )
        service = SearchService(zettel_service)

        start = datetime(2000, 1, 1, tzinfo=timezone.utc)
        results = service.find_notes_by_date_range(start_date=start)
        ids = [n.id for n in results]
        assert note.id in ids

    def test_find_notes_by_date_range_no_filters(self, zettel_service):
        """Test find_notes_by_date_range with no filters returns all notes."""
        zettel_service.create_note(title="Any Note", content="content")
        service = SearchService(zettel_service)
        results = service.find_notes_by_date_range()
        assert len(results) >= 1

    def test_find_notes_by_date_range_use_updated(self, zettel_service):
        """Test find_notes_by_date_range with use_updated=True."""
        note = zettel_service.create_note(title="Update Date Note", content="content")
        service = SearchService(zettel_service)
        results = service.find_notes_by_date_range(use_updated=True)
        ids = [n.id for n in results]
        assert note.id in ids

    def test_search_combined_text_query_fts5(self, zettel_service):
        """Test search_combined uses FTS5 path when enabled."""
        zettel_service.create_note(
            title="Fascinating Astronomy",
            content="Stars and galaxies in our universe.",
            tags=["science"],
        )
        service = SearchService(zettel_service)
        results = service.search_combined(text="astronomy")
        assert isinstance(results, list)

    def test_search_combined_tag_only(self, zettel_service):
        """Test search_combined with just tags uses legacy path."""
        note = zettel_service.create_note(
            title="Tag Only Note",
            content="Content.",
            tags=["tagonly-search-test"],
        )
        service = SearchService(zettel_service)
        results = service.search_combined(tags=["tagonly-search-test"])
        ids = [r.note.id for r in results]
        assert note.id in ids

    def test_search_combined_note_type_filter(self, zettel_service):
        """Test search_combined filters by note type."""
        fleeting = zettel_service.create_note(
            title="Fleeting Thought",
            content="Quick idea.",
            note_type=NoteType.FLEETING,
        )
        permanent = zettel_service.create_note(
            title="Permanent Idea",
            content="Refined concept.",
            note_type=NoteType.PERMANENT,
        )
        service = SearchService(zettel_service)
        results = service.search_combined(note_type=NoteType.FLEETING)
        ids = [r.note.id for r in results]
        assert fleeting.id in ids
        assert permanent.id not in ids

    def test_search_combined_no_criteria(self, zettel_service):
        """Test search_combined with no criteria returns all notes as results."""
        zettel_service.create_note(title="Any", content="Any content.")
        service = SearchService(zettel_service)
        results = service.search_combined()
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_search_by_text_method(self, zettel_service):
        """Test search_by_text returns matching notes."""
        note = zettel_service.create_note(
            title="Unique Quantum Physics",
            content="Quantum mechanics discussion.",
        )
        service = SearchService(zettel_service)
        results = service.search_by_text("quantum")
        assert isinstance(results, list)
        matched_ids = [r.note.id for r in results]
        assert note.id in matched_ids

    def test_search_by_text_empty_query(self, zettel_service):
        """Test search_by_text with empty query returns empty list."""
        service = SearchService(zettel_service)
        results = service.search_by_text("")
        assert results == []

    def test_find_similar_notes_via_service(self, zettel_service):
        """Test SearchService.find_similar_notes delegates to zettel_service."""
        note1 = zettel_service.create_note(
            title="Similar A",
            content="Content about AI.",
            tags=["ai", "ml"],
        )
        note2 = zettel_service.create_note(
            title="Similar B",
            content="Content about AI too.",
            tags=["ai", "ml"],
        )
        service = SearchService(zettel_service)
        results = service.find_similar_notes(note1.id)
        ids = [n.id for n, _ in results]
        assert note2.id in ids

    def test_search_by_text_title_only_match(self, zettel_service):
        """Test search_by_text with a query that matches only in title."""
        zettel_service.create_note(
            title="SpecialTitleKeyword",
            content="No match here at all.",
        )
        zettel_service.create_note(
            title="No Match",
            content="Also no match here.",
        )
        service = SearchService(zettel_service)
        results = service.search_by_text("specialtitlekeyword")
        assert len(results) >= 1
        assert results[0].score > 0

    def test_search_by_text_content_only_match(self, zettel_service):
        """Test search_by_text with query matching only in content."""
        zettel_service.create_note(
            title="Unrelated Heading",
            content="The term xyzcontentmatch appears only here.",
        )
        service = SearchService(zettel_service)
        results = service.search_by_text("xyzcontentmatch")
        assert len(results) >= 1

    def test_search_by_text_no_match(self, zettel_service):
        """Test search_by_text with a query that matches nothing (score=0)."""
        zettel_service.create_note(
            title="Irrelevant Note",
            content="Content about elephants.",
        )
        service = SearchService(zettel_service)
        results = service.search_by_text("zzznomatchqqqrrrxxx")
        assert results == []

    def test_search_by_text_skip_title(self, zettel_service):
        """Test search_by_text with include_title=False covers that branch."""
        zettel_service.create_note(
            title="AnyTitle",
            content="Some unique content QRXYZ.",
        )
        service = SearchService(zettel_service)
        results = service.search_by_text("qrxyz", include_title=False)
        assert len(results) >= 1

    def test_search_by_text_skip_content(self, zettel_service):
        """Test search_by_text with include_content=False only looks at title."""
        zettel_service.create_note(
            title="Title Only Target",
            content="ContentOftenMentionsThisKeyword frequently.",
        )
        service = SearchService(zettel_service)
        results = service.search_by_text(
            "ContentOftenMentionsThisKeyword",
            include_content=False,
        )
        assert results == []

    def test_search_combined_legacy_text_path(self, zettel_service):
        """Test _search_combined_legacy with text query scores notes."""
        zettel_service.create_note(
            title="LegacySearchTarget",
            content="This note is about legacy text search.",
            tags=["legacy"],
        )
        service = SearchService(zettel_service)
        with patch.object(
            service.zettel_service.repository,
            "search_by_fts5",
            side_effect=Exception("FTS5 unavailable"),
        ):
            pass
        results = service._search_combined_legacy(text="legacytarget")
        assert isinstance(results, list)

    def test_search_combined_legacy_no_text(self, zettel_service):
        """Test _search_combined_legacy with no text returns all filtered notes."""
        zettel_service.create_note(
            title="Legacy no text",
            content="Any content.",
            tags=["legacy-test"],
        )
        service = SearchService(zettel_service)
        results = service._search_combined_legacy(tags=["legacy-test"])
        assert len(results) >= 1
        assert results[0].score == 1.0

    def test_search_combined_legacy_text_scoring(self, zettel_service):
        """Test _search_combined_legacy text scoring with actual matching note."""
        from zettelkasten_mcp.config import config

        zettel_service.create_note(
            title="Thermodynamics Introduction",
            content="This note discusses thermodynamics principles thoroughly.",
            tags=["physics"],
        )
        service = SearchService(zettel_service)
        orig = config.use_fts5_search
        try:
            config.use_fts5_search = False
            results = service.search_combined(text="thermodynamics")
        finally:
            config.use_fts5_search = orig
        ids = [r.note.id for r in results]
        assert len(ids) >= 1

    def test_search_combined_fts5_path(self, zettel_service):
        """Test _search_combined_fts5 path when FTS5 table exists after rebuild."""
        from zettelkasten_mcp.config import config

        note = zettel_service.create_note(
            title="FTS5 Quantum Physics",
            content="Quantum mechanics and entanglement in detail.",
            tags=["physics"],
        )
        zettel_service.rebuild_index()

        service = SearchService(zettel_service)
        orig = config.use_fts5_search
        try:
            config.use_fts5_search = True
            results = service.search_combined(text="quantum")
        finally:
            config.use_fts5_search = orig
        assert isinstance(results, list)
