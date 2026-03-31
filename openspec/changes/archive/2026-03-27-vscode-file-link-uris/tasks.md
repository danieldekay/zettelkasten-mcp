## 1. Add vscode_uri to note response helpers

- [x] 1.1 In `_note_to_dict()`: add `"vscode_uri": f"vscode://file/{notes_dir / f'{note.id}.md'}"` immediately after the `"file_path"` entry
- [x] 1.2 In `_note_summary_dict()`: add `"vscode_uri": f"vscode://file/{notes_dir / f'{note.id}.md'}"` immediately after the `"file_path"` entry
- [x] 1.3 In `zk_create_note` return dict: add `"vscode_uri": f"vscode://file/{note_file_path}"` alongside the existing `"file_path"` key

## 2. Update tool docstrings

- [x] 2.1 In `zk_create_note` docstring: replace the multi-line `Note: ... file://...` hint with a single line: `Response includes \`vscode_uri\` — use it to create a clickable VS Code link to the note file.`
- [x] 2.2 In `zk_get_note` docstring: replace the multi-line `Note: ... file://...` hint with the same single-line `vscode_uri` instruction
- [x] 2.3 In `zk_search_notes` docstring: replace the multi-line `Note: ... file://...` hint with the same single-line `vscode_uri` instruction
- [x] 2.4 In `zk_get_linked_notes` docstring: update the `Note:` line to reference `vscode_uri`
- [x] 2.5 In `zk_find_similar_notes` docstring: replace the multi-line `Note: ... {notes_dir}/...` hint with the same single-line `vscode_uri` instruction
- [x] 2.6 In `zk_find_central_notes` docstring: update the `Note:` line to reference `vscode_uri`
- [x] 2.7 In `zk_find_orphaned_notes` docstring: update the `Note:` line to reference `vscode_uri`
- [x] 2.8 In `zk_list_notes_by_date` docstring: update the `Note:` line to reference `vscode_uri`

## 3. Update tests

- [x] 3.1 In `test_create_note_tool`: assert `"vscode_uri" in result` and that `result["vscode_uri"].startswith("vscode://file/")`
- [x] 3.2 Find (or add) a test for `zk_get_note` structured response and assert `"vscode_uri"` is present in the result
- [x] 3.3 Find (or add) a test for `zk_search_notes` structured response and assert each note dict in `result["notes"]` contains `"vscode_uri"` starting with `"vscode://file/"`

## 4. Verification

- [x] 4.1 Run `uv run pytest -v tests/test_mcp_server.py` — all tests must pass
- [x] 4.2 Run `uv run ruff check .` — no new lint issues
