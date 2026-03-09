"""
Unit tests for VaultMind embedding and vector store functionality.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch


class TestEmbeddings:
    """Test embedding generation."""
    
    @pytest.mark.unit
    def test_mock_embeddings_shape(self, mock_embeddings):
        arr = np.array(mock_embeddings)
        assert arr.shape == (4, 384)
    
    @pytest.mark.unit
    def test_embeddings_are_floats(self, mock_embeddings):
        assert all(isinstance(v, float) for row in mock_embeddings for v in row)
    
    @pytest.mark.slow
    def test_sentence_transformer_loads(self):
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        assert model is not None
    
    @pytest.mark.slow
    def test_embedding_generation(self, sample_chunks):
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(sample_chunks)
        assert embeddings.shape[0] == len(sample_chunks)
        assert embeddings.shape[1] == 384


class TestVectorStore:
    """Test vector store operations."""
    
    @pytest.mark.unit
    def test_faiss_import(self):
        import faiss
        assert hasattr(faiss, "IndexFlatL2")
    
    @pytest.mark.unit
    def test_faiss_index_creation(self):
        import faiss
        dimension = 384
        index = faiss.IndexFlatL2(dimension)
        assert index.d == dimension
        assert index.ntotal == 0
    
    @pytest.mark.unit
    def test_faiss_add_vectors(self, mock_embeddings):
        import faiss
        dimension = 384
        index = faiss.IndexFlatL2(dimension)
        vectors = np.array(mock_embeddings).astype("float32")
        index.add(vectors)
        assert index.ntotal == 4
    
    @pytest.mark.unit
    def test_faiss_search(self, mock_embeddings):
        import faiss
        dimension = 384
        index = faiss.IndexFlatL2(dimension)
        vectors = np.array(mock_embeddings).astype("float32")
        index.add(vectors)
        
        query = vectors[0:1]  # Search with first vector
        distances, indices = index.search(query, k=2)
        assert indices.shape == (1, 2)
        assert indices[0][0] == 0  # First result should be the query itself


class TestLangChainIntegration:
    """Test LangChain document handling."""
    
    @pytest.mark.unit
    def test_document_creation(self):
        from langchain_core.documents import Document
        doc = Document(page_content="Test content", metadata={"source": "test"})
        assert doc.page_content == "Test content"
        assert doc.metadata["source"] == "test"
    
    @pytest.mark.unit
    def test_text_splitter(self):
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
        text = "This is a test. " * 50
        chunks = splitter.split_text(text)
        assert len(chunks) > 1
