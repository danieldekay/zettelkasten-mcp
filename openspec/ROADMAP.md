# Zettelkasten MCP — Development Roadmap

> **Last Updated**: 2026-03-26
> **Source**: Research sprint 20260325 · 90 sources · 4 research tracks
> **OpenSpec changes**: `api-foundation`, `core-enhancements`, `advanced-features`, `analytics-discovery`

---

## Overview

```
Phase 1 (DONE)     Phase 2 (api-foundation)     Phase 3 (core-enhancements)
  Bug fixes    ──▶   Critical API surface    ──▶   Batch ops & verification
                     (P0 — pre-condition)            (P1 — production-ready)

Phase 4 (advanced-features)          Phase 5 (analytics-discovery)
  Flexible links & AI suggestions  ──▶  Temporal queries & tag clustering
  (P2 — differentiation)                (P2 — scale)
```

---

## Phase 1 — Shipped ✅

Bug fixes and initial stability work (archived). No outstanding items.

---

## Phase 2 — API Foundation · `openspec/changes/api-foundation` 🟡 Next

**Priority**: P0 · **Prerequisite for**: all subsequent phases
**Research basis**: 13 confirmed claims across 90 sources; single highest-impact set of changes

### Problem

All 14 MCP tools return plain-text strings → agent workflows parse natural language
to extract IDs and counts. The FTS5 search index is created but never queried →
O(n) linear scan on every search call. The `metadata` field exists in the data
model but is invisible through the API.

### Scope

| Capability | Change | GitHub Issue |
|------------|--------|--------------|
| `json-responses` | All 14 tools return structured JSON dicts with a `summary` key | #TBD |
| `fts5-search` | `zk_search_notes` uses FTS5 MATCH + BM25 ranking; O(n) scan removed | #TBD |
| `metadata-access` | `zk_create_note` / `zk_update_note` accept `metadata`; `zk_get_note` returns it | #TBD |

### Key Design Decisions

- **Dual response**: every tool returns `{..., "summary": "<previous plain text>"}` — non-breaking for display clients
- **FTS5 stays in sync**: create/update/delete each maintain `notes_fts` in the same transaction
- **Metadata as JSON string param**: LLM-friendly input, dict in response

### Success Criteria

- Zero tools return bare plain-text as primary response
- `zk_search_notes` < 50 ms on 10 000 notes
- `metadata` round-trips cleanly through create → get
- All 80+ existing tests pass (assertions updated)

### Task Count: 40 tasks across 4 groups

---

## Phase 3 — Core Enhancements · `openspec/changes/core-enhancements` 🔵 Queued

**Priority**: P1 · **Depends on**: Phase 2
**GitHub Issues**: #5, #6, #9, #14

### Problem

Agent workflows processing meeting transcripts require 15–50 sequential MCP
round-trips for bulk note + link creation. No tool confirms indexing state or
exposes DB vs. filesystem health.

### Scope

| Tool | Issue | Description |
|------|-------|-------------|
| `zk_create_notes_batch` | #5 | Create up to N notes in one transaction |
| `zk_create_links_batch` | #6 | Create multiple semantic links atomically |
| `zk_verify_note` | #9 | Check note exists in filesystem + SQLite index |
| `zk_get_index_status` | #14 | Health summary: file count vs. indexed count, orphaned records |

### Success Criteria

- Batch creation ≥ 10× faster than equivalent individual calls (N=50)
- `zk_verify_note` detects indexing gaps without manual DB inspection
- `zk_get_index_status` count matches `ls notes/ | wc -l`
- All existing + new tests pass (target: ≥ 80 tests)

### Task Count: 16 tasks across 5 groups

---

## Phase 4 — Advanced Features · `openspec/changes/advanced-features` ⚪ Planned

**Priority**: P2 · **Depends on**: Phase 3
**GitHub Issues**: #10, #11, #12, #16, #17

### Problem

The 7 hardcoded link types are insufficient for domain-specific knowledge graphs.
No guidance exists for choosing link types. Tags drift at scale. A DB failure
makes the server completely unusable even for reads.

### Scope

| Capability | Issue | Description |
|------------|-------|-------------|
| Flexible/custom link types | #10 | Register project-scoped custom link types via config |
| Link type inference | #11 | `zk_suggest_link_type` — pattern-matching, top-3 candidates with confidence |
| Auto-tag suggestions | #12 | `zk_suggest_tags` — TF-IDF against existing notes, top-10 suggestions |
| Graceful degradation | #16 | Read operations fall back to Markdown parsing when DB unavailable |
| Self-healing index | #17 | Startup drift check; auto-rebuild if delta > configurable threshold |

### Success Criteria

- Custom link types survive server restart
- `zk_suggest_link_type` returns in < 1 s for 5 KB notes
- `zk_suggest_tags` returns in < 500 ms against 1 000+ notes
- Server serves reads with a corrupt/missing DB
- Self-healing triggers rebuild when drift > 5% of total notes

### Task Count: 26 tasks across 6 groups

---

## Phase 5 — Analytics & Discovery · `openspec/changes/analytics-discovery` ⚪ Planned

**Priority**: P2 · **Depends on**: Phase 3
**GitHub Issues**: #13, #15

### Problem

With 1 000+ notes, users cannot answer "what did I capture this week?" or
"which topics cluster together?" without manual effort.

### Scope

| Tool | Issue | Description |
|------|-------|-------------|
| `zk_find_notes_in_timerange` | #13 | Filter by `created_at` or `updated_at` in ISO 8601 range; optionally expand to linked notes |
| `zk_analyze_tag_clusters` | #15 | Co-occurrence matrix; groups tags that appear together above threshold |

### Success Criteria

- Date range queries < 200 ms for 10 000 notes (SQLite indexed)
- `zk_analyze_tag_clusters` < 2 s for 1 000 tags / 10 000 notes

### Task Count: 11 tasks across 3 groups

---

## Backlog — Unspecced Features

Items from the research sprint identified as valuable but not yet in OpenSpec.
Each requires a separate `openspec propose` before implementation.

| Item | Priority | Description | Research Evidence |
|------|----------|-------------|-------------------|
| Note versioning / history | S3 | Store previous versions; `zk_get_note_history`, `zk_restore_note_version` | Enterprise KM requirements; practitioner requests |
| Import / export | S5 | Obsidian vault import (`[[wiki-links]]`→ ZK links); JSON + Graphviz DOT export | PKM portability; Boardman & Sasse 2004 |
| Multi-filter search | S4 | Combine `query` + `tags` + `note_type` + `date_range` + `metadata_key=value` | Codebase gap; GetApp user data |
| Note templates | S8 | `zk_create_note(template="literature")` pre-populates content structure | Obsidian Templater demand |
| Note review queue | C7 | `zk_get_review_queue(n)` — spaced repetition prioritization | Dunlosky 2013; Karpicke 2011 |
| Graph visualization export | C4 | `zk_export_graph(format="json"|"dot"|"cytoscape")` | D3.js / Gephi integration |
| AI link inference | C1 | `zk_suggest_links(note_id)` — embedding similarity + LLM link type suggestion | LiCoMemory 2025 |
| Daily notes | C6 | `zk_get_or_create_daily_note(date)` — temporal capture entry point | Logseq/Roam pattern |

---

## MoSCoW Summary

### Must-Have (all phases combined)

| Feature | Phase | Status |
|---------|-------|--------|
| Full CRUD for atomic notes | Existing | ✅ Done |
| Five canonical note types | Existing | ✅ Done |
| Typed bidirectional semantic links (12 types) | Existing | ✅ Done |
| **Structured JSON API responses** | 2 | 🟡 Next |
| **FTS5 full-text search** | 2 | 🟡 Next |
| Graph traversal (N-hop linked notes) | Existing + 3 | ✅ / 🔵 |
| Orphan note detection | Existing + 3 | ✅ / 🔵 |
| Data portability (Markdown source of truth) | Existing | ✅ Done |
| Tag management + usage counts | 2 + 5 | 🟡 / ⚪ |
| **Note metadata exposure** | 2 | 🟡 Next |

### Should-Have

| Feature | Phase | Status |
|---------|-------|--------|
| Batch note + link operations | 3 | 🔵 Queued |
| Health dashboard | 3 | 🔵 Queued |
| Semantic similarity (content-based) | 4 | ⚪ Planned |
| Multi-filter search | Backlog | ⬜ Unspecced |
| Import / export | Backlog | ⬜ Unspecced |
| Backlinks optimization | Existing + 2 | ✅ / 🟡 |
| Hub / centrality detection (PageRank) | Existing + 4 | ✅ / ⚪ |
| Note templates | Backlog | ⬜ Unspecced |
| Tag analytics (co-occurrence) | 5 | ⚪ Planned |
| Health dashboard / index verification | 3 | 🔵 Queued |

### Could-Have

| Feature | Phase | Status |
|---------|-------|--------|
| AI link inference | Backlog | ⬜ Unspecced |
| AI tag suggestions | 4 | ⚪ Planned |
| Natural language queries | Backlog | ⬜ Unspecced |
| Graph visualization export | Backlog | ⬜ Unspecced |
| Webhook / event system | Backlog | ⬜ Unspecced |
| Daily notes | Backlog | ⬜ Unspecced |
| Spaced repetition review queue | Backlog | ⬜ Unspecced |
| Tag hierarchy / ontology | Backlog | ⬜ Unspecced |
| Multi-user / collaborative support | Backlog | ⬜ Unspecced |
| Plugin / extension system | Backlog | ⬜ Unspecced |

---

## Total Task Count

| Phase | Change | Tasks | Status |
|-------|--------|-------|--------|
| Phase 1 | (archived) | — | ✅ Done |
| Phase 2 | `api-foundation` | 40 | 🟡 Ready |
| Phase 3 | `core-enhancements` | 16 | 🔵 Queued |
| Phase 4 | `advanced-features` | 26 | ⚪ Planned |
| Phase 5 | `analytics-discovery` | 11 | ⚪ Planned |
| **Total** | | **93 tasks** | |

---

## Implementation Order

```
START
  │
  ▼
Phase 2: api-foundation         ← START HERE
  • JSON responses (1.1–1.16)
  • FTS5 search fix (2.1–2.11)
  • Metadata access (3.1–3.11)
  • Tests + housekeeping (4.1–4.5)
  │
  ▼
Phase 3: core-enhancements
  • Batch create notes (1.1–1.5)
  • Batch create links (2.1–2.5)
  • Note verification (3.1–3.3)
  • Index health (4.1–4.3)
  │
  ├──▶ Phase 4: advanced-features   (can start after Phase 3)
  │      • Custom link types
  │      • Link + tag AI suggestions
  │      • Resilience / self-healing
  │
  └──▶ Phase 5: analytics-discovery (can start after Phase 3, parallel to Phase 4)
         • Temporal queries
         • Tag co-occurrence
```

To start implementing Phase 2, run:
```
/opsx:apply   (or ask Copilot to implement api-foundation)
```
