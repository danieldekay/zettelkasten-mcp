# Zettelkasten MCP Server - Development Instructions

This document provides comprehensive instructions for working with the Zettelkasten MCP Server codebase. Follow these guidelines when making changes, fixing bugs, or adding new features.

## Project Overview

The Zettelkasten MCP Server is a Model Context Protocol (MCP) server implementing the Zettelkasten knowledge management methodology. It enables creation, linking, and exploration of atomic notes through Claude and other MCP-compatible clients.

### Core Principles

1. **Atomicity**: Each note contains exactly one idea
2. **Connectivity**: Notes are linked to create a knowledge network
3. **Emergence**: Patterns emerge from the growing network
4. **Dual Storage**: Markdown files as source of truth, SQLite for indexing

## Architecture

```
zettelkasten-mcp/
├── src/zettelkasten_mcp/
│   ├── models/           # Data models (Pydantic schemas)
│   │   ├── schema.py     # Note, Link, Tag models
│   │   └── db_models.py  # SQLAlchemy database models
│   ├── storage/          # Storage layer
│   │   ├── base.py       # Abstract repository interface
│   │   └── note_repository.py  # Note persistence (Markdown + SQLite)
│   ├── services/         # Business logic
│   │   ├── zettel_service.py   # Core Zettelkasten operations
│   │   └── search_service.py   # Search and discovery
│   ├── server/           # MCP server
│   │   └── mcp_server.py # FastMCP server implementation
│   ├── config.py         # Configuration management
│   ├── utils.py          # Utility functions
│   └── main.py           # Entry point
├── tests/                # Comprehensive test suite
├── docs/                 # Documentation and prompts
└── data/                 # Runtime data (notes, database)
```

## Code Standards

### Python Style

- **Python Version**: >= 3.10
- **Formatting**: Black (automatic formatting applied)
- **Type Hints**: Use type hints for all function signatures
- **Docstrings**: Google-style docstrings for all public methods
- **Imports**: Group in order: stdlib, third-party, local

Example:
```python
from typing import List, Optional

from sqlalchemy import select
from pydantic import BaseModel

from zettelkasten_mcp.models.schema import Note, Tag


def create_note(title: str, content: str, tags: Optional[List[Tag]] = None) -> Note:
    """Create a new note with the given title and content.
    
    Args:
        title: The note title
        content: The note content in Markdown
        tags: Optional list of tags to attach
        
    Returns:
        The created Note instance with generated ID
        
    Raises:
        ValueError: If title or content is empty
    """
    pass
```

### Naming Conventions

- **Functions/Methods**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_leading_underscore`
- **MCP Tools**: Prefix with `zk_` (e.g., `zk_create_note`)

### Error Handling

Always handle errors gracefully with informative messages:

```python
try:
    note = repository.get(note_id)
except ValueError as e:
    logger.error(f"Failed to retrieve note {note_id}: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error retrieving note {note_id}: {e}")
    raise RuntimeError(f"Failed to retrieve note: {e}")
```

## Data Models

### Note Schema

Notes are the core entity with these properties:

- `id`: Timestamp-based unique identifier (YYYYMMDDTHHMMSSssssssccc)
- `title`: Human-readable title
- `content`: Markdown content
- `note_type`: One of FLEETING, LITERATURE, PERMANENT, STRUCTURE, HUB
- `tags`: List of Tag objects
- `links`: List of Link objects
- `created_at`: ISO 8601 timestamp
- `updated_at`: ISO 8601 timestamp
- `metadata`: Additional key-value pairs

### Link Types

The system supports semantic linking with these types:

| Type | Inverse | Symmetric | Description |
|------|---------|-----------|-------------|
| `reference` | `reference` | ✓ | Simple reference |
| `extends` | `extended_by` | ✗ | Builds upon concepts |
| `refines` | `refined_by` | ✗ | Clarifies/improves |
| `contradicts` | `contradicted_by` | ✗ | Opposes views |
| `questions` | `questioned_by` | ✗ | Poses questions |
| `supports` | `supported_by` | ✗ | Provides evidence |
| `related` | `related` | ✓ | Generic relationship |

### Tag Model

Tags are simple name-based categorizations with immutability enforced.

## Storage Layer

### Dual Storage Architecture

1. **Markdown Files** (Source of Truth)
   - Human-readable YAML frontmatter + Markdown content
   - Directly editable in any text editor
   - Version control friendly
   - Location: `ZETTELKASTEN_NOTES_DIR`

2. **SQLite Database** (Index)
   - Efficient querying and graph traversal
   - Automatically rebuilt from Markdown files
   - Can be deleted and regenerated
   - Location: `ZETTELKASTEN_DATABASE_PATH`

### Note Repository Pattern

The `NoteRepository` class implements CRUD operations:

```python
class NoteRepository(Repository[Note]):
    def create(self, note: Note) -> Note: ...
    def get(self, id: str) -> Optional[Note]: ...
    def update(self, note: Note) -> Note: ...
    def delete(self, id: str) -> None: ...
    def search(self, **kwargs) -> List[Note]: ...
```

**Critical Rules:**

1. **Always check for duplicate tags** before appending to prevent IntegrityError:
   ```python
   if db_tag not in db_note.tags:
       db_note.tags.append(db_tag)
   ```

2. **Clear associations before rebuilding** to avoid constraint violations:
   ```python
   db_note.tags = []  # Clear before re-adding
   ```

3. **Use transactions** for database operations
4. **Parse frontmatter** correctly when reading Markdown files
5. **Preserve user formatting** in content when possible

### Markdown Format

Notes are stored with YAML frontmatter:

```markdown
---
id: 20251109T120530123456789
title: Example Note
type: permanent
tags: [example, demo, test]
created: 2025-11-09T12:05:30.123456
updated: 2025-11-09T12:05:30.123456
---

# Example Note

Content goes here.

## Links
- extends [[20251109T120000000000000]] Description
- reference [[20251109T115500000000000]]
```

## Testing Requirements

### Test Coverage

All new code must include comprehensive tests:

- **Unit Tests**: Test individual functions/methods
- **Integration Tests**: Test component interactions
- **MCP Server Tests**: Test tool endpoints
- **Edge Cases**: Test error conditions and boundary cases

### Running Tests

```bash
# All tests
uv run pytest -v tests/

# Specific test file
uv run pytest -v tests/test_note_repository.py

# With coverage
uv run pytest --cov=zettelkasten_mcp --cov-report=term-missing tests/

# Specific test
uv run pytest -v tests/test_note_repository.py::test_create_note_with_duplicate_tags
```

### Test Structure

```python
def test_feature_name(fixture_name):
    """Test description explaining what is being tested.
    
    This docstring should explain:
    - What scenario is being tested
    - Why it's important
    - What behavior is expected
    """
    # Arrange
    setup_data = create_test_data()
    
    # Act
    result = function_under_test(setup_data)
    
    # Assert
    assert result.expected_property == expected_value
    assert len(result.collection) == expected_count
```

### Test Fixtures

Use fixtures from `conftest.py`:

- `temp_dirs`: Temporary directories for tests
- `test_config`: Test configuration
- `note_repository`: Initialized repository with test data

## MCP Server Implementation

### Tool Registration

All MCP tools follow this pattern:

```python
@self.mcp.tool()
def zk_tool_name(
    param1: str,
    param2: Optional[str] = None
) -> str:
    """Brief description of what the tool does.
    
    Args:
        param1: Description of first parameter
        param2: Description of optional parameter
        
    Returns:
        Description of return value
    """
    try:
        # Implementation
        result = self.service.operation(param1, param2)
        return format_success_response(result)
    except ValueError as e:
        return self.format_error_response(e)
    except Exception as e:
        logger.error(f"Unexpected error in zk_tool_name: {e}")
        return self.format_error_response(e)
```

### Tool Naming Convention

- Prefix: `zk_` for all Zettelkasten tools
- Format: `zk_verb_noun` (e.g., `zk_create_note`, `zk_get_linked_notes`)
- Be descriptive and consistent

## Common Patterns

### Creating Notes

```python
# Generate ID
note_id = generate_id()

# Create note object
note = Note(
    id=note_id,
    title=title,
    content=content,
    note_type=NoteType.PERMANENT,
    tags=[Tag(name=tag) for tag in tag_list],
    links=[]
)

# Persist
saved_note = repository.create(note)
```

### Creating Links

```python
# Create link object
link = Link(
    source_id=source_note.id,
    target_id=target_note.id,
    link_type=LinkType.EXTENDS,
    description="Optional description"
)

# Add to source note
source_note.add_link(
    target_id=target_note.id,
    link_type=LinkType.EXTENDS,
    description="Optional description"
)

# Update note
repository.update(source_note)
```

### Searching Notes

```python
# By content
notes = repository.search(content="search term")

# By tags
notes = repository.search(tags=["tag1", "tag2"])

# By note type
notes = repository.search(note_type=NoteType.PERMANENT)

# By links
notes = repository.search(linked_to="20251109T120000000000000")

# Combined
notes = repository.search(
    content="term",
    tags=["tag1"],
    note_type=NoteType.PERMANENT
)
```

## Bug Fix Workflow

When fixing bugs, follow this workflow:

1. **Reproduce**: Create a failing test that demonstrates the bug
2. **Diagnose**: Identify root cause through debugging/logging
3. **Fix**: Implement minimal fix addressing root cause
4. **Test**: Ensure test passes and no regressions
5. **Document**: Update relevant documentation
6. **Commit**: Use descriptive commit messages

### Commit Message Format

```
Fix: Brief description of what was fixed

- Detailed point 1 about the fix
- Detailed point 2 about the fix
- Reference to issue if applicable

Fixes #issue-number
```

Example:
```
Fix: Prevent duplicate tag associations causing IntegrityError

- Added duplicate tag check in update() method
- Prevents SQLite constraint violations on note_tags table
- Added 4 comprehensive tests for duplicate scenarios
- All 65 tests passing

Fixes #1
```

## Database Schema

### Tables

**notes**
- `id` (TEXT, PRIMARY KEY)
- `title` (TEXT)
- `content` (TEXT)
- `note_type` (TEXT)
- `created_at` (DATETIME)
- `updated_at` (DATETIME)

**tags**
- `id` (INTEGER, PRIMARY KEY)
- `name` (TEXT, UNIQUE)

**note_tags** (Association table)
- `note_id` (TEXT, FOREIGN KEY)
- `tag_id` (INTEGER, FOREIGN KEY)
- UNIQUE constraint on (note_id, tag_id) ← **Critical for preventing duplicates**

**links**
- `id` (INTEGER, PRIMARY KEY)
- `source_id` (TEXT, FOREIGN KEY)
- `target_id` (TEXT, FOREIGN KEY)
- `link_type` (TEXT)
- `description` (TEXT)
- `created_at` (DATETIME)

## Environment Configuration

### Required Variables

```bash
ZETTELKASTEN_NOTES_DIR=/path/to/notes
ZETTELKASTEN_DATABASE_PATH=/path/to/db/zettelkasten.db
ZETTELKASTEN_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Configuration Precedence

1. Environment variables
2. `.env` file
3. Command-line arguments
4. Default values in `config.py`

## Logging

Use structured logging throughout:

```python
import logging

logger = logging.getLogger(__name__)

# Info: Normal operations
logger.info(f"Created note {note.id} with title '{note.title}'")

# Warning: Recoverable issues
logger.warning(f"Note {note_id} not found, returning None")

# Error: Problems that need attention
logger.error(f"Failed to index note {note_id}: {e}")

# Debug: Detailed troubleshooting info
logger.debug(f"Processing tags: {[tag.name for tag in tags]}")
```

## Performance Considerations

### Batch Operations

When processing multiple notes:

```python
# Good: Batch processing
batch_size = 100
for i in range(0, len(notes), batch_size):
    batch = notes[i:i + batch_size]
    process_batch(batch)

# Bad: One at a time
for note in notes:
    process_note(note)  # Database transaction per note
```

### Query Optimization

Use eager loading for relationships:

```python
# Good: Eager load
query = select(DBNote).options(
    joinedload(DBNote.tags),
    joinedload(DBNote.outgoing_links)
)

# Bad: N+1 queries
notes = session.execute(select(DBNote)).scalars().all()
for note in notes:
    _ = note.tags  # Separate query per note!
```

## Documentation Standards

### Code Comments

- Explain **why**, not **what** (code shows what)
- Document non-obvious decisions
- Reference issues/PRs for context
- Keep comments up-to-date with code changes

```python
# Good
# Prevent duplicate tag associations that would violate the 
# UNIQUE(note_id, tag_id) constraint in note_tags table
if db_tag not in db_note.tags:
    db_note.tags.append(db_tag)

# Bad
# Check if tag is in list
if db_tag not in db_note.tags:
    db_note.tags.append(db_tag)
```

### API Documentation

Keep `README.md` up-to-date with:
- Installation instructions
- Configuration options
- MCP tool descriptions
- Usage examples
- Breaking changes

## Security Considerations

1. **Input Validation**: Validate all user inputs
2. **SQL Injection**: Use parameterized queries (SQLAlchemy handles this)
3. **Path Traversal**: Validate file paths stay within notes directory
4. **Resource Limits**: Implement pagination for large result sets

## Common Pitfalls

### ❌ Don't Do This

```python
# Forgetting to check for duplicate tags
db_note.tags.append(db_tag)  # IntegrityError!

# String formatting in SQL
session.execute(f"DELETE FROM notes WHERE id = {note_id}")  # SQL injection!

# Ignoring errors
try:
    risky_operation()
except:
    pass  # Silent failure!

# Modifying immutable objects
link.description = "new value"  # Pydantic will raise error
```

### ✅ Do This Instead

```python
# Check before appending
if db_tag not in db_note.tags:
    db_note.tags.append(db_tag)

# Use parameterized queries
session.execute(text("DELETE FROM notes WHERE id = :id"), {"id": note_id})

# Handle errors properly
try:
    risky_operation()
except ValueError as e:
    logger.error(f"Operation failed: {e}")
    raise

# Create new immutable object
new_link = link.model_copy(update={"description": "new value"})
```

## Contributing Workflow

1. **Branch**: Create feature branch from `main`
2. **Develop**: Write code following these instructions
3. **Test**: Ensure all tests pass
4. **Format**: Run Black formatter
5. **Commit**: Use descriptive commit messages
6. **Push**: Push to your fork
7. **PR**: Create pull request with detailed description
8. **Review**: Address feedback
9. **Merge**: Squash and merge to main

## Resources

- **MCP Documentation**: https://modelcontextprotocol.io/
- **Zettelkasten Method**: See `docs/project-knowledge/user/zettelkasten-methodology-technical.md`
- **Link Types**: See `docs/project-knowledge/user/link-types-in-zettelkasten-mcp-server.md`
- **Prompts**: See `docs/prompts/` for system and chat prompts

## Questions?

For questions or clarifications:
1. Check existing documentation in `docs/`
2. Review similar code in the codebase
3. Check test files for usage examples
4. Open a discussion on GitHub

---

Last Updated: November 9, 2025
Version: 1.2.1
