# watch-folder-indexing Specification

## Purpose
TBD - created by archiving change external-folder-indexing. Update Purpose after archive.
## Requirements
### Requirement: Watch-folder Markdown files are indexed at startup
The system SHALL scan each configured watch directory recursively for Markdown files (`.md` extension) during server startup, after primary notes indexing completes. Each discovered file SHALL be parsed for YAML frontmatter. Files with valid frontmatter containing at least a `title` or `id` field SHALL be ingested as read-only reference notes in the SQLite index. Files without compatible frontmatter SHALL be ingested as lightweight document stubs with an auto-generated `ext-<sha256[:12]>` ID derived from the file's absolute path, and a title derived from the filename (without extension). All ingested watch-folder notes SHALL have `is_readonly = True` and `source_path` set to their absolute file path. Parse errors in individual files SHALL be logged as WARNINGs and skipped without aborting startup.

#### Scenario: File with compatible frontmatter is ingested as a full note
- **WHEN** a watch directory contains a Markdown file with `id`, `title`, and `tags` in its YAML frontmatter
- **THEN** that file is indexed in SQLite with the declared `id` and `title`
- **AND** `is_readonly = True` and `source_path` equal to the file's absolute path

#### Scenario: File without frontmatter is ingested as a stub note
- **WHEN** a watch directory contains a Markdown file with no YAML frontmatter
- **THEN** that file is indexed with an auto-generated `ext-<sha256[:12]>` ID
- **AND** the title is the filename without the `.md` extension
- **AND** `is_readonly = True`

#### Scenario: Malformed frontmatter is skipped with a warning
- **WHEN** a watch directory contains a Markdown file with invalid YAML frontmatter
- **THEN** a WARNING is logged identifying the file and error
- **AND** that file is NOT added to the index
- **AND** all other valid files in the directory ARE still indexed

#### Scenario: No watch directories configured
- **WHEN** `watch_dirs` is empty
- **THEN** no watch-folder indexing occurs at startup and no errors are logged

### Requirement: Watch-folder notes respect read-only constraint
The system SHALL prevent any mutation operation (update content, delete, add/remove tags, add/remove links) on notes where `is_readonly = True`. Any attempt to mutate a read-only note via a service method SHALL raise a `PermissionError` with a message indicating the note is a read-only external reference and providing its `source_path`.

#### Scenario: Attempt to update a read-only note is rejected
- **WHEN** `ZettelService.update_note()` is called with a note ID belonging to a read-only watch-folder note
- **THEN** a `PermissionError` is raised
- **AND** the note's content and metadata remain unchanged in the index

#### Scenario: Attempt to delete a read-only note is rejected
- **WHEN** `ZettelService.delete_note()` is called with a note ID belonging to a read-only watch-folder note
- **THEN** a `PermissionError` is raised
- **AND** the note remains in the index

#### Scenario: Primary notes can still link to read-only notes
- **WHEN** `ZettelService.create_link()` creates a link where the target is a read-only watch-folder note
- **THEN** the link is created successfully
- **AND** the read-only note's data is NOT modified

