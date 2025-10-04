"""
Quick Multi-Vector System Test
Simple test to verify the multi-vector integration is working
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    """Test that all multi-vector components can be imported"""
    print("🧪 Testing Multi-Vector System Imports...")
    
    try:
        from utils.multi_vector_storage_interface import VectorStoreType, BaseVectorStore
        print("✅ Multi-vector interface imported successfully")
        
        from utils.multi_vector_storage_manager import get_multi_vector_manager
        print("✅ Multi-vector manager imported successfully")
        
        from utils.multi_vector_ui_components import render_vector_store_selector
        print("✅ Multi-vector UI components imported successfully")
        
        # Test adapter imports
        import utils.adapters
        print("✅ All vector store adapters imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_manager_initialization():
    """Test that the multi-vector manager can be initialized"""
    print("\n🧪 Testing Multi-Vector Manager Initialization...")
    
    try:
        from utils.multi_vector_storage_manager import get_multi_vector_manager
        manager = get_multi_vector_manager()
        print("✅ Multi-vector manager initialized successfully")
        
        # Test configuration loading
        config = manager.config
        print(f"✅ Configuration loaded with {len(config)} settings")
        
        return True
        
    except Exception as e:
        print(f"❌ Manager initialization failed: {e}")
        return False

def test_available_stores():
    """Test which vector stores are available"""
    print("\n🧪 Testing Available Vector Stores...")
    
    try:
        from utils.multi_vector_storage_interface import VectorStoreType
        
        available_stores = []
        for store_type in VectorStoreType:
            try:
                # Try to import the adapter
                if store_type.value == "weaviate":
                    from utils.adapters.weaviate_adapter import WeaviateAdapter
                elif store_type.value == "faiss":
                    from utils.adapters.faiss_adapter import FAISSAdapter
                elif store_type.value == "mock":
                    from utils.adapters.mock_adapter import MockAdapter
                elif store_type.value == "aws_opensearch":
                    from utils.adapters.aws_opensearch_adapter import AWSOpenSearchAdapter
                elif store_type.value == "azure_ai_search":
                    from utils.adapters.azure_ai_search_adapter import AzureAISearchAdapter
                elif store_type.value == "vertex_ai":
                    from utils.adapters.vertex_ai_adapter import VertexAIMatchingEngineAdapter
                elif store_type.value == "pinecone":
                    from utils.adapters.pinecone_adapter import PineconeAdapter
                elif store_type.value == "qdrant":
                    from utils.adapters.qdrant_adapter import QdrantAdapter
                elif store_type.value == "pgvector":
                    from utils.adapters.pgvector_adapter import PGVectorAdapter
                
                available_stores.append(store_type.value)
                print(f"✅ {store_type.value} adapter available")
                
            except Exception as e:
                print(f"⚠️ {store_type.value} adapter not available: {e}")
        
        print(f"\n📊 Summary: {len(available_stores)}/{len(VectorStoreType)} adapters available")
        return len(available_stores) > 0
        
    except Exception as e:
        print(f"❌ Store availability test failed: {e}")
        return False

def test_dashboard_integration():
    """Test that the dashboard can load the multi-vector tabs"""
    print("\n🧪 Testing Dashboard Integration...")
    
    try:
        # Test that the multi-vector tabs can be imported
        from tabs.multi_vector_document_ingestion import render_multi_vector_document_ingestion
        print("✅ Multi-vector document ingestion tab imported")
        
        from tabs.multi_vector_query_assistant import render_multi_vector_query_assistant
        print("✅ Multi-vector query assistant tab imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Dashboard integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 VaultMind Multi-Vector System Quick Test")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Manager Initialization", test_manager_initialization),
        ("Available Stores", test_available_stores),
        ("Dashboard Integration", test_dashboard_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Multi-vector system is ready.")
        print("\n💡 Next steps:")
        print("1. Restart your Streamlit app")
        print("2. Look for the new multi-vector tabs")
        print("3. Configure your preferred vector stores")
    else:
        print("⚠️ Some tests failed. Check the errors above.")
        print("\n💡 Troubleshooting:")
        print("1. Install missing dependencies: pip install -r requirements-multi-vector.txt")
        print("2. Check your Python environment")
        print("3. Verify file permissions")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
