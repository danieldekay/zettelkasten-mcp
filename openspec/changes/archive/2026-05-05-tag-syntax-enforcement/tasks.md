## 1. Tag Normalisation — Schema Layer

- [x] 1.1 Add module-level flag `_strict_tag_mode: bool = False` and function `set_strict_tag_mode(enabled: bool) -> None` to `schema.py`
- [x] 1.2 Add `_normalise_tag_name(raw: str) -> str` helper function in `schema.py`:
  - strip whitespace → lowercase → replace `[ _]+` with `-` → remove `[^a-z0-9-]` → collapse `--+` to `-` → strip leading/trailing `-`
  - raise `ValueError("Tag name cannot be empty after normalisation")` if result is empty
- [x] 1.3 Add `@field_validator("name", mode="before")` to `Tag` in `schema.py`:
  - call `_normalise_tag_name(v)`
  - if `_strict_tag_mode` and result differs from the stripped input, raise `ValueError(f"Tag '{v}' is not valid lowercase-kebab-case. Normalised form: '{result}'")`
  - return `result`
- [x] 1.4 Run `uv run pytest -v tests/` — all existing tests must still pass before adding new ones

## 2. Config — Strict Mode Option

- [x] 2.1 Add `strict_tag_syntax: bool` field to `ZettelkastenConfig` in `config.py`, defaulting to `os.getenv("ZETTELKASTEN_STRICT_TAGS", "false").lower() == "true"`
- [x] 2.2 In `MCPServer.__init__` (or the server startup path in `mcp_server.py`), call `set_strict_tag_mode(config.strict_tag_syntax)` after imports settle

## 3. MCP Tools — Normalisation Transparency

- [x] 3.1 In `zk_create_note`: after building `tag_list`, compute `normalised = [Tag(name=t).name for t in tag_list]`; collect pairs where input differs from normalised as `changes = [{"from": raw, "to": norm} for raw, norm in zip(tag_list, normalised) if raw != norm]`
- [x] 3.2 In `zk_create_note` success response dict: include `"normalised_tags": changes` (empty list if none changed)
- [x] 3.3 Apply the same changes to `zk_update_note` (only when `tag_list is not None`)
- [x] 3.4 Update `zk_create_note` and `zk_update_note` docstrings to mention automatic tag normalisation

## 4. New MCP Tool — `zk_normalize_tags`

- [x] 4.1 Register `zk_normalize_tags()` tool in `mcp_server.py` with no required parameters
- [x] 4.2 Implement the body:
  - fetch all notes via `self.zettel_service.list_notes(limit=None)` (or equivalent repository scan)
  - for each note, build `normalised_tags = [Tag(name=t.name).name for t in note.tags]`
  - if `normalised_tags != [t.name for t in note.tags]`, collect diff and call `self.zettel_service.update_note(note_id, tags=normalised_tags)`
- [x] 4.3 Return response dict: `total_notes_scanned`, `notes_updated`, `tags_changed`, `diff` (list of `{note_id, title, changes}` dicts), `summary`
- [x] 4.4 Handle errors gracefully: individual note update failures are logged and included in an `errors` list in the response; they do not abort the whole run

## 5. Tests

- [x] 5.1 Create `tests/test_tag_syntax.py` with unit tests for `_normalise_tag_name`:
  - `"IO-psychology"` → `"io-psychology"`
  - `"LLM Prompts"` → `"llm-prompts"` (space → hyphen)
  - `"SKILL.md"` → `"skill-md"` (dot removed)
  - `"adversarial-AI"` → `"adversarial-ai"`
  - `"The Q"` → `"the-q"` (space)
  - `"User story: Alice"` → `"user-story-alice"` (space + colon removed)
  - `"  --bad--  "` → `"bad"` (leading/trailing hyphens stripped)
  - `""` (empty) → raises `ValueError`
  - `"---"` (only hyphens) → raises `ValueError`
- [x] 5.2 Add `Tag` construction tests: `Tag(name="IO-psychology").name == "io-psychology"`
- [x] 5.3 Add strict mode tests: `set_strict_tag_mode(True)` → `Tag(name="IO-psychology")` raises `ValueError`; `Tag(name="io-psychology")` succeeds; reset with `set_strict_tag_mode(False)` after each test
- [x] 5.4 Add MCP-level tests in `tests/test_mcp_server.py`:
  - `zk_create_note` with `tags="IO-psychology,MCP"` → `normalised_tags == [{"from": "IO-psychology", "to": "io-psychology"}, {"from": "MCP", "to": "mcp"}]`
  - `zk_create_note` with already-compliant tags → `normalised_tags == []`
  - `zk_update_note` with mixed tags → same pattern
- [x] 5.5 Add `zk_normalize_tags` integration test: create notes with non-compliant tags, call tool, verify diff, call again → `notes_updated == 0`

## 6. Verification

- [x] 6.1 Run `uv run pytest -v tests/` — all tests pass
- [x] 6.2 Run `uv run ruff check .` — no new lint violations
- [x] 6.3 Run `uv run mypy src/` — no new type errors (pre-existing duplicate module error unrelated to this change)
- [x] 6.4 Run `uv run bandit -r src/` — clean
- [x] 6.5 Manual smoke test: call `zk_create_note` with `tags="IO-psychology,LLM Prompts"` via MCP inspector; verify stored tags are `io-psychology,llm-prompts` and `normalised_tags` is reported in response
