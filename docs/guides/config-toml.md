================================================================
Start of Project Knowledge File
================================================================

Purpose:
--------
This file is for reference documentation consumed by AI systems and developers.

Content:
--------

# Configuration File (`config.toml`)

The Zettelkasten MCP server can be configured via a TOML file in addition to
environment variables and CLI flags.

## Priority Order

Settings are resolved with the following precedence (highest wins):

```
CLI flags  >  config.toml  >  environment variables  >  built-in defaults
```

## Using a Config File

Pass the path to your config file using the `--config` flag:

```bash
zettelkasten-mcp --config /path/to/config.toml
```

In a VS Code `mcp.json`, add it to `args`:

```json
{
  "servers": {
    "zk": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory", "/path/to/zettelkasten-mcp",
        "run", "zettelkasten-mcp",
        "--config", "/path/to/config.toml"
      ]
    }
  }
}
```

## Full Schema Reference

All sections and keys are optional. Only the keys you specify override their
current values; anything omitted keeps its environment-variable default.

```toml
[storage]
# Absolute path to the directory containing Markdown note files.
# Env-var equivalent: ZETTELKASTEN_NOTES_DIR
notes_dir = "/home/user/notes/zettelkasten"

# Absolute path to the SQLite database file (created automatically if absent).
# Env-var equivalent: ZETTELKASTEN_DATABASE_PATH
database_path = "/home/user/notes/db/zettelkasten.db"

[server]
# Log verbosity: DEBUG, INFO, WARNING, ERROR, CRITICAL
# Env-var equivalent: ZETTELKASTEN_LOG_LEVEL
log_level = "INFO"

# MCP server display name.
# Env-var equivalent: ZETTELKASTEN_SERVER_NAME
name = "zettelkasten-mcp"

[watch]
# Extra read-only directories to index as reference notes.
# Env-var equivalent: ZETTELKASTEN_WATCH_DIRS (comma-separated)
dirs = ["/home/user/vault/references", "/home/user/shared-notes"]

[search]
# Enable FTS5 full-text search (requires SQLite built with FTS5).
# Env-var equivalent: USE_FTS5_SEARCH
use_fts5 = true

[index]
# Drift percentage that triggers an automatic re-index on startup.
# Set to 0 to disable.
# Env-var equivalent: ZETTELKASTEN_AUTO_REBUILD_THRESHOLD
auto_rebuild_threshold = 5

[tags]
# When false (default): tags are silently normalised to lowercase kebab-case on
# write (e.g. "IO Psychology" → "io-psychology", "FTS5" → "fts5").
# When true: tags that are not already in canonical form are rejected with an
# error so the caller must fix them explicitly.
# Env-var equivalent: ZETTELKASTEN_STRICT_TAGS
strict = false

[llm]
# Enable AI-generated note summaries via Azure OpenAI.
# Env-var equivalent: LLM_ENABLE_SUMMARIES
enable_summaries = false

# Azure OpenAI endpoint (required when enable_summaries = true).
# Env-var equivalent: AZURE_OPENAI_ENDPOINT
azure_endpoint = "https://my-resource.openai.azure.com/"

# Azure OpenAI API version.
# Env-var equivalent: AZURE_OPENAI_API_VERSION
azure_api_version = "2024-02-01"

# Deployment / model name.
# Env-var equivalent: LLM_MODEL
model = "gpt-4o"

# Sampling temperature (0.0–1.0).
# Env-var equivalent: LLM_TEMPERATURE
temperature = 0.2

# Maximum tokens for generated summaries.
# Env-var equivalent: LLM_MAX_TOKENS
max_tokens = 512
```

## Example: Minimal Config

```toml
[storage]
notes_dir    = "/home/alice/notes/zettelkasten"
database_path = "/home/alice/notes/db/zettelkasten.db"
```

## Example: Config with Watch Folders

```toml
[storage]
notes_dir    = "/home/alice/notes/zettelkasten"
database_path = "/home/alice/notes/db/zettelkasten.db"

[watch]
dirs = ["/home/alice/shared-vault", "/mnt/team-notes"]

[server]
log_level = "WARNING"
```

## Python Version Note

`config.toml` parsing uses the standard-library `tomllib` module (Python 3.11+).
On Python 3.10, the `tomli` package is used automatically — it is listed as a
conditional dependency in `pyproject.toml` and requires no manual installation.
