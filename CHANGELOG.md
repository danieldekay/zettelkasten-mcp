# Changelog

All notable changes to the Zettelkasten MCP Server are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions correspond to phases in the OpenSpec change pipeline.

---

## [Unreleased]

---

## [2.0.0] — 2026-03-27 — `feat/api-foundation` (Phases 2–5)

This release completes the four-phase API foundation programme, adding 9 new
MCP tools, a self-healing index, batch operations, custom link types, AI-assisted
suggestions, analytics tools, and graceful degradation when the database is
unavailable.

### Added

**Phase 5 — Analytics & Discovery (Issues #13, #15)**

- `zk_find_notes_in_timerange` — filter notes by `created_at` or `updated_at`
  within an ISO 8601 date range; supports `include_linked` to expand results
  with one-hop neighbours, and an optional `note_type` filter
- `zk_analyze_tag_clusters` — identify tag co-occurrence clusters using a SQL
  self-join and union-find grouping; configurable `min_co_occurrence` threshold
- `NoteRepository.find_in_timerange` — indexed column range query with timezone
  normalization (`_naive()` helper for mixed tz-aware/tz-naive datetimes)
- DB indexes on `notes.created_at` and `notes.updated_at` for sub-200 ms
  temporal queries at 10 000+ notes

**Phase 4 — Advanced Features (Issues #10, #11, #12, #16, #17)**

- `zk_register_link_type` — register project-scoped custom link types
  (symmetric or asymmetric with explicit inverse) persisted to
  `openspec/config.yaml`
- `zk_suggest_link_type` — keyword pattern-matching link-type inference;
  returns top-3 suggestions with confidence scores and a `low_confidence` flag
- `zk_suggest_tags` — TF-IDF cosine-similarity tag suggestions from the
  existing tag taxonomy; in-memory cache invalidated after `rebuild_index`
- `LinkTypeRegistry` — runtime registry replacing hardcoded `LinkType` enum
  checks throughout the repository layer; supports `is_valid`, `register`,
  `get_inverse`, `load_from_yaml`, `all_types`, `custom_types`
- `InferenceService` — pure Python pattern scorer, no ML dependencies,
  < 1 ms per suggestion pair
- `NoteRepository._db_available` flag — graceful degradation when SQLite
  is unreachable; `create` and `update` succeed even if DB indexing fails
- `NoteRepository._read_from_markdown` — direct filesystem read, bypasses
  SQLite (now the default path for `get()`)
- `ZETTELKASTEN_AUTO_REBUILD_THRESHOLD` config option — startup drift check
  (`_run_drift_check` in `main.py`) auto-rebuilds when `|fs - db| / fs > threshold`
- `ZETTELKASTEN_CUSTOM_LINK_TYPES_PATH` config option — path to custom link
  types YAML file (default `openspec/config.yaml`)

**Phase 3 — Core Enhancements (Issues #5, #6, #9, #14)**

- `zk_create_notes_batch` — atomic batch note creation; validates all items
  before any writes; rolls back written files on DB failure
- `zk_create_links_batch` — atomic multi-link creation; validates all types
  and target notes before writing; single DB `session.commit()`
- `zk_verify_note` — check filesystem + DB consistency for a single note;
  returns `file_exists`, `db_indexed`, `link_count`, `tag_count`, and a
  repair `hint` when diverged
- `zk_get_index_status` — vault health dashboard; returns `total_notes_filesystem`,
  `total_notes_indexed`, `orphaned_files`, `orphaned_db_records`,
  `orphaned_file_paths`, `orphaned_db_ids`, `database_size_mb`
- `NoteRepository.create_batch` — writes all Markdown files first, commits
  all DB records in one transaction; deletes written files if DB commit fails
- `NoteRepository.create_links_batch` — single-session DB batch insert
- `ZettelService.verify_note` — direct SQL consistency check (no side effects)
- `ZettelService.get_index_status` — filesystem glob + DB query comparison
- `ZettelService.create_notes_batch` / `create_links_batch` — service-layer
  wrappers with full input validation before any IO

**Phase 2 — API Foundation (Issues #1–#4, #7, #8)**

- All 14 MCP tools now return structured `dict` responses (never plain text)
- Uniform error envelope: `{"error": true, "error_type": "...", "message": "...", "summary": "..."}`
- `zk_get_note` returns `metadata` key (empty `{}` for notes without metadata)
- `zk_create_note` and `zk_update_note` accept `metadata` as JSON string or
  pre-parsed `dict`
- FTS5 full-text search with BM25 ranking via `notes_fts` virtual table
- `unicode61` tokenizer for multilingual content (German umlauts, etc.)
- FTS5 index synchronized on every `create`, `update`, and `delete`
- `zk_create_note` response includes `"warning"` key when DB is unavailable

**Documentation**

- `docs/ARCHITECTURE.md` — comprehensive system architecture document covering
  all layers, data flows, design decisions, and testing strategy
- `docs/moscow-top10-features.md` — 30-feature MoSCoW analysis of shipped and
  backlog capabilities
- `openspec/specs/` — synced main specs for `core-enhancements`,
  `advanced-features`, and `analytics-discovery`

### Changed

- `Link.link_type` changed from `LinkType` enum to validated `str`; a
  Pydantic `field_validator` calls `link_type_registry.is_valid()` — fully
  backward-compatible at the API level
- `NoteRepository.get()` now always reads from the Markdown file (filesystem
  as source of truth); SQLite is no longer consulted for single-note reads
- `ZettelService.create_link` uses `link_type_registry.get_inverse()` for
  bidirectional link semantics instead of a hardcoded dict
- `NoteRepository.update()` DB failure is now non-fatal (logs warning, sets
  `_db_available = False`) rather than re-raising
- `utils.py` `format_note_for_display` uses `link.link_type` directly (string)
  instead of `link.link_type.value`
- Test suite expanded to 233+ tests across 13 test files

### Fixed

- `TypeError: can't compare offset-naive and offset-aware datetimes` when
  sorting notes from a live database that stores tz-naive datetimes alongside
  test fixtures that use tz-aware datetimes; resolved with a `_naive()` helper
  in `find_in_timerange` sort key

### Deprecated / Removed

- Hardcoded `LinkType` enum check in `NoteRepository._parse_note_from_markdown`
  replaced by `link_type_registry.is_valid()`; unknown types now fall back to
  `"reference"` instead of raising

---

## [1.2.1] — 2026-01-30

- Fix duplicate tag associations causing `IntegrityError` on note update
  (`if db_tag not in db_note.tags` guard added)
- Comprehensive debug and fix documentation in `docs/DEBUG-FIXES-2026-01-30.md`

---

## [1.2.0] — 2025-11-09 (initial public release)

### Added

- Core Zettelkasten CRUD: `zk_create_note`, `zk_get_note`, `zk_update_note`,
  `zk_delete_note`
- Typed bidirectional semantic links with 7 built-in types (12 including
  inverses): `reference`, `extends`/`extended_by`, `refines`/`refined_by`,
  `contradicts`/`contradicted_by`, `questions`/`questioned_by`,
  `supports`/`supported_by`, `related`
- Tag management: `zk_get_all_tags`
- Search: `zk_search_notes` (text + tag + note type filters)
- Graph tools: `zk_get_linked_notes`, `zk_find_similar_notes`,
  `zk_find_central_notes`, `zk_find_orphaned_notes`, `zk_list_notes_by_date`
- Index operations: `zk_rebuild_index`
- Dual storage architecture: Markdown source of truth + SQLite index
- Five note types: `fleeting`, `literature`, `permanent`, `structure`, `hub`
- Timestamp-based collision-resistant note IDs (`YYYYMMDDTHHMMSSssssssccc`)
- SQLite FTS5 full-text search with BM25 ranking
- Python `uv` packaging with `pyproject.toml`
- MIT License

---

[Unreleased]: https://github.com/basf-global/zettelkasten-mcp/compare/HEAD...HEAD
[2.0.0]: https://github.com/basf-global/zettelkasten-mcp/compare/v1.2.1...feat/api-foundation
[1.2.1]: https://github.com/basf-global/zettelkasten-mcp/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/basf-global/zettelkasten-mcp/releases/tag/v1.2.0
