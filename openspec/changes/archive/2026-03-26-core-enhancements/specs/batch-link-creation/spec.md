## ADDED Requirements

### Requirement: Atomic batch link creation

The system SHALL provide a `zk_create_links_batch` MCP tool that creates multiple
semantic links in a single atomic operation.

Each link definition MUST include `source_id` and `target_id`. Fields `link_type`
(default `reference`) and `description` are optional.

The tool SHALL validate all link definitions — including that all source and target
notes exist and all `link_type` values are valid — before writing any links. If any
definition is invalid, the tool MUST return an error and write nothing.

#### Scenario: Successful batch link creation

- **WHEN** `zk_create_links_batch` is called with a list of valid link definitions
- **THEN** all links are created atomically
- **AND** the response includes `created` (count), `failed: 0`, and `errors: []`

#### Scenario: Invalid link_type aborts batch

- **WHEN** `zk_create_links_batch` is called and one link definition has an unrecognised `link_type`
- **THEN** no links are written
- **AND** the response includes an error naming the invalid type and listing valid options

#### Scenario: Missing target note aborts batch

- **WHEN** `zk_create_links_batch` is called and one `target_id` does not exist as a note
- **THEN** no links are written
- **AND** the response includes an error identifying the missing note ID

### Requirement: Batch link performance advantage

The system SHALL create 20 links via `zk_create_links_batch` faster than 20
sequential `zk_create_link` calls.

#### Scenario: Batch is faster than sequential

- **WHEN** 20 links are created using `zk_create_links_batch`
- **THEN** the elapsed time is less than 20 individual `zk_create_link` calls
