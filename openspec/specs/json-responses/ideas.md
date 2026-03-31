# Future Improvements: json-responses

## Enhancements

- **`zk_update_note` response should include `vscode_uri`** — The update tool returns
  `note_id`, `updated_fields`, and `summary` but no file path. Adding `file_path` and
  `vscode_uri` would make it consistent with all other note-returning tools and let agents
  immediately open the updated file.

- **`zk_delete_note` tombstone response** — Currently returns `{"deleted": true, "note_id": ...,
  "summary": ...}`. A `file_path` field (even to a now-deleted path) could help agents log or
  display what was removed.

- **`vscode_uri` for Windows** — The current `"vscode://file/" + str(Path)` construction works
  on Linux/macOS but would generate wrong URIs on Windows (backslashes). A helper function that
  normalises to forward slashes would make the implementation portable.

## Optimizations

- **Lazy `notes_dir` resolution** — `_note_to_dict` and `_note_summary_dict` both call
  `config.get_absolute_path(config.notes_dir)` on every invocation. Caching this once at
  server init (or as a computed property) would avoid repeated path resolution in large
  list results.

- **Batch response construction** — For list tools returning many notes (`zk_search_notes`,
  `zk_list_notes_by_date`), constructing a list of dicts via `_note_summary_dict` inside a
  comprehension is fine for small collections. For very large results, a generator-based
  approach with streaming JSON would reduce peak memory.

## User Experience

- **`vscode_uri` accessibility hint in summary** — The `summary` string is the human-readable
  line shown in agent output. Including a hint like `"(open in VS Code)"` next to the
  note title would make the `vscode_uri` field more discoverable to agents without reading
  the full dict schema.

- **Relative path in addition to absolute** — Agents working in the workspace context might
  benefit from a `workspace_relative_path` field (e.g., `data/notes/20251109T123456.md`) that
  can be used for workspace-scoped file links without knowing the absolute prefix.

## Integration Opportunities

- **Copilot Chat file link rendering** — The `vscode_uri` field enables clickable links in
  Copilot Chat, but only if the agent explicitly constructs a Markdown link like
  `[Note Title](vscode://file/path)`. A future improvement could include a pre-formatted
  Markdown link string in the response dict (e.g., `"vscode_link": "[Title](vscode://...)")`)
  so agents can embed it directly without constructing it.

- **OpenTelemetry / structured logging** — The `summary` field in every response is a natural
  telemetry point. Emitting a structured log event with `tool_name`, `note_id`, and `summary`
  on each successful tool call would enable tracing agent workflows without extra instrumentation.
