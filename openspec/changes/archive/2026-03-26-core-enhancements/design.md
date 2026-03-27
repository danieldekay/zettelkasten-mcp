# Design: Core Enhancements

## Context

The Zettelkasten MCP server uses a dual-storage pattern: Markdown files are the
source of truth; SQLite is an index for efficient querying. Before this change,
every write (note creation, link creation) was a single-item operation requiring
a separate round-trip. There was also no way to inspect whether a note or the
whole vault was consistent between the two storage layers.

## Goals / Non-Goals

**Goals:**
- Reduce agent round-trips for bulk ingestion workflows (batch note + link creation)
- Provide observability tools to check and diagnose filesystem/DB consistency
- Maintain the all-or-nothing atomicity guarantee users expect from write operations

**Non-Goals:**
- Streaming or async batch processing
- Partial-success responses (a batch either fully succeeds or fully fails)
- Automatic repair of orphaned records (only diagnosis — repair is via `zk_rebuild_index`)

## Decisions

### Decision 1: Validate before any IO

**Approach**: Both `create_notes_batch` and `create_links_batch` validate the
entire input list before writing a single file or DB record.

**Rationale**: Partial writes are harder to reason about and recover from than a
clean pre-flight failure. Raising on the first validation error with a clear index
reference makes it fast to fix the input and retry.

**Alternative considered**: Write-what-succeeds and report per-item errors. Rejected
because it leaves the vault in a partially updated state that agents then need to
handle.

### Decision 2: Files first, DB second — with file cleanup on DB failure

**Approach**: `NoteRepository.create_batch` writes all Markdown files to disk, then
commits all DB records in a single `session.commit()`. If the DB commit fails, the
already-written files are deleted before re-raising.

**Rationale**: Markdown files are the source of truth. Reverting DB-only is trivially
handled by `zk_rebuild_index`. Reverting filesystem writes (deleting files) is also
straightforward. Leaving orphaned files on a DB failure is acceptable only if the
exception propagates — here it is cleaned up explicitly.

### Decision 3: Link batch grouped by source note in service layer

**Approach**: `ZettelService.create_links_batch` groups incoming links by `source_id`
and calls `repository.update()` once per source note, while `NoteRepository.create_links_batch`
performs a single-session DB commit for all links from a given source.

**Rationale**: Link data lives in the Markdown file of the source note (as `## Links`
frontmatter) as well as in the DB. Grouping by source minimises filesystem writes
(one file rewrite per source note rather than one per link).

### Decision 4: verify_note and get_index_status are read-only and always query DB directly

**Approach**: Both methods bypass `_read_from_markdown` and query the DB directly via
`session_factory`. They do not trigger any writes or index repairs.

**Rationale**: Diagnostic tools should reflect the actual current state of both
storage layers without side effects.

## Risks / Trade-offs

- **Large batches hold a DB session open longer** → Mitigated by keeping transactions
  short and failing fast on validation.
- **File cleanup after DB failure may itself fail (OSError)** → Logged as a warning;
  the primary exception is still re-raised so the caller is aware of the failure.
- **get_index_status scans the entire filesystem glob on every call** → Acceptable for
  current vault sizes; a dedicated cached observer could be added if performance
  becomes an issue.

## Migration Plan

No schema changes. No breaking changes to existing MCP tools. New tools are additive.
