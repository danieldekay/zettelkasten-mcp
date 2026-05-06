---
name: zettelkasten-mcp
description: >
  Setup, operate, and troubleshoot the zettelkasten-mcp server. Covers installation (uv,
  Claude Desktop, VS Code), all zk_* tool patterns, environment configuration, index
  rebuilding, and how to file GitHub issues on entanglr/zettelkasten-mcp for recurring
  errors. Use when configuring the MCP server, running zk_* operations, or hitting errors.
  Triggers: "setup zettelkasten-mcp", "configure zk mcp", "zk_create_note", "rebuild index",
  "zettelkasten not working", "file a zk issue", "zk error".
author: Daniel Kaesmayr
metadata:
  version: "1.0.0"
  category: knowledge-management
  repo: https://github.com/entanglr/zettelkasten-mcp
  issues: https://github.com/entanglr/zettelkasten-mcp/issues
---

# Zettelkasten MCP — Operations Skill

Setup, operate, and troubleshoot the `zettelkasten-mcp` server.

## Installation

### Prerequisites

- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Python ≥ 3.10
- Claude Desktop or a VS Code MCP client

### Steps

```bash
git clone https://github.com/entanglr/zettelkasten-mcp.git
cd zettelkasten-mcp
uv sync --dev
cp .env.example .env
# Edit .env: set ZETTELKASTEN_NOTES_DIR and ZETTELKASTEN_DATABASE_PATH
```

### Environment variables (`.env`)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ZETTELKASTEN_NOTES_DIR` | ✅ | `./data/notes` | Where Markdown note files are stored |
| `ZETTELKASTEN_DATABASE_PATH` | ✅ | `./data/db/zettelkasten.db` | SQLite index path |
| `ZETTELKASTEN_LOG_LEVEL` | — | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `USE_FTS5_SEARCH` | — | `true` | Porter-stemmed BM25 full-text search |
| `LLM_ENABLE_SUMMARIES` | — | `false` | Azure OpenAI cross-language summaries |

### Connecting to Claude Desktop

Add to `claude_desktop_config.json` (`~/Library/Application Support/Claude/` on macOS):

```json
{
  "mcpServers": {
    "zettelkasten": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/zettelkasten-mcp", "python", "-m", "zettelkasten_mcp.main"],
      "env": {
        "ZETTELKASTEN_NOTES_DIR": "/absolute/path/to/notes",
        "ZETTELKASTEN_DATABASE_PATH": "/absolute/path/to/db/zettelkasten.db"
      }
    }
  }
}
```

### Connecting to VS Code (GitHub Copilot)

Add to `.vscode/mcp.json` or your user `mcp.json`:

```json
{
  "servers": {
    "zettelkasten": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "${workspaceFolder}", "python", "-m", "zettelkasten_mcp.main"],
      "env": {
        "ZETTELKASTEN_NOTES_DIR": "${env:HOME}/path/to/notes",
        "ZETTELKASTEN_DATABASE_PATH": "${env:HOME}/path/to/db/zettelkasten.db"
      }
    }
  }
}
```

## Core Tool Reference

### Notes

| Tool | Key parameters | Notes |
|---|---|---|
| `zk_create_note` | `title`, `content`, `note_type`, `tags[]` | Returns `note_id` (timestamp ID) |
| `zk_get_note` | `note_id` | Returns full note with links and tags |
| `zk_update_note` | `note_id`, `title?`, `content?`, `tags?` | Partial update — omit fields to keep unchanged |
| `zk_delete_note` | `note_id` | Removes Markdown file + database entry |
| `zk_search_notes` | `query?`, `tags?[]`, `note_type?`, `limit?` | FTS5 BM25 search + tag filter |
| `zk_list_notes` | `note_type?`, `tags?[]`, `limit?` | Browse without text search |

### Links

| Tool | Key parameters |
|---|---|
| `zk_create_link` | `source_id`, `target_id`, `link_type`, `description?`, `bidirectional?` |
| `zk_get_linked_notes` | `note_id`, `link_type?`, `direction?` (`incoming`/`outgoing`/`both`) |
| `zk_delete_link` | `source_id`, `target_id`, `link_type` |

### Maintenance

| Tool | Purpose |
|---|---|
| `zk_rebuild_index` | Rebuilds SQLite from Markdown files — run after direct file edits |
| `zk_get_stats` | Returns note count, link count, tag count, graph density |
| `zk_health_check` | Checks for orphan notes, broken links, duplicate IDs |

### Link types

`reference` · `extends` / `extended_by` · `refines` / `refined_by` · `contradicts` / `contradicted_by` · `questions` / `questioned_by` · `supports` / `supported_by` · `related`

Use `bidirectional=true` on `zk_create_link` to create both directions in one call.

## Common Operations

### Session start pattern

```
1. zk_health_check — detect any integrity issues first
2. zk_search_notes(query="[topic]") — orient on existing notes
3. Proceed with create/link/update
```

### After direct file edits

```
zk_rebuild_index  ← always run after editing .md files outside the MCP
```

### Finding related notes for linking

```
zk_search_notes(tags=["tag1", "tag2"])
zk_get_linked_notes(note_id="X", direction="both")
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ZETTELKASTEN_NOTES_DIR not set` | Missing `.env` or env not loaded | Check `.env` file exists; verify path is absolute |
| Search returns stale/wrong results | Index out of sync with Markdown files | Run `zk_rebuild_index` |
| `database is locked` | Multiple server instances | Kill all server processes; only one instance should run |
| Note not found after direct edit | Markdown edited outside MCP | Run `zk_rebuild_index` |
| Server fails to start | Port conflict or bad config | Check `ZETTELKASTEN_LOG_LEVEL=DEBUG` output; verify `.env` paths exist |
| Tags not appearing in search | FTS5 index stale | `zk_rebuild_index` |
| Duplicate note IDs | Clock skew or bulk import | Run `zk_health_check`; rename conflicting files manually |

## Filing GitHub Issues

When you hit a recurring error that isn't resolved by the steps above, file an issue at:
**https://github.com/entanglr/zettelkasten-mcp/issues/new**

### Good issue template

```markdown
## Summary
One-sentence description of the problem.

## Environment
- OS:
- Python version (`python --version`):
- zettelkasten-mcp version / commit:
- MCP client (Claude Desktop / VS Code / other):

## Steps to reproduce
1. ...
2. ...
3. ...

## Expected behaviour
...

## Actual behaviour
...

## Logs
Paste relevant lines from the log (set ZETTELKASTEN_LOG_LEVEL=DEBUG first).

## Notes / `.env` (redact paths if sensitive)
ZETTELKASTEN_NOTES_DIR=...
USE_FTS5_SEARCH=...
```

### Issue labels to use

| Label | When |
|---|---|
| `bug` | Server crashes, wrong results, data corruption |
| `database` | SQLite errors, index sync problems |
| `search` | FTS5 search incorrect or slow |
| `config` | Env var or client config problems |
| `performance` | Slow operations, memory |
| `question` | Usage questions (check README first) |

### Before filing: self-check

1. Run `zk_health_check` and include output
2. Set `ZETTELKASTEN_LOG_LEVEL=DEBUG` and reproduce — include relevant log lines
3. Search [existing issues](https://github.com/entanglr/zettelkasten-mcp/issues) for duplicates

## See Also

- [references/mcp-tool-patterns.md](references/mcp-tool-patterns.md) — example invocation patterns for common workflows
- Skill `zettelkasten-philosophy` — ZK theory and best practices
