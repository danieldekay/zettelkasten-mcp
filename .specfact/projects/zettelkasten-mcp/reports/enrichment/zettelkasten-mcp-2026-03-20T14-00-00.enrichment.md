# zettelkasten-mcp Enrichment Report

**Date**: 2026-03-20T14:00:00
**Bundle**: zettelkasten-mcp

---

## Missing Features

1. **MCP Note CRUD Tools** (Key: FEATURE-MCP-NOTE-CRUD-TOOLS)
   - Confidence: 0.95
   - Outcomes: User-facing MCP tools for note lifecycle management exposed over the Model Context Protocol
   - Stories:
     1. AI client can create a note via zk_create_note
        - Acceptance: zk_create_note accepts title, content, note_type, and comma-separated tags, creates note via ZettelService, returns note ID and markdown file path, rejects invalid note_type with descriptive error
     2. AI client can retrieve a note via zk_get_note
        - Acceptance: zk_get_note accepts identifier (ID or title), resolves by ID first then by title, returns formatted note with ID, file path, type, timestamps, tags, links section, returns not-found message for unknown identifier
     3. AI client can update a note via zk_update_note
        - Acceptance: zk_update_note accepts note_id plus optional title, content, note_type, tags, applies partial update via ZettelService, returns updated note ID on success
     4. AI client can delete a note via zk_delete_note
        - Acceptance: zk_delete_note accepts note_id, verifies note existence before deletion, delegates to ZettelService.delete_note, returns success confirmation

2. **MCP Semantic Linking Tools** (Key: FEATURE-MCP-SEMANTIC-LINKING)
   - Confidence: 0.95
   - Outcomes: MCP tools to build, traverse, and remove the semantic knowledge graph between notes
   - Stories:
     1. AI client can create a directional or bidirectional semantic link
        - Acceptance: zk_create_link accepts source_id, target_id, link_type (one of 12 values), optional description, and bidirectional flag, creates link via ZettelService, returns confirmation with link direction, returns error on duplicate UNIQUE constraint
     2. AI client can remove a link between notes
        - Acceptance: zk_remove_link accepts source_id, target_id, bidirectional flag, removes link via ZettelService.remove_link, returns confirmation
     3. AI client can traverse linked notes
        - Acceptance: zk_get_linked_notes accepts note_id and direction (outgoing, incoming, both), returns formatted list of connected notes with link type and description, handles empty network gracefully

3. **MCP Knowledge Discovery Tools** (Key: FEATURE-MCP-KNOWLEDGE-DISCOVERY)
   - Confidence: 0.95
   - Outcomes: MCP tools that let an AI client explore, search, and analyse the knowledge network structure
   - Stories:
     1. AI client can search notes by text, tags, or type
        - Acceptance: zk_search_notes accepts optional query, tags (comma-separated), note_type, and limit, delegates to SearchService.search_combined, returns ranked list with title, ID, file path, tags, created date, and 150-char content preview
     2. AI client can find notes similar to a given note
        - Acceptance: zk_find_similar_notes accepts note_id, threshold (0.0-1.0), and limit, returns notes ranked by similarity score with tag and content preview, handles not-found note
     3. AI client can identify hub/central notes by connection count
        - Acceptance: zk_find_central_notes accepts limit, returns notes sorted by total incoming+outgoing links, shows connection count per note with file path and preview
     4. AI client can find isolated (orphaned) notes
        - Acceptance: zk_find_orphaned_notes returns all notes with zero incoming and outgoing links, includes file path, tags, and content preview per orphan
     5. AI client can list all tags in the knowledge base
        - Acceptance: zk_get_all_tags returns alphabetically sorted list of all unique tag names with total count
     6. AI client can browse notes by creation or update date
        - Acceptance: zk_list_notes_by_date accepts optional start_date, end_date (ISO format), use_updated flag, and limit, returns chronologically ordered notes with formatted date and file path
     7. AI client can trigger a manual index rebuild
        - Acceptance: zk_rebuild_index calls ZettelService.rebuild_index, returns note count before and after rebuild, reports delta

4. **Semantic Link Type Taxonomy** (Key: FEATURE-SEMANTIC-LINK-TAXONOMY)
   - Confidence: 0.90
   - Outcomes: Domain model encoding Zettelkasten semantic relations with 12 link types and enforced inverse pairs
   - Stories:
     1. System enforces a closed vocabulary of 12 semantic link types
        - Acceptance: LinkType enum defines REFERENCE, EXTENDS, EXTENDED_BY, REFINES, REFINED_BY, CONTRADICTS, CONTRADICTED_BY, QUESTIONS, QUESTIONED_BY, SUPPORTS, SUPPORTED_BY, RELATED, link_type field validated against enum on model construction, invalid type raises ValueError
     2. Bidirectional link creation stores the correct inverse type
        - Acceptance: when bidirectional=True, ZettelService.create_link stores forward link with specified type and reverse link with semantically correct inverse (extends↔extended_by, refines↔refined_by, etc.), symmetric types (reference, related) use same type in both directions

5. **Note Type Classification System** (Key: FEATURE-NOTE-TYPE-CLASSIFICATION)
   - Confidence: 0.88
   - Outcomes: Domain model encoding the Zettelkasten note taxonomy (fleeting, literature, permanent, structure, hub) used for filtering and workflow steering
   - Stories:
     1. Notes are typed using a closed vocabulary of five Zettelkasten note types
        - Acceptance: NoteType enum defines FLEETING, LITERATURE, PERMANENT, STRUCTURE, HUB, note_type field defaults to PERMANENT, invalid note_type string rejected at creation with descriptive error listing valid values, note type persisted in YAML frontmatter and SQLite DB
     2. Note type is used as a filter criterion in combined search
        - Acceptance: zk_search_notes accepts note_type string, converts to NoteType enum before passing to SearchService.search_combined, returns only notes of that type when specified

6. **MCP Resources and Prompts Stubs** (Key: FEATURE-MCP-RESOURCES-PROMPTS)
   - Confidence: 0.75
   - Outcomes: Placeholder for MCP resources (note://) and prompts (system-prompt) not yet implemented but identified as architectural gap
   - Stories:
     1. Server exposes note content as an MCP resource (not yet implemented)
        - Acceptance: _register_resources currently passes without registering any resources, future implementation should register note://{note_id} URI template returning note content for MCP resource consumption
     2. Server exposes workflow prompts as MCP prompts (not yet implemented)
        - Acceptance: _register_prompts currently passes without registering any prompts, future implementation should register system prompt and workflow guidance prompts (knowledge creation, exploration, synthesis) as MCP prompt templates

---

## Confidence Adjustments

- FEATURE-ZETTELKASTENMCPSERVER: 0.75 (reason: stories are server init/lifecycle only; actual MCP tool surface now captured in FEATURE-MCP-NOTE-CRUD-TOOLS, FEATURE-MCP-SEMANTIC-LINKING, and FEATURE-MCP-KNOWLEDGE-DISCOVERY)
- FEATURE-NOTE: 0.90 (reason: confirmed core domain model with validate_title, add_tag, remove_tag, add_link, get_linked_note_ids, to_markdown; model is frozen/immutable except for list mutations)
- FEATURE-NOTEREPOSITORY: 0.95 (reason: confirmed dual-storage implementation; Markdown files as source of truth, SQLite FTS5 index for search; rebuild_index reconstructs DB from markdown files on demand)
- FEATURE-SEARCHSERVICE: 0.92 (reason: confirmed search_by_text (FTS5 + TF-IDF), search_by_tag, search_by_link, find_orphaned_notes, find_central_notes, find_notes_by_date_range, find_similar_notes, search_combined)
- FEATURE-ZETTELSERVICE: 0.92 (reason: confirmed full business logic layer including create_note, get_note, update_note, delete_note, tag management, create_link with inverse semantics, remove_link, get_linked_notes, rebuild_index, export_note, find_similar_notes)
- FEATURE-ZETTELKASTENCONFIG: 0.85 (reason: config reads from env vars ZETTELKASTEN_NOTES_DIR, ZETTELKASTEN_DATABASE_PATH, ZETTELKASTEN_LOG_LEVEL with sensible defaults and absolute path resolution)

---

## Business Context

- Priority: FEATURE-MCP-NOTE-CRUD-TOOLS and FEATURE-MCP-SEMANTIC-LINKING are the highest-value user-facing features; they define the public contract with MCP client applications (Claude, Copilot)
- Constraint: All note mutations must preserve bi-directional consistency: markdown file and SQLite index must stay in sync; the rebuild_index mechanism is the recovery path when they diverge
- Risk: FEATURE-MCP-RESOURCES-PROMPTS is a stub today; AI clients cannot discover domain knowledge through MCP resource URIs until resources are registered; this limits autonomous knowledge exploration workflows
- Architecture: Dual-storage (Markdown + SQLite FTS5) enables both human-readable persistence and fast programmatic search; the database is intentionally ephemeral (deletable and rebuilt)
- Quality: 65 tests across 7 test files; coverage includes repository, service, integration, MCP server, and semantic link tests; duplicate tag prevention (UNIQUE constraint on note_tags) is a known fixed bug documented in copilot-instructions.md
