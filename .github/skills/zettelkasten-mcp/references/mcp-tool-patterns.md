# MCP Tool Patterns — Common Workflows

Reference patterns for common zettelkasten-mcp operations. Copy and adapt.

## Capture a fleeting idea

```
zk_create_note(
  title="[brief label]",
  content="[raw thought — no polish needed]",
  note_type="fleeting",
  tags=["[topic]"]
)
```

## Process literature into a note

```
zk_create_note(
  title="[Author YYYY] — [Paper/Book Title]",
  content="## Source\n[full citation]\n\n## Key claims\n- ...\n\n## My response\n...",
  note_type="literature",
  tags=["[author-year]", "[domain]"]
)
```

## Promote fleeting → permanent

```
# 1. Get the fleeting note
zk_get_note(note_id="FLEETING_ID")

# 2. Create refined permanent note
zk_create_note(
  title="[declarative claim — one idea]",
  content="[own words, references sources]",
  note_type="permanent",
  tags=["[topic]", "[related-concept]"]
)

# 3. Link to source fleeting and literature notes
zk_create_link(source_id="PERM_ID", target_id="LIT_ID", link_type="extends", bidirectional=true)

# 4. Optionally delete the fleeting note
zk_delete_note(note_id="FLEETING_ID")
```

## Build a structure note (MOC)

```
zk_create_note(
  title="MOC: [Topic]",
  content="# MOC: [Topic]\n\nEntry point for all notes on [topic].\n\n## Core notes\n...\n\n## Subtopics\n...",
  note_type="structure",
  tags=["moc", "[topic]"]
)
# Then link all relevant permanent notes → this MOC with link_type="related"
```

## Find notes to link

```
# By semantic content
zk_search_notes(query="[concept phrase]", limit=10)

# By tag
zk_search_notes(tags=["tag1", "tag2"])

# By existing connections
zk_get_linked_notes(note_id="NOTE_ID", direction="both")
```

## Session health check

```
zk_health_check()  # look for orphan notes, broken links
zk_get_stats()     # graph density — aim for >2 avg links/note
```

## Rebuild after file edits

```
zk_rebuild_index()  # always run after any direct .md file edits
```
