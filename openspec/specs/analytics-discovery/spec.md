# Spec: Analytics & Discovery

## Purpose

Provides two analytical tools: temporal filtering of notes by date range, and
tag co-occurrence cluster analysis. Both tools are exposed as MCP tools.

---

## Requirement 1: Temporal Queries

The system SHALL expose `zk_find_notes_in_timerange` to filter notes by date.

### Scenario: Notes created in a date range

- GIVEN 50 notes created between 2026-01-01 and 2026-01-31
- WHEN `zk_find_notes_in_timerange(start_date="2026-01-01", end_date="2026-01-31")`
  is called with default `date_field="created_at"`
- THEN all 50 notes (and only those notes) are returned

### Scenario: Notes updated in a date range

- GIVEN a note created in 2025 but updated in 2026-03
- WHEN `zk_find_notes_in_timerange` is called with `date_field="updated_at"` covering 2026-03
- THEN the note is included in the results

### Scenario: Include linked notes

- GIVEN 5 notes in the date range, each linked to 2 notes outside the range
- WHEN `include_linked=true` is passed
- THEN up to 15 notes are returned (5 direct + linked neighbours deduped)

### Scenario: Empty date range

- GIVEN no notes match the specified range
- WHEN `zk_find_notes_in_timerange` is called
- THEN an empty list is returned with a summary: `{"count": 0, "notes": []}`

### Scenario: Invalid date format

- GIVEN `start_date="yesterday"` (non-ISO 8601)
- WHEN the tool is called
- THEN a `ValueError` is returned with a message explaining the expected format

---

## Requirement 2: Tag Co-occurrence Analysis

The system SHALL expose `zk_analyze_tag_clusters` to identify groups of tags
that frequently appear on the same notes.

### Scenario: Clusters above threshold

- GIVEN notes tagged with both `"ai-agents"` and `"agentic-programming"` 47 times
- WHEN `zk_analyze_tag_clusters(min_co_occurrence=10)` is called
- THEN a cluster containing both tags is returned with `count=47`
- AND up to 5 representative note IDs are included per cluster

### Scenario: Threshold filters sparse pairs

- GIVEN a tag pair that co-occurs only 2 times
- WHEN `min_co_occurrence=3` is used
- THEN that pair does not appear in the output

### Scenario: No clusters found

- GIVEN every tag appears on exactly one unique note (no overlap)
- WHEN `zk_analyze_tag_clusters` is called
- THEN an empty clusters list is returned (not an error)

### Scenario: Performance

- GIVEN 1 000 distinct tags across 10 000 notes
- WHEN `zk_analyze_tag_clusters` is called
- THEN the response is returned in < 2 s
