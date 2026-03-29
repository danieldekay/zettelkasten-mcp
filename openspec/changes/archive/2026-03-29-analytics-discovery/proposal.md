## Why

The Zettelkasten MCP server currently supports search (FTS5, tags, links) and basic discovery (orphans, central notes, similar notes), but lacks analytical tools for temporal exploration and tag relationship analysis. Users need to answer questions like "what did I work on last month?" and "which topics cluster together?" — capabilities that unlock deeper knowledge synthesis.

## What Changes

- Add `zk_find_notes_in_timerange` MCP tool for filtering notes by `created_at` or `updated_at` date ranges, with optional linked-note expansion and note-type filtering
- Add `zk_analyze_tag_clusters` MCP tool for identifying groups of tags that frequently co-occur on the same notes, using SQL self-join with union-find clustering
- Add database indexes on `created_at` and `updated_at` columns for temporal query performance
- Add comprehensive test suite covering both tools including edge cases and performance benchmarks

## Capabilities

### New Capabilities

- `analytics-discovery`: Temporal queries and tag co-occurrence analysis exposed as MCP tools

### Modified Capabilities

(none — these are net-new tools)

## Impact

- `db_models.py`: Add `index=True` to `created_at` and `updated_at` columns
- `note_repository.py`: Add `find_in_timerange` repository method
- `zettel_service.py`: Add `find_notes_in_timerange` service method
- `search_service.py`: Add `analyze_tag_clusters` service method
- `mcp_server.py`: Register two new MCP tools
- `tests/test_analytics_discovery.py`: New test file
- No breaking changes to existing APIs
