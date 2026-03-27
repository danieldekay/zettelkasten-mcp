## Purpose

Defines the FTS5 full-text search engine contract for `zk_search_notes`. BM25 ranking via SQLite FTS5 virtual table; Python-side keyword filtering is prohibited.

## Requirements

### Requirement: fts5-query-engine
`zk_search_notes` MUST use the SQLite FTS5 virtual table (`notes_fts`) for
full-text search when a `query` string is provided. Python-side content filtering
MUST NOT be used for keyword queries.

#### Scenario: keyword search uses FTS5
- **WHEN** `zk_search_notes(query="GraphRAG")` is called
- **THEN** results are produced by FTS5 MATCH query, not Python string search
- **THEN** results are sorted by BM25 relevance rank (most relevant first)

#### Scenario: filter-only search (no query string)
- **WHEN** `zk_search_notes(tags="ai", note_type="permanent")` is called with no `query`
- **THEN** results are produced by a SQL `WHERE` clause on `notes` and `note_tags` tables
- **THEN** the FTS5 join is NOT used (no unnecessary overhead)

#### Scenario: combined query + filter
- **WHEN** `zk_search_notes(query="machine learning", tags="ai", note_type="permanent")` is called
- **THEN** FTS5 MATCH filters text, AND SQL predicates filter by tag and note_type
- **THEN** only notes matching ALL three criteria are returned

#### Scenario: search performance
- **WHEN** `zk_search_notes` is called on a database with 10 000 notes
- **THEN** results are returned in < 50 ms

#### Scenario: FTS5 index kept in sync on write
- **WHEN** a note is created via `zk_create_note`
- **THEN** the corresponding FTS5 entry is inserted in the same DB transaction
- **WHEN** a note is updated via `zk_update_note`
- **THEN** the FTS5 entry is updated in the same DB transaction
- **WHEN** a note is deleted via `zk_delete_note`
- **THEN** the FTS5 entry is deleted in the same DB transaction

#### Scenario: empty query returns no results
- **WHEN** `zk_search_notes(query="")` is called with no filters
- **THEN** the response returns an empty `notes` list (not all notes)
