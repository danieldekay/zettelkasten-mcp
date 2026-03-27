## Context

`NoteRepository` in `src/zettelkasten_mcp/storage/note_repository.py` executes raw SQL via SQLAlchemy's `text()`. Several of these statements use Python f-strings to interpolate `note.id` and `id` directly into the SQL string. This pattern is vulnerable to SQL injection: a maliciously-crafted note ID passed to `update()`, `delete()`, or `_index_note()` would be executed as raw SQL.

The fix exists in the `feature/file-paths-in-responses` branch (commit `1547676`) but was never merged into `develop`.

Current state (three affected call sites):
```python
# _index_note() — two statements
text(f"DELETE FROM links WHERE source_id = '{note.id}'")
text(f"DELETE FROM note_tags WHERE note_id = '{note.id}'")

# update()
text(f"DELETE FROM links WHERE source_id = '{note.id}'")

# delete()
text(f"DELETE FROM links WHERE source_id = '{id}' OR target_id = '{id}'")
text(f"DELETE FROM note_tags WHERE note_id = '{id}'")
text(f"DELETE FROM notes WHERE id = '{id}'")
```

## Goals / Non-Goals

**Goals:**
- Replace all f-string SQL interpolation with SQLAlchemy named bind parameters (`:param_name`, `{"param_name": value}`)
- Remove the unused `Base` import that accompanies these methods
- Remove unused test variables (`updated_note`) left from prior test refactors
- Update two test docstrings from "SQLite IntegrityError" → "database IntegrityError" for backend portability

**Non-Goals:**
- Migrating raw `text()` SQL to full ORM expressions (out of scope; would require broader refactor)
- Changing any public API, MCP tool signature, or note data model
- Addressing other SQL statements in the file that already use parameterized queries

## Decisions

### Decision: Use SQLAlchemy named bind parameters, not positional

SQLAlchemy's `text()` supports both positional (`:1`) and named (`:param_name`) bind parameters. Named parameters are chosen because:
- The `delete()` method reuses the same `:id` parameter for three separate statements, making intent clear
- Named parameters match the existing codebase style (`{"note_id": note.id}`) used elsewhere

### Decision: Scope fix to exact call sites from the reference commit

The change targets the six f-string `text()` calls identified in commit `1547676`. No other changes are made to the surrounding logic to keep the diff minimal and reviewable.

### Decision: No `# noqa: S608` suppression after fix

The existing f-string lines carry `# noqa: S608` (Bandit's "possible SQL injection via string-based query construction" rule). After replacing with parameterized queries, these suppressions are not needed and should be removed as part of the fix.

## Risks / Trade-offs

- **Risk: bind parameter syntax typo** → Mitigation: existing test suite covers all three methods; a wrong parameter name raises a `CompileError` or `OperationalError` at runtime, caught by tests.
- **Risk: SQLite vs other backends** → Non-issue: SQLAlchemy named bind parameters are database-agnostic; the same syntax works across SQLite, PostgreSQL, and MySQL.
- **Trade-off: not migrating to full ORM** → Accepting residual use of `text()` keeps the change minimal; full ORM migration can be tracked separately.
