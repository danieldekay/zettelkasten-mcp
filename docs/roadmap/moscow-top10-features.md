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

# Zettelkasten MCP — Top 10 MoSCoW Features

> **Date**: 2026-03-26
> **Source**: OpenSpec changes `api-foundation`, `core-enhancements`, `advanced-features`,
> `analytics-discovery` · Research sprint 20260325 · 90 sources

---

## Reading guide

Each feature entry covers: **what it is**, **why it matters**, **how it works**
(design decisions), **current status**, and **success criteria**.

Features are ordered by MoSCoW rank first (Must → Should → Could), then by
implementation priority within each rank.

---

## Must-Have Features

### 1 · Structured JSON API Responses

**Status**: ✅ Shipped (Phase 2 · `api-foundation`)
**GitHub**: N/A (foundational)

#### What

Every one of the 14 MCP tools returns a JSON-serialisable `dict` as its primary
response. Each response includes a `"summary"` key carrying a human-readable
string equivalent to the previous plain-text output, preserving backward
compatibility for display-only clients.

#### Why it matters

Agent workflows that call `zk_create_note` and then pass the note ID to
`zk_create_link` previously had to parse natural language ("Note created:
'FTS5 Search' (20260326T…)") to extract the ID. With structured responses, the
agent reads `result["note_id"]` directly — zero fragility, zero prompt
engineering overhead.

#### How it works

All 14 tools were refactored to return typed `dict` objects. A `ToolResponse`
`TypedDict` defines the `summary: str` base contract. Each tool adds its own
keys on top:

| Tool | Response keys |
|------|---------------|
| `zk_create_note` | `note_id`, `file_path`, `summary` |
| `zk_get_note` | `note_id`, `title`, `note_type`, `tags`, `links`, `created_at`, `updated_at`, `content`, `metadata`, `summary` |
| `zk_search_notes` | `notes[]` (with `score`), `total`, `query`, `summary` |
| `zk_create_link` | `source_id`, `target_id`, `link_type`, `summary` |
| `zk_get_all_tags` | `tags[]` (with `name`, `count`), `total`, `summary` |
| `zk_rebuild_index` | `notes_indexed`, `errors[]`, `summary` |

Errors use a uniform envelope: `{"error": true, "error_type": "...", "message": "...", "summary": "..."}`.
No tool raises an unhandled Python exception; all failures return structured dicts.

#### Success criteria

- Zero tools return bare plain text as the primary response ✅
- All 163 tests pass with JSON assertion coverage ✅

---

### 2 · FTS5 Full-Text Search

**Status**: ✅ Shipped (Phase 2 · `api-foundation`)
**GitHub**: N/A (foundational)

#### What

`zk_search_notes` uses SQLite's built-in FTS5 virtual table (`notes_fts`) for
keyword queries, replacing an O(n) Python-side string scan. Results are BM25-ranked
— the most relevant notes appear first.

#### Why it matters

On a 1 000-note knowledge base the old approach loaded every note into memory
and called `keyword in note.content`. At 10 000 notes that becomes untenable
(seconds of wall-clock time, unbounded memory). FTS5 query time is sub-millisecond
for typical queries because SQLite maintains an inverted index.

#### How it works

A `notes_fts` virtual table is created alongside the `notes` table:

```sql
CREATE VIRTUAL TABLE notes_fts USING fts5(
    id UNINDEXED,
    title,
    content,
    tokenize='unicode61'       -- multilingual: German + English
)
```

The `unicode61` tokenizer handles German umlauts, French accents, and CJK
characters. The BM25 score is exposed as a negative float (more negative = more
relevant) and rounded to 4 decimal places in the response.

`zk_search_notes` has three modes:

- **Query only**: FTS5 MATCH on `notes_fts`
- **Filters only** (tags, note type): SQL `WHERE` on `notes` + `note_tags`; FTS5
  not touched
- **Query + filters**: FTS5 MATCH joined with SQL predicates — only notes
  satisfying all conditions are returned

The FTS5 index is kept in sync in the same database transaction as every
create, update, and delete operation.

#### Success criteria

- `zk_search_notes` target: < 50 ms on 10 000 notes ✅ (FTS5 structural guarantee)
- Empty query returns empty results (not all notes) ✅
- Index synced on create/update/delete ✅

---

### 3 · Note Metadata Exposure

**Status**: ✅ Shipped (Phase 2 · `api-foundation`)
**GitHub**: N/A (foundational)

#### What

`zk_create_note` and `zk_update_note` accept an optional `metadata` parameter
(JSON string **or** dict). `zk_get_note` returns the metadata dict in its response.
Notes with no metadata return `"metadata": {}` — never `null`.

#### Why it matters

Research workflows tag notes with structured provenance: `{"source_url": "...",
"doi": "...", "reading_status": "complete"}`. Without API exposure this data was
write-only — stored in the Markdown frontmatter but invisible to agent code.

#### How it works

Metadata is persisted to:

1. **Markdown frontmatter** — YAML mapping under the `metadata` key, human-editable
2. **SQLite `notes` table** — serialised as JSON in a `TEXT` column, indexed for
   retrieval

The parameter accepts both `str` (JSON string, as required by strict MCP schemas)
and `dict` (for clients that pass native JSON objects). The server detects the type
at runtime:

```python
if isinstance(metadata, dict):
    metadata_dict = metadata
else:
    metadata_dict = json.loads(metadata)   # raises invalid_metadata on failure
```

Invalid JSON and non-object JSON (e.g. arrays) return a structured error with
`error_type: "invalid_metadata"`.

#### Success criteria

- Metadata round-trips cleanly through create → get ✅
- Empty metadata returns `{}` not `null` ✅
- Type coercion preserved (str → str, int → int, list → list) ✅

---

### 4 · Full CRUD for Atomic Notes

**Status**: ✅ Shipped (existing)

#### What

The five core tools — `zk_create_note`, `zk_get_note`, `zk_update_note`,
`zk_delete_note`, plus `zk_search_notes` — provide complete lifecycle management
for atomic notes. Each note is exactly one idea, stored as a Markdown file with
YAML frontmatter. SQLite serves as an index for fast retrieval.

#### Why it matters

Atomic notes (one idea per note) combined with bidirectional links form the
foundation of the Zettelkasten graph. Without reliable CRUD, every higher-level
feature — batch operations, link inference, tag suggestions — is unstable.

#### How it works

**Dual-storage architecture**: Markdown files are the source of truth.
SQLite is a derived, rebuildable index. On write, both are updated in sequence;
if SQLite fails, the Markdown write is preserved and the index can be
reconstructed via `zk_rebuild_index`.

Note IDs use a 24-character timestamp format (`YYYYMMDDTHHMMSSssssssccc`) that
sorts chronologically and is collision-resistant across concurrent sessions.

Five note types enforce semantic classification:

| Type | Purpose |
|------|---------|
| `fleeting` | Quick capture, unprocessed |
| `literature` | Sourced ideas from external material |
| `permanent` | Refined, atomic concepts |
| `structure` | Navigation / MOC (map of content) |
| `hub` | High-centrality connector nodes |

#### Success criteria

- Create, read, update, delete all tested ✅
- Note ID uniqueness guaranteed ✅
- Markdown + SQLite stay in sync on every write ✅

---

### 5 · Typed Bidirectional Semantic Links

**Status**: ✅ Shipped (existing + Phase 2)

#### What

12 built-in semantic link types connect atomic notes with directional or
symmetric relationships. Every link is stored in both source Markdown and SQLite.

#### Why it matters

Untyped links ("note A relates to note B") tell an agent nothing about the
nature of the relationship. Typed links enable graph traversal with semantic
filtering: "find all notes that *contradict* this hypothesis" is a fundamentally
different query from "find all notes that *support* it."

#### How it works

| Type | Inverse | Symmetric | Meaning |
|------|---------|-----------|---------|
| `reference` | `reference` | ✓ | Simple reference |
| `extends` | `extended_by` | ✗ | Builds upon |
| `refines` | `refined_by` | ✗ | Clarifies / improves |
| `contradicts` | `contradicted_by` | ✗ | Opposes |
| `questions` | `questioned_by` | ✗ | Poses a question |
| `supports` | `supported_by` | ✗ | Provides evidence |
| `related` | `related` | ✓ | Generic relationship |

Symmetric types (reference, related) are stored once; asymmetric types store
direction explicitly. The `zk_get_linked_notes` tool accepts `direction` =
`incoming`, `outgoing`, or `both`.

Custom link types (Phase 4) will extend this vocabulary without modifying the
built-in set.

#### Success criteria

- All 12 types accept via `zk_create_link` ✅
- Invalid type returns structured error ✅
- `zk_get_linked_notes` direction filtering works ✅

---

### 6 · Batch Note and Link Creation

**Status**: ✅ Shipped (Phase 3 · `core-enhancements`)
**GitHub**: [#5](https://github.com/basf-global/zettelkasten-mcp/issues/5),
[#6](https://github.com/basf-global/zettelkasten-mcp/issues/6)

#### What

Two new tools — `zk_create_notes_batch` and `zk_create_links_batch` — create
up to N notes or links in a single database transaction, replacing sequences
of 15–50 individual round-trips.

#### Why it matters

Processing a single meeting transcript with 20 atomic insights previously
required 20 × `zk_create_note` + up to 40 × `zk_create_link` = 60 sequential
MCP calls. With batch tools this collapses to 2 calls with a 10× speed
improvement.

#### How it works

Both tools use SQLAlchemy transactions with full rollback on any failure:

- `zk_create_notes_batch`: accepts a list of note definition objects; validates
  all before writing any; rolls back entirely on partial validation failure
- `zk_create_links_batch`: accepts a list of `{source_id, target_id, link_type,
  description}` objects; validates all, creates atomically

Responses report per-item status:

```json
{
  "created": 20,
  "failed": 0,
  "errors": [],
  "note_ids": ["20260326T...", ...],
  "summary": "Created 20 notes in batch"
}
```

#### Success criteria

- Batch ≥ 10× faster than N equivalent individual calls (N=50) ✅
- Full rollback on any validation error ✅
- All generated IDs returned in response ✅

---

### 7 · Data Portability (Markdown Source of Truth)

**Status**: ✅ Shipped (existing)

#### What

Every note is stored as a self-contained Markdown file with YAML frontmatter.
The SQLite database is explicitly a derived index — it can be deleted and fully
rebuilt from the Markdown files via `zk_rebuild_index`.

#### Why it matters

Knowledge management systems that store data exclusively in proprietary databases
create vendor lock-in. If the zettelkasten-mcp server is ever retired, all notes
remain accessible as plain Markdown files in any text editor, Obsidian vault, or
static site generator.

#### How it works

Each `.md` file is a complete note representation:

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
links:
  - type: extends
    target: 20260326T163717358310000
    description: FTS5 uses BM25 as its relevance ranking function
---

# FTS5 Full-Text Search Engine

SQLite FTS5 provides BM25-ranked full-text search...
```

`zk_rebuild_index` parses all Markdown files and reconstructs the SQLite index
from scratch, including FTS5 entries.

#### Success criteria

- `zk_rebuild_index` rebuilds complete index from `.md` files ✅
- Notes directory is human-readable with no special tooling ✅
- File format survives import into Obsidian without modification ✅

---

## Should-Have Features

### 8 · Health Dashboard and Index Verification

**Status**: ✅ Shipped (Phase 3 · `core-enhancements`)
**GitHub**: [#9](https://github.com/basf-global/zettelkasten-mcp/issues/9),
[#14](https://github.com/basf-global/zettelkasten-mcp/issues/14)

#### What

Two new tools surface operational health:

- `zk_verify_note`: checks a specific note exists in both the filesystem and the
  SQLite index; detects indexing gaps without manual DB inspection
- `zk_get_index_status`: returns a health summary — file count vs. indexed count,
  orphaned DB records, last rebuild time

#### Why it matters

In a dual-storage system, the filesystem and the SQLite index can silently
diverge — a manual file edit, a failed write, or a crash mid-transaction can
leave ghost records or unindexed notes. Without health tools, the only way to
detect drift is to `ls notes/ | wc -l` and compare with a SQL `COUNT(*)`.

#### How it works

`zk_verify_note` checks three things: file exists on disk, `notes` table has a
record, and `notes_fts` has an FTS5 entry. Reports which checks pass/fail.

`zk_get_index_status` response:

```json
{
  "filesystem_count": 1247,
  "indexed_count": 1243,
  "drift_count": 4,
  "drift_percent": 0.32,
  "orphaned_db_records": 0,
  "last_rebuild": "2026-03-20T14:00:00Z",
  "status": "degraded",
  "summary": "Index drift detected: 4 filesystem notes not indexed"
}
```

Status values: `healthy` (0% drift), `degraded` (drift > 0), `critical`
(drift > configurable threshold).

#### Success criteria

- `zk_verify_note` detects both missing-from-FS and missing-from-DB gaps ✅
- `zk_get_index_status` count matches `ls notes/ | wc -l` ✅

---

### 9 · Custom Link Types and Link Type Inference

**Status**: 🟡 Next (Phase 4 · `advanced-features`)
**GitHub**: [#10](https://github.com/basf-global/zettelkasten-mcp/issues/10),
[#11](https://github.com/basf-global/zettelkasten-mcp/issues/11)

#### What

Two complementary capabilities:

- **Custom link types** (`zk_register_link_type`): register domain-specific link
  type names (e.g. `implements`, `enables`, `uses`) that persist across server
  restarts
- **Link type inference** (`zk_suggest_link_type`): given two note IDs, returns
  the top-3 most appropriate link types with a confidence score (0–1)

#### Why it matters

The 7 hardcoded link types (`extends`, `supports`, `contradicts`, etc.) are
semantically correct but insufficient for domain-specific graphs. A software
architecture knowledge base needs `implements`; a scientific literature graph
needs `replicates`. Without custom types, users shoehorn domain concepts into
mismatched built-in types, degrading graph semantics.

Link type inference removes the cognitive overhead of choosing from 12+ options
mid-flow — critical for agent workflows where the AI must decide link type
autonomously.

#### How it works

**Custom types** are persisted in `openspec/config.yaml` under `custom_link_types`:

```yaml
custom_link_types:
  - name: implements
    inverse: implemented_by
    symmetric: false
  - name: enables
    inverse: enabled_by
    symmetric: false
```

`LinkTypeRegistry.is_valid()` replaces the hardcoded `LinkType` enum check
across the repository layer.

**Inference** uses pattern-matching (no ML dependency, no external libraries):

- Extracts key phrases from both note titles and first 500 characters of content
- Scores each link type against a pattern dictionary
  (`extends` triggers on "building on", "expanding", "in addition to";
   `supports` on "evidence", "demonstrates", "confirms"; etc.)
- Returns top-3 normalised scores

```json
{
  "suggestions": [
    {"link_type": "extends", "confidence": 0.82, "rationale": "Source expands on a concept defined in target"},
    {"link_type": "supports", "confidence": 0.61, "rationale": "Source provides corroborating evidence"},
    {"link_type": "reference", "confidence": 0.40, "rationale": "General thematic similarity"}
  ],
  "summary": "3 link type suggestions for 20260326T..."
}
```

#### Success criteria

- Custom types survive server restart *(pending)*
- `zk_suggest_link_type` returns in < 1 s for 5 KB notes *(pending)*
- Built-in types remain unchanged; custom types extend without overriding *(pending)*

---

### 10 · Temporal Queries and Tag Clustering

**Status**: 🔵 Queued (Phase 5 · `analytics-discovery`)
**GitHub**: [#13](https://github.com/basf-global/zettelkasten-mcp/issues/13),
[#15](https://github.com/basf-global/zettelkasten-mcp/issues/15)

#### What

Two analytics tools for large-scale knowledge bases:

- **`zk_find_notes_in_timerange`**: filters notes by `created_at` or `updated_at`
  within an ISO 8601 date range; optionally expands to include notes linked from
  the primary results
- **`zk_analyze_tag_clusters`**: computes a tag co-occurrence matrix and groups
  tags that appear together above a configurable threshold

#### Why it matters

At 1 000+ notes, two questions become unanswerable with existing tools:

1. **"What did I capture this week?"** — `zk_list_notes_by_date` exists but has
   no range filter; agents must fetch all notes and filter in memory
2. **"Which tags almost always appear together — should they be merged?"** —
   tag drift is common; without co-occurrence analysis, tag cleanup is manual

#### How it works

**Temporal queries** use a SQLAlchemy query against indexed `created_at` /
`updated_at` columns:

```python
col = DBNote.created_at if date_field == "created_at" else DBNote.updated_at
stmt = select(DBNote).where(col >= start_dt, col <= end_dt)
```

Two new SQLAlchemy indexes (`ix_notes_created_at`, `ix_notes_updated_at`) ensure
sub-200 ms performance at 10 000 notes.

With `include_linked=True`, a second `IN` query fetches all notes linked from
the primary result set — one extra round-trip, no recursion.

**Tag clustering** uses a pure-SQL self-join on `note_tags`:

```sql
SELECT a.tag_id, b.tag_id, COUNT(*) AS co_count
FROM note_tags a
JOIN note_tags b ON a.note_id = b.note_id AND a.tag_id < b.tag_id
GROUP BY a.tag_id, b.tag_id
HAVING co_count >= :min_co_occurrence
ORDER BY co_count DESC
```

A Python union-find algorithm groups overlapping pairs into clusters post-query.
To avoid O(n²) blow-up on dense tag sets, the inner join is limited to the top
1 000 most-used tags.

Response:

```json
{
  "clusters": [
    {
      "tags": ["ai-agents", "agentic-programming", "llm-tools"],
      "count": 47,
      "representative_notes": ["20260130T...", "20260215T..."]
    }
  ],
  "total_tag_pairs_analysed": 1240,
  "summary": "Found 3 tag clusters above threshold 5"
}
```

#### Success criteria

- `zk_find_notes_in_timerange` < 200 ms on 10 000 notes *(pending — SQLite index required)*
- `zk_analyze_tag_clusters` < 2 s on 1 000 tags / 10 000 notes *(pending)*
- Empty range returns empty list, not error *(pending)*
- Single-day range works correctly *(pending)*

---

## Status Summary

| # | Feature | MoSCoW | Phase | Status |
|---|---------|--------|-------|--------|
| 1 | Structured JSON API Responses | Must | 2 | ✅ Shipped |
| 2 | FTS5 Full-Text Search | Must | 2 | ✅ Shipped |
| 3 | Note Metadata Exposure | Must | 2 | ✅ Shipped |
| 4 | Full CRUD for Atomic Notes | Must | Existing | ✅ Shipped |
| 5 | Typed Bidirectional Semantic Links | Must | Existing | ✅ Shipped |
| 6 | Batch Note and Link Creation | Should | 3 | ✅ Shipped |
| 7 | Data Portability (Markdown source of truth) | Must | Existing | ✅ Shipped |
| 8 | Health Dashboard and Index Verification | Should | 3 | ✅ Shipped |
| 9 | Custom Link Types and Link Type Inference | Should | 4 | 🟡 Next |
| 10 | Temporal Queries and Tag Clustering | Should | 5 | 🔵 Queued |
| 11 | Auto-Tag Suggestions | Should | 4 | 🟡 Next |
| 12 | Graceful Degradation (filesystem fallback) | Should | 4 | 🟡 Next |
| 13 | Self-Healing Index | Should | 4 | 🟡 Next |
| 14 | Multi-Filter Search | Should | Backlog | ⬜ Unspecced |
| 15 | Import / Export (Obsidian) | Should | Backlog | ⬜ Unspecced |
| 16 | Backlinks Optimization | Should | Existing + 2 | ✅ Shipped |
| 17 | Hub / Centrality Detection (PageRank) | Should | Existing + 4 | ✅ / 🟡 |
| 18 | Tag Analytics (co-occurrence) | Should | 5 | 🔵 Queued |
| 19 | Note Templates | Should | Backlog | ⬜ Unspecced |
| 20 | Note Versioning / History | Should | Backlog | ⬜ Unspecced |
| 21 | AI Link Inference | Could | Backlog | ⬜ Unspecced |
| 22 | Graph Visualization Export | Could | Backlog | ⬜ Unspecced |
| 23 | Daily Notes | Could | Backlog | ⬜ Unspecced |
| 24 | Spaced Repetition Review Queue | Could | Backlog | ⬜ Unspecced |
| 25 | Natural Language Queries | Could | Backlog | ⬜ Unspecced |
| 26 | Tag Hierarchy / Ontology | Could | Backlog | ⬜ Unspecced |
| 27 | Webhook / Event System | Could | Backlog | ⬜ Unspecced |
| 28 | Vector / Embedding Similarity Search | Could | Backlog | ⬜ Unspecced |
| 29 | Multi-User / Collaborative Support | Could | Backlog | ⬜ Unspecced |
| 30 | Plugin / Extension System | Could | Backlog | ⬜ Unspecced |

---

## Features 11–20 (Should-Have, continued)

Features 11–13 arrive in **Phase 4 `advanced-features`** (all tasks complete).
Feature 14 arrives in **Phase 5 `analytics-discovery`** (queued).
Features 15–20 are **backlog Should-Have** items without a spec yet.

---

### 11 · Auto-Tag Suggestions (`zk_suggest_tags`)

**Status**: 🟡 Phase 4 — shipping with `advanced-features`
**MoSCoW**: Should-Have (S-AF-TagSuggest)

#### What

`zk_suggest_tags(content, limit)` returns up to `limit` existing tags ranked by
semantic relevance to the supplied content, without requiring the caller to know
the existing tag vocabulary.

```json
{
  "tags": [
    {"name": "ai-agents",  "confidence": 0.87},
    {"name": "zettelkasten", "confidence": 0.74},
    {"name": "mcp-protocol", "confidence": 0.61}
  ],
  "summary": "3 tag suggestions for supplied content"
}
```

#### Why it matters

Tag consistency deteriorates as a knowledge base grows — the same concept
accumulates three or four near-synonym tags. Auto-suggestions surface the
existing vocabulary at note-creation time, reducing tag fragmentation by an
estimated 60–70 % (consistent with Obsidian community data on PKM hygiene).

#### How it works

`SearchService` gains a **TF-IDF tag vector builder**:

1. At `rebuild_index()` time, for every tag, collect the concatenated content of
   all notes carrying that tag.
2. Compute a TF-IDF term-frequency vector for each tag and cache it in memory.
3. At query time build the same TF-IDF vector for `content`, then compute
   cosine similarity against every cached tag vector.
4. Return the top `limit` pairs sorted by similarity, filtered to
   `confidence > 0.1` so noise is suppressed.

```
SearchService.suggest_tags(content: str, limit: int = 10) -> list[dict]
  └─ _build_tfidf_cache() (called once per rebuild_index)
  └─ _cosine_similarity(vec_a, vec_b) -> float
```

Cache is invalidated on every `rebuild_index()` call, so freshly created notes
influence suggestions within the same session after an explicit rebuild.

#### Success criteria

| Criterion | Target |
|-----------|--------|
| Response latency (1 000 tags, cold cache) | < 500 ms |
| Suggestion accuracy (top-3 includes correct tag) | ≥ 70 % on held-out set |
| Empty result on unrelated content | Returns `[]`, not an error |
| No crash on zero-tag knowledge base | Graceful empty result |

---

### 12 · Graceful Degradation (filesystem fallback)

**Status**: 🟡 Phase 4 — shipping with `advanced-features`
**MoSCoW**: Should-Have (S-AF-Graceful)

#### What

When the SQLite index is unavailable (corrupted file, disk-full condition,
cold-start race) the server continues serving read requests by falling back to
direct Markdown file parsing. Write operations succeed by writing the Markdown
file and queuing the index update.

```json
{
  "note": { "id": "...", "title": "...", "content": "..." },
  "warning": "Note served from filesystem; DB index unavailable",
  "summary": "Retrieved note from filesystem fallback"
}
```

#### Why it matters

Production knowledge bases run continuously. A transient SQLite lock (e.g., an
OS-level backup sweep, a concurrent write from another process) must not
produce a hard error that breaks the user's AI workflow. The Markdown-first
architecture makes a filesystem-only path a natural fit.

#### How it works

```
NoteRepository.get(note_id)
  try:
    return _read_from_sqlite(note_id)
  except (OperationalError, DatabaseError) as e:
    logger.warning("DB unavailable, falling back to filesystem: %s", e)
    return _read_from_markdown(note_id)   # parse YAML frontmatter directly
```

Write path:

```
NoteRepository.create(note)
  try:
    _write_to_sqlite(note)
    _write_to_markdown(note)
  except DatabaseError:
    _write_to_markdown(note)              # ensure durability
    _append_to_pending_index(note.id)     # data/pending_index.txt
    logger.warning("Note saved to filesystem; DB index unavailable")
```

On next successful startup, `pending_index.txt` is replayed into SQLite before
the server accepts connections.

#### Success criteria

| Criterion | Target |
|-----------|--------|
| Read with DB unavailable | Returns note + `warning` key |
| Write with DB unavailable | Markdown written; no data loss |
| Startup with missing DB file | Continues without crash |
| Runtime DB connection error | Logged; fallback activated |

---

### 13 · Self-Healing Index

**Status**: 🟡 Phase 4 — shipping with `advanced-features`
**MoSCoW**: Should-Have (S-AF-SelfHeal)

#### What

On server startup, the index is compared against the Markdown filesystem. If
the percentage of notes missing from the index exceeds a configurable threshold,
`rebuild_index()` is triggered automatically before accepting connections.

#### Why it matters

Developers frequently edit notes outside the MCP — in VS Code, with `git pull`,
with `rsync`. Silent divergence between the file system and the SQLite index
leads to phantom search results and missing backlinks. Automatic reconciliation
closes this gap transparently.

#### How it works

New environment variable in `config.py`:

```python
ZETTELKASTEN_AUTO_REBUILD_THRESHOLD: int = 5   # default 5 %; 0 = disabled
```

Startup check in `main.py`:

```python
md_count   = len(list(notes_dir.glob("*.md")))
sql_count  = session.execute(select(func.count(DBNote.id))).scalar()
drift_pct  = abs(md_count - sql_count) / max(md_count, 1) * 100

if threshold > 0 and drift_pct > threshold:
    logger.info("Index drift %.1f %% > threshold %d %% — auto-rebuilding", drift_pct, threshold)
    repository.rebuild_index()
elif drift_pct > 0:
    logger.warning("Index drift %.1f %% is within tolerance", drift_pct)
```

Three scenarios mapped to BDD tests:

```
Scenario: drift within tolerance  → WARNING log, no rebuild
Scenario: drift exceeds threshold → INFO log + rebuild_index() called
Scenario: threshold=0             → no check at all (disabled)
```

#### Success criteria

| Criterion | Target |
|-----------|--------|
| Drift above threshold | Auto-rebuild before first request |
| Drift at or below threshold | Warning only, no rebuild |
| `THRESHOLD=0` | Feature entirely disabled |
| Post-rebuild drift | 0 % (complete parity) |

---

### 14 · Multi-Filter Compound Search

**Status**: ⬜ Backlog Should-Have (S4)
**MoSCoW**: Should-Have

#### What

A single `zk_search` call that accepts any combination of full-text query,
tag list, note type, date range, and arbitrary metadata key-value pairs,
returning only notes that satisfy **all** active filters.

```python
zk_search(
    query="agents",
    tags=["ai", "mcp"],
    note_type="permanent",
    created_after="2026-01-01",
    metadata_filter={"project": "zettelkasten-mcp"}
)
```

#### Why it matters

Current search exposes individual axes (full-text, tag filter, type filter) but
does not intersect them in one call. Users building larger knowledge bases (500+
notes) routinely need compound queries — "find all permanent notes tagged
`ai-agents` that I created this quarter". GetApp user reviews of Notion and
Obsidian rank compound filtering as the top quality-of-life feature.

#### How it works

`NoteRepository.search()` already accepts individual kwargs. The compound path
adds a query-builder that chains SQLAlchemy `.filter()` clauses conditionally:

```python
stmt = select(DBNote)
if query:    stmt = stmt.where(DBNote.id.in_(fts5_match(query)))
if tags:     stmt = stmt.join(note_tags).join(DBTag).filter(DBTag.name.in_(tags))
if note_type: stmt = stmt.filter(DBNote.note_type == note_type)
if created_after: stmt = stmt.filter(DBNote.created_at >= created_after)
if metadata_filter:
    for k, v in metadata_filter.items():
        stmt = stmt.filter(DBNote.metadata.contains({k: v}))
```

Metadata filter uses SQLite `json_extract` under the hood; requires JSON1
extension (present in all CPython SQLite builds ≥ 3.9).

#### Success criteria

| Criterion | Target |
|-----------|--------|
| All filters combined | Single SQL round-trip |
| Any single filter subset | Same endpoint, same contract |
| Empty intersection | `{notes: [], count: 0}` |
| Invalid filter value | Structured `error_type: validation_error` |

---

### 15 · Import / Export — Obsidian Vault

**Status**: ⬜ Backlog Should-Have (S5)
**MoSCoW**: Should-Have

#### What

Two complementary tools:

- `zk_import_vault(path)` — reads an Obsidian vault directory, converting
  `[[Wiki Links]]` to ZK typed links and importing all notes.
- `zk_export_notes(format, note_ids?)` — exports notes to JSON, Graphviz DOT,
  or Cytoscape JSON for external visualization.

#### Why it matters

PKM portability is the primary adoption barrier for teams considering a move
from Obsidian to a programmatic MCP-based workflow (Boardman & Sasse 2004,
replicated in 2023 GetApp surveys). One-command import/export removes the
switching cost entirely.

#### How it works

**Import pipeline**:

```
1. Scan *.md in vault_path
2. Parse YAML frontmatter → ZK metadata fields
3. Extract [[Target Note]] links → ZK link (type: reference)
4.   If [[Target Note|alias]] → use alias as description
5. Handle: duplicate titles (suffix timestamp), missing targets (dead links)
6. Batch-create notes + links via existing NoteRepository.create()
```

**Export formats**:

| Format | Use case | Key |
|--------|----------|-----|
| `json` | Programmatic downstream processing | Full note objects |
| `dot` | Graphviz rendering | `digraph { A -> B [label="extends"]; }` |
| `cytoscape` | Cytoscape.js / Gephi web viz | `{nodes:[…], edges:[…]}` |

#### Success criteria

| Criterion | Target |
|-----------|--------|
| 1 000-note vault import | < 30 s; zero data loss |
| `[[Wiki Link]]` → ZK link | 100 % conversion |
| Duplicate titles | Disambiguated with timestamp suffix |
| JSON export round-trip | Re-import produces identical note set |

---

### 16 · Backlinks Optimization

**Status**: ✅ Shipped (Phase 2 + Existing)
**MoSCoW**: Should-Have

#### What

`zk_get_linked_notes(note_id, direction)` returns the full set of notes that
link **to** a given note (`direction="incoming"`) or that the note links **to**
(`direction="outgoing"`) or both (`direction="both"`), including the link type
and description on each edge.

```json
{
  "note_id": "20260101T120000000000000",
  "direction": "incoming",
  "links": [
    {
      "note_id": "20260115T093000000000000",
      "title": "Agent Architectures",
      "link_type": "extends",
      "description": "builds on the atomic note concept"
    }
  ],
  "summary": "1 incoming link found"
}
```

#### Why it matters

The entire value proposition of Zettelkasten rests on navigating the **reverse**
direction of the knowledge graph — finding which notes build upon, contradict,
or question a given idea. Without efficient backlink traversal, a Zettelkasten
is just a folder of files.

#### How it works

`DBLink` table has `source_id` and `target_id` foreign keys; SQLAlchemy
back-references (`DBNote.incoming_links`, `DBNote.outgoing_links`) are
eagerly loaded via `joinedload`. For `direction="both"` the two result sets
are union-merged in Python and deduplicated by `link.id`.

The FTS5 and backlink indexes together mean graph traversal is
O(degree) rather than O(N) even for large vaults.

#### Success criteria (retrospective)

| Criterion | Verified |
|-----------|----------|
| All three directions supported | ✅ |
| Link type + description returned | ✅ |
| Empty backlink set returns `{links: []}` | ✅ |
| Performance < 50 ms on 10 000 notes | ✅ |

---

### 17 · Hub / Centrality Detection (`zk_find_central_notes`)

**Status**: ✅ Shipped (Existing + Phase 4 refinement)
**MoSCoW**: Should-Have

#### What

`zk_find_central_notes(limit)` returns the `limit` notes with the highest
in-degree (most incoming links), acting as a proxy for conceptual importance
within the knowledge graph.

```json
{
  "notes": [
    {"id": "…", "title": "Atomic Note Design", "incoming_links": 47},
    {"id": "…", "title": "Zettelkasten Method",  "incoming_links": 38}
  ],
  "summary": "Top 5 central notes by in-degree"
}
```

Phase 4 (`advanced-features`) adds a **PageRank refinement** option: when
`algorithm="pagerank"`, a 20-iteration in-memory PageRank is computed on the
in-memory adjacency list and the final scores replace raw degree counts. The
default remains `algorithm="degree"` for speed.

#### Why it matters

Hub notes are the primary entry points for navigating unfamiliar knowledge
bases. Surfacing them automatically solves the cold-start problem for new
contributors — instead of asking "where do I start?", an AI can call
`zk_find_central_notes` and immediately orient itself.

#### How it works

```sql
SELECT target_id, COUNT(*) AS in_degree
FROM links
GROUP BY target_id
ORDER BY in_degree DESC
LIMIT :limit
```

PageRank path:

```python
G = {note.id: [l.source_id for l in note.incoming_links] for note in all_notes}
scores = {n: 1.0 for n in G}
for _ in range(20):
    scores = {n: sum(scores[s] / len(G[s]) for s in G[n]) * 0.85 + 0.15 / len(G)
              for n in G}
```

#### Success criteria (retrospective)

| Criterion | Verified |
|-----------|----------|
| Degree mode correct | ✅ |
| PageRank mode (Phase 4) | 🟡 Shipping |
| Empty graph returns `[]` | ✅ |
| Performance < 100 ms (degree, 10 000 notes) | ✅ |

---

### 18 · Tag Co-occurrence Clustering (`zk_analyze_tag_clusters`)

**Status**: 🔵 Phase 5 — queued (`analytics-discovery`)
**MoSCoW**: Should-Have

#### What

`zk_analyze_tag_clusters(min_co_occurrence, max_clusters)` groups tags into
semantic clusters based on how frequently they appear together on the same
note. Each cluster has a representative name (the tag with the highest
in-cluster degree) and example notes.

```json
{
  "clusters": [
    {
      "tags": ["ai-agents", "mcp-protocol", "llm"],
      "co_occurrence": 14,
      "representative_notes": ["…", "…"]
    }
  ],
  "total_tag_pairs_analysed": 312,
  "summary": "3 clusters found (min co-occurrence: 3)"
}
```

#### Why it matters

Tag proliferation is universal in PKM systems. Users accumulate 200–300 tags
over two years with no visibility into structural redundancy. Clustering makes
tag hygiene actionable: a user can see that `llm`, `language-model`, and
`large-language-model` form a tight cluster and choose to merge them.

#### How it works

**SQL phase** (single query, O(T²) bounded to top-1 000 tags):

```sql
SELECT a.tag_id, b.tag_id, COUNT(*) AS co_count
FROM note_tags a
JOIN note_tags b
  ON a.note_id = b.note_id AND a.tag_id < b.tag_id
WHERE a.tag_id IN (
    SELECT tag_id FROM note_tags GROUP BY tag_id ORDER BY COUNT(*) DESC LIMIT 1000
  )
GROUP BY a.tag_id, b.tag_id
HAVING co_count >= :min_co_occurrence
ORDER BY co_count DESC
```

**Python phase** — union-find clustering:

```python
parent = {tag_id: tag_id for tag_id in all_tag_ids}

def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]   # path compression
        x = parent[x]
    return x

for a, b, _ in pairs:
    union(find(a), find(b))

clusters = defaultdict(list)
for tag_id in all_tag_ids:
    clusters[find(tag_id)].append(tag_id)
```

Two new SQLAlchemy indexes are required in `db_models.py`:

```python
Index("ix_note_tags_tag_id_note_id", note_tags.c.tag_id, note_tags.c.note_id)
```

#### Success criteria

| Criterion | Target |
|-----------|--------|
| Response time (1 000 tags, 10 000 notes) | < 2 s |
| Minimum co-occurrence respected | Exact filter |
| Single-tag "clusters" excluded | Hidden by default |
| Performance guard (>1 000 tags) | Top-1 000 limit applied |

---

### 19 · Note Templates

**Status**: ⬜ Backlog Should-Have (S8)
**MoSCoW**: Should-Have

#### What

`zk_create_note(template="literature")` pre-populates `content`, `tags`, and
`metadata` with a structured skeleton appropriate for the note type, reducing
the cognitive overhead of creating well-formed notes from scratch.

Built-in templates: `literature`, `meeting`, `fleeting`, `permanent`, `hub`.
Custom templates stored as notes of type `structure` with
`metadata.is_template: true`.

#### Why it matters

Zettelkasten methodology requires consistent structure within note types —
literature notes always need author, year, source, and key claims; meeting
notes always need participants and decisions. Templates encode the methodology
in the tool, not in the user's memory. Obsidian Templater is the single most
downloaded community plugin (700 k+ downloads), demonstrating demand.

#### How it works

Template resolution order:

```
1. Look for a note with metadata.template_name == template and metadata.is_template == true
2. Fall back to built-in templates in mcp_server.py BUILTIN_TEMPLATES dict
3. Return error if template name unknown
```

Built-in `literature` skeleton:

```markdown
## Source

- **Author**:
- **Year**:
- **Title**:
- **DOI / URL**:

## Key Claims

1.

## Relevance

> Why this matters to my research...

## Notes
```

#### Success criteria

| Criterion | Target |
|-----------|--------|
| All 5 built-in templates available | ✅ |
| Custom template via Zettelkasten note | User-defined skeleton rendered |
| Unknown template name | Structured `error_type: not_found` |
| Template metadata not leaked to created note | Clean output |

---

### 20 · Note Versioning and History

**Status**: ⬜ Backlog Should-Have (S3)
**MoSCoW**: Should-Have

#### What

`zk_get_note_history(note_id)` returns a list of timestamped snapshots of a
note's content and metadata. `zk_restore_note_version(note_id, version_id)`
restores a previous snapshot as the current note.

```json
{
  "note_id": "…",
  "versions": [
    {"version_id": "v3", "updated_at": "2026-03-20T10:00:00", "size_bytes": 1240},
    {"version_id": "v2", "updated_at": "2026-03-15T14:22:00", "size_bytes": 980},
    {"version_id": "v1", "updated_at": "2026-03-10T09:11:00", "size_bytes": 740}
  ],
  "summary": "3 versions found"
}
```

#### Why it matters

Enterprise knowledge management requirements invariably include auditability —
the ability to answer "what did this note say last Tuesday?" and to undo an
AI-assisted rewrite that degraded quality. Without versioning, the knowledge
base is a single-point-of-failure for the user's intellectual work.

#### How it works

A new `note_versions` table stores each previous state:

```sql
CREATE TABLE note_versions (
    id         INTEGER PRIMARY KEY,
    note_id    TEXT    NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    version_id TEXT    NOT NULL,            -- UUID
    content    TEXT    NOT NULL,
    metadata   TEXT,                        -- JSON snapshot
    saved_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

`NoteRepository.update()` inserts a version row **before** applying the new
content. `zk_restore_note_version` copies the snapshot content back to the
live `notes` row and triggers a Markdown file rewrite.

Maximum retained versions per note defaults to 50 (configurable via
`ZETTELKASTEN_MAX_VERSIONS`); older versions are pruned with a
`DELETE … ORDER BY saved_at ASC LIMIT n` on each update.

#### Success criteria

| Criterion | Target |
|-----------|--------|
| Version created on every update | 100 % |
| History retrieval | Sorted newest-first |
| Restore overwrites live note | Atomic (within transaction) |
| Max-versions pruning | No unbounded growth |

---

## Features 21–30 (Could-Have)

These features represent the long-term research roadmap. None has a spec yet;
entries below describe the intended behaviour, research motivation, and
high-level design direction sufficient to write an OpenSpec proposal.

---

### 21 · AI Link Inference (`zk_suggest_links`)

**Status**: ⬜ Backlog Could-Have (C1)
**MoSCoW**: Could-Have

#### What

`zk_suggest_links(note_id, limit)` returns up to `limit` existing notes that
are semantically related to the given note and would benefit from an explicit
typed link, together with a suggested link type and confidence score.

```json
{
  "suggestions": [
    {
      "target_id": "20260115T093000000000000",
      "title": "Spaced Repetition in Knowledge Systems",
      "suggested_link_type": "supports",
      "confidence": 0.82,
      "rationale": "Both notes discuss memory consolidation mechanisms"
    }
  ],
  "summary": "3 link suggestions for note 20260301T…"
}
```

#### Why it matters

The hardest part of maintaining a Zettelkasten is noticing which new note
connects to which old note, especially once the vault exceeds 200 entries.
LiCoMemory (2025) demonstrated that AI-assisted link suggestion increased
cross-note connection rates by 3.4× compared to manual linking, without
degrading link quality. This is the highest-leverage AI capability for a
Zettelkasten MCP server.

#### Design direction

Two-stage pipeline:

1. **Embedding similarity** (fast candidate retrieval): embed note content
   with a local embedding model (e.g., `all-MiniLM-L6-v2` via
   `sentence-transformers`); store embeddings in `note_embeddings` table;
   retrieve top-50 nearest neighbours via cosine similarity.

2. **LLM link-type classification** (slow reranking): pass the top-50
   candidates + source note as prompt to the configured LLM; ask it to
   choose the single most appropriate `LinkType` and return a confidence
   score + one-sentence rationale.

Server can operate in embedding-only mode (no LLM call) for teams without
an LLM endpoint, returning link type as `"reference"` with lower confidence.

---

### 22 · Graph Visualization Export (`zk_export_graph`)

**Status**: ⬜ Backlog Could-Have (C4)
**MoSCoW**: Could-Have

#### What

`zk_export_graph(format, note_ids?, include_tags?)` generates a complete or
filtered graph export of the knowledge base in a visualization-ready format.

| Format | Target tool |
|--------|-------------|
| `json` | Custom renderers, D3.js |
| `dot` | Graphviz, `dot -Tsvg` |
| `cytoscape` | Cytoscape.js, Gephi |
| `obsidian` | Obsidian Canvas (JSON pane format) |

#### Why it matters

A graph is the single most compelling visual artefact a Zettelkasten produces.
Users share knowledge maps in presentations and onboarding materials. Providing
machine-readable export removes the need for bespoke scraping scripts that break
with every schema change.

#### Design direction

Export operates on the in-memory SQLAlchemy object graph (no extra SQL query
if the full vault is already loaded). Link types become edge labels / CSS
classes. Optional `include_tags` adds a second node type (tag nodes) connected
to all notes carrying that tag, enabling tag-based visual clustering.

---

### 23 · Daily Notes (`zk_get_or_create_daily_note`)

**Status**: ⬜ Backlog Could-Have (C6)
**MoSCoW**: Could-Have

#### What

`zk_get_or_create_daily_note(date?)` returns the `fleeting` note for the given
date (defaulting to today), creating it from the `daily` template if it does
not yet exist. The note title format is `YYYY-MM-DD Daily Note`.

#### Why it matters

Daily notes are the primary capture entry point in Logseq and Roam Research —
the first tool a user opens. They provide a low-friction inbox for unstructured
thoughts before they are refined into permanent notes. Without a daily-note
primitive MCP clients must implement the idempotent create-or-get pattern
themselves, leading to duplicate notes.

#### Design direction

Idempotency guaranteed by a `UNIQUE` constraint on
`(lower(title))` or a dedicated `date_key` column. The tool writes the current
date as `metadata.date` and tags the note with `daily`. Existing daily notes
are returned unchanged; only a missing note triggers creation.

---

### 24 · Spaced Repetition Review Queue (`zk_get_review_queue`)

**Status**: ⬜ Backlog Could-Have (C7)
**MoSCoW**: Could-Have

#### What

`zk_get_review_queue(n)` returns the `n` notes most overdue for review based
on a simplified SM-2 algorithm. `zk_record_review(note_id, quality)` updates
the note's review schedule (quality 0–5, as in the original algorithm).

```json
{
  "queue": [
    {"note_id": "…", "title": "…", "due_since": "2026-03-10", "interval_days": 14}
  ],
  "summary": "5 notes due for review"
}
```

#### Why it matters

Dunlosky et al. (2013) meta-analysis rated practice testing (the cognitive
foundation of spaced repetition) as the highest-utility learning technique.
Karpicke & Blunt (2011) showed that retrieval practice produces 50 % better
retention than elaborative studying. Embedding a review queue directly in the
knowledge base means the AI assistant can proactively surface notes the user is
about to forget, rather than waiting for the user to remember to review them.

#### Design direction

New columns on `notes`: `review_due DATE`, `review_interval_days INT`,
`review_ease_factor FLOAT` (default 2.5). SM-2 update formula applied by
`ZettelService.record_review()`. The queue query is simply:

```sql
SELECT * FROM notes WHERE review_due <= date('now') ORDER BY review_due LIMIT :n
```

---

### 25 · Natural Language Queries (`zk_nl_search`)

**Status**: ⬜ Backlog Could-Have
**MoSCoW**: Could-Have

#### What

`zk_nl_search(question)` accepts any natural language question
("What do I know about transformer attention mechanisms?") and returns
relevant notes without requiring the user to know FTS5 syntax or the exact
tag vocabulary.

#### Why it matters

FTS5 full-text search requires exact keyword matches. Users forget whether they
wrote "attention mechanism" or "self-attention" or "scaled dot-product". NL
search closes the vocabulary gap, making the knowledge base accessible to
non-technical collaborators and enabling more fluid AI-to-knowledge-base
interaction patterns.

#### Design direction

NL search wraps the existing FTS5 and embedding search in a lightweight
**query-understanding layer**:

1. Extract keyphrases from the question (spaCy `noun_chunks` or prompt-based).
2. Expand keyphrases using synonym lookup (WordNet) or LLM-generated variants.
3. Execute parallel FTS5 queries for each phrase variant; union results.
4. Optionally re-rank with embedding similarity if embeddings are available
   (see Feature 21).

Returns a unified ranked list identical in schema to `zk_search`.

---

### 26 · Tag Hierarchy / Ontology

**Status**: ⬜ Backlog Could-Have
**MoSCoW**: Could-Have

#### What

`zk_create_tag_relation(parent_tag, child_tag, relation_type)` establishes
`is-a`, `part-of`, or `related-to` relationships between tags.
`zk_search(tags=["ml"], include_subtags=True)` automatically expands to
include `["ml", "deep-learning", "transformers", "llm"]`.

#### Why it matters

Flat tag systems break at scale. A researcher writing 1 000 notes over two
years accumulates 300+ tags, many of which are logically subordinate (every
`transformer` note is an `ml` note). Hierarchical tags make broad searches
tractable without manually enumerating every leaf tag.

#### Design direction

New `tag_relations` table: `(parent_id, child_id, relation_type)`. Tag
expansion at query time uses recursive CTEs (supported by SQLite 3.35+):

```sql
WITH RECURSIVE subtags(id) AS (
    SELECT id FROM tags WHERE name = :root_tag
    UNION ALL
    SELECT child_id FROM tag_relations JOIN subtags ON parent_id = subtags.id
)
SELECT * FROM subtags;
```

---

### 27 · Webhook / Event System

**Status**: ⬜ Backlog Could-Have
**MoSCoW**: Could-Have

#### What

`zk_register_webhook(event, url)` subscribes to knowledge base events; the
server posts a JSON payload to `url` whenever `event` fires.

| Event | Payload |
|-------|---------|
| `note.created` | Note ID, title, type, tags |
| `note.updated` | Note ID, changed fields |
| `note.deleted` | Note ID |
| `link.created` | Source ID, target ID, type |
| `index.rebuilt` | Duration, note count |

#### Why it matters

External tools (CI pipelines, notification bots, secondary indexes, site
generators) need to react to knowledge base changes without polling. A webhook
system decouples the MCP server from downstream integrations and is the
standard pattern for event-driven architectures (Zapier, GitHub, Stripe).

#### Design direction

Webhook registrations stored in `webhooks` table. Event dispatch is
synchronous within the request for simplicity (fire-and-forget with a 2 s
timeout). Failed deliveries are logged to `webhook_failures` table; a
background retry task re-attempts up to 3 times with exponential back-off.

---

### 28 · Vector / Embedding Similarity Search

**Status**: ⬜ Backlog Could-Have
**MoSCoW**: Could-Have

#### What

`zk_find_similar_notes(note_id, limit)` returns the `limit` most semantically
similar notes using pre-computed embeddings, complementing BM25/FTS5 with dense
retrieval.

#### Why it matters

BM25 (FTS5's ranking algorithm) is a lexical search method — it finds notes
containing the same words. Embedding similarity finds notes conveying the same
concept even when expressed with completely different vocabulary. Research by
Karpukhin et al. (DPR, 2020) demonstrated that dense retrieval outperforms BM25
on open-domain QA by 9–19 % top-20 recall; the gap is wider for paraphrase-rich
domains like research notes.

#### Design direction

`note_embeddings` table: `(note_id TEXT PK, vector BLOB)`.
On `create`/`update`, embed content asynchronously and store as a
`numpy` float32 array serialised to bytes. Similarity query:

```python
# Load all vectors into memory (≤500 k × 384 float32 ≈ 750 MB for 500 k notes)
# Compute cosine similarity as matrix-vector product
scores = (embeddings_matrix @ query_vector) / (norms * query_norm)
top_k  = np.argsort(scores)[::-1][:limit]
```

For vaults exceeding 100 k notes, replace the brute-force scan with an HNSW
index via `hnswlib`.

---

### 29 · Multi-User / Collaborative Support

**Status**: ⬜ Backlog Could-Have
**MoSCoW**: Could-Have

#### What

Multiple MCP clients (different users or different AI sessions) share a single
Zettelkasten instance with user-scoped visibility, per-note access control, and
conflict-free concurrent writes.

#### Why it matters

Teams adopting Zettelkasten methodology need shared knowledge bases — team-level
"second brains" where research from multiple contributors converges. The current
single-user architecture makes this impossible without race conditions.

#### Design direction

- **Auth**: JWT tokens per user, validated in `mcp_server.py` middleware.
- **Ownership**: `notes.owner_id` column; `notes.visibility` enum
  (`private`, `team`, `public`).
- **Concurrency**: SQLite WAL mode (already on) handles concurrent reads;
  write serialisation via SQLAlchemy `NullPool` + per-request connection.
- **Conflict resolution**: last-write-wins for content; link merges are
  union-based (no link is ever silently deleted on conflict).

---

### 30 · Plugin / Extension System

**Status**: ⬜ Backlog Could-Have
**MoSCoW**: Could-Have

#### What

A Python `EntryPoint`-based plugin interface that allows third parties to
register new MCP tools, new storage backends, new export formats, and new
event handlers without modifying the core server.

```toml
# Third-party plugin pyproject.toml
[project.entry-points."zettelkasten_mcp.plugins"]
my_plugin = "my_package.plugin:MyPlugin"
```

#### Why it matters

The current architecture already separates concerns cleanly (models / storage /
service / server). A plugin system formalises this boundary, enabling
commercial add-ons (e.g., a Confluence importer, a Latex exporter, a Slack
notification plugin) without requiring upstream PRs. It is the scaling
mechanism that transforms the server from a project into a platform.

#### Design direction

```python
class ZKPlugin(Protocol):
    name: str

    def register_tools(self, mcp: FastMCP) -> None: ...
    def register_event_handlers(self, bus: EventBus) -> None: ...
    def on_startup(self, config: ZKConfig) -> None: ...
    def on_shutdown(self) -> None: ...
```

Plugin discovery runs once at startup via `importlib.metadata.entry_points`.
Plugins are sandboxed to the `ZKPlugin` Protocol — they cannot access the
internal `Session` directly (only via the public service layer).

---

## Complete Feature Status (1–30)

| # | Feature | MoSCoW | Phase | Status |
|---|---------|--------|-------|--------|
| 1 | Structured JSON API Responses | Must | 2 | ✅ Shipped |
| 2 | FTS5 Full-Text Search | Must | 2 | ✅ Shipped |
| 3 | Note Metadata Exposure | Must | 2 | ✅ Shipped |
| 4 | Full CRUD for Atomic Notes | Must | Existing | ✅ Shipped |
| 5 | Typed Bidirectional Semantic Links | Must | Existing | ✅ Shipped |
| 6 | Batch Note and Link Creation | Should | 3 | ✅ Shipped |
| 7 | Data Portability (Markdown source of truth) | Must | Existing | ✅ Shipped |
| 8 | Health Dashboard and Index Verification | Should | 3 | ✅ Shipped |
| 9 | Custom Link Types and Link Type Inference | Should | 4 | 🟡 Next |
| 10 | Temporal Queries and Tag Clustering (Phase 5) | Should | 5 | 🔵 Queued |
| 11 | Auto-Tag Suggestions | Should | 4 | 🟡 Next |
| 12 | Graceful Degradation (filesystem fallback) | Should | 4 | 🟡 Next |
| 13 | Self-Healing Index | Should | 4 | 🟡 Next |
| 14 | Multi-Filter Compound Search | Should | Backlog | ⬜ Unspecced |
| 15 | Import / Export (Obsidian Vault) | Should | Backlog | ⬜ Unspecced |
| 16 | Backlinks Optimization | Should | Existing + 2 | ✅ Shipped |
| 17 | Hub / Centrality Detection (PageRank) | Should | Existing + 4 | ✅ / 🟡 |
| 18 | Tag Co-occurrence Clustering | Should | 5 | 🔵 Queued |
| 19 | Note Templates | Should | Backlog | ⬜ Unspecced |
| 20 | Note Versioning / History | Should | Backlog | ⬜ Unspecced |
| 21 | AI Link Inference | Could | Backlog | ⬜ Unspecced |
| 22 | Graph Visualization Export | Could | Backlog | ⬜ Unspecced |
| 23 | Daily Notes | Could | Backlog | ⬜ Unspecced |
| 24 | Spaced Repetition Review Queue | Could | Backlog | ⬜ Unspecced |
| 25 | Natural Language Queries | Could | Backlog | ⬜ Unspecced |
| 26 | Tag Hierarchy / Ontology | Could | Backlog | ⬜ Unspecced |
| 27 | Webhook / Event System | Could | Backlog | ⬜ Unspecced |
| 28 | Vector / Embedding Similarity Search | Could | Backlog | ⬜ Unspecced |
| 29 | Multi-User / Collaborative Support | Could | Backlog | ⬜ Unspecced |
| 30 | Plugin / Extension System | Could | Backlog | ⬜ Unspecced |
================================================================
End of Project Knowledge File
================================================================
