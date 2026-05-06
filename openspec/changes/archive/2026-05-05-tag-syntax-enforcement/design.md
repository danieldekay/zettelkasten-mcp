## Context

`Tag` is a frozen Pydantic model with a single `name: str` field and no validator. Tags are written verbatim:

```python
# schema.py
class Tag(BaseModel):
    name: str = Field(..., description="Tag name")
    model_config = {"validate_assignment": True, "frozen": True}
```

In the MCP tools, comma-separated input is split and each token is stored as-is:

```python
# mcp_server.py — zk_create_note / zk_update_note
tag_list = [t.strip() for t in tags.split(",") if t.strip()]
```

No normalisation occurs anywhere in the pipeline: `Tag("IO-psychology")` and `Tag("io-psychology")` are different objects in the database.

## Goals / Non-Goals

**Goals:**
- Define canonical tag syntax: **all-lowercase, hyphen-separated words** (`^[a-z0-9][a-z0-9-]*$` with no leading/trailing hyphens, no consecutive hyphens)
- Auto-normalise on construction: `Tag("IO-psychology")` silently yields `Tag("io-psychology")`; spaces become hyphens; leading/trailing hyphens and consecutive hyphens are collapsed
- Add a `strict_tag_syntax` config option (env: `ZETTELKASTEN_STRICT_TAGS`): when `true`, reject rather than normalise (raise `ValueError` immediately, surfaced as an MCP error response)
- Expose normalisation transparency: when any submitted tag is changed, include `normalised_tags: [{"from": "IO-psychology", "to": "io-psychology"}, ...]` in `zk_create_note` / `zk_update_note` response
- Add `zk_normalize_tags` MCP tool: idempotently rewrites all existing note tags to canonical form, returning a per-note diff

**Non-Goals:**
- Merging semantically equivalent but lexically different tags (e.g., `ml` vs `machine-learning`)
- Auto-migrating on startup
- Enforcing a vocabulary allowlist

## Decisions

### Decision: Normalise in `Tag.__init__` via `field_validator`, not at the MCP layer

The `Tag` model is the single authoritative place where tag names are trusted. Placing validation there means every creation path (MCP tools, `ZettelService`, `NoteRepository` parse paths, `Note.add_tag`) benefits automatically without individual call-site changes.

The alternative — normalising only at MCP tool boundaries — would leave `NoteRepository._parse_frontmatter_tags`, `ZettelService.create_note`, and internal helpers unprotected.

### Decision: Normalisation algorithm

```
1. Strip leading/trailing whitespace
2. Lowercase the entire string
3. Replace any sequence of whitespace or underscores with a single hyphen
4. Remove characters that are not [a-z0-9-]
5. Collapse runs of hyphens to a single hyphen
6. Strip leading and trailing hyphens
7. If the result is empty, raise ValueError("Tag name cannot be empty after normalisation")
```

This is pure string transformation — no regex engine needed beyond the stdlib `re` module already in use.

### Decision: Strict mode is project-level config, not per-call

Strict mode (`strict_tag_syntax: bool`) lives in `ZettelkastenConfig` and is read from env var `ZETTELKASTEN_STRICT_TAGS=true`. This is consistent with the pattern used by `use_fts5_search` and `auto_rebuild_threshold`.

In strict mode, the `Tag` validator raises `ValueError` if the raw input differs from its normalised form, so the error surfaces before any storage write.

The `Tag` model cannot import `config` (circular dependency risk). Instead, strict mode is injected at call time: the MCP server reads `config.strict_tag_syntax` and calls a module-level `set_strict_tag_mode(enabled: bool)` function in `schema.py` during startup.

### Decision: `zk_normalize_tags` is a best-effort bulk migration tool

The tool iterates all notes, applies `Tag` normalisation to each tag name, updates notes where changes occurred, and returns:
```json
{
  "total_notes_scanned": 1521,
  "notes_updated": 43,
  "tags_changed": 87,
  "diff": [
    {"note_id": "...", "title": "...", "changes": [{"from": "IO-psychology", "to": "io-psychology"}]}
  ],
  "summary": "Normalised 87 tags across 43 notes"
}
```

Idempotent: running twice produces `"notes_updated": 0`.

### Decision: `parse_tags` in `utils.py` is unchanged

`parse_tags` splits on commas and strips whitespace — it does not construct `Tag` objects. Normalisation happens downstream when `Tag(name=...)` is constructed. No change needed.

## Risks / Trade-offs

- **Risk: silent normalisation surprises callers** → Mitigated by `normalised_tags` field in create/update responses; callers can log or surface this.
- **Risk: strict mode breaks existing integrations** → Strict mode is opt-in, off by default; no existing user is affected unless they explicitly set `ZETTELKASTEN_STRICT_TAGS=true`.
- **Risk: circular import with config** → Mitigated by the `set_strict_tag_mode()` injection pattern; `schema.py` holds a module-level `_strict_tag_mode = False` flag; `mcp_server.py` sets it on startup after importing both.
- **Trade-off: `Tag` is frozen, validator must return the normalised value** → Pydantic `field_validator` with `mode="before"` intercepts the raw input and returns the normalised string before the frozen model is constructed. No mutation of a frozen instance occurs.
