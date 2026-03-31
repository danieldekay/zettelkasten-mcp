## 1. Fix SQL Injection in note_repository.py

- [x] 1.1 Remove unused `Base` import from the `from zettelkasten_mcp.models.db_models import (...)` block in `note_repository.py`
- [x] 1.2 In `_index_note()`: replace `text(f"DELETE FROM links WHERE source_id = '{note.id}'")` with parameterized form and remove the `# noqa: S608` suppression
- [x] 1.3 In `_index_note()`: replace `text(f"DELETE FROM note_tags WHERE note_id = '{note.id}'")` with parameterized form and remove the `# noqa: S608` suppression
- [x] 1.4 In `update()`: replace `text(f"DELETE FROM links WHERE source_id = '{note.id}'")` with parameterized form and remove the `# noqa: S608` suppression
- [x] 1.5 In `delete()`: replace all three f-string DELETE statements (`links`, `note_tags`, `notes`) with parameterized forms

## 2. Test Cleanup

- [x] 2.1 In `test_note_repository.py`: remove unused variable `updated_note` in `test_update_note_with_duplicate_tags` (assign result directly to `_` or drop the assignment)
- [x] 2.2 In `test_note_repository.py`: remove unused variable `updated_note` in `test_update_note_preserves_existing_tags_without_duplicates`
- [x] 2.3 Update docstring in `test_create_note_with_duplicate_tags`: replace "SQLite IntegrityError" with "database IntegrityError"
- [x] 2.4 Update docstring in `test_update_note_with_duplicate_tags`: replace "SQLite IntegrityError" with "database IntegrityError"

## 3. Verification

- [x] 3.1 Run `uv run pytest -v tests/test_note_repository.py` — all tests must pass
- [x] 3.2 Run `uv run bandit -r src/` — no S608 findings in `note_repository.py`
- [x] 3.3 Run `uv run ruff check .` — no unused-import or unused-variable warnings
