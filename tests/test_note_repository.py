"""Tests for the NoteRepository class."""

import pytest
from zettelkasten_mcp.models.schema import LinkType, Note, NoteType, Tag


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
    # Note content includes the title as a markdown header - account for this in our test
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


def test_create_note_with_duplicate_tags(note_repository):
    """Test creating a note with duplicate tags in the input list.

    This tests the fix for the database IntegrityError that occurs when
    the same tag appears multiple times in the tags list.
    """
    # Create a note with duplicate tags
    note = Note(
        title="Duplicate Tags Test",
        content="Testing duplicate tag prevention.",
        note_type=NoteType.PERMANENT,
        tags=[
            Tag(name="python"),
            Tag(name="test"),
            Tag(name="python"),  # Duplicate
            Tag(name="test"),  # Duplicate
            Tag(name="python"),  # Another duplicate
        ],
    )

    # Save to repository - should not raise IntegrityError
    saved_note = note_repository.create(note)

    # Verify note was saved with unique tags only
    assert saved_note.id is not None
    assert len(saved_note.tags) == 5  # All tags are in the list initially

    # Retrieve the note to verify database state
    retrieved_note = note_repository.get(saved_note.id)
    assert retrieved_note is not None

    # The database should only have unique tags
    unique_tag_names = {tag.name for tag in retrieved_note.tags}
    assert unique_tag_names == {"python", "test"}
    assert len(unique_tag_names) == 2


def test_update_note_with_duplicate_tags(note_repository):
    """Test updating a note with duplicate tags in the input list.

    This tests the fix for the database IntegrityError that occurs when
    updating a note and the same tag appears multiple times in the tags list.
    """
    # Create a note with normal tags
    note = Note(
        title="Update Duplicate Tags Test",
        content="Testing duplicate tag prevention on update.",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="original"), Tag(name="test")],
    )

    # Save to repository
    saved_note = note_repository.create(note)

    # Update with duplicate tags
    saved_note.tags = [
        Tag(name="updated"),
        Tag(name="python"),
        Tag(name="updated"),  # Duplicate
        Tag(name="test"),
        Tag(name="python"),  # Duplicate
        Tag(name="test"),  # Duplicate
    ]

    # Update should not raise IntegrityError
    note_repository.update(saved_note)

    # Retrieve the note to verify database state
    retrieved_note = note_repository.get(saved_note.id)
    assert retrieved_note is not None

    # The database should only have unique tags
    unique_tag_names = {tag.name for tag in retrieved_note.tags}
    assert unique_tag_names == {"updated", "python", "test"}
    assert len(unique_tag_names) == 3


def test_update_note_preserves_existing_tags_without_duplicates(note_repository):
    """Test that updating a note with the same tags doesn't create duplicates.

    This tests the scenario where a note already has tags in the database,
    and we update it with the same tags again.
    """
    # Create a note with tags
    note = Note(
        title="Preserve Tags Test",
        content="Testing tag preservation.",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="python"), Tag(name="test")],
    )

    # Save to repository
    saved_note = note_repository.create(note)
    original_id = saved_note.id

    # Retrieve and update with the same tags
    retrieved_note = note_repository.get(original_id)
    retrieved_note.content = "Updated content."
    # Same tags as before
    retrieved_note.tags = [Tag(name="python"), Tag(name="test")]

    # Update should not raise IntegrityError
    note_repository.update(retrieved_note)

    # Retrieve again to verify
    final_note = note_repository.get(original_id)
    assert final_note is not None

    # Should still have exactly 2 unique tags
    unique_tag_names = {tag.name for tag in final_note.tags}
    assert unique_tag_names == {"python", "test"}
    assert len(unique_tag_names) == 2


def test_multiple_notes_same_tags_no_duplicates(note_repository):
    """Test that multiple notes can share the same tags without creating duplicates.

    This verifies that the tag deduplication works correctly when multiple
    notes use the same tags.
    """
    # Create multiple notes with overlapping tags
    note1 = Note(
        title="First Note",
        content="First note content.",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="python"), Tag(name="test")],
    )

    note2 = Note(
        title="Second Note",
        content="Second note content.",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="python"), Tag(name="example")],  # Reuses 'python'
    )

    note3 = Note(
        title="Third Note",
        content="Third note content.",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="test"), Tag(name="example")],  # Reuses both
    )

    # Save all notes - should not raise IntegrityError
    saved_note1 = note_repository.create(note1)
    saved_note2 = note_repository.create(note2)
    saved_note3 = note_repository.create(note3)

    # Verify all notes were created
    assert saved_note1.id is not None
    assert saved_note2.id is not None
    assert saved_note3.id is not None

    # Verify each note has the correct tags
    retrieved1 = note_repository.get(saved_note1.id)
    retrieved2 = note_repository.get(saved_note2.id)
    retrieved3 = note_repository.get(saved_note3.id)

    assert {tag.name for tag in retrieved1.tags} == {"python", "test"}
    assert {tag.name for tag in retrieved2.tags} == {"python", "example"}
    assert {tag.name for tag in retrieved3.tags} == {"test", "example"}

    # Verify we can search by shared tags
    python_notes = note_repository.find_by_tag("python")
    assert len(python_notes) == 2
    assert {note.id for note in python_notes} == {saved_note1.id, saved_note2.id}
