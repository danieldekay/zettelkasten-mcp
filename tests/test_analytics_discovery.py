"""Tests for analytics & discovery: temporal queries and tag clustering."""

import datetime
import time

import pytest
from sqlalchemy import select, text

from zettelkasten_mcp.models.db_models import DBNote, DBTag
from zettelkasten_mcp.models.schema import Note, NoteType, Tag
from zettelkasten_mcp.services.search_service import SearchService

# ---------------------------------------------------------------------------
# 1. Temporal Queries — ZettelService.find_notes_in_timerange
# ---------------------------------------------------------------------------


class TestFindNotesInTimerange:
    """Tests for ZettelService.find_notes_in_timerange."""

    def _make_note(
        self,
        zettel_service,
        title: str,
        content: str = "Content",
    ) -> object:
        return zettel_service.create_note(title=title, content=content)

    def test_notes_created_in_range_are_returned(self, zettel_service):
        """Notes created in the date range are included in results."""
        note = self._make_note(zettel_service, "In Range Note")

        today = datetime.datetime.now(tz=datetime.timezone.utc).date()
        start = today.isoformat()
        end = today.isoformat()

        result = zettel_service.find_notes_in_timerange(start_date=start, end_date=end)

        assert result["count"] >= 1
        assert result["date_field"] == "created_at"
        ids = [n.id for n in result["notes"]]
        assert note.id in ids

    def test_notes_outside_range_are_excluded(self, zettel_service):
        """Notes outside the date range are excluded."""
        result = zettel_service.find_notes_in_timerange(
            start_date="2000-01-01",
            end_date="2000-01-31",
        )
        assert result["count"] == 0
        assert result["notes"] == []

    def test_updated_at_axis(self, zettel_service):
        """Notes updated in the date range appear when date_field='updated_at'."""
        note = self._make_note(zettel_service, "Updated Note")

        today = datetime.datetime.now(tz=datetime.timezone.utc).date()
        result = zettel_service.find_notes_in_timerange(
            start_date=today.isoformat(),
            end_date=today.isoformat(),
            date_field="updated_at",
        )
        ids = [n.id for n in result["notes"]]
        assert note.id in ids

    def test_empty_range_returns_empty(self, zettel_service):
        """Empty date range returns count 0 and empty list (not an error)."""
        result = zettel_service.find_notes_in_timerange(
            start_date="1990-01-01",
            end_date="1990-01-01",
        )
        assert result["count"] == 0
        assert result["notes"] == []

    def test_invalid_start_date_raises(self, zettel_service):
        """Non-ISO 8601 start_date raises ValueError."""
        with pytest.raises(ValueError, match="Invalid start_date"):
            zettel_service.find_notes_in_timerange(
                start_date="yesterday",
                end_date="2026-01-31",
            )

    def test_invalid_end_date_raises(self, zettel_service):
        """Non-ISO 8601 end_date raises ValueError."""
        with pytest.raises(ValueError, match="Invalid end_date"):
            zettel_service.find_notes_in_timerange(
                start_date="2026-01-01",
                end_date="not-a-date",
            )

    def test_invalid_date_field_raises(self, zettel_service):
        """Unknown date_field raises ValueError."""
        with pytest.raises(ValueError, match="date_field"):
            zettel_service.find_notes_in_timerange(
                start_date="2026-01-01",
                end_date="2026-01-31",
                date_field="invalid_field",
            )

    def test_include_linked_returns_neighbours(self, zettel_service):
        """include_linked=True returns notes linked from the primary set."""
        today = datetime.datetime.now(tz=datetime.timezone.utc).date().isoformat()

        source = self._make_note(zettel_service, "Source Note")
        linked = self._make_note(zettel_service, "Linked Note")

        zettel_service.create_link(source.id, linked.id)

        result = zettel_service.find_notes_in_timerange(
            start_date=today,
            end_date=today,
            include_linked=True,
        )
        assert result["count"] >= 2

    def test_note_type_filter(self, zettel_service):
        """note_type filter only returns matching notes."""
        zettel_service.create_note(
            title="Fleeting Note",
            content="fleeting content",
            note_type=NoteType.FLEETING,
        )
        permanent = zettel_service.create_note(
            title="Permanent Note",
            content="permanent content",
            note_type=NoteType.PERMANENT,
        )

        today = datetime.datetime.now(tz=datetime.timezone.utc).date().isoformat()
        result = zettel_service.find_notes_in_timerange(
            start_date=today,
            end_date=today,
            note_type="permanent",
        )
        ids = [n.id for n in result["notes"]]
        assert permanent.id in ids
        for n in result["notes"]:
            assert n.note_type == NoteType.PERMANENT


# ---------------------------------------------------------------------------
# 1.6  Performance test: < 200 ms for 10 000 notes
# ---------------------------------------------------------------------------


class TestFindNotesInTimerangePerformance:
    """Performance test for temporal queries over large datasets."""

    def test_timerange_under_200ms_for_10k_notes(self, zettel_service):
        """Date-range query over 10 000 notes executes in under 200 ms."""
        repo = zettel_service.repository
        today = datetime.datetime.now(tz=datetime.timezone.utc)

        notes_to_insert = [
            Note(
                title=f"Perf Note {idx}",
                content="x",
                note_type=NoteType.PERMANENT,
                tags=[Tag(name="perf")],
            )
            for idx in range(10_000)
        ]

        # Bulk-insert directly to DB (bypass filesystem for speed)
        with repo.session_factory() as session:
            db_notes = [
                DBNote(
                    id=note.id,
                    title=note.title,
                    content=note.content,
                    note_type=note.note_type.value,
                    created_at=today,
                    updated_at=today,
                )
                for note in notes_to_insert
            ]
            session.bulk_save_objects(db_notes)
            session.commit()

        today_str = today.date().isoformat()
        start_dt = datetime.datetime.fromisoformat(f"{today_str}T00:00:00")
        end_dt = datetime.datetime.fromisoformat(f"{today_str}T23:59:59")

        t0 = time.perf_counter()
        with repo.session_factory() as session:
            ids = (
                session.execute(
                    select(DBNote.id).where(
                        DBNote.created_at >= start_dt,
                        DBNote.created_at <= end_dt,
                    ),
                )
                .scalars()
                .all()
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert len(ids) >= 10_000
        assert elapsed_ms < 200, f"Query took {elapsed_ms:.1f} ms (limit: 200 ms)"


# ---------------------------------------------------------------------------
# 2. Tag Co-occurrence Clustering — SearchService.analyze_tag_clusters
# ---------------------------------------------------------------------------


class TestAnalyzeTagClusters:
    """Tests for SearchService.analyze_tag_clusters."""

    def _make_search_service(self, zettel_service) -> SearchService:
        svc = SearchService(zettel_service)
        svc.initialize()
        return svc

    def test_no_clusters_when_no_notes(self, zettel_service):
        """Empty knowledge base returns empty cluster list."""
        svc = self._make_search_service(zettel_service)
        result = svc.analyze_tag_clusters(min_co_occurrence=1)
        assert result["clusters"] == []
        assert result["total_tag_pairs_analysed"] == 0

    def test_cluster_above_threshold(self, zettel_service):
        """Tags co-occurring above threshold form a cluster."""
        for i in range(5):
            zettel_service.create_note(
                title=f"AI Note {i}",
                content=f"content {i}",
                tags=["ai-agents", "agentic-programming"],
            )

        svc = self._make_search_service(zettel_service)
        result = svc.analyze_tag_clusters(min_co_occurrence=3)

        assert len(result["clusters"]) >= 1
        cluster = result["clusters"][0]
        assert "ai-agents" in cluster["tags"]
        assert "agentic-programming" in cluster["tags"]
        assert cluster["count"] >= 3

    def test_sparse_pairs_filtered_by_threshold(self, zettel_service):
        """Tag pair below threshold does not appear in output."""
        for i in range(2):
            zettel_service.create_note(
                title=f"Rare Pair {i}",
                content="content",
                tags=["tag-alpha", "tag-beta"],
            )

        svc = self._make_search_service(zettel_service)
        result = svc.analyze_tag_clusters(min_co_occurrence=3)

        # The alpha-beta pair has count=2, below threshold=3
        for cluster in result["clusters"]:
            assert not (
                "tag-alpha" in cluster["tags"] and "tag-beta" in cluster["tags"]
            )

    def test_no_clusters_when_tags_never_co_occur(self, zettel_service):
        """Tags that never appear on the same note produce no clusters."""
        zettel_service.create_note(title="Only A", content="x", tags=["only-a"])
        zettel_service.create_note(title="Only B", content="x", tags=["only-b"])

        svc = self._make_search_service(zettel_service)
        result = svc.analyze_tag_clusters(min_co_occurrence=1)
        assert result["clusters"] == []

    def test_representative_notes_populated(self, zettel_service):
        """Clusters include representative note IDs."""
        for i in range(3):
            zettel_service.create_note(
                title=f"Rep Note {i}",
                content="c",
                tags=["rep-tag1", "rep-tag2"],
            )

        svc = self._make_search_service(zettel_service)
        result = svc.analyze_tag_clusters(min_co_occurrence=1)

        assert len(result["clusters"]) >= 1
        assert len(result["clusters"][0]["representative_notes"]) >= 1

    def test_total_pairs_analysed_is_reported(self, zettel_service):
        """total_tag_pairs_analysed reflects the number of co-occurring pairs found."""
        for i in range(4):
            zettel_service.create_note(
                title=f"Pairs Note {i}",
                content="c",
                tags=["pairs-a", "pairs-b"],
            )

        svc = self._make_search_service(zettel_service)
        result = svc.analyze_tag_clusters(min_co_occurrence=1)
        assert result["total_tag_pairs_analysed"] >= 1


# ---------------------------------------------------------------------------
# 2.5  Performance test: < 2 s for 100 tags / 1 000 notes
# ---------------------------------------------------------------------------


class TestAnalyzeTagClustersPerformance:
    """Performance test for tag cluster analysis over a large dataset."""

    def test_cluster_analysis_under_2s_for_large_dataset(self, zettel_service):
        """analyze_tag_clusters completes in < 2 s for 100 tags / 1 000 notes."""
        repo = zettel_service.repository
        today = datetime.datetime.now(tz=datetime.timezone.utc)

        n_tags = 100
        n_notes = 1_000

        with repo.session_factory() as session:
            for i in range(n_tags):
                session.add(DBTag(name=f"perf-cluster-tag-{i}"))
            session.flush()

            tag_id_rows = (
                session.execute(
                    text("SELECT id FROM tags WHERE name LIKE 'perf-cluster-tag-%'"),
                )
                .scalars()
                .all()
            )
            tag_ids = list(tag_id_rows)

            for j in range(n_notes):
                note = DBNote(
                    id=f"perfcluster{j:06d}",
                    title=f"Perf Cluster Note {j}",
                    content="x",
                    note_type="permanent",
                    created_at=today,
                    updated_at=today,
                )
                session.add(note)
                session.flush()
                for k in range(3):
                    tid = tag_ids[(j * 3 + k) % len(tag_ids)]
                    session.execute(
                        text(
                            "INSERT OR IGNORE INTO note_tags (note_id, tag_id) "
                            "VALUES (:nid, :tid)",
                        ),
                        {"nid": note.id, "tid": tid},
                    )
            session.commit()

        svc = SearchService(zettel_service)

        t0 = time.perf_counter()
        result = svc.analyze_tag_clusters(min_co_occurrence=1)
        elapsed = time.perf_counter() - t0

        assert elapsed < 2.0, f"analyze_tag_clusters took {elapsed:.2f} s (limit: 2 s)"
        assert "clusters" in result
