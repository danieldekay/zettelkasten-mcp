# Tasks: Analytics & Discovery

Resolves: #13, #15

## 1. Temporal Queries (#13)

- [x] 1.1 Add DB indexes for `created_at` and `updated_at` in `db_models.py`
- [x] 1.2 Add `NoteRepository.find_in_timerange(start, end, date_field, note_type)`
- [x] 1.3 Add `ZettelService.find_notes_in_timerange(...)` with ISO 8601 validation
- [x] 1.4 Register `zk_find_notes_in_timerange` in `mcp_server.py`
- [x] 1.5 Write tests: date range match, updated_at axis, include_linked, empty range, invalid format
- [x] 1.6 Performance test: < 200 ms for 10 000 notes

## 2. Tag Co-occurrence Analysis (#15)

- [x] 2.1 Add `SearchService.analyze_tag_clusters(min_co_occurrence: int) -> dict`
- [x] 2.2 Implement union-find cluster grouping in Python
- [x] 2.3 Register `zk_analyze_tag_clusters` in `mcp_server.py`
- [x] 2.4 Write tests: clusters above threshold, sparse pairs filtered, no clusters
- [x] 2.5 Performance test: < 2 s for 1 000 tags / 10 000 notes

## 3. Housekeeping

- [x] 3.1 Update README with new tool signatures
- [x] 3.2 Run full test suite — all tests must pass
- [x] 3.3 Run `ruff format` and `ruff check` — zero violations
- [x] 3.4 Close GitHub issues #13, #15 referencing this change
