## ADDED Requirements

### Requirement: Per-note consistency verification

The system SHALL provide a `zk_verify_note` MCP tool that checks whether a specific
note is consistent between the filesystem (Markdown file) and the SQLite DB index.

The tool SHALL return:
- `note_id`: the queried ID
- `file_exists`: whether the `.md` file is present on disk
- `db_indexed`: whether the note has a DB record
- `link_count`: number of outgoing links recorded in the DB
- `tag_count`: number of tags recorded in the DB
- `hint` (optional): actionable advice when inconsistency is detected

#### Scenario: Fully indexed note

- **WHEN** `zk_verify_note` is called for a note that exists in both filesystem and DB
- **THEN** the response has `file_exists: true` and `db_indexed: true`
- **AND** `link_count` and `tag_count` reflect the current DB state

#### Scenario: File-only note (not indexed)

- **WHEN** `zk_verify_note` is called for a note that has a Markdown file but no DB record
- **THEN** the response has `file_exists: true` and `db_indexed: false`
- **AND** `hint` contains guidance to run `zk_rebuild_index`

#### Scenario: Note not found anywhere

- **WHEN** `zk_verify_note` is called with an ID that has neither a file nor a DB record
- **THEN** the response has `file_exists: false` and `db_indexed: false`
