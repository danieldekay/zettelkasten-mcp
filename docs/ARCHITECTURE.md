================================================================
Start of Project Knowledge File
================================================================

Purpose:
--------
This file is designed to be consumed by AI systems for analysis, review,
or other automated processes. It solely serves the purpose of background
information and should NOT under any circumstances leak into the user's
interaction with the AI when actually USING the Zettelkasten MCP tools to
process, explore or synthesize user-supplied information.

Content:
--------

# Architecture — Zettelkasten MCP Server

> **Version**: 2.0 (Phase 5 — `feat/api-foundation`)
> **Last updated**: 2026-03-27

---

## Overview

The Zettelkasten MCP server is a Python application that exposes the
Zettelkasten knowledge-management methodology as a set of
[Model Context Protocol](https://modelcontextprotocol.io/) (MCP) tools.
It has a layered architecture with a dual-storage backend (Markdown files +
SQLite) and is designed to remain functional even when its database index
is unavailable.

```
┌────────────────────────────────────────────────────────────────┐
│                      MCP Client (Claude etc.)                  │
└─────────────────────────────┬──────────────────────────────────┘
                              │  MCP protocol (stdio)
┌─────────────────────────────▼──────────────────────────────────┐
│                    ZettelkastenMcpServer                        │
│   server/mcp_server.py  ·  FastMCP wrapper  ·  24 tools        │
└──────┬─────────────────────────┬───────────────────────────────┘
       │                         │
┌──────▼──────────┐   ┌──────────▼────────────────────────────┐
│  ZettelService  │   │ SearchService  │  InferenceService     │
│  (CRUD, links,  │   │ (search, tags, │  (link inference,     │
│   batch, health)│   │  analytics)    │   pattern scoring)    │
└──────┬──────────┘   └──────────┬────────────────────────────┘
       │                         │
┌──────▼─────────────────────────▼──────────────────────────────┐
│                       NoteRepository                           │
│   storage/note_repository.py                                   │
│   ┌─────────────────────┐   ┌──────────────────────────────┐  │
│   │   Markdown Files     │   │       SQLite (index)         │  │
│   │   (source of truth)  │   │  FTS5 · indexes · relations  │  │
│   │   data/notes/*.md    │   │  data/db/zettelkasten.db     │  │
│   └─────────────────────┘   └──────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
zettelkasten-mcp/
├── src/zettelkasten_mcp/
│   ├── config.py                 Configuration (env vars, Pydantic model)
│   ├── main.py                   Entry point, arg parsing, drift check
│   ├── utils.py                  ID generation, logging, formatting helpers
│   ├── models/
│   │   ├── schema.py             Pydantic domain models + LinkTypeRegistry
│   │   └── db_models.py          SQLAlchemy ORM models + init_db()
│   ├── storage/
│   │   ├── base.py               Abstract Repository[T] interface
│   │   └── note_repository.py    Dual-storage implementation
│   ├── services/
│   │   ├── zettel_service.py     Note CRUD, links, batch ops, health
│   │   ├── search_service.py     FTS5 search, tag suggestions, clustering
│   │   └── inference_service.py  Pattern-based link-type inference
│   └── server/
│       └── mcp_server.py         FastMCP tool registrations + error handling
├── tests/
│   ├── conftest.py               Shared fixtures (temp dirs, config, repo)
│   ├── test_models.py
│   ├── test_note_repository.py
│   ├── test_zettel_service.py
│   ├── test_search_service.py
│   ├── test_semantic_links.py
│   ├── test_integration.py
│   ├── test_mcp_server.py
│   ├── test_main.py
│   ├── test_utils.py
│   ├── test_advanced_features.py  Custom types, inference, degradation, drift
│   ├── test_batch_operations.py   Batch notes/links, verify, health
│   └── test_analytics_discovery.py Temporal queries, tag clusters
├── data/
│   ├── notes/                    Markdown note files (source of truth)
│   └── db/                       SQLite database
├── docs/                         Documentation
└── openspec/                     OpenSpec change proposals and archived changes
```

---

## Layer Descriptions

### 1. Entry Point — `main.py`

Parses CLI arguments, applies them to the global `config`, calls `init_db()`,
loads custom link types from `openspec/config.yaml`, runs the startup drift
check (`_run_drift_check`), and starts the `ZettelkastenMcpServer` which
blocks on `mcp.run()`.

**Startup drift check**: compares `*.md` file count in `notes_dir` against the
`COUNT(*)` in the SQLite `notes` table. If the percentage difference exceeds
`ZETTELKASTEN_AUTO_REBUILD_THRESHOLD` (default 5 %), `rebuild_index()` is
called automatically before the server accept connections.

---

### 2. Configuration — `config.py`

`ZettelkastenConfig` is a Pydantic `BaseModel` loaded at module import time.
All settings have environment variable overrides.

| Environment variable | Default | Description |
|---|---|---|
| `ZETTELKASTEN_NOTES_DIR` | `data/notes` | Markdown notes directory |
| `ZETTELKASTEN_DATABASE_PATH` | `data/db/zettelkasten.db` | SQLite file path |
| `ZETTELKASTEN_LOG_LEVEL` | `INFO` | Python logging level |
| `ZETTELKASTEN_AUTO_REBUILD_THRESHOLD` | `5` | Drift % that triggers auto-rebuild (0 = disabled) |
| `ZETTELKASTEN_CUSTOM_LINK_TYPES_PATH` | `openspec/config.yaml` | YAML file for custom link types |
| `USE_FTS5_SEARCH` | `true` | Enable SQLite FTS5 full-text search |

`get_absolute_path(path)` resolves relative paths relative to `base_dir`
(defaults to the current working directory).

---

### 3. Data Models — `models/`

#### `schema.py` — Domain models (Pydantic)

| Class | Description |
|---|---|
| `Note` | Atomic note: `id`, `title`, `content`, `note_type`, `tags`, `links`, `metadata`, timestamps |
| `Link` | Typed directed edge: `source_id`, `target_id`, `link_type` (validated str), `description` |
| `Tag` | Simple name wrapper, immutable |
| `NoteType` | Enum: `fleeting`, `literature`, `permanent`, `structure`, `hub` |
| `LinkType` | Enum of built-in link type constants (kept for backward compatibility) |
| `LinkTypeDef` | Dataclass: `name`, `inverse`, `symmetric` |
| `LinkTypeRegistry` | Runtime registry of all valid link types (built-in + custom) |
| `generate_id()` | Thread-safe `YYYYMMDDTHHMMSSssssssccc` timestamp ID |

**`LinkTypeRegistry`** replaces the old hardcoded `LinkType` enum check
throughout the repository layer. It supports:
- `is_valid(name)` — used as the single validation gate for all link creation
- `register(name, inverse, symmetric)` — adds custom types (raises on duplicate)
- `get_inverse(name)` — used by `ZettelService.create_link` for bidirectional logic
- `load_from_yaml(path)` — loads persisted custom types on server startup

**`Link.link_type`** is a validated `str` (not `LinkType` enum). A
`field_validator` calls `link_type_registry.is_valid()` to enforce the
constraint. Using strings instead of enums allows custom link types to
coexist seamlessly with built-in ones without a code change.

#### `db_models.py` — SQLAlchemy ORM

| ORM class | SQLite table | Key columns |
|---|---|---|
| `DBNote` | `notes` | `id` (PK, indexed), `title`, `content`, `note_type`, `created_at` (indexed), `updated_at` (indexed) |
| `DBTag` | `tags` | `id` (PK), `name` (UNIQUE) |
| `DBLink` | `links` | `id` (PK), `source_id` (FK), `target_id` (FK), `link_type`, `description` |
| `note_tags` | association | `note_id` + `tag_id` (composite PK, UNIQUE constraint) |

`init_db()` creates all tables if they don't exist and returns an `Engine`.
`get_session_factory(engine)` returns a `sessionmaker`.

The `notes_fts` FTS5 virtual table (created on first access) mirrors
`notes.id`, `notes.title`, and `notes.content` for sub-millisecond BM25
full-text search.

---

### 4. Storage Layer — `storage/`

#### `base.py` — Abstract interface

`Repository[T]` is a generic ABC defining `create`, `get`, `update`,
`delete`, and `search`. `NoteRepository` is its only implementation.

#### `note_repository.py` — Dual-storage implementation

The central implementation principle: **Markdown files are the source of
truth**.

**Read path (`get`)**
Reads directly from the `{id}.md` file via `_read_from_markdown()`, parsing
YAML frontmatter with `python-frontmatter`. The SQLite index is *not* used for
single-note reads, eliminating stale-cache races.

**Write path (`create`, `update`)**
1. Serialize `Note` → Markdown (`_note_to_markdown`)
2. Write file to `notes_dir/{id}.md` (within `file_lock`)
3. Call `_index_note()` to write to SQLite
4. If SQLite fails, set `_db_available = False`, log a warning, and return
   the note — the write still succeeds, the index can be repaired later

**Bulk read path (`get_all`)**
Prefers the SQLite index for efficiency (batch IDs → individual
`_read_from_markdown` calls). Falls back to a filesystem glob when
`_db_available = False`.

**Key methods**

| Method | Description |
|---|---|
| `create(note)` | Write Markdown + index; non-fatal DB failure |
| `get(id)` | Direct Markdown file read |
| `update(note)` | Overwrite Markdown + re-index |
| `delete(id)` | Remove file + DB record |
| `get_all()` | DB-ordered IDs → Markdown reads; filesystem fallback |
| `create_batch(notes)` | All files first, one DB `session.commit()`; rollback files on failure |
| `create_links_batch(source_id, links)` | Single DB transaction for multiple links |
| `find_in_timerange(start, end, date_field, …)` | Indexed column range query + optional linked-note expansion |
| `search_by_fts5(query, …)` | BM25 full-text search via FTS5 virtual table |
| `rebuild_index()` | Glob all `*.md`, re-index every note into SQLite + FTS5 |

**Graceful degradation**

`_db_available: bool` tracks whether SQLite is operational at runtime.
Set to `False` on any `create`, `update`, or `get_all` DB exception.
When `False`, `get_all()` falls back to a filesystem glob automatically.

---

### 5. Service Layer — `services/`

Services are the business logic layer. They do not access the database
directly; they call `NoteRepository` methods.

#### `ZettelService`

Orchestrates all note-lifecycle operations.

| Method group | Methods |
|---|---|
| CRUD | `create_note`, `get_note`, `get_note_by_title`, `update_note`, `delete_note`, `get_all_notes` |
| Links | `create_link`, `remove_link`, `get_linked_notes` |
| Discovery | `find_similar_notes`, `export_note` |
| Batch | `create_notes_batch`, `create_links_batch` |
| Health | `verify_note`, `get_index_status` |
| Analytics | `find_notes_in_timerange` |
| Extensibility | `register_link_type` |

**`create_link`** handles bidirectional semantics: if `bidirectional=True`,
the inverse link type is looked up via `link_type_registry.get_inverse()` and
a reverse link is created on the target note.

**`register_link_type`** calls `LinkTypeRegistry.register()` and persists the
new type to `${ZETTELKASTEN_CUSTOM_LINK_TYPES_PATH}` (YAML), so it survives
server restarts.

**`find_notes_in_timerange`** validates ISO 8601 dates, expands bare date
strings to cover the full day, and delegates to
`NoteRepository.find_in_timerange`.

#### `SearchService`

All search and discovery operations.

| Method | Description |
|---|---|
| `search_by_text(query, …)` | In-memory TF-IDF scored text search (legacy path) |
| `search_combined(text, tags, note_type, …)` | FTS5 or legacy path based on `config.use_fts5_search` |
| `find_orphaned_notes()` | SQL: notes with no outgoing or incoming links |
| `find_central_notes(limit)` | SQL: notes with highest in-degree |
| `suggest_tags(content, limit)` | TF-IDF cosine similarity against cached tag vectors |
| `analyze_tag_clusters(min_co_occurrence)` | SQL co-occurrence self-join + union-find |
| `invalidate_tag_cache()` | Reset the in-memory TF-IDF tag cache |

**TF-IDF tag cache**

Built lazily on the first `suggest_tags()` call:
1. Load all notes via `zettel_service.get_all_notes()`
2. For each tag, sum term frequencies across all notes carrying that tag
3. Apply IDF weighting using overall document frequency
4. Store `{tag_name: {term: tfidf_weight}}` in `self._tag_cache`

Cache is invalidated by calling `invalidate_tag_cache()` (also called
implicitly after `rebuild_index()`).

**Tag clustering**

Single SQL query self-joins `note_tags` on `note_id` to produce
`(tag_a, tag_b, co_count)` pairs above the minimum threshold, limited to
the top-1 000 most-used tags to bound the O(T²) join. Python union-find
then groups overlapping pairs into clusters.

#### `InferenceService`

Purely in-memory, no database access.

Given two `Note` objects, `suggest_link_type()` scores each built-in link
type against a hard-coded pattern dictionary (e.g. `extends` scores on
`"building on"`, `"expands"`, `"further"` etc.). Returns the top-3 types
sorted by score with a `low_confidence` flag when all scores fall below 0.4.
Runs in O(|patterns| × |content|); typically < 1 ms.

---

### 6. MCP Server — `server/mcp_server.py`

`ZettelkastenMcpServer` wraps a `FastMCP` instance from the
`mcp[cli]` package.

**Initialization order**
1. Instantiate `FastMCP` with server name and version
2. Instantiate `ZettelService` and `SearchService`
3. Call `initialize()` on both services
4. Call `_register_tools()`, `_register_resources()`, `_register_prompts()`

**Tool contract**

Every tool returns a JSON-serializable `dict` (never plain text). The base
contract requires a `summary: str` key. All tools add domain-specific keys
on top. Errors are returned as structured dicts with keys `error: True`,
`error_type`, `message`, and `summary` — no tool raises an unhandled Python
exception to the MCP client.

**Tool registration**

Tools are registered with `@self.mcp.tool()` using consistent naming
(`name="zk_*"`). Each tool follows the pattern:

```python
@self.mcp.tool()
def zk_example(param: str) -> dict:
    try:
        result = self.zettel_service.some_operation(param)
        return {"key": result, "summary": "Success message"}
    except ValueError as e:
        return self.format_error_response(e)
    except Exception as e:
        return self.format_error_response(e)
```

**Available tools (24)**

| Category | Tools |
|---|---|
| Note CRUD | `zk_create_note`, `zk_get_note`, `zk_update_note`, `zk_delete_note` |
| Batch | `zk_create_notes_batch`, `zk_create_links_batch` |
| Links | `zk_create_link`, `zk_remove_link`, `zk_get_linked_notes` |
| Search & Discovery | `zk_search_notes`, `zk_find_similar_notes`, `zk_find_central_notes`, `zk_find_orphaned_notes`, `zk_list_notes_by_date` |
| Tags | `zk_get_all_tags`, `zk_suggest_tags` |
| Analytics | `zk_find_notes_in_timerange`, `zk_analyze_tag_clusters` |
| Intelligence | `zk_register_link_type`, `zk_suggest_link_type` |
| Operations | `zk_rebuild_index`, `zk_verify_note`, `zk_get_index_status` |

---

## Data Flow: Note Creation

```
zk_create_note(title, content, tags, metadata)
  │
  ▼ ZettelkastenMcpServer
  │  parse metadata → dict
  │  call zettel_service.create_note(...)
  │
  ▼ ZettelService.create_note()
  │  validate title + content
  │  construct Note(id=generate_id(), ...)
  │  call repository.create(note)
  │
  ▼ NoteRepository.create(note)
  │  serialize note → Markdown (YAML frontmatter + content)
  │  write notes_dir/{id}.md  ← filesystem write (always)
  │  call _index_note(note)
  │    ├─ upsert DBNote, DBTag, DBLink, FTS5 row
  │    └─ session.commit()
  │  if DB fails: set _db_available=False, log warning, return note
  │
  ▼ return Note → ZettelService → MCP server
  │
  ▼ return {"note_id": ..., "file_path": ..., "summary": ..., ["warning": ...]}
```

---

## Data Flow: Note Search (FTS5 path)

```
zk_search_notes(query="machine learning", tags=["ai"])
  │
  ▼ ZettelkastenMcpServer
  │  parse tags list
  │
  ▼ SearchService.search_combined(text, tags, ...)
  │  config.use_fts5_search == True → _search_combined_fts5()
  │
  ▼ NoteRepository.search_by_fts5(query)
  │  SELECT ... FROM notes_fts WHERE notes_fts MATCH :query
  │  ORDER BY bm25(notes_fts) → (id, score, snippet)
  │
  ▼ filter results by tags in Python if tags provided
  ▼ for each id: repository.get(id) → _read_from_markdown(id)
  ▼ return [SearchResult(note, score, matched_terms, context)]
  │
  ▼ return {"notes": [...], "total": N, "query": "...", "summary": "..."}
```

---

## Markdown File Format

Each note is stored as a self-contained `.md` file:

```markdown
---
id: 20260326T163736056791000
title: FTS5 Full-Text Search Engine
type: permanent
tags: [fts5, sqlite, search]
created: 2026-03-26T16:37:36.056791+00:00
updated: 2026-03-26T16:37:36.056791+00:00
metadata:
  source: api-foundation
---

# FTS5 Full-Text Search Engine

SQLite FTS5 provides BM25-ranked full-text search...

## Links
- extends [[20260326T163717358310000]] FTS5 uses BM25 as its ranking function
- reference [[20260101T120000000000000]]
```

---

## Note ID Format

IDs are lexicographically sortable timestamps with collision resistance:

```
YYYYMMDDTHHMMSSssssssccc
│        │      │     │
│        │      │     └── 3-digit counter (0–999, resets per microsecond)
│        │      └──────── 6-digit microseconds
│        └─────────────── HHMMSS (ISO 8601 basic)
└──────────────────────── YYYYMMDD date
```

Thread safety is guaranteed via `_id_lock` (`threading.RLock`). Up to
10⁹ unique IDs per second are theoretically possible.

---

## Graceful Degradation

The server is designed to remain operational when the SQLite index is
unavailable (corrupt file, disk-full, permissions change):

| Scenario | Behaviour |
|---|---|
| `create` with DB down | Markdown written; `_db_available = False`; warning logged |
| `update` with DB down | Markdown overwritten; `_db_available = False`; warning logged |
| `get(id)` | Always reads from Markdown — no DB dependency |
| `get_all()` with `_db_available = False` | Filesystem glob, sorted by filename |
| `zk_create_note` response | Includes `"warning"` key when `_db_available == False` |
| Missing DB at startup | `init_db()` creates it; no crash |
| Repair | `zk_rebuild_index` re-syncs everything from Markdown |

---

## Self-Healing Index

On startup, `_run_drift_check()` in `main.py`:

1. Count `.md` files in `notes_dir`
2. Count rows in `notes` table
3. Compute `drift_pct = |fs_count - db_count| / fs_count × 100`
4. If `drift_pct > ZETTELKASTEN_AUTO_REBUILD_THRESHOLD`: run `rebuild_index()`
5. If `drift_pct > 0` but below threshold: log `WARNING`
6. If `threshold == 0`: disabled entirely

---

## Custom Link Types

Custom link types extend the built-in vocabulary without modifying source code:

**Registration (runtime)**
```python
zk_register_link_type(name="implements", inverse="implemented_by", symmetric=False)
```

**Persistence** (`openspec/config.yaml`)
```yaml
custom_link_types:
  - name: implements
    inverse: implemented_by
    symmetric: false
```

**Loading** (server startup, `main.py`)
```python
link_type_registry.load_from_yaml(config.get_absolute_path(config.custom_link_types_path))
```

The `LinkTypeRegistry` module-level singleton `link_type_registry` is the
single source of truth for link-type validation across the entire codebase.

---

## Testing Strategy

Tests are organized to mirror the source structure:

| Test file | What it covers |
|---|---|
| `test_models.py` | Note/Link/Tag model validation, ID format, immutability |
| `test_note_repository.py` | CRUD, Markdown round-trips, metadata, duplicate tags |
| `test_zettel_service.py` | Service delegation, create/update/delete/link/search |
| `test_search_service.py` | FTS5, legacy search, orphan/central/similar note discovery |
| `test_semantic_links.py` | All 12 link types, bidirectional semantics, persistence |
| `test_integration.py` | Full system: create → link → search → rebuild flow |
| `test_mcp_server.py` | Tool registration, structured responses, error envelopes |
| `test_main.py` | CLI arg parsing, server startup, db error exit |
| `test_utils.py` | ID generation, tag parsing, display formatting |
| `test_advanced_features.py` | LinkTypeRegistry, InferenceService, TF-IDF suggestions, graceful degradation, drift check |
| `test_batch_operations.py` | Batch note/link creation (atomicity, rollback), verify_note, get_index_status |
| `test_analytics_discovery.py` | Temporal queries, tag clustering, performance benchmarks |

**Run the full suite:**
```bash
uv run pytest -v
uv run pytest --cov=zettelkasten_mcp --cov-report=term-missing
```

---

## Dependency Map

```
mcp_server.py
  └── ZettelService        (zettel_service.py)
        └── NoteRepository (note_repository.py)
              ├── schema.py       (Note, Link, Tag, LinkTypeRegistry)
              ├── db_models.py    (DBNote, DBTag, DBLink, init_db)
              └── config.py
  └── SearchService        (search_service.py)
        └── ZettelService  (for get_all_notes, get_note)
  └── InferenceService     (inference_service.py)
        └── schema.py      (Note, LinkType pattern keys)
main.py
  └── config.py
  └── schema.py            (link_type_registry)
  └── mcp_server.py
```

All service dependencies are injected via constructor parameters, making
every layer independently testable with mocks or temp-dir fixtures.
================================================================
End of Project Knowledge File
================================================================
