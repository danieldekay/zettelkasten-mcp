# Proposal: Advanced Features — Link Types, AI Suggestions & Resilience

## Summary

Extend the Zettelkasten MCP server with smarter linking, flexible semantics, and
self-healing infrastructure after the core enhancements (Phase 2) are stable.

## GitHub Issues

| Issue                                                            | Title                                                   | Label           |
| ---------------------------------------------------------------- | ------------------------------------------------------- | --------------- |
| [#10](https://github.com/entanglr/zettelkasten-mcp/issues/10) | Support flexible/custom link types                      | p2              |
| [#11](https://github.com/entanglr/zettelkasten-mcp/issues/11) | Implement link type inference (`zk_suggest_link_type`)  | p2, ai-assisted |
| [#12](https://github.com/entanglr/zettelkasten-mcp/issues/12) | Implement auto-tagging suggestions (`zk_suggest_tags`)  | p2, ai-assisted |
| [#16](https://github.com/entanglr/zettelkasten-mcp/issues/16) | Implement graceful degradation with filesystem fallback | p2, reliability |
| [#17](https://github.com/entanglr/zettelkasten-mcp/issues/17) | Implement self-healing index with auto-rebuild          | p2              |

## Problem

The current 7 hardcoded link types are insufficient for domain-specific
knowledge graphs (e.g. `implements`, `enables`, `uses`). There is no guidance
for users on which link type to choose. Tags drift out of consistency at scale.
A database failure makes the server completely unusable even for read operations.
An out-of-sync index is not automatically detected or repaired.

## Proposed Changes

1. **Flexible link types** (#10) — allow registering custom link types persisted
   in `openspec/config.yaml` (project-scoped) or `config.py` (globally).
2. **Link type inference** (#11) — `zk_suggest_link_type` analyses note content
   and returns the top-3 most appropriate link types with confidence scores.
3. **Auto-tagging suggestions** (#12) — `zk_suggest_tags` uses TF-IDF similarity
   against existing notes to suggest consistent tags.
4. **Graceful degradation** (#16) — all read operations fall back to direct
   Markdown file parsing when the DB is unavailable.
5. **Self-healing index** (#17) — startup check compares filesystem vs. index
   count; if delta exceeds a configurable threshold, auto-rebuilds or warns.

## Out of Scope

- Temporal queries / analytics (Phase 4)
- Changing the existing 7 built-in link types

## Success Criteria

- Custom link types survive server restart
- `zk_suggest_link_type` returns a result in < 1 s for notes up to 5 KB
- `zk_suggest_tags` returns top-10 suggestions in < 500 ms against 1 000+ notes
- Server serves read requests with a corrupt/missing DB (graceful degradation)
- Self-healing triggers rebuild when drift > 5% of total notes
