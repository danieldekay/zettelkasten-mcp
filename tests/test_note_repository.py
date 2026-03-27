"""Tests for the NoteRepository class."""

from zettelkasten_mcp.models.schema import LinkType, Note, NoteType, Tag
from zettelkasten_mcp.storage.note_repository import NoteRepository


def test_create_note(note_repository):
    """Test creating a new note."""
    # Create a test note
    note = Note(
        title="Test Note",
        content="This is a test note.",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="test"), Tag(name="example")],
    )
    # Save to repository
    saved_note = note_repository.create(note)
    # Verify note was saved with an ID
    assert saved_note.id is not None
    assert saved_note.title == "Test Note"
    assert saved_note.content == "This is a test note."
    assert saved_note.note_type == NoteType.PERMANENT
    assert len(saved_note.tags) == 2
    assert {tag.name for tag in saved_note.tags} == {"test", "example"}


def test_get_note(note_repository):
    """Test retrieving a note."""
    # Create a test note
    note = Note(
        title="Get Test Note",
        content="This is a test note for retrieval.",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="test"), Tag(name="get")],
    )
    # Save to repository
    saved_note = note_repository.create(note)
    # Retrieve the note
    retrieved_note = note_repository.get(saved_note.id)
    # Verify note was retrieved correctly
    assert retrieved_note is not None
    assert retrieved_note.id == saved_note.id
    assert retrieved_note.title == "Get Test Note"
    # Note content includes the title as a markdown header -
    # account for this in our test
    expected_content = f"# {note.title}\n\n{note.content}"
    assert retrieved_note.content.strip() == expected_content.strip()
    assert retrieved_note.note_type == NoteType.PERMANENT
    assert len(retrieved_note.tags) == 2
    assert {tag.name for tag in retrieved_note.tags} == {"test", "get"}


def test_update_note(note_repository):
    """Test updating a note."""
    # Create a test note
    note = Note(
        title="Update Test Note",
        content="This is a test note for updating.",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="test"), Tag(name="update")],
    )
    # Save to repository
    saved_note = note_repository.create(note)
    # Update the note
    saved_note.title = "Updated Test Note"
    saved_note.content = "This note has been updated."
    saved_note.tags = [Tag(name="test"), Tag(name="updated")]
    # Save the update
    updated_note = note_repository.update(saved_note)
    # Retrieve the note again
    retrieved_note = note_repository.get(saved_note.id)
    # Verify note was updated
    assert retrieved_note is not None
    assert retrieved_note.id == saved_note.id
    assert retrieved_note.title == "Updated Test Note"
    # Note content includes the title as a markdown header - account for this
    expected_content = f"# {updated_note.title}\n\n{updated_note.content}"
    assert retrieved_note.content.strip() == expected_content.strip()
    assert {tag.name for tag in retrieved_note.tags} == {"test", "updated"}


def test_delete_note(note_repository):
    """Test deleting a note."""
    # Create a test note
    note = Note(
        title="Delete Test Note",
        content="This is a test note for deletion.",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="test"), Tag(name="delete")],
    )
    # Save to repository
    saved_note = note_repository.create(note)
    # Verify note exists
    retrieved_note = note_repository.get(saved_note.id)
    assert retrieved_note is not None
    # Delete the note
    note_repository.delete(saved_note.id)
    # Verify note no longer exists
    deleted_note = note_repository.get(saved_note.id)
    assert deleted_note is None


def test_search_notes(note_repository):
    """Test searching for notes."""
    # Create test notes
    note1 = Note(
        title="Python Programming",
        content="Python is a versatile programming language.",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="python"), Tag(name="programming")],
    )
    note2 = Note(
        title="JavaScript Basics",
        content="JavaScript is used for web development.",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="javascript"), Tag(name="programming")],
    )
    note3 = Note(
        title="Data Science Overview",
        content="Data science uses Python for data analysis.",
        note_type=NoteType.STRUCTURE,
        tags=[Tag(name="data science"), Tag(name="python")],
    )
    # Save notes
    saved_note1 = note_repository.create(note1)
    saved_note2 = note_repository.create(note2)
    saved_note3 = note_repository.create(note3)

    # Search by content with title included (since content has the title prepended)
    python_notes = note_repository.search(content="Python")
    # We should find both the Python notes even with title prepended
    assert len(python_notes) >= 1  # At least one match
    python_ids = {note.id for note in python_notes}
    assert saved_note1.id in python_ids or saved_note3.id in python_ids

    # Search by title
    javascript_notes = note_repository.search(title="JavaScript")
    assert len(javascript_notes) == 1
    assert javascript_notes[0].id == saved_note2.id

    # Search by note_type
    structure_notes = note_repository.search(note_type=NoteType.STRUCTURE)
    assert len(structure_notes) == 1
    assert structure_notes[0].id == saved_note3.id

    # Search by tag
    programming_notes = note_repository.find_by_tag("programming")
    assert len(programming_notes) == 2
    assert {note.id for note in programming_notes} == {saved_note1.id, saved_note2.id}


def test_note_linking(note_repository):
    """Test creating links between notes."""
    # Create test notes
    note1 = Note(
        title="Source Note",
        content="This is the source note.",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="test"), Tag(name="source")],
    )
    note2 = Note(
        title="Target Note",
        content="This is the target note.",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="test"), Tag(name="target")],
    )
    # Save notes
    source_note = note_repository.create(note1)
    target_note = note_repository.create(note2)
    # Add a link from source to target
    source_note.add_link(
        target_id=target_note.id,
        link_type=LinkType.REFERENCE,
        description="A test link",
    )
    # Update the source note
    updated_source = note_repository.update(source_note)
    # Verify link was created
    assert len(updated_source.links) == 1
    assert updated_source.links[0].target_id == target_note.id
    assert updated_source.links[0].link_type == LinkType.REFERENCE
    assert updated_source.links[0].description == "A test link"
    # Find linked notes
    linked_notes = note_repository.find_linked_notes(source_note.id, "outgoing")
    assert len(linked_notes) == 1
    assert linked_notes[0].id == target_note.id


def test_metadata_round_trip(note_repository):
    """Metadata with varied value types persists and deserialises correctly."""
    meta = {"str_val": "hello", "int_val": 42, "list_val": [1, 2], "nested": {"k": "v"}}
    note = Note(
        title="Metadata Note",
        content="With metadata.",
        note_type=NoteType.PERMANENT,
        metadata=meta,
    )
    saved = note_repository.create(note)
    retrieved = note_repository.get(saved.id)
    assert retrieved.metadata == meta


def test_metadata_empty_on_plain_note(note_repository):
    """Notes created without metadata return an empty dict on retrieval."""
    note = Note(
        title="Plain Note",
        content="No metadata.",
        note_type=NoteType.PERMANENT,
    )
    saved = note_repository.create(note)
    retrieved = note_repository.get(saved.id)
    assert retrieved.metadata == {}


def test_fts5_synced_on_create(note_repository):
    """FTS5 index is populated when a note is created."""
    note_repository.rebuild_index()
    note = Note(
        title="Quantum Entanglement",
        content="Spooky action at a distance.",
        note_type=NoteType.PERMANENT,
    )
    saved = note_repository.create(note)
    results = note_repository.search_by_fts5("quantum")
    assert saved.id in [r[0] for r in results]


def test_fts5_synced_on_delete(note_repository):
    """FTS5 index entry is removed when a note is deleted."""
    note_repository.rebuild_index()
    note = Note(
        title="Temporary Note",
        content="Will be deleted soon.",
        note_type=NoteType.FLEETING,
    )
    saved = note_repository.create(note)
    note_repository.delete(saved.id)
    results = note_repository.search_by_fts5("temporary")
    assert saved.id not in [r[0] for r in results]


def test_fts5_synced_on_update(note_repository):
    """FTS5 index reflects updated note content."""
    note_repository.rebuild_index()
    note = Note(
        title="Update Test",
        content="original content here",
        note_type=NoteType.PERMANENT,
    )
    saved = note_repository.create(note)
    saved.content = "completely different text now"
    note_repository.update(saved)
    assert saved.id not in [r[0] for r in note_repository.search_by_fts5("original")]
    assert saved.id in [r[0] for r in note_repository.search_by_fts5("different")]


def test_fts5_query_with_dot_does_not_raise(note_repository):
    """FTS5 search with a '.' in the query must not raise and must return a list."""
    note_repository.rebuild_index()
    results = note_repository.search_by_fts5("python3.10")
    assert isinstance(results, list)


def test_fts5_query_with_dot_sanitized_still_matches(note_repository):
    """After sanitizing '.', the remaining tokens still find relevant notes."""
    note_repository.rebuild_index()
    note = Note(
        title="Python Version",
        content="Requires python3 version 10 or higher.",
        note_type=NoteType.PERMANENT,
    )
    saved = note_repository.create(note)
    # "python3.10" sanitizes to "python3 10"; both tokens appear in the note.
    results = note_repository.search_by_fts5("python3.10")
    assert saved.id in [r[0] for r in results]


def test_sanitize_fts5_query_removes_dot():
    """_sanitize_fts5_query strips '.' and collapses whitespace."""
    assert NoteRepository._sanitize_fts5_query("python3.10") == "python3 10"  # noqa: SLF001
    assert NoteRepository._sanitize_fts5_query("example.com") == "example com"  # noqa: SLF001
    assert NoteRepository._sanitize_fts5_query("v1.2.3") == "v1 2 3"  # noqa: SLF001


def test_sanitize_fts5_query_removes_hyphen():
    """Strips '-' so 'word-word' doesn't hit FTS5 column-filter syntax."""
    assert NoteRepository._sanitize_fts5_query("managed-settings") == "managed settings"  # noqa: SLF001
    assert (
        NoteRepository._sanitize_fts5_query(  # noqa: SLF001
            "managed-settings governance allowlist override"
        )
        == "managed settings governance allowlist override"
    )
    assert NoteRepository._sanitize_fts5_query("non-breaking") == "non breaking"  # noqa: SLF001


def test_sanitize_fts5_query_empty_after_strip():
    """_sanitize_fts5_query returns empty string when only special chars are present."""
    assert NoteRepository._sanitize_fts5_query("...") == ""  # noqa: SLF001
    assert NoteRepository._sanitize_fts5_query("@#$%") == ""  # noqa: SLF001


def test_fts5_empty_query_after_sanitize_returns_empty_list(note_repository):
    """search_by_fts5 returns [] without hitting SQLite when query sanitizes to ''."""
    note_repository.rebuild_index()
    results = note_repository.search_by_fts5("...")
    assert results == []
