## ADDED Requirements

### Requirement: Atomic batch note creation

The system SHALL provide a `zk_create_notes_batch` MCP tool that creates multiple
notes in a single atomic operation, returning per-note results.

Each note definition MUST include `title` and `content`. Fields `note_type`, `tags`,
and `metadata` are optional; `note_type` defaults to `permanent`.

The tool SHALL validate all note definitions before writing any notes. If any
definition is invalid, the tool MUST return an error and write nothing.

#### Scenario: Successful batch creation

- **WHEN** `zk_create_notes_batch` is called with a list of valid note definitions
- **THEN** all notes are created atomically
- **AND** the response includes `created` (count), `note_ids` (list), `failed: 0`, and `errors: []`

#### Scenario: Validation failure aborts entire batch

- **WHEN** `zk_create_notes_batch` is called and one note definition has an empty title
- **THEN** no notes are written
- **AND** the response includes an error message identifying the failing index

#### Scenario: Invalid note_type is rejected

- **WHEN** `zk_create_notes_batch` is called with a note whose `note_type` is not a valid enum value
- **THEN** no notes are written
- **AND** the response includes a validation error naming the invalid type and listing valid options

### Requirement: Batch performance advantage

The system SHALL create 50 notes via `zk_create_notes_batch` faster than 50
sequential `zk_create_note` calls.

#### Scenario: Batch is faster than sequential

- **WHEN** 50 notes are created using `zk_create_notes_batch`
- **THEN** the elapsed time is less than 50 individual `zk_create_note` calls
