# Tasks: Analytics & Discovery

Resolves: #13, #15

## 1. Temporal Queries (#13)

- [ ] 1.1 Add DB indexes for `created_at` and `updated_at` in `db_models.py`
- [ ] 1.2 Add `NoteRepository.find_in_timerange(start, end, date_field, note_type)`
- [ ] 1.3 Add `ZettelService.find_notes_in_timerange(...)` with ISO 8601 validation
- [ ] 1.4 Register `zk_find_notes_in_timerange` in `mcp_server.py`
- [ ] 1.5 Write tests: date range match, updated_at axis, include_linked, empty range, invalid format
- [ ] 1.6 Performance test: < 200 ms for 10 000 notes

## 2. Tag Co-occurrence Analysis (#15)

- [ ] 2.1 Add `SearchService.analyze_tag_clusters(min_co_occurrence: int) -> dict`
- [ ] 2.2 Implement union-find cluster grouping in Python
- [ ] 2.3 Register `zk_analyze_tag_clusters` in `mcp_server.py`
- [ ] 2.4 Write tests: clusters above threshold, sparse pairs filtered, no clusters
- [ ] 2.5 Performance test: < 2 s for 1 000 tags / 10 000 notes

## 3. Housekeeping

- [ ] 3.1 Update README with new tool signatures
- [ ] 3.2 Run full test suite — all tests must pass
- [ ] 3.3 Run `ruff format` and `ruff check` — zero violations
- [ ] 3.4 Close GitHub issues #13, #15 referencing this change
