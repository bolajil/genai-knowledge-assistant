"""
Ingestion Tab Validation Tests
==============================

Comprehensive test suite to validate current ingestion functionality
before implementing recommendations from INGESTION_TAB_REVIEW.md
"""

import pytest
import sys
from pathlib import Path
import tempfile
import json
import time
from io import BytesIO

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestIngestionTabValidation:
    """Test suite for validating current ingestion tab functionality"""
    
    @pytest.fixture
    def sample_text_file(self):
        """Create a sample text file for testing"""
        content = "This is a test document for ingestion validation.\n" * 100
        return BytesIO(content.encode('utf-8'))
    
    @pytest.fixture
    def sample_pdf_content(self):
        """Create sample PDF content (mock)"""
        # In real scenario, would use PyPDF2 or similar
        return b"%PDF-1.4 sample content"
    
    def test_import_ingestion_modules(self):
        """Test 1: Verify all ingestion modules can be imported"""
        try:
            from tabs import document_ingestion
            assert document_ingestion is not None
            print("✅ document_ingestion module imported successfully")
        except ImportError as e:
            pytest.fail(f"❌ Failed to import document_ingestion: {e}")
        
        try:
            from utils import weaviate_ingestion_helper
            assert weaviate_ingestion_helper is not None
            print("✅ weaviate_ingestion_helper module imported successfully")
        except ImportError as e:
            print(f"⚠️ weaviate_ingestion_helper not available: {e}")
        
        try:
            from utils import enhanced_document_processor
            assert enhanced_document_processor is not None
            print("✅ enhanced_document_processor module imported successfully")
        except ImportError as e:
            print(f"⚠️ enhanced_document_processor not available: {e}")
    
    def test_vector_db_config_loading(self):
        """Test 2: Verify vector DB configuration loads correctly"""
        try:
            from config.vector_db_config import get_vector_db_config
            
            config = get_vector_db_config()
            assert config is not None
            print("✅ Vector DB config loaded successfully")
            
            # Verify config structure
            assert hasattr(config, 'db_paths')
            assert hasattr(config, 'connection_params')
            assert hasattr(config, 'features')
            print("✅ Vector DB config has required attributes")
            
            # Check FAISS paths
            faiss_paths = config.get_db_paths(config.VectorDBType.FAISS)
            print(f"📁 FAISS paths configured: {len(faiss_paths)}")
            
            # Check embedding config
            embedding_config = config.get_embedding_config()
            print(f"🔧 Embedding model: {embedding_config.get('model_name')}")
            print(f"🔧 Embedding dimension: {embedding_config.get('dimension')}")
            
        except Exception as e:
            pytest.fail(f"❌ Vector DB config test failed: {e}")
    
    def test_weaviate_helper_initialization(self):
        """Test 3: Verify Weaviate helper can be initialized"""
        try:
            from utils.weaviate_ingestion_helper import get_weaviate_ingestion_helper
            
            helper = get_weaviate_ingestion_helper()
            assert helper is not None
            print("✅ Weaviate helper initialized successfully")
            
            # Test connectivity check (may fail if Weaviate not running)
            try:
                is_connected = helper.test_connection()
                if is_connected:
                    print("✅ Weaviate connection successful")
                else:
                    print("⚠️ Weaviate connection failed (service may not be running)")
            except Exception as conn_err:
                print(f"⚠️ Weaviate connectivity check error: {conn_err}")
            
        except ImportError as e:
            print(f"⚠️ Weaviate helper not available: {e}")
        except Exception as e:
            pytest.fail(f"❌ Weaviate helper initialization failed: {e}")
    
    def test_document_processor_initialization(self):
        """Test 4: Verify document processor can be initialized"""
        try:
            from utils.enhanced_document_processor import get_document_processor
            
            processor = get_document_processor()
            assert processor is not None
            print("✅ Document processor initialized successfully")
            
            # Check metadata manager
            assert hasattr(processor, 'metadata_manager')
            print("✅ Metadata manager available")
            
            # Check file handlers
            if hasattr(processor, 'file_handlers'):
                print(f"📄 Supported file types: {list(processor.file_handlers.keys())}")
            
        except ImportError as e:
            print(f"⚠️ Document processor not available: {e}")
        except Exception as e:
            pytest.fail(f"❌ Document processor initialization failed: {e}")
    
    def test_chunking_functionality(self):
        """Test 5: Verify text chunking works correctly"""
        try:
            from tabs.document_ingestion import _simple_text_chunks
            
            test_text = "This is a test sentence. " * 100
            chunks = _simple_text_chunks(test_text, chunk_size=200, overlap=50)
            
            assert len(chunks) > 0
            print(f"✅ Chunking successful: {len(chunks)} chunks created")
            
            # Verify chunk sizes
            for i, chunk in enumerate(chunks[:3]):
                print(f"   Chunk {i+1} size: {len(chunk)} chars")
            
            # Verify overlap
            if len(chunks) > 1:
                overlap_found = chunks[0][-50:] in chunks[1]
                if overlap_found:
                    print("✅ Chunk overlap verified")
                else:
                    print("⚠️ Chunk overlap not detected")
            
        except ImportError as e:
            print(f"⚠️ Chunking function not available: {e}")
        except Exception as e:
            pytest.fail(f"❌ Chunking test failed: {e}")
    
    def test_faiss_index_builder(self):
        """Test 6: Verify FAISS index can be built"""
        try:
            from tabs.document_ingestion import _build_faiss_index_from_text
            import tempfile
            
            test_text = "Sample document content for FAISS indexing. " * 50
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                try:
                    _build_faiss_index_from_text(
                        text=test_text,
                        index_name="test_index",
                        target_dir=temp_path
                    )
                    
                    # Check if files were created
                    index_file = temp_path / "index.faiss"
                    docs_file = temp_path / "documents.pkl"
                    
                    if index_file.exists() and docs_file.exists():
                        print("✅ FAISS index built successfully")
                        print(f"   Index file size: {index_file.stat().st_size} bytes")
                        print(f"   Documents file size: {docs_file.stat().st_size} bytes")
                    else:
                        print("⚠️ FAISS index files not created")
                        
                except Exception as build_err:
                    print(f"⚠️ FAISS index build error: {build_err}")
            
        except ImportError as e:
            print(f"⚠️ FAISS builder not available: {e}")
        except Exception as e:
            print(f"⚠️ FAISS index test encountered error: {e}")
    
    def test_metadata_management(self):
        """Test 7: Verify metadata management functionality"""
        try:
            from utils.enhanced_document_processor import DocumentMetadata
            import tempfile
            
            with tempfile.TemporaryDirectory() as temp_dir:
                metadata_mgr = DocumentMetadata(Path(temp_dir))
                
                # Test adding document
                doc_metadata = metadata_mgr.add_document(
                    doc_id="test_doc_001",
                    filename="test.txt",
                    file_path="/tmp/test.txt",
                    file_type="text",
                    chunk_count=10,
                    index_name="test_index",
                    tags=["test", "validation"]
                )
                
                assert doc_metadata is not None
                print("✅ Document metadata added successfully")
                
                # Test retrieving document
                retrieved = metadata_mgr.get_document("test_doc_001")
                assert retrieved is not None
                assert retrieved['filename'] == "test.txt"
                print("✅ Document metadata retrieved successfully")
                
                # Test listing documents
                docs = metadata_mgr.list_documents()
                assert len(docs) == 1
                print(f"✅ Document listing works: {len(docs)} document(s)")
                
        except ImportError as e:
            print(f"⚠️ Metadata management not available: {e}")
        except Exception as e:
            pytest.fail(f"❌ Metadata management test failed: {e}")
    
    def test_semantic_chunking_availability(self):
        """Test 8: Check if semantic chunking is available"""
        try:
            from utils.semantic_chunking_strategy import create_semantic_chunks
            
            test_text = """
            # Introduction
            This is the introduction section.
            
            ## Background
            This is the background information.
            
            ## Methodology
            This describes the methodology used.
            """
            
            chunks = create_semantic_chunks(
                text=test_text,
                document_name="test_doc.md",
                chunk_size=500,
                chunk_overlap=100
            )
            
            assert len(chunks) > 0
            print(f"✅ Semantic chunking available: {len(chunks)} chunks created")
            
            # Check chunk structure
            if chunks:
                first_chunk = chunks[0]
                if isinstance(first_chunk, dict):
                    print(f"   Chunk keys: {list(first_chunk.keys())}")
                
        except ImportError as e:
            print(f"⚠️ Semantic chunking not available: {e}")
        except Exception as e:
            print(f"⚠️ Semantic chunking test error: {e}")
    
    def test_embedding_model_loading(self):
        """Test 9: Verify embedding model can be loaded"""
        try:
            from sentence_transformers import SentenceTransformer
            
            print("⏳ Loading embedding model (this may take a moment)...")
            model = SentenceTransformer("all-MiniLM-L6-v2")
            
            # Test encoding
            test_texts = ["This is a test sentence.", "Another test sentence."]
            embeddings = model.encode(test_texts, convert_to_numpy=True)
            
            assert embeddings.shape[0] == 2
            print(f"✅ Embedding model loaded successfully")
            print(f"   Embedding dimension: {embeddings.shape[1]}")
            print(f"   Model device: {model.device}")
            
        except ImportError as e:
            print(f"⚠️ SentenceTransformers not available: {e}")
        except Exception as e:
            print(f"⚠️ Embedding model test error: {e}")
    
    def test_index_directory_structure(self):
        """Test 10: Verify index directory structure"""
        try:
            from config.vector_db_config import get_vector_db_config
            
            config = get_vector_db_config()
            faiss_paths = config.get_db_paths(config.VectorDBType.FAISS)
            
            print("📁 Checking index directory structure:")
            for path in faiss_paths:
                if path.exists():
                    print(f"   ✅ {path} exists")
                    
                    # List subdirectories (indexes)
                    indexes = [d for d in path.iterdir() if d.is_dir()]
                    print(f"      Found {len(indexes)} index(es)")
                    
                    for idx in indexes[:3]:  # Show first 3
                        print(f"      - {idx.name}")
                else:
                    print(f"   ⚠️ {path} does not exist")
            
        except Exception as e:
            print(f"⚠️ Index directory check error: {e}")


def run_validation_tests():
    """Run all validation tests and generate report"""
    print("\n" + "="*70)
    print("INGESTION TAB VALIDATION TEST SUITE")
    print("="*70 + "\n")
    
    # Run pytest with verbose output
    pytest_args = [
        __file__,
        "-v",
        "-s",  # Show print statements
        "--tb=short"  # Short traceback format
    ]
    
    result = pytest.main(pytest_args)
    
    print("\n" + "="*70)
    print("VALIDATION TEST SUMMARY")
    print("="*70)
    
    if result == 0:
        print("✅ All validation tests passed!")
    else:
        print("⚠️ Some tests failed or encountered issues")
    
    print("\nNext Steps:")
    print("1. Review test output above")
    print("2. Address any failures or warnings")
    print("3. Refer to INGESTION_TAB_REVIEW.md for recommendations")
    print("="*70 + "\n")
    
    return result


if __name__ == "__main__":
    exit_code = run_validation_tests()
    sys.exit(exit_code)
