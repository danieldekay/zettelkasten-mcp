## ADDED Requirements

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
