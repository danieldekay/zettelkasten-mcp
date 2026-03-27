"""Service for searching and discovering notes in the Zettelkasten."""

import math
import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_, select, text
from sqlalchemy.orm import joinedload

from zettelkasten_mcp.config import config
from zettelkasten_mcp.models.db_models import DBLink, DBNote, DBTag
from zettelkasten_mcp.models.schema import Note, NoteType
from zettelkasten_mcp.services.zettel_service import ZettelService


@dataclass
class SearchResult:
    """A search result with a note and its relevance score."""

    note: Note
    score: float
    matched_terms: set[str]
    matched_context: str


class SearchService:
    """Service for searching notes in the Zettelkasten."""

    def __init__(self, zettel_service: ZettelService | None = None) -> None:
        """Initialize the search service."""
        self.zettel_service = zettel_service or ZettelService()
        # TF-IDF tag suggestion cache
        self._tag_cache: dict[str, dict[str, float]] | None = None

    def initialize(self) -> None:
        """Initialize the service and dependencies."""
        # Initialize the zettel service if it hasn't been initialized
        self.zettel_service.initialize()

    def search_by_text(
        self,
        query: str,
        include_content: bool = True,
        include_title: bool = True,
    ) -> list[SearchResult]:
        """Search for notes by text content."""
        if not query:
            return []

        # Normalize query
        query = query.lower()
        query_terms = set(query.split())

        # Get all notes
        all_notes = self.zettel_service.get_all_notes()
        results = []

        for note in all_notes:
            score = 0.0
            matched_terms: set[str] = set()
            matched_context = ""

            # Check title
            if include_title and note.title:
                title_lower = note.title.lower()
                # Exact match in title is highest score
                if query in title_lower:
                    score += 2.0
                    matched_context = f"Title: {note.title}"
                # Check for term matches in title
                for term in query_terms:
                    if term in title_lower:
                        score += 0.5
                        matched_terms.add(term)

            # Check content
            if include_content and note.content:
                content_lower = note.content.lower()
                # Exact match in content
                if query in content_lower:
                    score += 1.0
                    # Extract a snippet around the match
                    index = content_lower.find(query)
                    start = max(0, index - 40)
                    end = min(len(content_lower), index + len(query) + 40)
                    snippet = note.content[start:end]
                    matched_context = f"Content: ...{snippet}..."
                # Check for term matches in content
                for term in query_terms:
                    if term in content_lower:
                        score += 0.2
                        matched_terms.add(term)

            # Add to results if score is positive
            if score > 0:
                results.append(
                    SearchResult(
                        note=note,
                        score=score,
                        matched_terms=matched_terms,
                        matched_context=matched_context,
                    ),
                )

        # Sort by score (descending)
        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def search_by_tag(self, tags: str | list[str]) -> list[Note]:
        """Search for notes by tags."""
        if isinstance(tags, str):
            return self.zettel_service.get_notes_by_tag(tags)
        # If we have multiple tags, find notes with any of the tags
        all_matching_notes = []
        for tag in tags:
            notes = self.zettel_service.get_notes_by_tag(tag)
            all_matching_notes.extend(notes)
        # Remove duplicates by converting to a dictionary by ID
        unique_notes = {note.id: note for note in all_matching_notes}
        return list(unique_notes.values())

    def search_by_link(self, note_id: str, direction: str = "both") -> list[Note]:
        """Search for notes linked to/from a note."""
        return self.zettel_service.get_linked_notes(note_id, direction)

    def find_orphaned_notes(self) -> list[Note]:
        """Find notes with no incoming or outgoing links."""
        orphans = []

        with self.zettel_service.repository.session_factory() as session:
            # Subquery for notes with links
            notes_with_links = (
                select(DBNote.id)
                .outerjoin(
                    DBLink,
                    or_(
                        DBNote.id == DBLink.source_id,
                        DBNote.id == DBLink.target_id,
                    ),
                )
                .where(
                    or_(
                        DBLink.source_id is not None,
                        DBLink.target_id is not None,
                    ),
                )
                .subquery()
            )

            # Query for notes without links
            query = (
                select(DBNote)
                .options(
                    joinedload(DBNote.tags),
                    joinedload(DBNote.outgoing_links),
                    joinedload(DBNote.incoming_links),
                )
                .where(DBNote.id.not_in(select(notes_with_links)))
            )

            result = session.execute(query)
            orphaned_db_notes = result.unique().scalars().all()

            # Convert DB notes to model Notes
            for db_note in orphaned_db_notes:
                note = self.zettel_service.get_note(db_note.id)
                if note:
                    orphans.append(note)

        return orphans

    def find_central_notes(self, limit: int = 10) -> list[tuple[Note, int]]:
        """Find notes with the most connections (incoming + outgoing links)."""
        note_connections = []
        # Direct database query to count connections for all notes at once
        with self.zettel_service.repository.session_factory() as session:
            # Use a CTE for better readability and performance
            query = text("""
            WITH outgoing AS (
                SELECT source_id as note_id, COUNT(*) as outgoing_count
                FROM links
                GROUP BY source_id
            ),
            incoming AS (
                SELECT target_id as note_id, COUNT(*) as incoming_count
                FROM links
                GROUP BY target_id
            )
            SELECT n.id,
                COALESCE(o.outgoing_count, 0) as outgoing,
                COALESCE(i.incoming_count, 0) as incoming,
                (COALESCE(o.outgoing_count, 0) + COALESCE(i.incoming_count, 0)) as total
            FROM notes n
            LEFT JOIN outgoing o ON n.id = o.note_id
            LEFT JOIN incoming i ON n.id = i.note_id
            WHERE (COALESCE(o.outgoing_count, 0) + COALESCE(i.incoming_count, 0)) > 0
            ORDER BY total DESC
            LIMIT :limit
            """)

            results = session.execute(query, {"limit": limit}).all()

            # Process results
            for note_id, outgoing_count, incoming_count, _ in results:
                total_connections = outgoing_count + incoming_count
                if total_connections > 0:  # Only include notes with connections
                    note = self.zettel_service.get_note(note_id)
                    if note:
                        note_connections.append((note, total_connections))

        # Sort by total connections (descending)
        note_connections.sort(key=lambda x: x[1], reverse=True)

        # Return top N notes
        return note_connections[:limit]

    def find_notes_by_date_range(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        use_updated: bool = False,
    ) -> list[Note]:
        """Find notes created or updated within a date range."""
        all_notes = self.zettel_service.get_all_notes()
        matching_notes = []

        for note in all_notes:
            # Get the relevant date
            date = note.updated_at if use_updated else note.created_at

            # Check if in range
            if start_date and date < start_date:
                continue
            if end_date and date >= end_date + datetime.timedelta(seconds=1):
                continue

            matching_notes.append(note)

        # Sort by date (descending)
        matching_notes.sort(
            key=lambda x: x.updated_at if use_updated else x.created_at,
            reverse=True,
        )

        return matching_notes

    def find_similar_notes(self, note_id: str) -> list[tuple[Note, float]]:
        """Find notes similar to the given note based on shared tags and links."""
        return self.zettel_service.find_similar_notes(note_id)

    def search_combined(
        self,
        text: str | None = None,
        tags: list[str] | None = None,
        note_type: NoteType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[SearchResult]:
        """Perform a combined search with multiple criteria.

        Uses FTS5 full-text search if enabled and text query provided,
        otherwise falls back to legacy in-memory search.

        Args:
            text: Text query (FTS5 syntax supported if enabled)
            tags: Filter by tags
            note_type: Filter by note type
            start_date: Filter by creation date (start)
            end_date: Filter by creation date (end)

        Returns:
            List of SearchResult objects sorted by relevance
        """
        # Choose search strategy based on feature flag
        if config.use_fts5_search and text:
            return self._search_combined_fts5(
                text,
                tags,
                note_type,
                start_date,
                end_date,
            )
        return self._search_combined_legacy(text, tags, note_type, start_date, end_date)

    def _search_combined_fts5(
        self,
        text: str,
        tags: list[str] | None = None,
        note_type: NoteType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[SearchResult]:
        """FTS5-based combined search (fast, uses full-text index)."""
        # Step 1: FTS5 full-text search (fast!)
        fts_results = self.zettel_service.repository.search_by_fts5(
            query=text,
            limit=100,  # Over-fetch for post-filtering
        )

        # Step 2: Load only matching notes (not all!)
        candidate_notes = []
        for note_id, bm25_score, snippet in fts_results:
            note = self.zettel_service.get_note(note_id)
            if note:
                candidate_notes.append((note, bm25_score, snippet))

        # Step 3: Apply additional filters (tags, type, date)
        filtered_results = []
        for note, bm25_score, snippet in candidate_notes:
            # Check note type
            if note_type and note.note_type != note_type:
                continue

            # Check date range
            if start_date and note.created_at < start_date:
                continue
            if end_date and note.created_at > end_date:
                continue

            # Check tags
            if tags:
                note_tag_names = {tag.name for tag in note.tags}
                if not any(tag in note_tag_names for tag in tags):
                    continue

            # Convert BM25 score to positive (more negative = better in FTS5)
            # Normalize to 0-10 scale for consistency with legacy
            normalized_score = abs(bm25_score)

            filtered_results.append(
                SearchResult(
                    note=note,
                    score=normalized_score,
                    matched_terms=set(text.lower().split()),
                    matched_context=snippet,  # Use FTS5 snippet
                ),
            )

        # Already sorted by BM25 (FTS5 does this)
        return filtered_results

    def _search_combined_legacy(  # noqa: PLR0912
        self,
        text: str | None = None,
        tags: list[str] | None = None,
        note_type: NoteType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[SearchResult]:
        """Legacy in-memory search (slow, loads all notes)."""
        # Start with all notes
        all_notes = self.zettel_service.get_all_notes()

        # Filter by criteria
        filtered_notes = []
        for note in all_notes:
            # Check note type
            if note_type and note.note_type != note_type:
                continue

            # Check date range
            if start_date and note.created_at < start_date:
                continue
            if end_date and note.created_at > end_date:
                continue

            # Check tags
            if tags:
                note_tag_names = {tag.name for tag in note.tags}
                if not any(tag in note_tag_names for tag in tags):
                    continue

            # Made it through all filters
            filtered_notes.append(note)

        # If we have a text query, score the notes
        results = []
        if text:
            text = text.lower()
            query_terms = set(text.split())

            for note in filtered_notes:
                score = 0.0
                matched_terms: set[str] = set()
                matched_context = ""

                # Check title
                title_lower = note.title.lower()
                if text in title_lower:
                    score += 2.0
                    matched_context = f"Title: {note.title}"

                for term in query_terms:
                    if term in title_lower:
                        score += 0.5
                        matched_terms.add(term)

                # Check content
                content_lower = note.content.lower()
                if text in content_lower:
                    score += 1.0
                    index = content_lower.find(text)
                    start = max(0, index - 40)
                    end = min(len(content_lower), index + len(text) + 40)
                    snippet = note.content[start:end]
                    matched_context = f"Content: ...{snippet}..."

                for term in query_terms:
                    if term in content_lower:
                        score += 0.2
                        matched_terms.add(term)

                # Add to results if score is positive
                if score > 0:
                    results.append(
                        SearchResult(
                            note=note,
                            score=score,
                            matched_terms=matched_terms,
                            matched_context=matched_context,
                        ),
                    )
        else:
            # If no text query, just add all filtered notes with a default score
            results = [
                SearchResult(
                    note=note,
                    score=1.0,
                    matched_terms=set(),
                    matched_context="",
                )
                for note in filtered_notes
            ]

        # Sort by score (descending)
        results.sort(key=lambda x: x.score, reverse=True)
        return results

    # ------------------------------------------------------------------
    # TF-IDF tag suggestions
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Return lowercased word tokens from *text*."""
        return re.findall(r"[a-z]+", text.lower())

    def _build_tag_cache(self) -> dict[str, dict[str, float]]:
        """Build a TF-IDF vector for each tag from all tagged notes.

        Returns a mapping of {tag_name: {term: tfidf_weight}}.
        """
        all_notes = self.zettel_service.get_all_notes()
        n_docs = len(all_notes) or 1

        # Collect term frequencies per tag and document frequencies per term
        tag_tf: dict[str, dict[str, int]] = {}
        df: dict[str, int] = {}

        for note in all_notes:
            tokens = self._tokenize(f"{note.title} {note.content}")
            note_terms = set(tokens)
            for term in note_terms:
                df[term] = df.get(term, 0) + 1

            for tag in note.tags:
                if tag.name not in tag_tf:
                    tag_tf[tag.name] = {}
                for term in tokens:
                    tag_tf[tag.name][term] = tag_tf[tag.name].get(term, 0) + 1

        # Convert to TF-IDF
        tag_vectors: dict[str, dict[str, float]] = {}
        for tag_name, tf_map in tag_tf.items():
            total = sum(tf_map.values()) or 1
            vec: dict[str, float] = {}
            for term, cnt in tf_map.items():
                tfidf = (cnt / total) * math.log(n_docs / df.get(term, 1) + 1)
                if tfidf > 0:
                    vec[term] = tfidf
            tag_vectors[tag_name] = vec

        return tag_vectors

    def _cosine_similarity(
        self, vec_a: dict[str, float], vec_b: dict[str, float],
    ) -> float:
        """Compute cosine similarity between two sparse TF-IDF vectors."""
        shared = set(vec_a) & set(vec_b)
        dot = sum(vec_a[t] * vec_b[t] for t in shared)
        mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
        mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
        denom = mag_a * mag_b
        return dot / denom if denom > 0 else 0.0

    def suggest_tags(self, content: str, limit: int = 10) -> list[dict]:
        """Suggest tags for *content* using TF-IDF cosine similarity.

        Args:
            content: Text content to match against existing tag taxonomy.
            limit: Maximum number of suggestions to return.

        Returns:
            List of ``{"tag": str, "confidence": float}`` dicts sorted by
            confidence descending. Returns an empty list if no relevant
            matches are found.
        """
        if self._tag_cache is None:
            self._tag_cache = self._build_tag_cache()

        if not self._tag_cache:
            return []

        tokens = self._tokenize(content)
        if not tokens:
            return []

        # Build query TF vector
        query_tf: dict[str, float] = {}
        for term in tokens:
            query_tf[term] = query_tf.get(term, 0) + 1
        total = len(tokens)
        query_vec = {t: cnt / total for t, cnt in query_tf.items()}

        results = []
        for tag_name, tag_vec in self._tag_cache.items():
            sim = self._cosine_similarity(query_vec, tag_vec)
            if sim > 0:
                results.append({"tag": tag_name, "confidence": round(sim, 4)})

        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results[:limit]

    def invalidate_tag_cache(self) -> None:
        """Invalidate the TF-IDF tag cache (call after rebuild_index)."""
        self._tag_cache = None

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def analyze_tag_clusters(self, min_co_occurrence: int = 2) -> dict:
        """Identify clusters of tags that frequently appear together.

        Uses a SQL co-occurrence self-join limited to the top-1000 most-used
        tags, then groups overlapping pairs with union-find in Python.

        Args:
            min_co_occurrence: Minimum shared-note count for a pair to be
                included (default 2).

        Returns:
            Dict with:
            - ``clusters``: list of ``{"tags": [...], "count": int,
              "representative_notes": [...]}``
            - ``total_tag_pairs_analysed``: int
        """
        repo = self.zettel_service.repository

        with repo.session_factory() as session:
            rows = session.execute(
                text("""
                    SELECT a.tag_id AS tag_a, b.tag_id AS tag_b,
                           COUNT(*) AS co_count,
                           GROUP_CONCAT(a.note_id) AS note_ids
                    FROM note_tags a
                    JOIN note_tags b
                      ON a.note_id = b.note_id AND a.tag_id < b.tag_id
                    WHERE a.tag_id IN (
                        SELECT tag_id FROM note_tags
                        GROUP BY tag_id ORDER BY COUNT(*) DESC LIMIT 1000
                    )
                    GROUP BY a.tag_id, b.tag_id
                    HAVING co_count >= :min_co
                    ORDER BY co_count DESC
                """),
                {"min_co": min_co_occurrence},
            ).fetchall()

            # Fetch tag id->name mapping for all involved tag IDs
            involved = {r.tag_a for r in rows} | {r.tag_b for r in rows}
            if involved:
                id_name_rows = session.execute(
                    select(DBTag.id, DBTag.name).where(DBTag.id.in_(involved)),
                ).fetchall()
            else:
                id_name_rows = []

        if not rows:
            return {"clusters": [], "total_tag_pairs_analysed": 0}

        id_to_name = {r.id: r.name for r in id_name_rows}
        total_pairs = len(rows)

        # Union-Find implementation
        parent: dict[int, int] = {}

        def _find(x: int) -> int:
            while x in parent and parent[x] != x:
                x = parent[x]
            return x

        def _union(x: int, y: int) -> None:
            px, py = _find(x), _find(y)
            if px != py:
                parent[py] = px

        # Build clusters from pairs
        pair_data: dict[tuple[int, int], tuple[int, list[str]]] = {}
        for row in rows:
            _union(row.tag_a, row.tag_b)
            pair_data[(row.tag_a, row.tag_b)] = (
                row.co_count,
                (row.note_ids or "").split(",")[:5],
            )

        # Group tags by cluster root
        cluster_map: dict[int, set[int]] = {}
        all_tag_ids = {tid for pair in pair_data for tid in pair}
        for tid in all_tag_ids:
            root = _find(tid)
            cluster_map.setdefault(root, set()).add(tid)

        # For each cluster find the highest-count pair for representative notes
        clusters = []
        for tag_ids in cluster_map.values():
            best_count = 0
            best_notes: list[str] = []
            for (ta, tb), (co_count, note_ids) in pair_data.items():
                if (ta in tag_ids or tb in tag_ids) and co_count > best_count:
                    best_count = co_count
                    best_notes = note_ids

            tag_names = [
                id_to_name[tid] for tid in sorted(tag_ids) if tid in id_to_name
            ]
            if tag_names:
                clusters.append(
                    {
                        "tags": tag_names,
                        "count": best_count,
                        "representative_notes": best_notes,
                    },
                )

        clusters.sort(key=lambda c: c["count"], reverse=True)
        return {"clusters": clusters, "total_tag_pairs_analysed": total_pairs}
