# Spec: Advanced Features

## Requirement 1: Flexible/Custom Link Types (resolves #10)

The system SHALL allow users to register project-local custom link types beyond
the 7 built-in types.

### Scenario: Register a symmetric custom link type

- GIVEN a call to `zk_register_link_type` with `name="complements"`, `symmetric=true`
- WHEN the registration succeeds
- THEN `zk_create_link` accepts `"complements"` as a valid `link_type`
- AND the type persists across server restarts

### Scenario: Register an asymmetric custom link type

- GIVEN a call with `name="implements"`, `inverse="implemented_by"`, `symmetric=false`
- WHEN the registration succeeds
- THEN `zk_create_link` accepts both `"implements"` and `"implemented_by"`

### Scenario: Duplicate registration

- GIVEN an attempt to register a type that already exists (built-in or custom)
- WHEN `zk_register_link_type` is called
- THEN the tool returns an error and the existing type is unchanged

---

## Requirement 2: Link Type Inference (resolves #11)

The system SHALL expose `zk_suggest_link_type` that recommends the most
appropriate link type for a source–target pair.

### Scenario: Confident suggestion

- GIVEN two notes where source builds on concepts defined in target
- WHEN `zk_suggest_link_type(source_id, target_id)` is called
- THEN the primary suggestion is `"extends"` with confidence > 0.6
- AND at least two alternative suggestions are returned

### Scenario: Low-confidence result

- GIVEN two notes with little semantic overlap
- WHEN `zk_suggest_link_type` is called
- THEN all confidence scores are < 0.4
- AND the response includes a `"low_confidence": true` flag

---

## Requirement 3: Auto-Tagging Suggestions (resolves #12)

The system SHALL expose `zk_suggest_tags` that returns consistent tag
recommendations based on note content and the existing tag taxonomy.

### Scenario: Suggestions for new note content

- GIVEN note content that overlaps with 20 existing notes tagged `"ai-agents"`
- WHEN `zk_suggest_tags(content)` is called
- THEN `"ai-agents"` appears in the top-5 suggestions with confidence > 0.7

### Scenario: No relevant matches

- GIVEN content on a topic not covered by any existing notes
- WHEN `zk_suggest_tags` is called
- THEN an empty suggestions list is returned (not an error)

---

## Requirement 4: Graceful Degradation (resolves #16)

The system SHALL continue to serve read operations when the SQLite database is
unavailable, by falling back to direct Markdown file parsing.

### Scenario: DB file missing at startup

- GIVEN the DB file does not exist when the server starts
- WHEN `zk_get_note(note_id)` is called
- THEN the note is read from its Markdown file
- AND a WARNING is logged: `"Database unavailable, using filesystem fallback"`

### Scenario: DB connection error at runtime

- GIVEN the DB becomes unreadable mid-session (e.g. permissions change)
- WHEN any read tool is invoked
- THEN the fallback path is used without raising an exception to the client

### Scenario: Write operations with unavailable DB

- GIVEN the DB is unavailable
- WHEN `zk_create_note` is called
- THEN the Markdown file is written
- AND the tool returns a warning: `"Note saved to filesystem; DB index unavailable"`

---

## Requirement 5: Self-Healing Index (resolves #17)

The system SHALL detect and optionally auto-correct index drift on startup.

### Scenario: Drift within tolerance

- GIVEN filesystem has 100 notes and DB has 98 notes (2% drift)
- WHEN the server starts with default config (`auto_rebuild_threshold: 5`)
- THEN a WARNING is logged but no rebuild is triggered

### Scenario: Drift exceeds threshold

- GIVEN filesystem has 100 notes and DB has 90 notes (10% drift)
- WHEN the server starts with `auto_rebuild_threshold: 5`
- THEN `rebuild_index()` is called automatically
- AND an INFO log states `"Auto-rebuild triggered: 10% drift detected"`

### Scenario: Auto-rebuild disabled

- GIVEN `auto_rebuild_threshold: 0` in config
- WHEN drift of any size is detected
- THEN no auto-rebuild occurs
- AND a WARNING is logged with the exact counts
