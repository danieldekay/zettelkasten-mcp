## MODIFIED Requirements

### Requirement: structured-response
Every MCP tool MUST return a JSON-serialisable dict as its primary response.
The dict MUST contain a `"summary"` key with a human-readable string equivalent
to the previous plain-text response. Structured keys vary per tool and are
defined in each tool's docstring.

Every response dict that includes a `file_path` key MUST also include a
`vscode_uri` key whose value is `"vscode://file/" + file_path`. This URI allows
VS Code and GitHub Copilot Chat to render the note as a clickable link that
opens the file directly in the editor.

#### Scenario: create note — structured response
- **WHEN** `zk_create_note` is called with valid parameters
- **THEN** the response contains `note_id`, `file_path`, `vscode_uri`, and `summary` keys
- **AND** `vscode_uri` has the form `vscode://file/{absolute_path_to_note_md}`

#### Scenario: get note — structured response
- **WHEN** `zk_get_note` is called with a valid identifier
- **THEN** the response contains `note_id`, `title`, `note_type`, `tags` (list),
  `links` (list of dicts), `created_at`, `updated_at`, `content`, `metadata` (dict),
  `file_path`, `vscode_uri`, and `summary` keys
- **AND** `vscode_uri` has the form `vscode://file/{absolute_path_to_note_md}`

#### Scenario: search notes — structured response
- **WHEN** `zk_search_notes` is called with a query
- **THEN** the response contains `notes` (list of dicts with `note_id`, `title`,
  `note_type`, `tags`, `preview`, `score`, `file_path`, `vscode_uri`), `total`, and `summary` keys
- **AND** each note dict's `vscode_uri` has the form `vscode://file/{absolute_path_to_note_md}`

#### Scenario: create link — structured response
- **WHEN** `zk_create_link` is called with valid source, target, and link type
- **THEN** the response contains `source_id`, `target_id`, `link_type`, and `summary` keys

#### Scenario: linked notes — structured response
- **WHEN** `zk_get_linked_notes` is called
- **THEN** the response contains `note_id`, `direction`, `notes` (list of dicts
  including `link_type`, `description`, `file_path`, `vscode_uri`), `total`, and `summary` keys

#### Scenario: find orphaned notes — structured response
- **WHEN** `zk_find_orphaned_notes` is called
- **THEN** the response contains `notes` (list of dicts with `file_path` and `vscode_uri`), `total`, and `summary` keys

#### Scenario: find central notes — structured response
- **WHEN** `zk_find_central_notes` is called
- **THEN** the response contains `notes` (list of dicts with `note_id`, `title`,
  `connection_count`, `file_path`, `vscode_uri`), `total`, and `summary` keys

#### Scenario: get all tags — structured response
- **WHEN** `zk_get_all_tags` is called
- **THEN** the response contains `tags` (list of dicts with `name` and `count`),
  `total`, and `summary` keys

#### Scenario: tool error — structured error response
- **WHEN** any tool raises a handled exception (ValueError, note-not-found, etc.)
- **THEN** the response contains `error: true`, `error_type`, `message`, and
  `summary` keys — it does NOT raise an unhandled Python exception

#### Scenario: vscode_uri opens note in VS Code editor
- **WHEN** a user or agent follows a `vscode_uri` value from any note-returning tool
- **THEN** VS Code opens the corresponding markdown note file at the correct absolute path
