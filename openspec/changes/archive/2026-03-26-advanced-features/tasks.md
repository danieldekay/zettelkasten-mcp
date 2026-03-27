# Tasks: Advanced Features

Resolves: #10, #11, #12, #16, #17

## 1. Flexible/Custom Link Types (#10)

- [x] 1.1 Add `LinkTypeRegistry` class in `models/schema.py`
- [x] 1.2 Replace enum-based validation in `NoteRepository` with registry lookup
- [x] 1.3 Add `ZettelService.register_link_type(name, inverse, symmetric)`
- [x] 1.4 Register `zk_register_link_type` in `mcp_server.py`
- [x] 1.5 Persist custom types to `openspec/config.yaml`
- [x] 1.6 Load custom types from config on server startup
- [x] 1.7 Write tests: register symmetric, register asymmetric, duplicates rejected

## 2. Link Type Inference (#11)

- [x] 2.1 Create `services/inference_service.py` with pattern-matching scorer
- [x] 2.2 Add `InferenceService.suggest_link_type(source: Note, target: Note) -> dict`
- [x] 2.3 Register `zk_suggest_link_type` in `mcp_server.py`
- [x] 2.4 Write tests: confident match, low-confidence result
- [x] 2.5 Performance test: < 1 s for 5 KB notes

## 3. Auto-Tagging Suggestions (#12)

- [x] 3.1 Extend `SearchService` with TF-IDF tag vector builder
- [x] 3.2 Add `SearchService.suggest_tags(content: str, limit: int) -> list[dict]`
- [x] 3.3 Invalidate cache on `rebuild_index()`
- [x] 3.4 Register `zk_suggest_tags` in `mcp_server.py`
- [x] 3.5 Write tests: relevant suggestions, no-match empty list
- [x] 3.6 Performance test: < 500 ms for 1 000 tags

## 4. Graceful Degradation (#16)

- [x] 4.1 Add `NoteRepository._read_from_markdown(note_id)` fallback
- [x] 4.2 Wrap `NoteRepository.get()` in try/except with fallback
- [x] 4.3 Add warning log on fallback path
- [x] 4.4 Handle write operations logging warning when DB unavailable
- [x] 4.5 Write tests: DB missing, mid-session DB failure, write with unavailable DB

## 5. Self-Healing Index (#17)

- [x] 5.1 Add `ZETTELKASTEN_AUTO_REBUILD_THRESHOLD` to `config.py` (default: 5)
- [x] 5.2 Add startup drift check in `main.py`
- [x] 5.3 Write tests: within tolerance, exceeds threshold, threshold=0 disabled

## 6. Housekeeping

- [x] 6.1 Update README with new tool signatures and `AUTO_REBUILD_THRESHOLD` env var
- [x] 6.2 Run full test suite — all tests must pass
- [x] 6.3 Run `ruff format` and `ruff check` — zero violations
- [x] 6.4 Close GitHub issues #10, #11, #12, #16, #17 referencing this change
