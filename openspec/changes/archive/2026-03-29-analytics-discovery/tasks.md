## 1. Database Indexes

- [x] 1.1 Add `index=True` to `created_at` column in `DBNote` model (`db_models.py`) - Already present
- [x] 1.2 Add `index=True` to `updated_at` column in `DBNote` model (`db_models.py`) - Already present
- [x] 1.3 Generate and verify migration for new indexes - Not needed, indexes already present

## 2. Repository Layer — Temporal Queries

- [x] 2.1 Add `find_in_timerange` method to `NoteRepository` (`note_repository.py`) with SQLAlchemy query filtering by date column, supporting `start_date`, `end_date`, `date_field`, and eager-loading tags + outgoing links
- [x] 2.2 Add linked-note expansion: if `include_linked=True`, fetch notes linked from primary result set via second query

## 3. Service Layer — Temporal Queries

- [x] 3.1 Add `find_notes_in_timerange` to `ZettelService` (`zettel_service.py`) with ISO 8601 date validation via `datetime.fromisoformat`, raising `ValueError` on failure
- [x] 3.2 Wire repository call, format response as `{"count": N, "notes": [...]}`

## 4. Service Layer — Tag Co-occurrence Analysis

- [x] 4.1 Add `analyze_tag_clusters` to `SearchService` (`search_service.py`) implementing SQL self-join on `note_tags` with `LIMIT 1000` on inner sub-query for performance
- [x] 4.2 Implement union-find clustering in Python to group overlapping tag pairs into clusters
- [x] 4.3 Collect up to 5 representative note IDs per cluster from most co-occurring pair
- [x] 4.4 Return `{"clusters": [...], "total_tag_pairs_analysed": N}` format

## 5. MCP Tool Registration

- [x] 5.1 Register `zk_find_notes_in_timerange` tool in `mcp_server.py` with parameters: `start_date`, `end_date`, `date_field` (default `"created_at"`), `include_linked` (default `false`), `note_type` (optional)
- [x] 5.2 Register `zk_analyze_tag_clusters` tool in `mcp_server.py` with parameter: `min_co_occurrence` (default `2`)

## 6. Tests

- [x] 6.1 Write tests for temporal queries: date range filtering, `updated_at` field, `include_linked`, empty range, invalid date format
- [x] 6.2 Write tests for tag co-occurrence: clusters above threshold, threshold filtering, empty clusters, response format
- [x] 6.3 Add performance test for tag clustering with 1,000 tags across 10,000 notes (< 2s)
