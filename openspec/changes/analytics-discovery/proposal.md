## Why

The Zettelkasten MCP server currently has no way to explore knowledge temporally or discover thematic clusters. Users cannot answer "what did I capture in January?" or "which topics cluster together in my notes?" — temporal browsing and knowledge-map discovery stay manual and slow.

## What Changes

- **New tool** `zk_find_notes_in_timerange`: filters notes by `created_at` or `updated_at` within an ISO 8601 date range; optionally includes linked neighbours via `include_linked`
- **New tool** `zk_analyze_tag_clusters`: computes tag co-occurrence pairs (SQL self-join + union-find), groups them into clusters, and returns representative note IDs per cluster
- `ZettelService` gains `find_notes_in_timerange(start_date, end_date, date_field, include_linked, note_type)` method
- `SearchService` gains `analyze_tag_clusters(min_co_occurrence: int)` method
- `DBNote.created_at` and `DBNote.updated_at` columns gain `index=True` in `db_models.py` (auto-generates `ix_notes_created_at`, `ix_notes_updated_at`)

## Capabilities

### New Capabilities
- `analytics-discovery`: temporal date-range queries and tag co-occurrence cluster analysis, exposed as `zk_find_notes_in_timerange` and `zk_analyze_tag_clusters` MCP tools

### Modified Capabilities
<!-- No existing capability requirements are changing -->

## Impact

- `src/zettelkasten_mcp/models/db_models.py` — add `index=True` to date columns
- `src/zettelkasten_mcp/services/zettel_service.py` — add `find_notes_in_timerange`
- `src/zettelkasten_mcp/services/search_service.py` — add `analyze_tag_clusters`
- `src/zettelkasten_mcp/server/mcp_server.py` — register two new MCP tools
- `tests/` — new test module covering both tools
- No breaking changes to existing APIs; purely additive
