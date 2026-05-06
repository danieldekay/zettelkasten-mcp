"""Tests for Tag normalisation and strict-mode enforcement."""

import pytest

from zettelkasten_mcp.models.schema import Tag, _normalise_tag_name, set_strict_tag_mode


class TestNormaliseTagName:
    """Unit tests for the _normalise_tag_name helper."""

    def test_uppercase_becomes_lowercase(self):
        assert _normalise_tag_name("IO-psychology") == "io-psychology"

    def test_space_becomes_hyphen(self):
        assert _normalise_tag_name("LLM Prompts") == "llm-prompts"

    def test_dot_is_removed(self):
        assert _normalise_tag_name("SKILL.md") == "skill-md"

    def test_uppercase_word_lowercased(self):
        assert _normalise_tag_name("adversarial-AI") == "adversarial-ai"

    def test_space_between_short_words(self):
        assert _normalise_tag_name("The Q") == "the-q"

    def test_colon_and_space_removed(self):
        assert _normalise_tag_name("User story: Alice") == "user-story-alice"

    def test_leading_trailing_hyphens_stripped(self):
        assert _normalise_tag_name("  --bad--  ") == "bad"

    def test_underscore_becomes_hyphen(self):
        assert _normalise_tag_name("machine_learning") == "machine-learning"

    def test_multiple_spaces_collapse_to_one_hyphen(self):
        assert _normalise_tag_name("a  b") == "a-b"

    def test_already_canonical_unchanged(self):
        assert _normalise_tag_name("io-psychology") == "io-psychology"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            _normalise_tag_name("")

    def test_only_hyphens_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            _normalise_tag_name("---")

    def test_only_special_chars_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            _normalise_tag_name("!@#$%")


class TestTagConstruction:
    """Tag model normalises name on construction."""

    def test_uppercase_normalised(self):
        assert Tag(name="IO-psychology").name == "io-psychology"

    def test_space_normalised(self):
        assert Tag(name="LLM Prompts").name == "llm-prompts"

    def test_already_compliant_unchanged(self):
        assert Tag(name="machine-learning").name == "machine-learning"

    def test_str_returns_normalised_name(self):
        assert str(Tag(name="FTS5")) == "fts5"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            Tag(name="")


class TestStrictMode:
    """Tag construction in strict mode rejects non-canonical names."""

    def setup_method(self):
        set_strict_tag_mode(False)

    def teardown_method(self):
        set_strict_tag_mode(False)

    def test_strict_rejects_uppercase(self):
        set_strict_tag_mode(True)
        with pytest.raises(ValueError, match="not valid lowercase kebab-case"):
            Tag(name="IO-psychology")

    def test_strict_accepts_canonical(self):
        set_strict_tag_mode(True)
        tag = Tag(name="io-psychology")
        assert tag.name == "io-psychology"

    def test_strict_rejects_space(self):
        set_strict_tag_mode(True)
        with pytest.raises(ValueError, match="not valid lowercase kebab-case"):
            Tag(name="llm prompts")

    def test_non_strict_silently_normalises(self):
        set_strict_tag_mode(False)
        assert Tag(name="IO-psychology").name == "io-psychology"

    def test_mode_reset_between_tests(self):
        set_strict_tag_mode(True)
        set_strict_tag_mode(False)
        # Should not raise in non-strict mode
        assert Tag(name="MCP").name == "mcp"
