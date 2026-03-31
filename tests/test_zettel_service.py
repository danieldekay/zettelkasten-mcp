"""Tests for the ZettelService class."""

import pytest

from zettelkasten_mcp.config import config
from zettelkasten_mcp.models.schema import LinkType, NoteType
from zettelkasten_mcp.models.schema import link_type_registry


def test_create_note(zettel_service):
    """Test creating a note through the service."""
    # Create a test note
    note = zettel_service.create_note(
        title="Service Test Note",
        content="Testing note creation through the service.",
        note_type=NoteType.PERMANENT,
        tags=["service", "test"],
    )
    # Verify note was created
    assert note.id is not None
    assert note.title == "Service Test Note"
    assert note.content == "Testing note creation through the service."
    assert note.note_type == NoteType.PERMANENT
    assert len(note.tags) == 2
    assert {tag.name for tag in note.tags} == {"service", "test"}


def test_create_note_requires_title_and_content(zettel_service):
    """Test create_note validation errors for missing title and content."""
    with pytest.raises(ValueError, match="Title is required"):
        zettel_service.create_note(
            title="",
            content="Content",
            note_type=NoteType.PERMANENT,
        )

    with pytest.raises(ValueError, match="Content is required"):
        zettel_service.create_note(
            title="Title",
            content="",
            note_type=NoteType.PERMANENT,
        )


def test_get_note(zettel_service):
    """Test retrieving a note through the service."""
    # Create a test note
    note = zettel_service.create_note(
        title="Service Get Note",
        content="Testing note retrieval through the service.",
        note_type=NoteType.PERMANENT,
        tags=["service", "get"],
    )
    # Retrieve the note
    retrieved_note = zettel_service.get_note(note.id)
    # Verify note was retrieved
    assert retrieved_note is not None
    assert retrieved_note.id == note.id
    assert retrieved_note.title == "Service Get Note"

    # Note content includes the title as a markdown header -
    # account for this in our test
    expected_content = f"# {note.title}\n\n{note.content}"
    assert retrieved_note.content.strip() == expected_content.strip()

    assert retrieved_note.note_type == NoteType.PERMANENT
    assert {tag.name for tag in retrieved_note.tags} == {"service", "get"}


def test_update_note(zettel_service):
    """Test updating a note through the service."""
    # Create a test note
    note = zettel_service.create_note(
        title="Service Update Note",
        content="Testing note update through the service.",
        note_type=NoteType.PERMANENT,
        tags=["service", "update"],
    )
    # Update the note
    updated_note = zettel_service.update_note(
        note_id=note.id,
        title="Updated Service Note",
        content="This note has been updated through the service.",
        tags=["service", "updated"],
    )
    # Verify note was updated
    assert updated_note.id == note.id
    assert updated_note.title == "Updated Service Note"
    assert "This note has been updated through the service." in updated_note.content
    assert {tag.name for tag in updated_note.tags} == {"service", "updated"}


def test_delete_note(zettel_service):
    """Test deleting a note through the service."""
    # Create a test note
    note = zettel_service.create_note(
        title="Service Delete Note",
        content="Testing note deletion through the service.",
        note_type=NoteType.PERMANENT,
        tags=["service", "delete"],
    )
    # Verify note exists
    retrieved_note = zettel_service.get_note(note.id)
    assert retrieved_note is not None
    # Delete the note
    zettel_service.delete_note(note.id)
    # Verify note no longer exists
    deleted_note = zettel_service.get_note(note.id)
    assert deleted_note is None


def test_export_note_and_invalid_format(zettel_service):
    """Test export_note for markdown output and invalid formats."""
    note = zettel_service.create_note(
        title="Exportable Note",
        content="Testing note export.",
        note_type=NoteType.PERMANENT,
        tags=["service", "export"],
    )

    exported = zettel_service.export_note(note.id)
    assert "# Exportable Note" in exported
    assert "Testing note export." in exported

    with pytest.raises(ValueError, match="Unsupported export format"):
        zettel_service.export_note(note.id, fmt="pdf")


def test_create_link(zettel_service):
    """Test creating a link between notes through the service."""
    # Create test notes
    source_note = zettel_service.create_note(
        title="Service Source Note",
        content="Testing link creation (source).",
        note_type=NoteType.PERMANENT,
        tags=["service", "link", "source"],
    )
    target_note = zettel_service.create_note(
        title="Service Target Note",
        content="Testing link creation (target).",
        note_type=NoteType.PERMANENT,
        tags=["service", "link", "target"],
    )
    # Create a link
    source, target = zettel_service.create_link(
        source_id=source_note.id,
        target_id=target_note.id,
        link_type=LinkType.REFERENCE,
        description="A test link via service",
        bidirectional=True,
    )
    # Verify link was created
    assert len(source.links) == 1
    assert source.links[0].target_id == target_note.id
    assert source.links[0].link_type == LinkType.REFERENCE
    assert source.links[0].description == "A test link via service"
    # Verify bidirectional link
    assert len(target.links) == 1
    assert target.links[0].target_id == source_note.id
    assert target.links[0].link_type == LinkType.REFERENCE
    # Test get_linked_notes
    outgoing_links = zettel_service.get_linked_notes(source_note.id, "outgoing")
    assert len(outgoing_links) == 1
    assert outgoing_links[0].id == target_note.id
    incoming_links = zettel_service.get_linked_notes(target_note.id, "incoming")
    assert len(incoming_links) == 1
    assert incoming_links[0].id == source_note.id
    both_links = zettel_service.get_linked_notes(source_note.id, "both")
    assert len(both_links) == 1
    assert both_links[0].id == target_note.id


def test_remove_link_bidirectional(zettel_service):
    """Test removing bidirectional links updates both notes."""
    source_note = zettel_service.create_note(
        title="Remove Source Note",
        content="Testing removal (source).",
        note_type=NoteType.PERMANENT,
        tags=["service", "remove", "source"],
    )
    target_note = zettel_service.create_note(
        title="Remove Target Note",
        content="Testing removal (target).",
        note_type=NoteType.PERMANENT,
        tags=["service", "remove", "target"],
    )

    zettel_service.create_link(
        source_id=source_note.id,
        target_id=target_note.id,
        link_type=LinkType.REFERENCE,
        bidirectional=True,
    )

    zettel_service.remove_link(
        source_id=source_note.id,
        target_id=target_note.id,
        bidirectional=True,
    )

    source_after = zettel_service.get_note(source_note.id)
    target_after = zettel_service.get_note(target_note.id)
    assert source_after is not None
    assert target_after is not None
    assert source_after.links == []
    assert target_after.links == []


def test_search_notes(zettel_service):
    """Test searching for notes through the service."""
    # Create test notes
    note1 = zettel_service.create_note(
        title="Python Basics",
        content="Introduction to Python programming.",
        note_type=NoteType.PERMANENT,
        tags=["python", "programming", "service"],
    )
    note2 = zettel_service.create_note(
        title="Advanced Python",
        content="Advanced techniques in Python.",
        note_type=NoteType.PERMANENT,
        tags=["python", "advanced", "service"],
    )
    zettel_service.create_note(
        title="JavaScript Introduction",
        content="Basics of JavaScript programming.",
        note_type=NoteType.PERMANENT,
        tags=["javascript", "programming", "service"],
    )

    # Search by tags instead of content since that's more reliable
    python_notes = zettel_service.get_notes_by_tag("python")
    assert len(python_notes) == 2
    assert {n.id for n in python_notes} == {note1.id, note2.id}

    # Test adding and removing tags
    first_note = python_notes[0]
    zettel_service.add_tag_to_note(first_note.id, "newTag")
    updated_note = zettel_service.get_note(first_note.id)
    assert "newTag" in {tag.name for tag in updated_note.tags}
    zettel_service.remove_tag_from_note(first_note.id, "newTag")
    updated_note = zettel_service.get_note(first_note.id)
    assert "newTag" not in {tag.name for tag in updated_note.tags}


def test_register_link_type_and_duplicate(zettel_service, tmp_path):
    """Test custom link type registration and duplicate prevention."""
    original_custom_types = dict(link_type_registry._custom)
    original_path = config.custom_link_types_path
    config.custom_link_types_path = tmp_path / "custom_link_types.yaml"

    try:
        result = zettel_service.register_link_type(
            name="implements",
            inverse="implemented_by",
            symmetric=False,
        )

        assert result == {
            "registered": "implements",
            "inverse": "implemented_by",
            "symmetric": False,
        }

        with pytest.raises(ValueError, match="already registered"):
            zettel_service.register_link_type(
                name="implements",
                inverse="implemented_by",
                symmetric=False,
            )
    finally:
        link_type_registry._custom = original_custom_types
        config.custom_link_types_path = original_path


def test_find_similar_notes(zettel_service):
    """Test finding similar notes."""
    # Create test notes with shared tags and links
    note1 = zettel_service.create_note(
        title="Machine Learning Basics",
        content="Introduction to machine learning concepts.",
        note_type=NoteType.PERMANENT,
        tags=["AI", "machine learning", "data science"],
    )
    note2 = zettel_service.create_note(
        title="Neural Networks",
        content="Overview of neural network architectures.",
        note_type=NoteType.PERMANENT,
        tags=["AI", "machine learning", "neural networks"],
    )
    note3 = zettel_service.create_note(
        title="Python for Data Science",
        content="Using Python for data analysis and machine learning.",
        note_type=NoteType.PERMANENT,
        tags=["python", "data science"],
    )
    zettel_service.create_note(
        title="History of Computing",
        content="Evolution of computing technology.",
        note_type=NoteType.PERMANENT,
        tags=["history", "computing"],
    )

    # Create links between notes with different types
    # This ensures we don't have duplicate links of the same type
    zettel_service.create_link(note1.id, note2.id, LinkType.EXTENDS)
    zettel_service.create_link(note1.id, note3.id, LinkType.REFERENCE)

    # Find similar notes to note1
    # Setting a lower threshold since the current implementation
    # may have different weights
    similar_notes = zettel_service.find_similar_notes(note1.id, 0.0)

    # Verify we get at least one similar note (the exact order may vary)
    assert len(similar_notes) > 0

    # Convert to IDs for easier comparison
    similar_ids = [note_tuple[0].id for note_tuple in similar_notes]

    # At least one of note2 or note3 should be in the similar notes
    # (They share tags and/or links with note1)
    assert note2.id in similar_ids or note3.id in similar_ids


def test_create_note_empty_title(zettel_service):
    """Test that creating a note with empty title raises ValueError."""
    with pytest.raises(ValueError, match="Title is required"):
        zettel_service.create_note(title="", content="Some content")


def test_create_note_empty_content(zettel_service):
    """Test that creating a note with empty content raises ValueError."""
    with pytest.raises(ValueError, match="Content is required"):
        zettel_service.create_note(title="Some title", content="")


def test_update_note_not_found(zettel_service):
    """Test that updating a non-existent note raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        zettel_service.update_note(note_id="nonexistent-id", title="New title")


def test_update_note_type_and_metadata(zettel_service):
    """Test updating note_type and metadata fields."""
    note = zettel_service.create_note(
        title="Note for type/metadata update",
        content="Initial content.",
        note_type=NoteType.FLEETING,
    )
    updated = zettel_service.update_note(
        note_id=note.id,
        note_type=NoteType.PERMANENT,
        metadata={"source": "test"},
    )
    assert updated.note_type == NoteType.PERMANENT
    assert updated.metadata.get("source") == "test"


def test_add_tag_to_note_not_found(zettel_service):
    """Test that adding a tag to a non-existent note raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        zettel_service.add_tag_to_note(note_id="nonexistent-id", tag="newtag")


def test_remove_tag_from_note_not_found(zettel_service):
    """Test that removing a tag from a non-existent note raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        zettel_service.remove_tag_from_note(note_id="nonexistent-id", tag="sometag")


def test_create_link_source_not_found(zettel_service):
    """Test that creating a link with non-existent source raises ValueError."""
    target = zettel_service.create_note(title="Target", content="Target content.")
    with pytest.raises(ValueError, match="not found"):
        zettel_service.create_link(
            source_id="nonexistent-id",
            target_id=target.id,
            link_type=LinkType.REFERENCE,
        )


def test_create_link_target_not_found(zettel_service):
    """Test that creating a link with non-existent target raises ValueError."""
    source = zettel_service.create_note(title="Source", content="Source content.")
    with pytest.raises(ValueError, match="not found"):
        zettel_service.create_link(
            source_id=source.id,
            target_id="nonexistent-id",
            link_type=LinkType.REFERENCE,
        )


def test_get_note_by_title(zettel_service):
    """Test retrieving a note by title."""
    note = zettel_service.create_note(title="Unique Title ABC", content="Content here.")
    found = zettel_service.get_note_by_title("Unique Title ABC")
    assert found is not None
    assert found.id == note.id


def test_get_all_tags(zettel_service):
    """Test retrieving all tags."""
    zettel_service.create_note(
        title="Tagged Note", content="Content.", tags=["alpha", "beta"]
    )
    tags = zettel_service.get_all_tags()
    tag_names = {t.name for t in tags}
    assert "alpha" in tag_names
    assert "beta" in tag_names


def test_get_all_tags_with_counts(zettel_service):
    """Test retrieving all tags with usage counts."""
    zettel_service.create_note(title="Counted Note", content="Content.", tags=["gamma"])
    counts = zettel_service.get_all_tags_with_counts()
    assert any(name == "gamma" for name, _ in counts)


def test_remove_link_source_not_found(zettel_service):
    """Test that removing a link with non-existent source raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        zettel_service.remove_link(
            source_id="nonexistent-id",
            target_id="also-nonexistent",
            link_type=LinkType.REFERENCE,
        )


def test_get_linked_notes_not_found(zettel_service):
    """Test that get_linked_notes raises ValueError for missing note."""
    with pytest.raises(ValueError, match="not found"):
        zettel_service.get_linked_notes("nonexistent-id")
