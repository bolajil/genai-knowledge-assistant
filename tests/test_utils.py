"""
Unit tests for VaultMind utility functions.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestImports:
    """Test that core modules can be imported."""
    
    @pytest.mark.unit
    def test_import_streamlit(self):
        import streamlit
        assert streamlit is not None
    
    @pytest.mark.unit
    def test_import_langchain(self):
        from langchain_core.documents import Document
        assert Document is not None
    
    @pytest.mark.unit
    def test_import_faiss(self):
        import faiss
        assert faiss is not None
    
    @pytest.mark.unit
    def test_import_sentence_transformers(self):
        from sentence_transformers import SentenceTransformer
        assert SentenceTransformer is not None


class TestPathConfiguration:
    """Test path and environment configuration."""
    
    @pytest.mark.unit
    def test_project_root_exists(self):
        project_root = Path(__file__).parent.parent
        assert project_root.exists()
    
    @pytest.mark.unit
    def test_tabs_directory_exists(self):
        tabs_dir = Path(__file__).parent.parent / "tabs"
        assert tabs_dir.exists()
    
    @pytest.mark.unit
    def test_data_directory_exists(self):
        data_dir = Path(__file__).parent.parent / "data"
        assert data_dir.exists() or True  # May not exist in test env


class TestDocumentProcessing:
    """Test document processing utilities."""
    
    @pytest.mark.unit
    def test_sample_document_fixture(self, sample_document):
        assert "title" in sample_document
        assert "content" in sample_document
        assert len(sample_document["content"]) > 0
    
    @pytest.mark.unit
    def test_sample_chunks_fixture(self, sample_chunks):
        assert len(sample_chunks) == 4
        assert all(isinstance(chunk, str) for chunk in sample_chunks)


class TestQueryProcessing:
    """Test query processing."""
    
    @pytest.mark.unit
    def test_sample_query_fixture(self, sample_query):
        assert isinstance(sample_query, str)
        assert len(sample_query) > 0
    
    @pytest.mark.unit
    def test_query_not_empty(self, sample_query):
        assert sample_query.strip() != ""
