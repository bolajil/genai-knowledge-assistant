"""
Pytest configuration and fixtures for VaultMind tests.
"""
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set test environment
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")


@pytest.fixture
def sample_document():
    """Sample document for testing ingestion."""
    return {
        "title": "Test Document",
        "content": "This is a test document with sample content for testing purposes.",
        "metadata": {
            "source": "test",
            "author": "Test Author",
            "date": "2026-01-01"
        }
    }


@pytest.fixture
def sample_query():
    """Sample query for testing search."""
    return "What is the main purpose of this document?"


@pytest.fixture
def sample_chunks():
    """Sample text chunks for testing embeddings."""
    return [
        "VaultMind is an enterprise knowledge assistant.",
        "It supports multiple vector databases including FAISS and Weaviate.",
        "The system uses LangGraph for autonomous reasoning.",
        "Document quality control detects OCR errors automatically."
    ]


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = "This is a mock response from the LLM."
    return mock


@pytest.fixture
def mock_embeddings():
    """Mock embedding vectors."""
    import numpy as np
    return np.random.rand(4, 384).tolist()  # 4 chunks, 384 dimensions


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit session state and functions."""
    with patch("streamlit.session_state", {}):
        with patch("streamlit.write"):
            with patch("streamlit.error"):
                with patch("streamlit.success"):
                    yield


@pytest.fixture
def temp_upload_dir(tmp_path):
    """Temporary upload directory for testing."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return upload_dir


@pytest.fixture
def temp_index_dir(tmp_path):
    """Temporary index directory for testing."""
    index_dir = tmp_path / "faiss_index"
    index_dir.mkdir()
    return index_dir


# Markers for different test types
def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external deps)")
    config.addinivalue_line("markers", "integration: Integration tests (may need external services)")
    config.addinivalue_line("markers", "slow: Slow tests (embedding generation, etc.)")
    config.addinivalue_line("markers", "requires_api: Tests requiring real API keys")
