# Zettelkasten MCP Server

A Model Context Protocol (MCP) server that implements the Zettelkasten knowledge management methodology, allowing you to create, link, explore and synthesize atomic notes through Claude and other MCP-compatible clients.

## What is Zettelkasten?

The Zettelkasten method is a knowledge management system developed by German sociologist Niklas Luhmann, who used it to produce over 70 books and hundreds of articles. It consists of three core principles:

1. **Atomicity**: Each note contains exactly one idea, making it a discrete unit of knowledge
2. **Connectivity**: Notes are linked together to create a network of knowledge, with meaningful relationships between ideas
3. **Emergence**: As the network grows, new patterns and insights emerge that weren't obvious when the individual notes were created

What makes the Zettelkasten approach powerful is how it enables exploration in multiple ways:

- **Vertical exploration**: dive deeper into specific topics by following connections within a subject area.
- **Horizontal exploration**: discover unexpected relationships between different fields by traversing links that cross domains.

This structure invites serendipitous discoveries as you follow trails of thought from note to note, all while keeping each piece of information easily accessible through its unique identifier. Luhmann called his system his "second brain" or "communication partner" - this digital implementation aims to provide similar benefits through modern technology.

## Features

- Create atomic notes with unique timestamp-based IDs
- Link notes bidirectionally to build a knowledge graph
- Tag notes for categorical organization
- Search notes by content, tags, or links
- Use markdown format for human readability and editing
- Integrate with Claude through MCP for AI-assisted knowledge management
- Dual storage architecture (see below)
- Synchronous operation model for simplified architecture

## Examples

- Knowledge creation: [A small Zettelkasten knowledge network about the Zettelkasten method itself](https://github.com/entanglr/zettelkasten-mcp/discussions/5)

## Note Types

The Zettelkasten MCP server supports different types of notes:

|Type|Handle|Description|
|---|---|---|
|**Fleeting notes**|`fleeting`|Quick, temporary notes for capturing ideas|
|**Literature notes**|`literature`|Notes from reading material|
|**Permanent notes**|`permanent`|Well-formulated, evergreen notes|
|**Structure notes**|`structure`|Index or outline notes that organize other notes|
|**Hub notes**|`hub`|Entry points to the Zettelkasten on key topics|

## Link Types

The Zettelkasten MCP server uses a comprehensive semantic linking system that creates meaningful connections between notes. Each link type represents a specific relationship, allowing for a rich, multi-dimensional knowledge graph.

| Primary Link Type | Inverse Link Type | Relationship Description |
|-------------------|-------------------|--------------------------|
| `reference` | `reference` | Simple reference to related information (symmetric relationship) |
| `extends` | `extended_by` | One note builds upon or develops concepts from another |
| `refines` | `refined_by` | One note clarifies or improves upon another |
| `contradicts` | `contradicted_by` | One note presents opposing views to another |
| `questions` | `questioned_by` | One note poses questions about another |
| `supports` | `supported_by` | One note provides evidence for another |
| `related` | `related` | Generic relationship (symmetric relationship) |

## Prompting

To ensure maximum effectiveness, we recommend using a system prompt ("project instructions"), project knowledge, and an appropriate chat prompt when asking the LLM to process information, or explore or synthesize your Zettelkasten notes. The `docs` directory in this repository contains the necessary files to get you started:

### System prompts

Pick one:

- [system-prompt.md](https://github.com/entanglr/zettelkasten-mcp/blob/main/docs/prompts/system/system-prompt.md)
- [system-prompt-with-protocol.md](https://github.com/entanglr/zettelkasten-mcp/blob/main/docs/prompts/system/system-prompt-with-protocol.md)

### Project knowledge

For end users:

- [zettelkasten-methodology-technical.md](https://github.com/entanglr/zettelkasten-mcp/blob/main/docs/project-knowledge/user/zettelkasten-methodology-technical.md)
- [link-types-in-zettelkasten-mcp-server.md](https://github.com/entanglr/zettelkasten-mcp/blob/main/docs/project-knowledge/user/link-types-in-zettelkasten-mcp-server.md)
- (more info relevant to your project)

### Chat Prompts

- [chat-prompt-knowledge-creation.md](https://github.com/entanglr/zettelkasten-mcp/blob/main/docs/prompts/chat/chat-prompt-knowledge-creation.md)
- [chat-prompt-knowledge-creation-batch.md](https://github.com/entanglr/zettelkasten-mcp/blob/main/docs/prompts/chat/chat-prompt-knowledge-creation-batch.md)
- [chat-prompt-knowledge-exploration.md](https://github.com/entanglr/zettelkasten-mcp/blob/main/docs/prompts/chat/chat-prompt-knowledge-exploration.md)
- [chat-prompt-knowledge-synthesis.md](https://github.com/entanglr/zettelkasten-mcp/blob/main/docs/prompts/chat/chat-prompt-knowledge-synthesis.md)

### Project knowledge (dev)

For developers and contributors:

- [Example - A simple MCP server.md](https://github.com/entanglr/zettelkasten-mcp/blob/main/docs/project-knowledge/dev/Example%20-%20A%20simple%20MCP%20server%20that%20exposes%20a%20website%20fetching%20tool.md)
- [MCP Python SDK-README.md](https://github.com/entanglr/zettelkasten-mcp/blob/main/docs/project-knowledge/dev/MCP%20Python%20SDK-README.md)
- [llms-full.txt](https://github.com/entanglr/zettelkasten-mcp/blob/main/docs/project-knowledge/dev/llms-full.txt)

NB: Optionally include the source code with a tool like [repomix](https://github.com/yamadashy/repomix).

## Storage Architecture

This system uses a dual storage approach:

1. **Markdown Files**: All notes are stored as human-readable Markdown files with YAML frontmatter for metadata. These files are the **source of truth** and can be:
   - Edited directly in any text editor
   - Placed under version control (Git, etc.)
   - Backed up using standard file backup procedures
   - Shared or transferred like any other text files

2. **SQLite Database**: Functions as an indexing layer that:
   - Facilitates efficient querying and search operations
   - Enables Claude to quickly traverse the knowledge graph
   - Maintains relationship information for faster link traversal
   - Is automatically rebuilt from Markdown files when needed

If you edit Markdown files directly outside the system, you'll need to run the `zk_rebuild_index` tool to update the database. The database itself can be deleted at any time - it will be regenerated from your Markdown files.

## Installation

```bash
# Clone the repository
git clone https://github.com/entanglr/zettelkasten-mcp.git
cd zettelkasten-mcp

# Create a virtual environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv add "mcp[cli]"

# Install dev dependencies
uv sync --all-extras
```

## Configuration

Create a `.env` file in the project root by copying the example:

```bash
cp .env.example .env
```

Then edit the file to configure your connection parameters.

## Usage

### Starting the Server

```bash
python -m zettelkasten_mcp.main
```

Or with explicit configuration:

```bash
python -m zettelkasten_mcp.main --notes-dir ./data/notes --database-path ./data/db/zettelkasten.db
```

### Connecting to Claude Desktop

Add the following configuration to your Claude Desktop:

```json
{
  "mcpServers": {
    "zettelkasten": {
      "command": "/absolute/path/to/zettelkasten-mcp/.venv/bin/python",
      "args": [
        "-m",
        "zettelkasten_mcp.main"
      ],
      "env": {
        "ZETTELKASTEN_NOTES_DIR": "/absolute/path/to/zettelkasten-mcp/data/notes",
        "ZETTELKASTEN_DATABASE_PATH": "/absolute/path/to/zettelkasten-mcp/data/db/zettelkasten.db",
        "ZETTELKASTEN_LOG_LEVEL": "INFO",
        "ZETTELKASTEN_AUTO_REBUILD_THRESHOLD": "5",
        "ZETTELKASTEN_CUSTOM_LINK_TYPES_PATH": "/absolute/path/to/custom_link_types.yaml",
        "ZETTELKASTEN_WATCH_DIRS": "/path/to/watch-folder1,/path/to/watch-folder2"
      }
    }
  }
}
```

## Watch Folders

Watch folders let you index external Markdown directories as **read-only reference notes** alongside your primary notes. This is useful for referencing existing note archives, documentation, or any collection of Markdown files without copying them into your notes directory.

### Configuration

Set `ZETTELKASTEN_WATCH_DIRS` to a comma-separated list of absolute directory paths:

```bash
ZETTELKASTEN_WATCH_DIRS=/path/to/folder1,/path/to/folder2
```

At startup the server indexes all `.md` files found recursively in each watch directory. Files with compatible YAML frontmatter (title, tags, id, etc.) are parsed; files without frontmatter get a deterministic `ext-<hash>` ID and use the filename stem as the title.

### Behaviour

- Watch-folder notes are **read-only**: `zk_update_note` and `zk_delete_note` will refuse to modify them.
- You can create **links from your primary notes to watch-folder notes** (unidirectional). Bidirectional links to read-only notes are silently downgraded to unidirectional.
- Watch-folder notes appear in `zk_search_notes`, `zk_get_note`, `zk_get_linked_notes`, and `zk_list_notes` by default. Use `include_external: false` on `zk_list_notes` to exclude them.
- Run `zk_sync_watch_folders` at any time to re-index the watch directories without restarting the server.

## Available MCP Tools

All tools have been prefixed with `zk_` for better organization:

| Tool | Description | Response Keys |
|---|---|---|
| `zk_create_note` | Create a new note with a title, content, and optional tags | `note_id`, `file_path`, `summary` |
| `zk_create_notes_batch` | Create multiple notes in one atomic transaction | `created`, `note_ids`, `failed`, `errors`, `summary` |
| `zk_get_note` | Retrieve a specific note by ID or title | `note_id`, `title`, `note_type`, `tags`, `links`, `created_at`, `updated_at`, `content`, `metadata`, `summary` |
| `zk_update_note` | Update an existing note's content or metadata | `note_id`, `updated_fields`, `summary` |
| `zk_delete_note` | Delete a note | `note_id`, `deleted`, `summary` |
| `zk_create_link` | Create links between notes | `source_id`, `target_id`, `link_type`, `summary` |
| `zk_create_links_batch` | Create multiple semantic links atomically | `created`, `failed`, `errors`, `summary` |
| `zk_verify_note` | Verify filesystem/DB consistency for a note | `note_id`, `file_exists`, `db_indexed`, `link_count`, `tag_count`, `summary` |
| `zk_get_index_status` | Return filesystem vs. DB index health summary | `total_notes_filesystem`, `total_notes_indexed`, `orphaned_files`, `orphaned_db_records`, `database_size_mb`, `summary` |
| `zk_remove_link` | Remove links between notes | `source_id`, `target_id`, `removed`, `summary` |
| `zk_search_notes` | Search for notes by content, tags, or links | `notes[]` (each with `score`), `total`, `query`, `summary` |
| `zk_get_linked_notes` | Find notes linked to a specific note | `note_id`, `direction`, `notes[]`, `total`, `summary` |
| `zk_get_all_tags` | List all tags in the system | `tags[]` (each with `name`, `count`), `total`, `summary` |
| `zk_find_similar_notes` | Find notes similar to a given note | `notes[]`, `total`, `summary` |
| `zk_find_central_notes` | Find notes with the most connections | `notes[]` (each with `connection_count`), `total`, `summary` |
| `zk_find_orphaned_notes` | Find notes with no connections | `notes[]`, `total`, `summary` |
| `zk_list_notes_by_date` | List notes by creation/update date | `notes[]`, `total`, `summary` |
| `zk_list_notes` | List all notes with optional type/tag/external filters | `notes[]`, `total`, `include_external`, `summary` |
| `zk_rebuild_index` | Rebuild the database index from Markdown files | `notes_indexed`, `errors[]`, `summary` |
| `zk_register_link_type` | Register a custom link type with optional inverse | `registered`, `inverse`, `symmetric`, `summary` |
| `zk_suggest_link_type` | Suggest a link type for two notes using heuristics | `suggestions[]` (each with `link_type`, `confidence`), `low_confidence`, `summary` |
| `zk_suggest_tags` | Suggest tags for note content using TF-IDF similarity | `suggestions[]` (each with `tag`, `score`), `total`, `summary` |
| `zk_find_notes_in_timerange` | Find notes by `created_at` or `updated_at` date range (ISO 8601) | `count`, `notes[]`, `date_field`, `summary` |
| `zk_analyze_tag_clusters` | Identify tag clusters by co-occurrence frequency | `clusters[]` (each with `tags`, `count`, `representative_notes`), `total_tag_pairs_analysed`, `summary` |
| `zk_sync_watch_folders` | Re-index all configured watch-folder directories | `scanned`, `added`, `removed`, `errors[]`, `summary` |

All tools return `error: true`, `error_type`, `message`, and `summary` on failure.

## Project Structure

```
zettelkasten-mcp/
├── src/zettelkasten_mcp/
│   ├── config.py                 Configuration (env vars, Pydantic model)
│   ├── main.py                   Entry point, arg parsing, startup drift check
│   ├── models/
│   │   ├── schema.py             Pydantic domain models + LinkTypeRegistry
│   │   └── db_models.py          SQLAlchemy ORM + init_db()
│   ├── storage/
│   │   ├── base.py               Abstract Repository[T] interface
│   │   └── note_repository.py    Dual-storage implementation
│   ├── services/
│   │   ├── zettel_service.py     Note CRUD, links, batch ops, health, analytics
│   │   ├── search_service.py     FTS5 search, tag suggestions, clustering
│   │   └── inference_service.py  Pattern-based link-type inference
│   └── server/
│       └── mcp_server.py         FastMCP tool registrations + error handling
├── data/
│   ├── notes/                    Markdown note files (source of truth)
│   └── db/                       SQLite database (index, rebuildable)
├── docs/
│   ├── ARCHITECTURE.md           Detailed system architecture
│   └── moscow-top10-features.md  MoSCoW feature analysis
├── tests/                        Comprehensive test suite (233+ tests)
├── openspec/                     OpenSpec change proposals and archives
├── .env.example                  Environment variable template
└── README.md
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a full walkthrough of
every layer, data flows, and design decisions.

## Tests

Comprehensive test suite for Zettelkasten MCP covering all layers of the application from models to the MCP server implementation.

### How to Run the Tests

From the project root directory, run:

#### Using pytest directly
```bash
python -m pytest -v tests/
```

#### Using UV
```bash
uv run pytest -v tests/
```

#### With coverage report
```bash
uv run pytest --cov=zettelkasten_mcp --cov-report=term-missing tests/
```

#### Running a specific test file
```bash
uv run pytest -v tests/test_models.py
```

#### Running a specific test class
```bash
uv run pytest -v tests/test_models.py::TestNoteModel
```

#### Running a specific test function
```bash
uv run pytest -v tests/test_models.py::TestNoteModel::test_note_validation
```

### Tests Directory Structure

```
tests/
├── conftest.py                  Shared fixtures (temp dirs, config, repo, service)
├── test_models.py               Note/Link/Tag model validation, ID format
├── test_note_repository.py      CRUD, Markdown round-trips, metadata
├── test_zettel_service.py       Service delegation and note lifecycle
├── test_search_service.py       FTS5, legacy search, orphan/central discovery
├── test_semantic_links.py       All 12 link types, bidirectional semantics
├── test_integration.py          Full system: create → link → search → rebuild
├── test_mcp_server.py           Tool registration, structured responses, errors
├── test_main.py                 CLI arg parsing, server startup, db error exit
├── test_utils.py                ID generation, tag parsing, display formatting
├── test_advanced_features.py    Custom types, inference, TF-IDF, degradation
├── test_batch_operations.py     Batch note/link creation, verify, index health
└── test_analytics_discovery.py  Temporal queries, tag clusters, performance
```

## Important Notice

**⚠️ USE AT YOUR OWN RISK**: This software is experimental and provided as-is without warranty of any kind. While efforts have been made to ensure data integrity, it may contain bugs that could potentially lead to data loss or corruption. Always back up your notes regularly and use caution when testing with important information.

## Credit Where Credit's Due

This MCP server was crafted with the assistance of Claude, who helped organize the atomic thoughts of this project into a coherent knowledge graph. Much like a good Zettelkasten system, Claude connected the dots between ideas that might otherwise have remained isolated. Unlike Luhmann's paper-based system, however, Claude didn't require 90,000 index cards to be effective.

## License

MIT License
