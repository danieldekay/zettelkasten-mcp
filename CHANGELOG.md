# Changelog

All notable changes to the Zettelkasten MCP Server are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions correspond to phases in the OpenSpec change pipeline.

---

## [Unreleased]

---

## [1.4.0] — 2026-05-06

This release adds **FTS5 full-text search with Porter stemming and LLM-powered summaries**, **external folder (watch folder) indexing**, **tag syntax enforcement and normalisation**, a **CLI entry point**, and **VS Code task integration**.

### New features

#### FTS5 Full-Text Search & LLM Summaries

- Replaced the old `notes_fts` virtual table with `fts5_notes` using the `unicode61` tokenizer and Porter stemming for better search quality across languages.
- Extended FTS columns: `en_summary`, `en_keywords` alongside `title`, `content`, and `tags` — enabling semantic-style queries.
- BM25 weights tuned per column (`title=10`, `en_keywords=15`, `tags=8`, `en_summary=3`).
- **Auto-OR fallback** — when a phrase query returns zero results, the server automatically retries with `OR` between terms, surfacing partial matches instead of empty results.
- **FTS5 pre-warming** at server startup to eliminate cold-start latency on the first search.
- **`LLMSummaryService`** — generates English summaries and keywords via Azure OpenAI (`DefaultAzureCredential`). Disabled gracefully when `AZURE_OPENAI_ENDPOINT` is unset or `LLM_ENABLE_SUMMARIES=false`.
- **`SummaryCacheService`** — SHA-256 content-hash cache that survives `rebuild_index()` calls, avoiding redundant LLM API calls.
- **Migration script** `migrations/add_llm_summary_fields.py` — idempotent, safe to run on existing installations.

```env
LLM_ENABLE_SUMMARIES=true
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
LLM_MODEL=gpt-4o
```

#### External Folder Indexing (Watch Folders)

Index any external Markdown directory as **read-only reference notes** alongside your primary Zettelkasten notes.

- **`ZETTELKASTEN_WATCH_DIRS`** — comma-separated list of directories to index at startup. Files with YAML frontmatter are parsed fully; files without frontmatter receive a deterministic `ext-<sha256[:12]>` ID and use the filename stem as title.
- **`zk_sync_watch_folders`** — MCP tool to re-index all watch directories on demand without restarting the server.
- **`zk_list_notes`** — new MCP tool to list all notes with optional `note_type`, `tags`, and `include_external` filters.
- **Read-only guards** — `zk_update_note` and `zk_delete_note` refuse to modify watch-folder notes with a clear `PermissionError`.
- **Safe linking** — unidirectional links from primary notes to watch-folder notes are fully supported.
- **`is_readonly` / `source_path`** fields added to all note responses.

#### Tag Syntax Enforcement & Normalisation

- Tags are now normalised to `lowercase-kebab-case` before storage (`spaces` and `underscores` → hyphens, leading/trailing hyphens stripped, consecutive hyphens collapsed).
- New config option `ZETTELKASTEN_STRICT_TAGS` (default `false`): when `true`, non-canonical tags raise a `ValueError` instead of being silently corrected.
- `zk_create_note` and `zk_update_note` report any normalisation that occurred in the tool response.
- New tool **`zk_normalize_tags`** — bulk-normalises all tags across every note in the vault.

#### CLI Entry Point

- `zettelkasten-mcp` is now a proper `[project.scripts]` entry point; install with `uv sync` and start the server with `zettelkasten-mcp`.

#### VS Code Integration

- Five new VS Code tasks under `.vscode/tasks.json`: **ZK: Search Notes**, **ZK: Search by Tag**, **ZK: List All Tags**, **ZK: List Recent Notes**, **ZK: Open Note by ID**.
- Tasks run against your configured vault directly from the VS Code Command Palette.

---

## [1.3.0] — 2026-03-27

This release adds 9 new MCP tools across four themes: **batch operations** to
create many notes or links in one call, **vault health** tools to spot and
diagnose inconsistencies, **smart suggestions** for tags and link types powered
by your existing knowledge base, and **time-based discovery** to explore what
you wrote in a given period. The server is also now resilient — if the database
is unavailable, notes can still be created and read from the Markdown files
directly. Custom link types let teams define their own relationship vocabulary
beyond the built-in seven.

### New tools

| Tool | What it does |
|------|-------------|
| `zk_create_notes_batch` | Create multiple notes in a single call, all-or-nothing |
| `zk_create_links_batch` | Link multiple note pairs at once |
| `zk_verify_note` | Check whether a note's file and database record are in sync |
| `zk_get_index_status` | Health dashboard — counts, orphaned files, database size |
| `zk_register_link_type` | Define a custom relationship type for your project |
| `zk_suggest_link_type` | Get suggestions for how two notes might be related |
| `zk_suggest_tags` | Get tag recommendations based on your existing tag vocabulary |
| `zk_find_notes_in_timerange` | Find notes created or updated within a date range |
| `zk_analyze_tag_clusters` | Discover which tags tend to appear together |

### Other improvements

- **Resilient writes** — notes are saved to disk even when the database is
  temporarily unavailable; the index self-heals on next startup
- **Auto-rebuild** — on startup the server detects if files and database have
  drifted and rebuilds automatically (configurable threshold)
- **Structured responses** — all tools now return consistent JSON, making
  errors easier to handle in automation
- **Multilingual search** — full-text search handles German umlauts and other
  non-ASCII characters correctly
- **Metadata support** — `zk_create_note` and `zk_update_note` now accept a
  `metadata` field for arbitrary key-value data
- Test suite expanded to 233 tests across 13 test files

### Fixed

- Crash when sorting notes that mix timezone-aware and timezone-naive timestamps

---

## [1.2.1] — 2026-01-30

- Fix duplicate tag associations causing `IntegrityError` on note update
  (`if db_tag not in db_note.tags` guard added)
- Comprehensive debug and fix documentation in `docs/archive/debug-fixes-2026-01-30.md`

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

[Unreleased]: https://github.com/entanglr/zettelkasten-mcp/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/entanglr/zettelkasten-mcp/compare/v1.2.1...v1.3.0
[1.2.1]: https://github.com/entanglr/zettelkasten-mcp/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/entanglr/zettelkasten-mcp/releases/tag/v1.2.0
