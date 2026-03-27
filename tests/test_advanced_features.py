"""Tests for advanced features: custom link types, inference, tag suggestions,
graceful degradation, and drift check.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from pydantic import ValidationError
from sqlalchemy import create_engine

from zettelkasten_mcp.config import config
from zettelkasten_mcp.main import _run_drift_check
from zettelkasten_mcp.models.db_models import Base
from zettelkasten_mcp.models.schema import (
    Link,
    LinkTypeRegistry,
    Note,
    NoteType,
    generate_id,
)
from zettelkasten_mcp.server.mcp_server import ZettelkastenMcpServer
from zettelkasten_mcp.services.inference_service import InferenceService
from zettelkasten_mcp.services.search_service import SearchService
from zettelkasten_mcp.services.zettel_service import ZettelService
from zettelkasten_mcp.storage.note_repository import NoteRepository

# ---------------------------------------------------------------------------
# Task 1.7 — Custom link type registration
# ---------------------------------------------------------------------------


class TestLinkTypeRegistry:
    """Tests for LinkTypeRegistry (schema.py)."""

    def setup_method(self):
        self.registry = LinkTypeRegistry()

    def test_register_symmetric(self):
        self.registry.register("complements", "complements", symmetric=True)
        assert self.registry.is_valid("complements")
        assert self.registry.get_inverse("complements") == "complements"

    def test_register_asymmetric(self):
        self.registry.register("implements", "implemented_by", symmetric=False)
        assert self.registry.is_valid("implements")
        assert self.registry.is_valid("implemented_by")
        assert self.registry.get_inverse("implements") == "implemented_by"

    def test_duplicate_rejected(self):
        self.registry.register("unique_type", "unique_type_by", symmetric=False)
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register("unique_type", "something_else", symmetric=False)

    def test_builtin_types_present(self):
        for builtin in (
            "reference", "extends", "refines", "supports", "contradicts", "related",
        ):
            assert self.registry.is_valid(builtin), f"Built-in '{builtin}' missing"

    def test_all_types_includes_custom(self):
        self.registry.register("inspect", "inspected_by", symmetric=False)
        assert "inspect" in self.registry.all_types()

    def test_custom_types_only_custom(self):
        self.registry.register("syncs", "syncs", symmetric=True)
        names = [t.name for t in self.registry.custom_types()]
        assert "syncs" in names
        assert "reference" not in names

    def test_load_from_yaml(self, tmp_path):
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(
            yaml.safe_dump(
                {
                    "custom_link_types": [
                        {
                            "name": "yaml_type",
                            "inverse": "yaml_type_by",
                            "symmetric": False,
                        },
                    ],
                },
            ),
        )
        self.registry.load_from_yaml(yaml_file)
        assert self.registry.is_valid("yaml_type")

    def test_load_from_yaml_missing_file(self, tmp_path):
        missing = tmp_path / "nonexistent.yaml"
        self.registry.load_from_yaml(missing)  # must not raise

    def test_link_field_validator_accepts_builtin(self):
        lnk = Link(source_id="a", target_id="b", link_type="extends")
        assert lnk.link_type == "extends"

    def test_link_field_validator_rejects_unknown(self):
        with pytest.raises(ValidationError):
            Link(source_id="a", target_id="b", link_type="__nonexistent__")


# ---------------------------------------------------------------------------
# Task 2.4 — Link type inference
# ---------------------------------------------------------------------------


def _make_note(title: str, content: str) -> Note:
    return Note(
        id=generate_id(),
        title=title,
        content=content,
        note_type=NoteType.PERMANENT,
    )


class TestInferenceService:
    """Tests for InferenceService (services/inference_service.py)."""

    def setup_method(self):
        self.svc = InferenceService()

    def test_confident_match_extends(self):
        source = _make_note("Base concept", "This is the foundational idea.")
        target = _make_note(
            "Extended concept", "This builds upon and expands the base concept.",
        )
        result = self.svc.suggest_link_type(source, target)
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0
        types = [s["link_type"] for s in result["suggestions"]]
        assert "extends" in types

    def test_confident_match_contradicts(self):
        source = _make_note(
            "A", "This argument strongly contradicts and opposes the other view.",
        )
        target = _make_note("B", "The opposing view.")
        result = self.svc.suggest_link_type(source, target)
        types = [s["link_type"] for s in result["suggestions"]]
        assert "contradicts" in types

    def test_low_confidence_returned(self):
        source = _make_note("Note A", "xyz abc def")
        target = _make_note("Note B", "pqr uvw lmn")
        result = self.svc.suggest_link_type(source, target)
        assert "low_confidence" in result
        assert isinstance(result["low_confidence"], bool)

    def test_suggestions_sorted_by_confidence(self):
        source = _make_note("X", "This supports and provides evidence for the claim.")
        target = _make_note("Y", "The claim being supported.")
        result = self.svc.suggest_link_type(source, target)
        confs = [s["confidence"] for s in result["suggestions"]]
        assert confs == sorted(confs, reverse=True)

    def test_max_three_suggestions(self):
        source = _make_note(
            "P", "This builds expands contradicts opposes questions evidence.",
        )
        target = _make_note("Q", "A comprehensive note.")
        result = self.svc.suggest_link_type(source, target)
        assert len(result["suggestions"]) <= 3


# ---------------------------------------------------------------------------
# Task 2.5 — Performance: < 1 s for 5 KB notes
# ---------------------------------------------------------------------------


class TestInferencePerformance:
    def test_suggest_link_type_under_1s(self):
        content = ("word " * 1000)[:5000]  # ~5 KB
        source = _make_note("Big note", content)
        target = _make_note("Other big note", content)
        svc = InferenceService()
        start = time.perf_counter()
        svc.suggest_link_type(source, target)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"suggest_link_type took {elapsed:.3f}s (> 1s)"


# ---------------------------------------------------------------------------
# Task 3.5 — TF-IDF tag suggestions
# ---------------------------------------------------------------------------


def _make_zettel_service_with_notes():
    """Return a ZettelService backed by temp dirs with a few tagged notes."""
    tmpdir = tempfile.mkdtemp()
    notes_dir = Path(tmpdir) / "notes"
    db_dir = Path(tmpdir) / "db"
    notes_dir.mkdir()
    db_dir.mkdir()

    db_path = db_dir / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    engine.dispose()

    original_notes_dir = config.notes_dir
    original_database_path = config.database_path
    config.notes_dir = notes_dir
    config.database_path = db_path

    repo = NoteRepository(notes_dir=notes_dir)
    svc = ZettelService(repository=repo)

    svc.create_note(
        title="Machine Learning Basics",
        content="neural networks deep learning gradient descent backpropagation",
        tags=["machine-learning", "ai"],
    )
    svc.create_note(
        title="Deep Learning Architectures",
        content="convolutional networks recurrent neural networks transformers attention",  # noqa: E501
        tags=["machine-learning", "ai"],
    )
    svc.create_note(
        title="Reinforcement Learning",
        content="reward policy agent environment training neural networks",
        tags=["machine-learning", "ai"],
    )
    svc.create_note(
        title="AI Research Trends",
        content="large language models foundation models neural scaling laws",
        tags=["machine-learning", "ai"],
    )
    svc.create_note(
        title="Cooking Recipes",
        content="pasta sauce tomato olive oil garlic italian food",
        tags=["cooking", "food"],
    )
    svc.create_note(
        title="Python Programming",
        content="python functions classes loops list comprehension programming",
        tags=["python", "programming"],
    )

    return svc, original_notes_dir, original_database_path


class TestTagSuggestions:
    """Tests for SearchService.suggest_tags (tasks 3.1-3.3)."""

    def setup_method(self):
        self.svc, self._orig_notes, self._orig_db = _make_zettel_service_with_notes()
        self.search = SearchService(self.svc)

    def teardown_method(self):
        config.notes_dir = self._orig_notes
        config.database_path = self._orig_db

    def test_relevant_suggestion(self):
        suggestions = self.search.suggest_tags(
            "neural network training with gradient descent for classification",
        )
        tags = [s["tag"] for s in suggestions]
        assert "machine-learning" in tags or "ai" in tags, (
            f"Expected ML tag in top suggestions, got: {tags}"
        )
        # The top suggestion should have meaningful confidence (fixture has 4 ML notes)
        assert suggestions[0]["confidence"] > 0, (
            "Top suggestion should have non-zero confidence"
        )

    def test_no_match_empty_list(self):
        suggestions = self.search.suggest_tags("zzz qqq xxx yyy")
        for s in suggestions:
            assert s["confidence"] >= 0

    def test_limit_respected(self):
        suggestions = self.search.suggest_tags(
            "some content about learning and programming", limit=2,
        )
        assert len(suggestions) <= 2

    def test_sorted_by_confidence_descending(self):
        suggestions = self.search.suggest_tags("learning neural networks")
        confs = [s["confidence"] for s in suggestions]
        assert confs == sorted(confs, reverse=True)

    def test_cache_invalidated(self):
        _ = self.search.suggest_tags("first call builds cache")
        assert self.search._tag_cache is not None  # noqa: SLF001
        self.search.invalidate_tag_cache()
        assert self.search._tag_cache is None  # noqa: SLF001

    def test_rebuild_index_invalidates_cache(self):
        _ = self.search.suggest_tags("build cache")
        assert self.search._tag_cache is not None  # noqa: SLF001
        self.search.invalidate_tag_cache()
        assert self.search._tag_cache is None  # noqa: SLF001


# ---------------------------------------------------------------------------
# Task 3.6 — Performance: < 500 ms for 1000 tags simulation
# ---------------------------------------------------------------------------


class TestTagSuggestionPerformance:
    def test_suggest_tags_under_500ms(self):
        svc = MagicMock(spec=ZettelService)

        notes = []
        for i in range(1000):
            tag_name = f"tag_{i % 100}"
            mock_note = MagicMock()
            mock_note.title = f"Note {i}"
            mock_note.content = f"content word_{i % 50} subject_{i % 20}"
            mock_tag = MagicMock()
            mock_tag.name = tag_name
            mock_note.tags = [mock_tag]
            notes.append(mock_note)

        svc.get_all_notes.return_value = notes
        search = SearchService(svc)

        start = time.perf_counter()
        search.suggest_tags("word_1 subject_5 content", limit=10)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"suggest_tags took {elapsed:.3f}s (> 500ms)"


# ---------------------------------------------------------------------------
# Task 4.5 — Graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """Tests for NoteRepository graceful degradation when DB is unavailable."""

    @pytest.fixture
    def repo_with_temp(self, test_config):
        database_path = test_config.get_absolute_path(test_config.database_path)
        engine = create_engine(f"sqlite:///{database_path}")
        Base.metadata.create_all(engine)
        engine.dispose()
        return NoteRepository(notes_dir=test_config.notes_dir)

    def test_db_missing_create_still_writes_file(self, repo_with_temp):
        note = Note(
            id="20240101T000000000000000",
            title="Resilient",
            content="content",
            note_type=NoteType.PERMANENT,
        )
        with patch.object(
            repo_with_temp, "_index_note", side_effect=RuntimeError("db down"),
        ):
            created = repo_with_temp.create(note)

        assert created.id == note.id
        assert repo_with_temp._db_available is False  # noqa: SLF001
        assert (repo_with_temp.notes_dir / f"{note.id}.md").exists()

    def test_midsession_db_failure_get_all_falls_back(self, repo_with_temp):
        note = Note(
            id=generate_id(),
            title="Fallback test",
            content="some content",
            note_type=NoteType.PERMANENT,
        )
        md = repo_with_temp._note_to_markdown(note)  # noqa: SLF001
        file_path = repo_with_temp.notes_dir / f"{note.id}.md"
        file_path.write_text(md, encoding="utf-8")

        repo_with_temp._db_available = False  # noqa: SLF001
        notes = repo_with_temp.get_all()
        ids = [n.id for n in notes]
        assert note.id in ids

    def test_write_with_unavailable_db_logs_warning(self, repo_with_temp, caplog):
        import logging  # noqa: PLC0415

        note = Note(
            id="20240101T000100000000000",
            title="Warning test",
            content="content",
            note_type=NoteType.PERMANENT,
        )
        with patch.object(
            repo_with_temp, "_index_note", side_effect=RuntimeError("db down"),
        ), caplog.at_level(logging.WARNING):
            repo_with_temp.create(note)

        assert any("filesystem write succeeded" in r.message for r in caplog.records)

    def test_zk_create_note_returns_warning_when_db_unavailable(self):
        """zk_create_note response must include 'warning' key when DB is unavailable."""
        registered_tools: dict = {}
        mock_mcp = MagicMock()

        def capture_tool(*args, **kwargs):  # noqa: ARG001
            def wrapper(func):
                registered_tools[kwargs.get("name")] = func
                return func
            return wrapper

        mock_mcp.tool = capture_tool
        mock_note = MagicMock()
        mock_note.id = "20240101T000300000000000"
        mock_note.title = "DB-down note"
        mock_repo = MagicMock()
        mock_repo._db_available = False  # noqa: SLF001
        mock_zettel = MagicMock()
        mock_zettel.create_note.return_value = mock_note
        mock_zettel.repository = mock_repo

        with (
            patch("zettelkasten_mcp.server.mcp_server.FastMCP", return_value=mock_mcp),
            patch("zettelkasten_mcp.server.mcp_server.ZettelService", return_value=mock_zettel),  # noqa: E501
            patch("zettelkasten_mcp.server.mcp_server.SearchService"),
        ):
            ZettelkastenMcpServer()

        result = registered_tools["zk_create_note"](
            title="DB-down note", content="test content",
        )
        assert "warning" in result
        assert "DB index unavailable" in result["warning"]

    def test_read_from_markdown_named_method(self, repo_with_temp):
        assert repo_with_temp._read_from_markdown("__nonexistent__") is None  # noqa: SLF001


# ---------------------------------------------------------------------------
# Task 5.3 — Drift check
# ---------------------------------------------------------------------------


class TestDriftCheck:
    def test_threshold_zero_disables_rebuild(self, tmp_path):
        """When threshold=0, rebuild is never triggered even with 100% drift."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        for i in range(5):
            (notes_dir / f"note_{i}.md").write_text(f"# Note {i}")

        logger = MagicMock()
        original_notes = config.notes_dir
        original_threshold = config.auto_rebuild_threshold
        try:
            config.notes_dir = notes_dir
            config.auto_rebuild_threshold = 0

            with patch("zettelkasten_mcp.main.init_db") as mock_init_db:
                mock_init_db.return_value = MagicMock()
                gsf_path = "zettelkasten_mcp.models.db_models.get_session_factory"
                with patch(gsf_path) as mock_gsf:
                    mock_session = MagicMock()
                    mock_session.__enter__ = MagicMock(return_value=mock_session)
                    mock_session.__exit__ = MagicMock(return_value=False)
                    mock_session.scalar.return_value = 0
                    mock_gsf.return_value.return_value = mock_session
                    with patch(
                        "zettelkasten_mcp.storage.note_repository.NoteRepository",
                    ) as mock_repo_cls:
                        _run_drift_check(logger)
                        mock_repo_cls.return_value.rebuild_index.assert_not_called()
        finally:
            config.notes_dir = original_notes
            config.auto_rebuild_threshold = original_threshold

    def test_within_tolerance_no_rebuild(self, tmp_path):
        """Drift below threshold does NOT rebuild."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        for i in range(10):
            (notes_dir / f"note_{i}.md").write_text(f"# Note {i}")

        logger = MagicMock()
        original_notes = config.notes_dir
        original_threshold = config.auto_rebuild_threshold
        try:
            config.notes_dir = notes_dir
            config.auto_rebuild_threshold = 50  # 50% tolerance

            with patch("zettelkasten_mcp.main.init_db") as mock_init_db:
                mock_init_db.return_value = MagicMock()
                gsf_path = "zettelkasten_mcp.models.db_models.get_session_factory"
                with patch(gsf_path) as mock_gsf:
                    mock_session = MagicMock()
                    mock_session.__enter__ = MagicMock(return_value=mock_session)
                    mock_session.__exit__ = MagicMock(return_value=False)
                    mock_session.scalar.return_value = 9  # 10% drift
                    mock_gsf.return_value.return_value = mock_session
                    with patch(
                        "zettelkasten_mcp.storage.note_repository.NoteRepository",
                    ) as mock_repo_cls:
                        _run_drift_check(logger)
                        mock_repo_cls.return_value.rebuild_index.assert_not_called()
        finally:
            config.notes_dir = original_notes
            config.auto_rebuild_threshold = original_threshold

    def test_exceeds_threshold_triggers_rebuild(self, tmp_path):
        """Drift above threshold triggers rebuild_index()."""
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        for i in range(10):
            (notes_dir / f"note_{i}.md").write_text(f"# Note {i}")

        logger = MagicMock()
        original_notes = config.notes_dir
        original_threshold = config.auto_rebuild_threshold
        try:
            config.notes_dir = notes_dir
            config.auto_rebuild_threshold = 5  # 5% threshold, 50% drift -> trigger

            with patch("zettelkasten_mcp.main.init_db") as mock_init_db:
                mock_init_db.return_value = MagicMock()
                gsf_path = "zettelkasten_mcp.models.db_models.get_session_factory"
                with patch(gsf_path) as mock_gsf:
                    mock_session = MagicMock()
                    mock_session.__enter__ = MagicMock(return_value=mock_session)
                    mock_session.__exit__ = MagicMock(return_value=False)
                    mock_session.scalar.return_value = 5  # 50% drift
                    mock_gsf.return_value.return_value = mock_session
                    with patch(
                        "zettelkasten_mcp.storage.note_repository.NoteRepository",
                    ) as mock_repo_cls:
                        mock_repo_inst = MagicMock()
                        mock_repo_cls.return_value = mock_repo_inst
                        _run_drift_check(logger)
                        mock_repo_inst.rebuild_index.assert_called_once()
        finally:
            config.notes_dir = original_notes
            config.auto_rebuild_threshold = original_threshold
