## ADDED Requirements

### Requirement: Parameterized SQL queries in NoteRepository

The system SHALL use parameterized SQL queries (named bind parameters) for all
raw SQL statements executed via `text()` in `NoteRepository`. F-string or
string-concatenation interpolation of user-controlled values into SQL strings
is prohibited.

#### Scenario: Delete operations use bind parameters

- **WHEN** `NoteRepository.delete(id)` is called with any note ID
- **THEN** the SQL DELETE statements use named bind parameters (`:id`) rather than f-string interpolation
- **AND** the executed SQL does not contain the literal value of `id` embedded in the query string

#### Scenario: Index operations use bind parameters

- **WHEN** `NoteRepository._index_note(note)` rebuilds links and tags for a note
- **THEN** all DELETE statements use named bind parameters (`:note_id`) rather than f-string interpolation

#### Scenario: Update operations use bind parameters

- **WHEN** `NoteRepository.update(note)` removes existing links before re-adding
- **THEN** the DELETE statement uses named bind parameters (`:note_id`) rather than f-string interpolation

#### Scenario: Note ID containing SQL metacharacters does not cause errors

- **WHEN** a note with an ID containing characters like `'`, `--`, or `;` is passed to `delete()`, `update()`, or `_index_note()`
- **THEN** the operation completes safely with no SQL errors and no unintended data modification
