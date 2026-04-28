# Proposal: Core Enhancements — Batch Operations, Verification & Health

## Summary

Deliver the four P1 enhancements from the 2026 Q1 backlog (#4) that close the
most impactful gaps identified during production usage of the Zettelkasten MCP
server.

## GitHub Issues

| Issue                                                            | Title                                                   | Label |
| ---------------------------------------------------------------- | ------------------------------------------------------- | ----- |
| [#5](https://github.com/entanglr/zettelkasten-mcp/issues/5)   | Implement batch note creation (`zk_create_notes_batch`) | p1    |
| [#6](https://github.com/entanglr/zettelkasten-mcp/issues/6)   | Implement batch link creation (`zk_create_links_batch`) | p1    |
| [#9](https://github.com/entanglr/zettelkasten-mcp/issues/9)   | Add note verification tool (`zk_verify_note`)           | p1    |
| [#14](https://github.com/entanglr/zettelkasten-mcp/issues/14) | Add database health dashboard (`zk_get_index_status`)   | p1    |

## Problem

Production workflows that process meeting transcripts into atomic notes require
15–50 MCP round-trips just for creation and linking. Each call opens a separate
database transaction, making bulk ingestion slow and fragile. There is also no
way to confirm that a newly-created note has been indexed, nor any overview of
the overall health of the database vs. the filesystem.

## Proposed Changes

1. **`zk_create_notes_batch`** — create up to N notes in one transaction,
   returning all generated IDs.
2. **`zk_create_links_batch`** — create multiple semantic links atomically with
   full rollback on any failure.
3. **`zk_verify_note`** — check that a single note exists in both the filesystem
   and the SQLite index, returning counts of links and tags.
4. **`zk_get_index_status`** — return a health summary comparing filesystem
   note count vs. indexed count, listing any orphaned files or DB records.

## Out of Scope

- Auto-tagging / AI suggestions (Phase 3)
- Temporal or co-occurrence queries (Phase 4)
- Changes to the Markdown file format

## Success Criteria

- Batch creation is ≥10× faster in wall-clock time than equivalent individual calls
- `zk_verify_note` reveals indexing gaps without manual DB inspection
- `zk_get_index_status` counts match `ls notes/ | wc -l` output
- All existing and new tests pass (target: ≥80 tests)
