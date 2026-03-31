# Technical Debt: json-responses

## High Priority

- [ ] **Spec text incorrect: `connection_count` vs `connections`** — The spec scenario for
  `zk_find_central_notes` names the key `connection_count` but the implementation uses
  `connections`. Tests also assert `connections`. The spec must be corrected to avoid
  misleading future implementors or agents reading the spec. Fix: edit
  `openspec/specs/json-responses/spec.md` scenario text.

- [ ] **`vscode_uri` absent from base spec** — The delta from `vscode-file-link-uris` has not
  been synced to the main spec. Until synced, `openspec show json-responses` does not reflect
  the current implementation contract. Fix: run `/opsx:sync-specs vscode-file-link-uris`.

## Medium Priority

- [ ] **Spec text ambiguous: `description` vs `link_description`** — The linked-notes scenario
  says dicts include `description`, but the implementation key is `link_description`. No test
  asserts this key by name. Fix: (a) correct the spec to say `link_description`, and (b) add
  an assertion in `test_get_linked_notes_success` that the linked note dict contains
  `link_description`.

- [ ] **`zk_create_note` inline response dict** — This tool builds `note_id`, `file_path`,
  `vscode_uri`, `summary` manually rather than calling `_note_to_dict`. If new fields are added
  to `_note_to_dict` in the future, `zk_create_note` will silently omit them. Fix: modify
  `zk_create_note` to call `_note_to_dict(note)` and overlay `summary` and `warning`.

- [ ] **Documentation not updated for `vscode_uri`** — `README.md` tool table, `ARCHITECTURE.md`
  response diagram, and `docs/roadmap/moscow-top10-features.md` all show old response shapes
  without `vscode_uri`. Fix: update these files when the sync-specs step is complete.

## Low Priority

- [ ] **Error key uses Python `True` not JSON `true`** — `"error": True` serialises correctly
  via JSON, but the spec says `error: true`. No issue in practice; worth noting for spec
  readers who may expect a JSON literal.

- [ ] **`get note` scenario omits `file_path`/`vscode_uri`** — The spec scenario for
  `zk_get_note` does not list `file_path` or `vscode_uri` in its THEN clause, even though
  the implementation (via `_note_to_dict`) includes them. The scenario is incomplete.

## Refactoring Opportunities

- Consolidate inline response dicts scattered across individual tool handlers into helper methods.
  Currently `_note_to_dict` and `_note_summary_dict` cover most note responses, but `zk_create_note`
  and `zk_update_note` still build inline. A `_note_created_dict(note)` helper would enforce
  consistency.
