## Context

All MCP tools that return note data already include a `file_path` key containing the absolute OS filesystem path (e.g. `/home/user/notes/data/notes/20251109T123456.md`). This path is correct but **not automatically linkified** by VS Code Copilot Chat. The Copilot Chat UI only renders clickable file links from `vscode://file/{path}` URIs — the same scheme VS Code uses internally for the "Go to file" picker and editor tab links.

Two central helper methods produce all note response dicts:
- `_note_to_dict(note)` — full-detail response (used by single-note tools)
- `_note_summary_dict(note)` — summary response (used by list/search tools)

One tool constructs its own path inline:
- `zk_create_note` builds `note_file_path` directly in the handler

## Goals / Non-Goals

**Goals:**
- Add `vscode_uri: str` field to every note response dict, computed as `"vscode://file/" + str(notes_dir / f"{note.id}.md")`
- At the two helper sites and the `zk_create_note` inline site — **3 total code changes**
- Update tool docstrings to document `vscode_uri` and remove the stale `file://` hint
- Assert `vscode_uri` in existing MCP server tests

**Non-Goals:**
- Removing `file_path` (kept for backward compatibility and non-VS Code agents)
- Supporting Windows-style paths or drive letters (the server runs on Linux/macOS where `vscode://file/` paths use forward slashes)
- Dynamic workspace-relative paths (absolute is reliable and consistent)
- Any server, storage, or model layer changes

## Decisions

### Decision: `vscode://file/{path}` as URI scheme

VS Code's file link format is `vscode://file/{absolute_path}`. It opens the file in the current VS Code window regardless of the workspace. This is the most reliable format for VS Code Copilot Chat to render as a clickable link — other schemes (`file://`, plain paths) are not consistently linkified in chat output.

### Decision: Centralise construction in the two helpers

`_note_to_dict` and `_note_summary_dict` are the canonical places to add `vscode_uri`. This means every tool that calls either helper gets the field automatically, with zero per-tool changes. `zk_create_note` is the only tool that builds its path inline and must be updated separately.

### Decision: String concatenation not `Path`

`vscode://file/{path}` expects a forward-slash path string. Using `f"vscode://file/{notes_dir / note.id + '.md'}"` (str coercion of `Path`) handles this correctly on Linux/macOS. No URL-encoding is needed for paths that contain only standard filesystem characters.

### Decision: Keep docstring hint minimal

Tool docstrings should tell agents: "Use `vscode_uri` to create a clickable VS Code link." One line is sufficient. The verbose multi-line `file://` hint blocks are removed.

## Risks / Trade-offs

- **Risk: vscode_uri breaks on Windows paths with drive letters** → Mitigation: the server is Linux-only in current deployment; document the constraint.
- **Trade-off: two fields for one file** → Keeping `file_path` means any agent or external consumer that already reads it continues to work. `vscode_uri` is purely additive.
- **Risk: tests missing new field assertion** → Mitigated by requiring `vscode_uri` assertions in test tasks.
