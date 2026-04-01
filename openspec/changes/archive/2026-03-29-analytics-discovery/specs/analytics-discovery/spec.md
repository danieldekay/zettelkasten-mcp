## ADDED Requirements

### Requirement: Temporal Note Queries
The system SHALL expose `zk_find_notes_in_timerange` as an MCP tool that returns
notes whose `created_at` or `updated_at` timestamp falls within a caller-supplied
ISO 8601 date range. The tool SHALL accept: `start_date` (str), `end_date` (str),
`date_field` (str, default `"created_at"`), `include_linked` (bool, default
`false`), and `note_type` (str, optional). It SHALL return a JSON object of the
form `{"count": <int>, "notes": [...]}`.

#### Scenario: Notes created in a date range
- **WHEN** `zk_find_notes_in_timerange(start_date="2026-01-01", end_date="2026-01-31")` is called with 50 notes created in January 2026
- **THEN** all 50 notes (and only those notes) are returned with `count=50`

#### Scenario: Notes filtered by updated_at
- **WHEN** `zk_find_notes_in_timerange` is called with `date_field="updated_at"` and a range covering 2026-03
- **THEN** notes last modified in that range are returned regardless of their creation date

#### Scenario: Include linked neighbour notes
- **WHEN** 5 notes fall in the date range and each links to 2 notes outside the range, and `include_linked=true` is passed
- **THEN** up to 15 notes are returned (5 direct + linked neighbours, deduped)

#### Scenario: Filter by note type
- **WHEN** `note_type="permanent"` is supplied
- **THEN** only permanent-type notes within the date range are returned

#### Scenario: Empty result set
- **WHEN** no notes fall within the specified date range
- **THEN** the tool returns `{"count": 0, "notes": []}` without error

#### Scenario: Invalid date format
- **WHEN** `start_date` is a non-ISO 8601 string (e.g., `"yesterday"`)
- **THEN** the tool returns an error response containing a message that states the expected ISO 8601 format

### Requirement: Date Column Indexing
The system SHALL declare `index=True` on `DBNote.created_at` and
`DBNote.updated_at` columns so that SQLAlchemy generates single-column indexes
(`ix_notes_created_at`, `ix_notes_updated_at`) on the underlying SQLite table.

#### Scenario: Index present after schema creation
- **WHEN** the database is initialised (tables created)
- **THEN** `ix_notes_created_at` and `ix_notes_updated_at` indexes exist in the SQLite schema

### Requirement: Tag Co-occurrence Cluster Analysis
The system SHALL expose `zk_analyze_tag_clusters` as an MCP tool that identifies
groups of tags which frequently appear together on the same notes. It SHALL
accept `min_co_occurrence` (int) and return a JSON object of the form:
`{"clusters": [{"tags": [...], "count": <int>, "representative_notes": [...]}], "total_tag_pairs_analysed": <int>}`.
Each cluster SHALL include up to 5 representative note IDs.

#### Scenario: Clusters above threshold
- **WHEN** two tags co-occur on 47 notes and `min_co_occurrence=10` is used
- **THEN** a cluster containing both tags is returned with `count=47` and up to 5 `representative_notes`

#### Scenario: Threshold filters sparse pairs
- **WHEN** a tag pair co-occurs only 2 times and `min_co_occurrence=3` is set
- **THEN** that tag pair does NOT appear in the clusters output

#### Scenario: No clusters found
- **WHEN** every tag appears on exactly one unique note (no co-occurrence)
- **THEN** the tool returns `{"clusters": [], "total_tag_pairs_analysed": <n>}` without error

#### Scenario: Performance under load
- **WHEN** 1 000 distinct tags exist across 10 000 notes
- **THEN** `zk_analyze_tag_clusters` returns a result within 2 seconds
