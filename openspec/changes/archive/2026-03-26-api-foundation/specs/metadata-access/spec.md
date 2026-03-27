## ADDED Requirements

### Requirement: metadata-write
`zk_create_note` and `zk_update_note` MUST accept an optional `metadata`
parameter containing a JSON string or dict of arbitrary key-value pairs.
The metadata MUST be persisted to both the Markdown frontmatter and the
SQLite `notes` table.

#### Scenario: create note with metadata
- **WHEN** `zk_create_note` is called with `metadata='{"source_url": "https://arxiv.org/abs/2404.16130", "reading_status": "complete"}'`
- **THEN** the note is created with the metadata dict stored in the `metadata` field
- **THEN** the Markdown frontmatter contains the metadata as a YAML mapping
- **THEN** the response dict includes the parsed `metadata` dict (not the raw string)

#### Scenario: update note metadata
- **WHEN** `zk_update_note` is called with a `metadata` parameter
- **THEN** the entire metadata dict is replaced with the new value
- **THEN** the Markdown frontmatter is updated accordingly

#### Scenario: invalid metadata JSON
- **WHEN** `zk_create_note` or `zk_update_note` is called with a `metadata` parameter that is not valid JSON
- **THEN** the tool returns a structured error response with `error: true` and `error_type: "invalid_metadata"`
- **THEN** no note is created or modified

### Requirement: metadata-read
`zk_get_note` MUST include the `metadata` dict in its response. Notes with no
stored metadata MUST return an empty dict `{}` (not `null` or absent key).

#### Scenario: get note with metadata
- **WHEN** `zk_get_note` is called for a note that has stored metadata
- **THEN** the response dict contains `"metadata"` with the correct key-value pairs

#### Scenario: get note without metadata
- **WHEN** `zk_get_note` is called for a note that has no stored metadata
- **THEN** the response dict contains `"metadata": {}`

#### Scenario: metadata round-trip
- **WHEN** a note is created with metadata, then retrieved with `zk_get_note`
- **THEN** the retrieved metadata exactly matches what was stored (no data loss, no type coercion)
