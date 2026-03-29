## ADDED Requirements

### Requirement: Temporal Queries

The system SHALL expose `zk_find_notes_in_timerange` to filter notes by date range.

#### Scenario: Notes created in a date range

- **WHEN** `zk_find_notes_in_timerange(start_date="2026-01-01", end_date="2026-01-31")` is called with default `date_field="created_at"`
- **THEN** all notes created between those dates (and only those notes) are returned

#### Scenario: Notes updated in a date range

- **WHEN** `zk_find_notes_in_timerange` is called with `date_field="updated_at"` covering a date range
- **THEN** notes updated within that range are included in the results, regardless of creation date

#### Scenario: Include linked notes

- **WHEN** `include_linked=true` is passed and notes in the date range link to notes outside the range
- **THEN** the result includes both the direct matches and their linked neighbours, deduplicated

#### Scenario: Empty date range

- **WHEN** `zk_find_notes_in_timerange` is called with a range matching no notes
- **THEN** an empty list is returned: `{"count": 0, "notes": []}`

#### Scenario: Invalid date format

- **WHEN** `start_date="yesterday"` (non-ISO 8601) is passed
- **THEN** a `ValueError` is raised with a message explaining the expected ISO 8601 format

### Requirement: Tag Co-occurrence Analysis

The system SHALL expose `zk_analyze_tag_clusters` to identify groups of tags that frequently appear on the same notes.

#### Scenario: Clusters above threshold

- **WHEN** `zk_analyze_tag_clusters(min_co_occurrence=10)` is called and tag pairs co-occur above the threshold
- **THEN** clusters containing those tags are returned with their co-occurrence count
- **AND** up to 5 representative note IDs are included per cluster

#### Scenario: Threshold filters sparse pairs

- **WHEN** `min_co_occurrence=3` is used and a tag pair co-occurs only 2 times
- **THEN** that pair does not appear in the output

#### Scenario: No clusters found

- **WHEN** every tag appears on exactly one unique note (no overlap)
- **THEN** an empty clusters list is returned: `{"clusters": [], "total_tag_pairs_analysed": 0}`

#### Scenario: Performance

- **WHEN** `zk_analyze_tag_clusters` is called with 1,000 distinct tags across 10,000 notes
- **THEN** the response is returned in under 2 seconds
