## ADDED Requirements

### Requirement: structured-response
Every MCP tool MUST return a JSON-serialisable dict as its primary response.
The dict MUST contain a `"summary"` key with a human-readable string equivalent
to the previous plain-text response. Structured keys vary per tool and are
defined in each tool's docstring.

#### Scenario: create note — structured response
- **WHEN** `zk_create_note` is called with valid parameters
- **THEN** the response contains `note_id`, `file_path`, and `summary` keys

#### Scenario: get note — structured response
- **WHEN** `zk_get_note` is called with a valid identifier
- **THEN** the response contains `note_id`, `title`, `note_type`, `tags` (list),
  `links` (list of dicts), `created_at`, `updated_at`, `content`, `metadata` (dict),
  and `summary` keys

#### Scenario: search notes — structured response
- **WHEN** `zk_search_notes` is called with a query
- **THEN** the response contains `notes` (list of dicts with `note_id`, `title`,
  `note_type`, `tags`, `preview`, `score`), `total`, and `summary` keys

#### Scenario: create link — structured response
- **WHEN** `zk_create_link` is called with valid source, target, and link type
- **THEN** the response contains `source_id`, `target_id`, `link_type`, and `summary` keys

#### Scenario: linked notes — structured response
- **WHEN** `zk_get_linked_notes` is called
- **THEN** the response contains `note_id`, `direction`, `notes` (list of dicts
  including `link_type` and `description`), `total`, and `summary` keys

#### Scenario: find orphaned notes — structured response
- **WHEN** `zk_find_orphaned_notes` is called
- **THEN** the response contains `notes` (list of dicts), `total`, and `summary` keys

#### Scenario: find central notes — structured response
- **WHEN** `zk_find_central_notes` is called
- **THEN** the response contains `notes` (list of dicts with `note_id`, `title`,
  `connection_count`), `total`, and `summary` keys

#### Scenario: get all tags — structured response
- **WHEN** `zk_get_all_tags` is called
- **THEN** the response contains `tags` (list of dicts with `name` and `count`),
  `total`, and `summary` keys

#### Scenario: tool error — structured error response
- **WHEN** any tool raises a handled exception (ValueError, note-not-found, etc.)
- **THEN** the response contains `error: true`, `error_type`, `message`, and
  `summary` keys — it does NOT raise an unhandled Python exception
