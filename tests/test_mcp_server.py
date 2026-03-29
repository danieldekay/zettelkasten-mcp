# tests/test_mcp_server.py
"""Tests for the MCP server implementation."""
from unittest.mock import MagicMock, patch

from zettelkasten_mcp.models.schema import LinkType, NoteType
from zettelkasten_mcp.server.mcp_server import ZettelkastenMcpServer


class TestMcpServer:
    """Tests for the ZettelkastenMcpServer class."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Capture the tool decorator functions when registering
        self.registered_tools = {}

        # Create a mock for FastMCP
        self.mock_mcp = MagicMock()

        # Mock the tool decorator to capture registered functions BEFORE server creation
        def mock_tool_decorator(*args, **kwargs):
            def tool_wrapper(func):
                # Store the function with its name
                name = kwargs.get("name")
                self.registered_tools[name] = func
                return func
            return tool_wrapper
        self.mock_mcp.tool = mock_tool_decorator

        # Mock the ZettelService and SearchService
        self.mock_zettel_service = MagicMock()
        self.mock_search_service = MagicMock()

        # Create patchers for FastMCP, ZettelService, and SearchService
        self.mcp_patcher = patch("zettelkasten_mcp.server.mcp_server.FastMCP", return_value=self.mock_mcp)
        self.zettel_patcher = patch("zettelkasten_mcp.server.mcp_server.ZettelService", return_value=self.mock_zettel_service)
        self.search_patcher = patch("zettelkasten_mcp.server.mcp_server.SearchService", return_value=self.mock_search_service)

        # Start the patchers
        self.mcp_patcher.start()
        self.zettel_patcher.start()
        self.search_patcher.start()

        # Create a server instance AFTER setting up the mocks
        self.server = ZettelkastenMcpServer()

    def teardown_method(self):
        """Clean up after each test."""
        self.mcp_patcher.stop()
        self.zettel_patcher.stop()
        self.search_patcher.stop()

    def test_server_initialization(self):
        """Test server initialization."""
        # Check services are initialized
        assert self.mock_zettel_service.initialize.called
        assert self.mock_search_service.initialize.called

    def test_create_note_tool(self):
        """Test the zk_create_note tool."""
        # Check the tool is registered
        assert "zk_create_note" in self.registered_tools
        # Set up return value for create_note
        mock_note = MagicMock()
        mock_note.id = "test123"
        mock_note.title = "Test Note"
        self.mock_zettel_service.create_note.return_value = mock_note
        # Call the tool function directly
        create_note_func = self.registered_tools["zk_create_note"]
        result = create_note_func(
            title="Test Note",
            content="Test content",
            note_type="permanent",
            tags="tag1, tag2",
        )
        # Verify result is a dict with expected keys
        assert isinstance(result, dict)
        assert result["note_id"] == mock_note.id
        assert "file_path" in result
        assert "summary" in result
        assert mock_note.id in result["summary"]
        # Verify service call
        self.mock_zettel_service.create_note.assert_called_with(
            title="Test Note",
            content="Test content",
            note_type=NoteType.PERMANENT,
            tags=["tag1", "tag2"],
            metadata=None,
        )

    def test_get_note_tool(self):
        """Test the zk_get_note tool."""
        # Check the tool is registered
        assert "zk_get_note" in self.registered_tools

        # Set up mock note
        mock_note = MagicMock()
        mock_note.id = "test123"
        mock_note.title = "Test Note"
        mock_note.content = "Test content"
        mock_note.note_type = NoteType.PERMANENT
        mock_note.metadata = {}
        mock_note.created_at.isoformat.return_value = "2023-01-01T12:00:00"
        mock_note.updated_at.isoformat.return_value = "2023-01-01T12:30:00"
        mock_tag1 = MagicMock()
        mock_tag1.name = "tag1"
        mock_tag2 = MagicMock()
        mock_tag2.name = "tag2"
        mock_note.tags = [mock_tag1, mock_tag2]
        mock_note.links = []

        # Set up return value for get_note
        self.mock_zettel_service.get_note.return_value = mock_note

        # Call the tool function directly
        get_note_func = self.registered_tools["zk_get_note"]
        result = get_note_func(identifier="test123")

        # Verify result is a dict
        assert isinstance(result, dict)
        assert result["note_id"] == "test123"
        assert result["title"] == "Test Note"
        assert result["content"] == "Test content"
        assert "tag1" in result["tags"]
        assert "metadata" in result
        assert "summary" in result

        # Verify service call
        self.mock_zettel_service.get_note.assert_called_with("test123")

    def test_create_link_tool(self):
        """Test the zk_create_link tool."""
        # Check the tool is registered
        assert "zk_create_link" in self.registered_tools

        # Set up mock notes
        source_note = MagicMock()
        source_note.id = "source123"
        target_note = MagicMock()
        target_note.id = "target456"

        # Set up return value for create_link
        self.mock_zettel_service.create_link.return_value = (source_note, target_note)

        # Call the tool function directly
        create_link_func = self.registered_tools["zk_create_link"]
        result = create_link_func(
            source_id="source123",
            target_id="target456",
            link_type="extends",
            description="Test link",
            bidirectional=True,
        )

        # Verify result is a dict
        assert isinstance(result, dict)
        assert result["source_id"] == "source123"
        assert result["target_id"] == "target456"
        assert result["link_type"] == "extends"
        assert result["bidirectional"] is True
        assert "summary" in result

        # Verify service call
        self.mock_zettel_service.create_link.assert_called_with(
            source_id="source123",
            target_id="target456",
            link_type=LinkType.EXTENDS,
            description="Test link",
            bidirectional=True,
        )

    def test_search_notes_tool(self):
        """Test the zk_search_notes tool."""
        # Check the tool is registered
        assert "zk_search_notes" in self.registered_tools

        # Set up mock notes
        mock_note1 = MagicMock()
        mock_note1.id = "note1"
        mock_note1.title = "Note 1"
        mock_note1.content = "This is note 1 content"
        mock_note1.note_type = MagicMock()
        mock_note1.note_type.value = "permanent"
        mock_tag1 = MagicMock()
        mock_tag1.name = "tag1"
        mock_tag2 = MagicMock()
        mock_tag2.name = "tag2"
        mock_note1.tags = [mock_tag1, mock_tag2]
        mock_note1.created_at.isoformat.return_value = "2023-01-01T00:00:00"
        mock_note1.updated_at.isoformat.return_value = "2023-01-01T00:00:00"

        mock_note2 = MagicMock()
        mock_note2.id = "note2"
        mock_note2.title = "Note 2"
        mock_note2.content = "This is note 2 content"
        mock_note2.note_type = MagicMock()
        mock_note2.note_type.value = "permanent"
        mock_tag1 = MagicMock()
        mock_tag1.name = "tag1"
        mock_note2.tags = [mock_tag1]
        mock_note2.created_at.isoformat.return_value = "2023-01-02T00:00:00"
        mock_note2.updated_at.isoformat.return_value = "2023-01-02T00:00:00"

        # Set up mock search results
        mock_result1 = MagicMock()
        mock_result1.note = mock_note1
        mock_result2 = MagicMock()
        mock_result2.note = mock_note2

        self.mock_search_service.search_combined.return_value = [mock_result1, mock_result2]

        # Call the tool function directly
        search_notes_func = self.registered_tools["zk_search_notes"]
        result = search_notes_func(
            query="test query",
            tags="tag1, tag2",
            note_type="permanent",
            limit=10,
        )

        # Verify result is a dict
        assert isinstance(result, dict)
        assert result["total"] == 2
        assert len(result["notes"]) == 2
        assert result["query"] == "test query"
        assert "summary" in result
        note_titles = [n["title"] for n in result["notes"]]
        assert "Note 1" in note_titles
        assert "Note 2" in note_titles

        # Verify service call
        self.mock_search_service.search_combined.assert_called_with(
            text="test query",
            tags=["tag1", "tag2"],
            note_type=NoteType.PERMANENT,
        )

    def test_create_note_with_metadata(self):
        """Test zk_create_note passes parsed metadata to the service."""
        assert "zk_create_note" in self.registered_tools
        mock_note = MagicMock()
        mock_note.id = "meta123"
        mock_note.title = "Meta Note"
        self.mock_zettel_service.create_note.return_value = mock_note

        create_note_func = self.registered_tools["zk_create_note"]
        result = create_note_func(
            title="Meta Note",
            content="Content",
            metadata='{"source": "paper", "year": 2025}',
        )

        assert isinstance(result, dict)
        assert result["note_id"] == mock_note.id
        call_kwargs = self.mock_zettel_service.create_note.call_args.kwargs
        assert call_kwargs["metadata"] == {"source": "paper", "year": 2025}

    def test_create_note_invalid_json_metadata(self):
        """Test zk_create_note returns structured error for invalid metadata JSON."""
        create_note_func = self.registered_tools["zk_create_note"]
        result = create_note_func(
            title="Test",
            content="Content",
            metadata="not valid json",
        )
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "invalid_metadata"
        assert "metadata" in result["message"].lower()

    def test_create_note_metadata_not_object(self):
        """Test zk_create_note rejects metadata that is a JSON array."""
        create_note_func = self.registered_tools["zk_create_note"]
        result = create_note_func(
            title="Test",
            content="Content",
            metadata="[1, 2, 3]",
        )
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "invalid_metadata"

    def test_create_note_metadata_as_dict(self):
        """Test zk_create_note accepts a pre-parsed dict for metadata."""
        mock_note = MagicMock()
        mock_note.id = "dictmeta1"
        mock_note.title = "Dict Meta Note"
        self.mock_zettel_service.create_note.return_value = mock_note

        create_note_func = self.registered_tools["zk_create_note"]
        result = create_note_func(
            title="Dict Meta Note",
            content="Content",
            metadata={"source": "test", "year": 2026},
        )

        assert isinstance(result, dict)
        assert result["note_id"] == mock_note.id
        call_kwargs = self.mock_zettel_service.create_note.call_args.kwargs
        assert call_kwargs["metadata"] == {"source": "test", "year": 2026}

    def test_update_note_with_metadata(self):
        """Test zk_update_note passes parsed metadata to the service."""
        assert "zk_update_note" in self.registered_tools
        mock_note = MagicMock()
        mock_note.id = "upd123"
        mock_note.title = "Updated"
        self.mock_zettel_service.get_note.return_value = mock_note
        self.mock_zettel_service.update_note.return_value = mock_note

        update_note_func = self.registered_tools["zk_update_note"]
        result = update_note_func(
            note_id="upd123",
            metadata='{"key": "value"}',
        )

        assert isinstance(result, dict)
        assert "note_id" in result
        call_kwargs = self.mock_zettel_service.update_note.call_args.kwargs
        assert call_kwargs["metadata"] == {"key": "value"}

    def test_update_note_metadata_as_dict(self):
        """Test zk_update_note accepts a pre-parsed dict for metadata."""
        mock_note = MagicMock()
        mock_note.id = "upd456"
        mock_note.title = "Updated"
        self.mock_zettel_service.get_note.return_value = mock_note
        self.mock_zettel_service.update_note.return_value = mock_note

        update_note_func = self.registered_tools["zk_update_note"]
        result = update_note_func(
            note_id="upd456",
            metadata={"key": "value", "count": 3},
        )

        assert isinstance(result, dict)
        assert "note_id" in result
        call_kwargs = self.mock_zettel_service.update_note.call_args.kwargs
        assert call_kwargs["metadata"] == {"key": "value", "count": 3}

    def test_get_note_not_found_returns_structured_error(self):
        """Test zk_get_note returns structured error dict when note not found."""
        self.mock_zettel_service.get_note.return_value = None
        self.mock_zettel_service.get_note_by_title.return_value = None

        get_note_func = self.registered_tools["zk_get_note"]
        result = get_note_func(identifier="nonexistent")

        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "not_found"
        assert "nonexistent" in result["message"]

    def test_get_note_returns_metadata(self):
        """Test zk_get_note includes metadata in returned dict."""
        mock_note = MagicMock()
        mock_note.id = "mn1"
        mock_note.title = "My Note"
        mock_note.content = "Content"
        mock_note.note_type = MagicMock()
        mock_note.note_type.value = "permanent"
        mock_note.tags = []
        mock_note.links = []
        mock_note.metadata = {"source": "test"}
        mock_note.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_note.updated_at.isoformat.return_value = "2024-01-01T00:00:00"
        self.mock_zettel_service.get_note.return_value = mock_note

        result = self.registered_tools["zk_get_note"](identifier="mn1")

        assert isinstance(result, dict)
        assert result["metadata"] == {"source": "test"}

    def test_get_all_tags_returns_dict_with_counts(self):
        """Test zk_get_all_tags returns dict with tag name and count."""
        self.mock_zettel_service.get_all_tags_with_counts.return_value = [
            ("ai", 3),
            ("research", 5),
        ]
        result = self.registered_tools["zk_get_all_tags"]()

        assert isinstance(result, dict)
        assert result["total"] == 2
        tag_names = [t["name"] for t in result["tags"]]
        assert "ai" in tag_names
        assert "research" in tag_names
        tag_counts = {t["name"]: t["count"] for t in result["tags"]}
        assert tag_counts["research"] == 5

    def test_error_handling(self):
        """Test error handling in the server."""
        # Test ValueError handling returns structured dict
        value_error = ValueError("Invalid input")
        result = self.server.format_error_response(value_error)
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "validation_error"
        assert "Invalid input" in result["message"]

        # Test IOError handling
        io_error = OSError("File not found")
        result = self.server.format_error_response(io_error)
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "file_system_error"
        assert "File not found" in result["message"]

        # Test general exception handling
        general_error = Exception("Something went wrong")
        result = self.server.format_error_response(general_error)
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "internal_error"
        assert "Something went wrong" in result["message"]

    def test_create_note_invalid_type(self):
        """Test zk_create_note returns error for invalid note type."""
        create_note_func = self.registered_tools["zk_create_note"]
        result = create_note_func(
            title="Test",
            content="Content",
            note_type="invalid_type",
        )
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "validation_error"
        assert "invalid_type" in result["message"]

    def test_create_note_service_exception(self):
        """Test zk_create_note returns error when service raises."""
        self.mock_zettel_service.create_note.side_effect = OSError("Disk full")
        create_note_func = self.registered_tools["zk_create_note"]
        result = create_note_func(title="Test", content="Content")
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "file_system_error"

    def test_update_note_success(self):
        """Test zk_update_note returns updated note info."""
        mock_note = MagicMock()
        mock_note.id = "upd123"
        mock_note.title = "Updated Note"
        self.mock_zettel_service.get_note.return_value = mock_note
        self.mock_zettel_service.update_note.return_value = mock_note

        update_func = self.registered_tools["zk_update_note"]
        result = update_func(
            note_id="upd123",
            title="Updated Note",
            content="New content",
            note_type="fleeting",
            tags="a, b",
        )

        assert isinstance(result, dict)
        assert result["note_id"] == "upd123"
        assert "updated_fields" in result
        assert "title" in result["updated_fields"]
        assert "content" in result["updated_fields"]
        assert "note_type" in result["updated_fields"]
        assert "summary" in result

    def test_update_note_not_found(self):
        """Test zk_update_note returns structured error when note not found."""
        self.mock_zettel_service.get_note.return_value = None
        update_func = self.registered_tools["zk_update_note"]
        result = update_func(note_id="missing", title="New title")
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "not_found"

    def test_update_note_invalid_type(self):
        """Test zk_update_note returns error for invalid note type."""
        mock_note = MagicMock()
        mock_note.id = "n1"
        self.mock_zettel_service.get_note.return_value = mock_note

        update_func = self.registered_tools["zk_update_note"]
        result = update_func(note_id="n1", note_type="bad_type")
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "validation_error"

    def test_update_note_invalid_json_metadata(self):
        """Test zk_update_note returns error for invalid metadata JSON."""
        mock_note = MagicMock()
        mock_note.id = "n1"
        self.mock_zettel_service.get_note.return_value = mock_note

        update_func = self.registered_tools["zk_update_note"]
        result = update_func(note_id="n1", metadata="not-json")
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "invalid_metadata"

    def test_update_note_metadata_not_object(self):
        """Test zk_update_note rejects metadata that is not a JSON object."""
        mock_note = MagicMock()
        mock_note.id = "n1"
        self.mock_zettel_service.get_note.return_value = mock_note

        update_func = self.registered_tools["zk_update_note"]
        result = update_func(note_id="n1", metadata="[1, 2]")
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "invalid_metadata"

    def test_delete_note_success(self):
        """Test zk_delete_note returns success response."""
        mock_note = MagicMock()
        mock_note.id = "del1"
        mock_note.title = "To Delete"
        self.mock_zettel_service.get_note.return_value = mock_note

        delete_func = self.registered_tools["zk_delete_note"]
        result = delete_func(note_id="del1")

        assert isinstance(result, dict)
        assert result["note_id"] == "del1"
        assert result["deleted"] is True
        assert "summary" in result
        self.mock_zettel_service.delete_note.assert_called_with("del1")

    def test_delete_note_not_found(self):
        """Test zk_delete_note returns structured error when note not found."""
        self.mock_zettel_service.get_note.return_value = None

        delete_func = self.registered_tools["zk_delete_note"]
        result = delete_func(note_id="ghost")

        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "not_found"

    def test_create_link_invalid_type(self):
        """Test zk_create_link returns error for invalid link type."""
        create_link_func = self.registered_tools["zk_create_link"]
        result = create_link_func(
            source_id="s1",
            target_id="t1",
            link_type="invalid_link",
        )
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "validation_error"
        assert "invalid_link" in result["message"]

    def test_remove_link_success(self):
        """Test zk_remove_link returns success response."""
        source_note = MagicMock()
        source_note.id = "s1"
        target_note = MagicMock()
        target_note.id = "t1"
        self.mock_zettel_service.remove_link.return_value = (source_note, target_note)

        remove_link_func = self.registered_tools["zk_remove_link"]
        result = remove_link_func(source_id="s1", target_id="t1")

        assert isinstance(result, dict)
        assert result["source_id"] == "s1"
        assert result["target_id"] == "t1"
        assert result["removed"] is True
        assert result["bidirectional"] is False
        assert "summary" in result

    def test_remove_link_bidirectional(self):
        """Test zk_remove_link with bidirectional=True."""
        source_note = MagicMock()
        target_note = MagicMock()
        self.mock_zettel_service.remove_link.return_value = (source_note, target_note)

        remove_link_func = self.registered_tools["zk_remove_link"]
        result = remove_link_func(source_id="s1", target_id="t1", bidirectional=True)

        assert isinstance(result, dict)
        assert result["bidirectional"] is True
        assert "Bidirectional" in result["summary"]

    def test_remove_link_exception(self):
        """Test zk_remove_link returns structured error on exception."""
        self.mock_zettel_service.remove_link.side_effect = ValueError("Not found")

        remove_link_func = self.registered_tools["zk_remove_link"]
        result = remove_link_func(source_id="s1", target_id="t1")

        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "validation_error"

    def test_search_notes_no_results(self):
        """Test zk_search_notes returns empty results structure."""
        self.mock_search_service.search_combined.return_value = []

        search_func = self.registered_tools["zk_search_notes"]
        result = search_func(query="nonexistent")

        assert isinstance(result, dict)
        assert result["total"] == 0
        assert len(result["notes"]) == 0
        assert "No matching" in result["summary"]

    def test_search_notes_invalid_type(self):
        """Test zk_search_notes returns error for invalid note type filter."""
        search_func = self.registered_tools["zk_search_notes"]
        result = search_func(note_type="bad_type")

        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "validation_error"

    def test_sync_watch_folders_returns_summary(self, tmp_path):
        """Test zk_sync_watch_folders calls the watch-folder service and returns counts."""
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        mock_service = MagicMock()
        mock_service.sync_all.return_value = {
            "scanned": 3,
            "added": 2,
            "removed": 1,
            "errors": [(str(watch_dir / "bad.md"), "invalid yaml")],
        }

        with patch(
            "zettelkasten_mcp.server.mcp_server.config.watch_dirs",
            [watch_dir],
        ), patch(
            "zettelkasten_mcp.services.watch_folder_service.WatchFolderService",
            return_value=mock_service,
        ) as mock_watch_service:
            result = self.registered_tools["zk_sync_watch_folders"]()

        assert isinstance(result, dict)
        assert result["scanned"] == 3
        assert result["added"] == 2
        assert result["removed"] == 1
        assert result["errors"] == [(str(watch_dir / "bad.md"), "invalid yaml")]
        assert "3 scanned" in result["summary"]
        assert "2 added" in result["summary"]
        assert "1 removed" in result["summary"]
        mock_watch_service.assert_called_once_with(
            watch_dirs=[watch_dir],
            repository=self.mock_zettel_service.repository,
        )
        mock_service.sync_all.assert_called_once()

    def test_list_notes_excludes_external_notes_when_requested(self):
        """Test zk_list_notes(include_external=False) filters out read-only notes."""
        internal_note = self._make_mock_note("n1", "Internal Note")
        internal_note.is_readonly = False
        external_note = self._make_mock_note("n2", "External Note")
        external_note.is_readonly = True
        external_note.source_path = "/tmp/watch/external.md"

        self.mock_zettel_service.search_notes.return_value = [
            internal_note,
            external_note,
        ]

        list_notes_func = self.registered_tools["zk_list_notes"]
        result = list_notes_func(include_external=False, limit=10)

        assert isinstance(result, dict)
        assert result["total"] == 1
        assert len(result["notes"]) == 1
        assert result["notes"][0]["note_id"] == "n1"
        assert result["include_external"] is False
        self.mock_zettel_service.search_notes.assert_called_with(
            tags=None,
            note_type=None,
        )

    def _make_mock_note(self, note_id="n1", title="Test"):
        """Helper to create a consistent mock note."""
        note = MagicMock()
        note.id = note_id
        note.title = title
        note.content = "Some content here"
        note.note_type = MagicMock()
        note.note_type.value = "permanent"
        note.tags = []
        note.links = []
        note.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        note.updated_at.isoformat.return_value = "2024-01-01T00:00:00"
        return note

    def test_get_linked_notes_success(self):
        """Test zk_get_linked_notes returns list of linked notes."""
        source_note = self._make_mock_note("src1", "Source")
        linked_note = self._make_mock_note("tgt1", "Target")

        mock_link = MagicMock()
        mock_link.target_id = "tgt1"
        mock_link.link_type.value = "extends"
        mock_link.description = "builds on"
        source_note.links = [mock_link]

        self.mock_zettel_service.get_linked_notes.return_value = [linked_note]
        self.mock_zettel_service.get_note.return_value = source_note

        get_linked_func = self.registered_tools["zk_get_linked_notes"]
        result = get_linked_func(note_id="src1", direction="outgoing")

        assert isinstance(result, dict)
        assert result["note_id"] == "src1"
        assert result["total"] == 1
        assert result["direction"] == "outgoing"
        assert "notes" in result
        assert "summary" in result

    def test_get_linked_notes_invalid_direction(self):
        """Test zk_get_linked_notes returns error for invalid direction."""
        get_linked_func = self.registered_tools["zk_get_linked_notes"]
        result = get_linked_func(note_id="n1", direction="sideways")

        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "validation_error"
        assert "sideways" in result["message"]

    def test_get_linked_notes_no_links(self):
        """Test zk_get_linked_notes returns empty results for unlinked note."""
        self.mock_zettel_service.get_linked_notes.return_value = []
        self.mock_zettel_service.get_note.return_value = self._make_mock_note()

        get_linked_func = self.registered_tools["zk_get_linked_notes"]
        result = get_linked_func(note_id="n1", direction="both")

        assert isinstance(result, dict)
        assert result["total"] == 0
        assert "No" in result["summary"]

    def test_get_linked_notes_incoming(self):
        """Test zk_get_linked_notes with incoming direction."""
        linked_note = self._make_mock_note("src1", "Source")
        mock_link = MagicMock()
        mock_link.target_id = "n1"
        mock_link.link_type.value = "reference"
        mock_link.description = None
        linked_note.links = [mock_link]

        self.mock_zettel_service.get_linked_notes.return_value = [linked_note]
        self.mock_zettel_service.get_note.return_value = None

        get_linked_func = self.registered_tools["zk_get_linked_notes"]
        result = get_linked_func(note_id="n1", direction="incoming")

        assert isinstance(result, dict)
        assert result["total"] == 1

    def test_find_similar_notes_success(self):
        """Test zk_find_similar_notes returns notes with similarity scores."""
        similar_note = self._make_mock_note("sim1", "Similar Note")
        self.mock_zettel_service.find_similar_notes.return_value = [
            (similar_note, 0.75),
        ]

        find_similar_func = self.registered_tools["zk_find_similar_notes"]
        result = find_similar_func(note_id="n1", threshold=0.3, limit=5)

        assert isinstance(result, dict)
        assert result["total"] == 1
        assert result["notes"][0]["similarity"] == 0.75
        assert "summary" in result

    def test_find_similar_notes_empty(self):
        """Test zk_find_similar_notes returns empty structure when none found."""
        self.mock_zettel_service.find_similar_notes.return_value = []

        find_similar_func = self.registered_tools["zk_find_similar_notes"]
        result = find_similar_func(note_id="n1")

        assert isinstance(result, dict)
        assert result["total"] == 0
        assert "No similar" in result["summary"]

    def test_find_similar_notes_exception(self):
        """Test zk_find_similar_notes returns structured error on exception."""
        self.mock_zettel_service.find_similar_notes.side_effect = ValueError("bad id")

        find_similar_func = self.registered_tools["zk_find_similar_notes"]
        result = find_similar_func(note_id="bad")

        assert isinstance(result, dict)
        assert result["error"] is True

    def test_find_central_notes_success(self):
        """Test zk_find_central_notes returns notes with connection counts."""
        central_note = self._make_mock_note("c1", "Central Note")
        self.mock_search_service.find_central_notes.return_value = [
            (central_note, 10),
        ]

        find_central_func = self.registered_tools["zk_find_central_notes"]
        result = find_central_func(limit=5)

        assert isinstance(result, dict)
        assert result["total"] == 1
        assert result["notes"][0]["connections"] == 10
        assert "summary" in result

    def test_find_central_notes_empty(self):
        """Test zk_find_central_notes returns empty results."""
        self.mock_search_service.find_central_notes.return_value = []

        find_central_func = self.registered_tools["zk_find_central_notes"]
        result = find_central_func()

        assert isinstance(result, dict)
        assert result["total"] == 0
        assert "No notes" in result["summary"]

    def test_find_central_notes_exception(self):
        """Test zk_find_central_notes returns structured error on exception."""
        self.mock_search_service.find_central_notes.side_effect = OSError("DB error")

        find_central_func = self.registered_tools["zk_find_central_notes"]
        result = find_central_func()

        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "file_system_error"

    def test_find_orphaned_notes_success(self):
        """Test zk_find_orphaned_notes returns orphaned notes list."""
        orphan = self._make_mock_note("o1", "Orphaned Note")
        self.mock_search_service.find_orphaned_notes.return_value = [orphan]

        find_orphans_func = self.registered_tools["zk_find_orphaned_notes"]
        result = find_orphans_func()

        assert isinstance(result, dict)
        assert result["total"] == 1
        assert result["notes"][0]["note_id"] == "o1"
        assert "summary" in result

    def test_find_orphaned_notes_empty(self):
        """Test zk_find_orphaned_notes returns empty when no orphans."""
        self.mock_search_service.find_orphaned_notes.return_value = []

        find_orphans_func = self.registered_tools["zk_find_orphaned_notes"]
        result = find_orphans_func()

        assert isinstance(result, dict)
        assert result["total"] == 0
        assert "No orphaned" in result["summary"]

    def test_find_orphaned_notes_exception(self):
        """Test zk_find_orphaned_notes returns structured error on exception."""
        self.mock_search_service.find_orphaned_notes.side_effect = Exception("fail")

        find_orphans_func = self.registered_tools["zk_find_orphaned_notes"]
        result = find_orphans_func()

        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "internal_error"

    def test_list_notes_by_date_success(self):
        """Test zk_list_notes_by_date returns notes within date range."""
        note = self._make_mock_note("d1", "Dated Note")
        self.mock_search_service.find_notes_by_date_range.return_value = [note]

        list_by_date_func = self.registered_tools["zk_list_notes_by_date"]
        result = list_by_date_func(
            start_date="2024-01-01",
            end_date="2024-12-31",
            use_updated=False,
            limit=10,
        )

        assert isinstance(result, dict)
        assert result["total"] == 1
        assert result["notes"][0]["note_id"] == "d1"
        assert "created" in result["summary"]

    def test_list_notes_by_date_use_updated(self):
        """Test zk_list_notes_by_date with use_updated=True reflects in summary."""
        self.mock_search_service.find_notes_by_date_range.return_value = []

        list_by_date_func = self.registered_tools["zk_list_notes_by_date"]
        result = list_by_date_func(use_updated=True)

        assert isinstance(result, dict)
        assert "updated" in result["summary"]

    def test_list_notes_by_date_no_results(self):
        """Test zk_list_notes_by_date returns empty when no notes in range."""
        self.mock_search_service.find_notes_by_date_range.return_value = []

        list_by_date_func = self.registered_tools["zk_list_notes_by_date"]
        result = list_by_date_func(start_date="2020-01-01")

        assert isinstance(result, dict)
        assert result["total"] == 0
        assert "No notes" in result["summary"]

    def test_list_notes_by_date_invalid_date(self):
        """Test zk_list_notes_by_date returns error for invalid date format."""
        list_by_date_func = self.registered_tools["zk_list_notes_by_date"]
        result = list_by_date_func(start_date="not-a-date")

        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "validation_error"
        assert "date" in result["message"].lower()

    def test_list_notes_by_date_only_end(self):
        """Test zk_list_notes_by_date with only end_date."""
        note = self._make_mock_note("d2", "Another Note")
        self.mock_search_service.find_notes_by_date_range.return_value = [note]

        list_by_date_func = self.registered_tools["zk_list_notes_by_date"]
        result = list_by_date_func(end_date="2024-12-31")

        assert isinstance(result, dict)
        assert result["total"] == 1
        assert "before" in result["summary"]

    def test_rebuild_index_success(self):
        """Test zk_rebuild_index returns index count."""
        note1 = self._make_mock_note("n1", "Note 1")
        note2 = self._make_mock_note("n2", "Note 2")
        self.mock_zettel_service.get_all_notes.side_effect = [[note1], [note1, note2]]

        rebuild_func = self.registered_tools["zk_rebuild_index"]
        result = rebuild_func()

        assert isinstance(result, dict)
        assert result["notes_indexed"] == 2
        assert result["errors"] == []
        assert "+1" in result["summary"]

    def test_rebuild_index_exception(self):
        """Test zk_rebuild_index returns structured error on exception."""
        self.mock_zettel_service.get_all_notes.side_effect = Exception("DB error")

        rebuild_func = self.registered_tools["zk_rebuild_index"]
        result = rebuild_func()

        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "internal_error"

    def test_create_link_duplicate_raises_integrity_error(self):
        """Test zk_create_link returns conflict error for duplicate link."""
        from sqlalchemy import exc as sqlalchemy_exc

        self.mock_zettel_service.create_link.side_effect = sqlalchemy_exc.IntegrityError(
            "UNIQUE constraint failed", None, None,
        )

        create_link_func = self.registered_tools["zk_create_link"]
        result = create_link_func(source_id="s1", target_id="t1", link_type="reference")

        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "conflict"

    def test_get_note_exception(self):
        """Test zk_get_note returns structured error when service raises."""
        self.mock_zettel_service.get_note.side_effect = OSError("Disk error")

        get_note_func = self.registered_tools["zk_get_note"]
        result = get_note_func(identifier="n1")

        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_type"] == "file_system_error"
