## Why

Tags in the Zettelkasten accept any arbitrary string today. The MCP tools `zk_create_note` and `zk_update_note` parse a comma-separated tag string and store each token verbatim — no normalisation, no validation. Over time this leads to tag fragmentation: `IO-psychology`, `io-psychology`, `LLM-prompts`, and `llm-prompts` coexist in the database as four distinct tags, all meaning the same thing. This was observed in the live notes-workspace where ~90 notes had to be manually corrected in a single maintenance pass.

The root cause is the absence of a tag syntax rule. Without a canonical form, every caller — humans typing tags, LLMs completing tool calls, scripts — can invent their own casing and separator convention, and the damage accumulates silently.

## What Changes

- Define a canonical tag syntax rule: **lowercase kebab-case** — all characters lowercase, words separated by hyphens, no spaces, no uppercase letters.
- Add a `field_validator` to the `Tag` Pydantic model in `schema.py` that normalises tags to the canonical form on construction (auto-lowercases; replaces spaces with `-`).
- Add a strict-mode option (off by default, configurable via `config.yaml`) that *rejects* non-compliant tags instead of normalising them, so advanced users can enforce a zero-tolerance policy.
- Surface validation feedback in `zk_create_note` and `zk_update_note`: if normalisation changes a submitted tag, include a `normalised_tags` field in the response summary so the caller is aware.
- Add a `zk_normalize_tags` MCP tool that bulk-normalises all existing tags in the database, returning a diff of what changed.

## Capabilities

### New Capabilities

- `zk_normalize_tags` MCP tool: scans all notes and rewrites tags to canonical form, returning a per-note diff of changed tags.

### Modified Capabilities

- `Tag` schema model: construction now normalises the tag name (lowercase + hyphens); validation raises `ValueError` if strict mode is enabled and the input is already non-compliant after stripping.
- `zk_create_note`, `zk_update_note`: response includes `normalised_tags` list when any submitted tags were changed during normalisation.

## Non-Goals

- Merging semantically equivalent tags that have different words (e.g., `ml` and `machine-learning`). This is a future concern; only syntactic normalisation is in scope.
- Migrating existing notes on server startup. Normalisation is applied at write time; historical notes remain unchanged until `zk_normalize_tags` is called.
- Enforcing a controlled vocabulary or tag allowlist.

## Impact

- **Code**: `src/zettelkasten_mcp/models/schema.py` (Tag model), `src/zettelkasten_mcp/server/mcp_server.py` (two tools updated, one new), `src/zettelkasten_mcp/config.py` (new config option), `src/zettelkasten_mcp/utils.py` (`parse_tags` updated)
- **Tests**: `tests/test_tag_syntax.py` (new), `tests/test_mcp_server.py` (updated)
- **No breaking API change**: normalisation is silent by default; existing callers that pass compliant tags are unaffected
- **Potential behaviour change**: callers that pass `MCP` as a tag will now receive `mcp`; the `normalised_tags` response field makes this transparent
