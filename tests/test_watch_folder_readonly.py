"""Tests for read-only mutation guards on watch-folder notes."""

import pytest

from zettelkasten_mcp.models.schema import Note, NoteType, Tag, generate_id


def _make_readonly_note(**kwargs) -> Note:
    defaults = dict(
        id=generate_id(),
        title="External Note",
        content="External content.",
        note_type=NoteType.PERMANENT,
        tags=[],
        links=[],
        metadata={},
        is_readonly=True,
        source_path="/some/watch/folder/note.md",
    )
    defaults.update(kwargs)
    return Note(**defaults)


def _make_writable_note(**kwargs) -> Note:
    defaults = dict(
        id=generate_id(),
        title="Primary Note",
        content="Primary content.",
        note_type=NoteType.PERMANENT,
        tags=[],
        links=[],
        metadata={},
    )
    defaults.update(kwargs)
    return Note(**defaults)


class TestUpdateNoteGuard:
    def test_update_readonly_note_raises_permission_error(self, zettel_service):
        """Attempting to update a read-only note raises PermissionError."""
        # Create the note in the repository as read-only
        note = _make_readonly_note()
        zettel_service.repository._index_note(note)

        # Patch get() to return the readonly note
        from unittest.mock import patch
        with patch.object(zettel_service.repository, "get", return_value=note):
            with pytest.raises(PermissionError, match="read-only"):
                zettel_service.update_note(
                    note_id=note.id,
                    title="New Title",
                )

    def test_update_writable_note_succeeds(self, zettel_service):
        """Updating a regular (non-readonly) note works without error."""
        note = zettel_service.create_note(
            title="Regular Note",
            content="Content.",
            note_type=NoteType.PERMANENT,
        )
        updated = zettel_service.update_note(
            note_id=note.id,
            title="Updated Title",
        )
        assert updated.title == "Updated Title"


class TestDeleteNoteGuard:
    def test_delete_readonly_note_raises_permission_error(self, zettel_service):
        """Attempting to delete a read-only note raises PermissionError."""
        note = _make_readonly_note()
        zettel_service.repository._index_note(note)

        from unittest.mock import patch
        with patch.object(zettel_service.repository, "get", return_value=note):
            with pytest.raises(PermissionError, match="read-only"):
                zettel_service.delete_note(note_id=note.id)

    def test_delete_nonexistent_note_raises_value_error(self, zettel_service):
        """Deleting an ID that doesn't exist raises ValueError."""
        with pytest.raises(ValueError):
            zettel_service.delete_note(note_id="nonexistent-id")


class TestCreateLinkToReadonly:
    def test_link_to_readonly_note_allowed_unidirectional(self, zettel_service):
        """Creating a unidirectional link targeting a read-only note is allowed."""
        source = zettel_service.create_note(
            title="Source",
            content="Source content.",
            note_type=NoteType.PERMANENT,
        )
        target = _make_readonly_note()
        zettel_service.repository._index_note(target)

        from unittest.mock import patch
        # Return the readonly note when target is looked up
        original_get = zettel_service.repository.get

        def patched_get(note_id):
            if note_id == target.id:
                return target
            return original_get(note_id)

        with patch.object(zettel_service.repository, "get", side_effect=patched_get):
            result_source, result_target = zettel_service.create_link(
                source_id=source.id,
                target_id=target.id,
                link_type="reference",
                bidirectional=False,
            )
        assert result_source is not None
        link_targets = {lnk.target_id for lnk in result_source.links}
        assert target.id in link_targets

    def test_bidirectional_link_to_readonly_skips_reverse(self, zettel_service):
        """Bidirectional link to a read-only note creates only the forward link."""
        from unittest.mock import patch
        source = zettel_service.create_note(
            title="Source",
            content="Content.",
            note_type=NoteType.PERMANENT,
        )
        target = _make_readonly_note()
        zettel_service.repository._index_note(target)

        original_get = zettel_service.repository.get

        def patched_get(note_id):
            if note_id == target.id:
                return target
            return original_get(note_id)

        with patch.object(zettel_service.repository, "get", side_effect=patched_get):
            result_source, result_rev = zettel_service.create_link(
                source_id=source.id,
                target_id=target.id,
                link_type="reference",
                bidirectional=True,
            )
        # Forward link exists
        link_targets = {lnk.target_id for lnk in result_source.links}
        assert target.id in link_targets
        # No reverse note returned (readonly target, skipped)
        assert result_rev is None
