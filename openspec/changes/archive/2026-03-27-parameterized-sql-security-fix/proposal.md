## Why

Raw f-string interpolation is used for SQL queries in `note_repository.py`, exposing the application to SQL injection vulnerabilities. These must be replaced with parameterized queries to meet basic security standards. The issue was identified and fixed in `feature/file-paths-in-responses` but was never merged to `develop`.

## What Changes

- Replace all f-string SQL queries with parameterized queries using named placeholders in `NoteRepository`
  - `_index_note()`: two `DELETE` statements using `note.id`
  - `update()`: one `DELETE FROM links` statement using `note.id`
  - `delete()`: three `DELETE` statements (`links`, `note_tags`, `notes`) using `id`
- Remove unused `Base` import from `note_repository.py`
- Remove unused variables (`updated_note`) in `test_note_repository.py`
- Update test docstrings: replace "SQLite IntegrityError" with "database IntegrityError" for portability

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `core-enhancements`: The `NoteRepository` SQL execution pattern changes from f-string interpolation to parameterized queries — this is a security-level requirement change to the persistence layer.

## Impact

- **Code**: `src/zettelkasten_mcp/storage/note_repository.py` (3 methods: `_index_note`, `update`, `delete`)
- **Tests**: `tests/test_note_repository.py` (minor cleanup: unused variable removal, docstring wording)
- **No API changes**: All public method signatures remain identical
- **No dependency changes**: Uses existing SQLAlchemy `text()` with bind parameters already supported
