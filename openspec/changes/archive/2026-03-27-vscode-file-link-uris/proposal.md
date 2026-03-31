## Why

MCP tool responses already include a `file_path` key with the absolute filesystem path to each note. However, VS Code / GitHub Copilot Chat does not auto-linkify plain filesystem paths — an agent must explicitly construct a clickable link. The `vscode://file/{path}` URI scheme is what VS Code recognises natively: any occurrence of this URI in a chat response becomes a clickable link that opens the file directly in the editor. Without it, agents either show the raw path as unlinked text or have to guess the right URI format.

## What Changes

- Add a `vscode_uri` field (format: `vscode://file/{absolute_path}`) to every response dict that currently contains `file_path`:
  - `_note_to_dict()` helper — used by `zk_get_note`, `zk_get_linked_notes`, `zk_find_similar_notes`, `zk_find_central_notes`, `zk_find_orphaned_notes`, `zk_list_notes_by_date`
  - `_note_summary_dict()` helper — used by `zk_search_notes`
  - `zk_create_note` return dict (constructs its own path inline)
- Update tool docstrings to document the `vscode_uri` field and instruct agents to use it for clickable links in VS Code
- Remove the misleading `file://` URI hint from current docstrings (Copilot Chat does not linkify `file://` URIs)

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `json-responses`: The response contract for note-returning tools changes — `vscode_uri` is added alongside the existing `file_path` key. Affected scenarios: create note, get note, search notes, linked notes, find orphaned/central notes.

## Impact

- **Code**: `src/zettelkasten_mcp/server/mcp_server.py` — `_note_to_dict`, `_note_summary_dict`, `zk_create_note`, and all tool docstrings that reference file path format
- **Tests**: `tests/test_mcp_server.py` — response schema tests will need to assert `vscode_uri` is present
- **No API breaking changes**: `file_path` is kept; `vscode_uri` is additive
- **No storage or model changes**
