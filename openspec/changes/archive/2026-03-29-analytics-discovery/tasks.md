## 1. Database — Index date columns

- [x] 1.1 Add `index=True` to `DBNote.created_at` column in `db_models.py`
- [x] 1.2 Add `index=True` to `DBNote.updated_at` column in `db_models.py`

## 2. Repository layer — Temporal query

- [x] 2.1 Add `find_notes_in_timerange` method to `NoteRepository` in `note_repository.py`
- [x] 2.2 Implement ISO 8601 date parsing with `datetime.fromisoformat`; raise `ValueError` on invalid input
- [x] 2.3 Build SQLAlchemy query filtering by `created_at` or `updated_at` using `joinedload` for tags and links
- [x] 2.4 Implement `include_linked` second-pass query (one `IN` clause, no recursion)
- [x] 2.5 Implement optional `note_type` filter

## 3. Service layer — Temporal query

- [x] 3.1 Add `find_notes_in_timerange(start_date, end_date, date_field, include_linked, note_type)` to `ZettelService`
- [x] 3.2 Return `{"count": <int>, "notes": [...]}` dict from the service method

## 4. Repository/service layer — Tag cluster analysis

- [x] 4.1 Add `analyze_tag_clusters(min_co_occurrence: int)` to `SearchService`
- [x] 4.2 Implement tag co-occurrence SQL query (self-join on `note_tags` with `HAVING co_count >= :min`)
- [x] 4.3 Limit inner join to top-1000 tags by note count for performance
- [x] 4.4 Implement union-find cluster grouping in Python (no external graph libraries)
- [x] 4.5 Collect up to 5 representative note IDs per cluster
- [x] 4.6 Return `{"clusters": [...], "total_tag_pairs_analysed": <int>}`

## 5. MCP server — Register new tools

- [x] 5.1 Register `zk_find_notes_in_timerange` tool in `mcp_server.py`
- [x] 5.2 Register `zk_analyze_tag_clusters` tool in `mcp_server.py`

## 6. Tests

- [x] 6.1 Write tests for `find_notes_in_timerange`: date range match, `updated_at` field, linked neighbours, `note_type` filter
- [x] 6.2 Write test for empty date range result
- [x] 6.3 Write test for invalid date format → `ValueError`
- [x] 6.4 Write tests for `analyze_tag_clusters`: cluster above threshold, threshold filtering, empty result
- [x] 6.5 Write test for `ix_notes_created_at` and `ix_notes_updated_at` indexes present in schema
