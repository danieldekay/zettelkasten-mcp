# Code Review: json-responses

## Overview

The structured JSON response contract is fully implemented in `mcp_server.py` via two
central helper methods (`_note_to_dict`, `_note_summary_dict`) and the `format_error_response`
method. All 251 tests pass. The implementation is clean, consistent, and well-tested.

## Strengths

- Two helpers centralise response construction — adding a field in one place propagates to all tools automatically
- `format_error_response` provides a single, typed error envelope used everywhere
- `vscode_uri` correctly uses `"vscode://file/" + str(Path)` — reliable on Linux/macOS
- All tools return dicts; none raise unhandled exceptions to the MCP layer
- Test coverage for `mcp_server.py` is 86% (well above the file-level average)

## Code Quality

- **Readability**: High — response construction is declarative and grouped logically per tool
- **Maintainability**: High for most tools. `zk_create_note` builds its response inline rather than using `_note_to_dict` (minor inconsistency, see Tech Debt)
- **Test Coverage**: 86% on `mcp_server.py`. All 9 spec scenarios have at least one test
- **Documentation**: Tool docstrings describe `vscode_uri`. README and ARCHITECTURE.md show `file_path` but have not yet been updated for `vscode_uri`

## Discrepancies Found

### 1. `connection_count` vs `connections` — spec/implementation mismatch

The spec says `zk_find_central_notes` returns dicts with `connection_count`, but the
implementation uses the key `connections`. Tests also assert `connections`, so the behaviour
is internally consistent — but the spec text is wrong. The spec should say `connections`.

**Scope**: spec text only — implementation and tests are aligned.

### 2. `description` vs `link_description` — spec/test mismatch

The spec says linked-note dicts include `link_type` and `description`. The implementation uses
`link_description`. Tests do not assert this key by name (they only check `total` and `note_id`).

**Scope**: spec text diverges from implementation. Test coverage for this key is absent.

### 3. `vscode_uri` not in base spec

The `vscode-file-link-uris` change added a delta spec, but `openspec/specs/json-responses/spec.md`
has not been updated yet. The base spec still describes create-note response as containing only
`note_id`, `file_path`, `summary` — `vscode_uri` is absent from the base spec text.

**Action**: Run `/opsx:sync-specs` to apply the delta.

## Concerns

- `zk_create_note` constructs `note_file_path` inline and then builds its own return dict rather than delegating to `_note_to_dict`. This means any future field additions to `_note_to_dict` won't automatically appear in the create response.
- Documentation (`README.md`, `ARCHITECTURE.md`, `docs/roadmap/moscow-top10-features.md`) still lists old response keys and does not mention `vscode_uri`.

## Recommendations

1. Fix spec text: `connection_count` → `connections` in the `find central notes` scenario
2. Clarify spec text: `description` → `link_description` in the `linked notes` scenario
3. Sync delta spec with `/opsx:sync-specs`
4. Update `README.md` tool table and `ARCHITECTURE.md` diagram to include `vscode_uri`
5. Consider refactoring `zk_create_note` to delegate its return dict to `_note_to_dict` (low priority)
