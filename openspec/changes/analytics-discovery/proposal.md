# Proposal: Analytics & Discovery — Temporal Queries and Tag Clustering

## Summary

Add analytics tools that answer "what did I learn this week?" and "which
topics cluster together?" — enabling review workflows and tag taxonomy
maintenance at scale.

## GitHub Issues

| Issue                                                            | Title                                                      | Label         |
| ---------------------------------------------------------------- | ---------------------------------------------------------- | ------------- |
| [#13](https://github.com/basf-global/zettelkasten-mcp/issues/13) | Add temporal queries (`zk_find_notes_in_timerange`)        | p2, query     |
| [#15](https://github.com/basf-global/zettelkasten-mcp/issues/15) | Add tag co-occurrence analysis (`zk_analyze_tag_clusters`) | p2, analytics |

## Problem

With 1 000+ notes it becomes impossible to answer:

- "Show me everything I captured in the last two weeks"
- "Which tags almost always appear together — could they be merged or grouped?"

The current search tools require exact terms; there is no date-range or
co-occurrence mode.

## Proposed Changes

1. **`zk_find_notes_in_timerange`** (#13) — filters notes by `created_at` or
   `updated_at` within an ISO 8601 date range, with optional expansion to
   include notes linked from the results.
2. **`zk_analyze_tag_clusters`** (#15) — computes a co-occurrence matrix over
   all `note_tags` rows and groups tags that appear together above a configurable
   threshold.

## Out of Scope

- Visualisation / charting (no runtime dependency on matplotlib etc.)
- Semantic / vector-similarity search

## Success Criteria

- `zk_find_notes_in_timerange` supports both `created_at` and `updated_at` axes
- Date range queries return in < 200 ms for 10 000 notes (SQLite index)
- `zk_analyze_tag_clusters` completes in < 2 s for 1 000 tags / 10 000 notes
- All edge cases covered: empty range, single-day range, overlapping clusters
