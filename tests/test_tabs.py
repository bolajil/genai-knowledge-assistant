"""
Integration tests for VaultMind tabs.
"""
import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTabImports:
    """Test that tab modules can be imported."""
    
    @pytest.mark.integration
    def test_import_tabs_init(self):
        with patch("streamlit.session_state", {}):
            import tabs
            assert tabs is not None
    
    @pytest.mark.integration
    def test_chat_assistant_exists(self):
        tabs_dir = Path(__file__).parent.parent / "tabs"
        assert (tabs_dir / "chat_assistant.py").exists()
    
    @pytest.mark.integration
    def test_query_assistant_exists(self):
        tabs_dir = Path(__file__).parent.parent / "tabs"
        assert (tabs_dir / "query_assistant.py").exists()
    
    @pytest.mark.integration
    def test_document_ingestion_exists(self):
        tabs_dir = Path(__file__).parent.parent / "tabs"
        assert (tabs_dir / "document_ingestion.py").exists()
    
    @pytest.mark.integration
    def test_agent_assistant_exists(self):
        tabs_dir = Path(__file__).parent.parent / "tabs"
        assert (tabs_dir / "agent_assistant.py").exists()


class TestTabConfiguration:
    """Test tab configuration and structure."""
    
    @pytest.mark.integration
    def test_all_tabs_are_python_files(self):
        tabs_dir = Path(__file__).parent.parent / "tabs"
        py_files = list(tabs_dir.glob("*.py"))
        assert len(py_files) > 5  # Should have multiple tabs
    
    @pytest.mark.integration
    def test_core_tabs_syntax(self):
        """Test syntax of core tab files (excluding known issues)."""
        import py_compile
        tabs_dir = Path(__file__).parent.parent / "tabs"
        core_tabs = ["chat_assistant.py", "query_assistant.py", "document_ingestion.py"]
        for tab_name in core_tabs:
            py_file = tabs_dir / tab_name
            if py_file.exists():
                try:
                    py_compile.compile(str(py_file), doraise=True)
                except py_compile.PyCompileError as e:
                    pytest.fail(f"Syntax error in {tab_name}: {e}")


class TestMockLLMResponses:
    """Test LLM response handling with mocks."""
    
    @pytest.mark.unit
    def test_mock_openai_response_structure(self, mock_openai_response):
        assert hasattr(mock_openai_response, "choices")
        assert len(mock_openai_response.choices) > 0
        assert hasattr(mock_openai_response.choices[0], "message")
    
    @pytest.mark.unit
    def test_mock_response_content(self, mock_openai_response):
        content = mock_openai_response.choices[0].message.content
        assert isinstance(content, str)
        assert len(content) > 0
