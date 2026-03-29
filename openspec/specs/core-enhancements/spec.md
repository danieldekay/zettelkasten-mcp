# Spec: Core Enhancements — Batch Operations, Verification & Health

## Purpose
Provides batch operations for efficient note and link creation, verification tools to ensure filesystem-database consistency, and health monitoring capabilities for the Zettelkasten system.

## Requirement 1: Batch Note Creation (resolves #5)

The system SHALL expose a `zk_create_notes_batch` MCP tool that accepts a list
of note definitions and creates all of them within a single database transaction.

### Scenario: Successful batch creation
- GIVEN a list of 15 valid note definitions
- WHEN `zk_create_notes_batch` is called
- THEN all 15 notes are written to the filesystem
- AND all 15 notes are indexed in SQLite
- AND the tool returns a JSON object containing all 15 generated IDs
- AND the total wall-clock time is less than the sum of 15 individual `zk_create_note` calls

### Scenario: Partial validation failure
- GIVEN a list of note definitions where one has an empty title
- WHEN `zk_create_notes_batch` is called
- THEN no notes are created (full rollback)
- AND the tool returns an error identifying which item failed validation and why

### Scenario: Database error mid-batch
- GIVEN a batch of 10 notes where the DB raises an error after note 5
- WHEN `zk_create_notes_batch` is called
- THEN the transaction is rolled back
- AND no notes appear in the filesystem or DB
- AND the error message includes the partial progress point

### Scenario: Invalid note_type is rejected
- WHEN `zk_create_notes_batch` is called with a note whose `note_type` is not a valid enum value
- THEN no notes are written
- AND the response includes a validation error naming the invalid type and listing valid options

## Requirement 1b: Batch Note Creation Performance

The system SHALL create 50 notes via `zk_create_notes_batch` faster than 50
sequential `zk_create_note` calls.

### Scenario: Batch is faster than sequential
- WHEN 50 notes are created using `zk_create_notes_batch`
- THEN the elapsed time is less than 50 individual `zk_create_note` calls

## Requirement 2: Batch Link Creation (resolves #6)

The system SHALL expose a `zk_create_links_batch` MCP tool that creates
multiple semantic links atomically.

### Scenario: Successful batch linking
- GIVEN a list of 20 valid link definitions referencing existing notes
- WHEN `zk_create_links_batch` is called
- THEN all 20 links are created in one transaction
- AND the tool returns `{"created": 20, "failed": 0, "errors": []}`

### Scenario: Invalid link type in batch
- GIVEN a batch where one link has an unsupported `link_type`
- WHEN `zk_create_links_batch` is called
- THEN the entire batch is rejected
- AND the error identifies the offending link by index and type name

### Scenario: Non-existent target note
- GIVEN a batch where one link references a target note ID that does not exist
- WHEN `zk_create_links_batch` is called
- THEN the entire batch is rejected with a `NoteNotFoundError`

## Requirement 2b: Batch Link Creation Performance

The system SHALL create 20 links via `zk_create_links_batch` faster than 20
sequential `zk_create_link` calls.

### Scenario: Batch is faster than sequential
- WHEN 20 links are created using `zk_create_links_batch`
- THEN the elapsed time is less than 20 individual `zk_create_link` calls

## Requirement 3: Note Verification (resolves #9)

The system SHALL expose a `zk_verify_note` MCP tool that confirms the
consistency of a single note between the filesystem and database index.

### Scenario: Fully consistent note
- GIVEN a note that exists on the filesystem and in the DB index
- WHEN `zk_verify_note` is called with its ID
- THEN the response contains `"file_exists": true`, `"db_indexed": true`
- AND returns the link count and tag count for that note

### Scenario: File exists but not indexed
- GIVEN a Markdown file that was written but the index was never rebuilt
- WHEN `zk_verify_note` is called with its ID
- THEN the response contains `"file_exists": true`, `"db_indexed": false`
- AND includes a hint: `"Run zk_rebuild_index to sync"`

### Scenario: Note ID not found anywhere
- GIVEN a note ID that does not correspond to any file or DB record
- WHEN `zk_verify_note` is called
- THEN the response contains `"file_exists": false`, `"db_indexed": false`

## Requirement 4: Index Health Dashboard (resolves #14)

The system SHALL expose a `zk_get_index_status` MCP tool that returns a
comprehensive health summary of the database vs. the filesystem.

### Scenario: Healthy system
- GIVEN a system where all Markdown files are indexed and no stale DB records exist
- WHEN `zk_get_index_status` is called
- THEN `orphaned_files` and `orphaned_db_records` are both 0
- AND `total_notes_filesystem` equals `total_notes_indexed`

### Scenario: Orphaned files detected
- GIVEN that 3 note files exist on disk but are absent from the DB
- WHEN `zk_get_index_status` is called
- THEN `orphaned_files` equals 3
- AND the response lists each orphaned file path

### Scenario: Stale DB records detected
- GIVEN that 2 DB entries reference files that no longer exist on disk
- WHEN `zk_get_index_status` is called
- THEN `orphaned_db_records` equals 2
- AND `database_size_mb` is reported
## Requirements
### Requirement: Note search results include source provenance
The system SHALL include `is_readonly` (boolean) and `source_path` (string or null) in the data returned by search, list, and get-note operations so that callers can distinguish primary notes from read-only watch-folder references. When `is_readonly` is `True`, `source_path` SHALL contain the absolute path to the source file. When `is_readonly` is `False` (or absent), `source_path` SHALL be `null`.

#### Scenario: Search results for a primary note omit source_path
- **WHEN** `zk_search_notes` returns results that include a primary (writable) note
- **THEN** the result entry for that note has `is_readonly: false` and `source_path: null`

#### Scenario: Search results for a watch-folder note include source_path
- **WHEN** `zk_search_notes` returns results that include a watch-folder (read-only) note
- **THEN** the result entry for that note has `is_readonly: true` and `source_path` set to the absolute file path of the source Markdown file

### Requirement: List notes supports filtering by source type
The system SHALL accept an optional `include_external` boolean parameter on `zk_list_notes` (default `true`). When `include_external` is `false`, only primary (writable) notes SHALL be returned. When `include_external` is `true` (the default), both primary and watch-folder notes SHALL be returned.

#### Scenario: Default list includes watch-folder notes
- **WHEN** `zk_list_notes` is called without `include_external`
- **THEN** the response includes both primary notes and watch-folder notes

#### Scenario: Filtering excludes watch-folder notes
- **WHEN** `zk_list_notes` is called with `include_external: false`
- **THEN** the response contains only primary notes
- **AND** no watch-folder note IDs appear in the results

