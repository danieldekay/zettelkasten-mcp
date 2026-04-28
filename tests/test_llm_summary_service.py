"""Tests for LLMSummaryService (Azure OpenAI integration)."""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from zettelkasten_mcp.config import config
from zettelkasten_mcp.services.llm_summary_service import LLMSummaryService


@pytest.fixture(autouse=True)
def reset_llm_state():
    """Ensure each test starts with a clean config state."""
    original_enabled = config.llm_enable_summaries
    original_endpoint = config.azure_openai_endpoint
    original_model = config.llm_model
    yield
    config.llm_enable_summaries = original_enabled
    config.azure_openai_endpoint = original_endpoint
    config.llm_model = original_model


class TestLLMSummaryServiceIsEnabled:
    def test_disabled_when_flag_false(self):
        config.llm_enable_summaries = False
        config.azure_openai_endpoint = "https://example.openai.azure.com/"
        svc = LLMSummaryService()
        assert not svc.is_enabled()

    def test_disabled_when_endpoint_empty(self):
        config.llm_enable_summaries = True
        config.azure_openai_endpoint = ""
        svc = LLMSummaryService()
        assert not svc.is_enabled()

    def test_enabled_when_both_set(self):
        config.llm_enable_summaries = True
        config.azure_openai_endpoint = "https://example.openai.azure.com/"
        svc = LLMSummaryService()
        assert svc.is_enabled()


class TestLLMSummaryServiceGenerateSummary:
    def _make_mock_response(self, summary: str, keywords: list[str]) -> MagicMock:
        content = json.dumps({"summary": summary, "keywords": keywords})
        message = MagicMock()
        message.content = content
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]
        return response

    def test_generate_summary_returns_none_when_disabled(self):
        config.llm_enable_summaries = False
        config.azure_openai_endpoint = ""
        svc = LLMSummaryService()
        result = svc.generate_summary("Title", "Content")
        assert result is None

    def test_generate_summary_returns_dict_on_success(self):
        config.llm_enable_summaries = True
        config.azure_openai_endpoint = "https://example.openai.azure.com/"

        mock_response = self._make_mock_response(
            "A helpful English summary.", ["keyword1", "keyword2"]
        )

        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.AzureOpenAI.return_value = mock_client

        mock_identity = MagicMock()
        mock_identity.DefaultAzureCredential.return_value = MagicMock()
        mock_identity.get_bearer_token_provider.return_value = MagicMock()

        with patch.dict(sys.modules, {"openai": mock_openai, "azure.identity": mock_identity}):
            svc = LLMSummaryService()
            svc._client = None  # noqa: SLF001 — reset lazy-init for test
            result = svc.generate_summary("My Note", "Note body content.", ["tag1"])

        assert result is not None
        assert result["summary"] == "A helpful English summary."
        assert result["keywords"] == ["keyword1", "keyword2"]

    def test_generate_summary_returns_none_on_api_exception(self):
        config.llm_enable_summaries = True
        config.azure_openai_endpoint = "https://example.openai.azure.com/"

        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API error")
        mock_openai.AzureOpenAI.return_value = mock_client

        mock_identity = MagicMock()

        with patch.dict(sys.modules, {"openai": mock_openai, "azure.identity": mock_identity}):
            svc = LLMSummaryService()
            svc._client = None  # noqa: SLF001
            result = svc.generate_summary("My Note", "Content", [])

        assert result is None

    def test_generate_summary_returns_none_on_invalid_json(self):
        config.llm_enable_summaries = True
        config.azure_openai_endpoint = "https://example.openai.azure.com/"

        message = MagicMock()
        message.content = "not valid json {{{"
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]

        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = response
        mock_openai.AzureOpenAI.return_value = mock_client

        mock_identity = MagicMock()

        with patch.dict(sys.modules, {"openai": mock_openai, "azure.identity": mock_identity}):
            svc = LLMSummaryService()
            svc._client = None  # noqa: SLF001
            result = svc.generate_summary("My Note", "Content", [])

        assert result is None

    def test_keywords_normalised_to_lowercase(self):
        config.llm_enable_summaries = True
        config.azure_openai_endpoint = "https://example.openai.azure.com/"

        mock_response = self._make_mock_response(
            "Summary text.", ["Python", "MachineLearning", "AI"]
        )

        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.AzureOpenAI.return_value = mock_client

        mock_identity = MagicMock()

        with patch.dict(sys.modules, {"openai": mock_openai, "azure.identity": mock_identity}):
            svc = LLMSummaryService()
            svc._client = None  # noqa: SLF001
            result = svc.generate_summary("Note", "Content", [])

        assert result is not None
        assert all(k == k.lower() for k in result["keywords"])

    def test_import_error_returns_none_gracefully(self):
        """If azure-identity / openai packages are missing, generate_summary returns None."""
        config.llm_enable_summaries = True
        config.azure_openai_endpoint = "https://example.openai.azure.com/"

        svc = LLMSummaryService()
        # Force _get_client to hit the ImportError path
        with patch.dict("sys.modules", {"azure.identity": None, "openai": None}):
            result = svc.generate_summary("Title", "Content", [])

        # The service should degrade gracefully
        assert result is None
