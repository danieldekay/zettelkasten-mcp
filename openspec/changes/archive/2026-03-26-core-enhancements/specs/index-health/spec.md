## ADDED Requirements

### Requirement: Index health dashboard

The system SHALL provide a `zk_get_index_status` MCP tool that returns a
health summary comparing the filesystem note count with the SQLite DB index.

The tool SHALL return:
- `total_notes_filesystem`: count of `.md` files in the notes directory
- `total_notes_indexed`: count of notes in the DB
- `orphaned_files`: count of `.md` files that have no DB record
- `orphaned_db_records`: count of DB records that have no corresponding `.md` file
- `orphaned_file_paths`: list of paths for orphaned files
- `orphaned_db_ids`: list of IDs for orphaned DB records
- `database_size_mb`: current size of the SQLite database file in megabytes

#### Scenario: Healthy system

- **WHEN** `zk_get_index_status` is called and filesystem and DB are in sync
- **THEN** `orphaned_files` and `orphaned_db_records` are both `0`
- **AND** `total_notes_filesystem` equals `total_notes_indexed`

#### Scenario: Orphaned filesystem files

- **WHEN** one or more `.md` files exist that have no corresponding DB record
- **THEN** `orphaned_files` is greater than `0`
- **AND** `orphaned_file_paths` lists the affected paths

#### Scenario: Stale DB records

- **WHEN** one or more DB records exist for notes whose `.md` files have been deleted
- **THEN** `orphaned_db_records` is greater than `0`
- **AND** `orphaned_db_ids` lists the affected note IDs
