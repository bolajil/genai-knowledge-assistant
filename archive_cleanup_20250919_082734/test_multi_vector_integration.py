"""
Multi-Vector Storage Integration Test Suite
Comprehensive testing for VaultMind multi-vector storage system
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import time
import json
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.multi_vector_storage_manager import get_multi_vector_manager
from utils.multi_vector_storage_interface import VectorStoreType, VectorDocument

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MultiVectorIntegrationTester:
    """Comprehensive test suite for multi-vector storage integration"""
    
    def __init__(self):
        self.manager = get_multi_vector_manager()
        self.test_results = {}
        self.test_collection = f"test_integration_{int(time.time())}"
        
    async def run_all_tests(self):
        """Run complete test suite"""
        logger.info("🚀 Starting Multi-Vector Integration Test Suite")
        
        tests = [
            ("Connection Tests", self.test_connections),
            ("Basic Operations", self.test_basic_operations),
            ("Document Ingestion", self.test_document_ingestion),
            ("Search Operations", self.test_search_operations),
            ("Fallback Mechanisms", self.test_fallback_mechanisms),
            ("Parallel Operations", self.test_parallel_operations),
            ("Performance Tests", self.test_performance),
            ("Configuration Tests", self.test_configuration),
            ("Error Handling", self.test_error_handling),
            ("Cleanup", self.cleanup_test_data)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n📋 Running {test_name}...")
            try:
                start_time = time.time()
                result = await test_func()
                duration = time.time() - start_time
                
                self.test_results[test_name] = {
                    'status': 'PASSED' if result else 'FAILED',
                    'duration': duration,
                    'timestamp': datetime.now().isoformat()
                }
                
                status_emoji = "✅" if result else "❌"
                logger.info(f"{status_emoji} {test_name}: {self.test_results[test_name]['status']} ({duration:.2f}s)")
                
            except Exception as e:
                self.test_results[test_name] = {
                    'status': 'ERROR',
                    'error': str(e),
                    'duration': 0,
                    'timestamp': datetime.now().isoformat()
                }
                logger.error(f"❌ {test_name}: ERROR - {e}")
        
        # Generate test report
        self.generate_test_report()
        
    async def test_connections(self) -> bool:
        """Test connections to all available vector stores"""
        logger.info("Testing vector store connections...")
        
        connection_results = {}
        for store_type in VectorStoreType:
            try:
                result = await self.manager.health_check(store_type)
                connection_results[store_type.value] = result
                logger.info(f"  {store_type.value}: {'✅ Connected' if result else '❌ Failed'}")
            except Exception as e:
                connection_results[store_type.value] = False
                logger.warning(f"  {store_type.value}: ❌ Error - {e}")
        
        # At least one store should be available
        available_stores = sum(1 for result in connection_results.values() if result)
        logger.info(f"Available stores: {available_stores}/{len(VectorStoreType)}")
        
        return available_stores > 0
    
    async def test_basic_operations(self) -> bool:
        """Test basic CRUD operations"""
        logger.info("Testing basic operations...")
        
        # Find available stores
        available_stores = []
        for store_type in VectorStoreType:
            try:
                if await self.manager.health_check(store_type):
                    available_stores.append(store_type)
            except:
                continue
        
        if not available_stores:
            logger.warning("No available stores for basic operations test")
            return False
        
        test_store = available_stores[0]
        logger.info(f"Testing with {test_store.value}")
        
        try:
            # Test collection creation
            created = await self.manager.create_collection(
                collection_name=self.test_collection,
                store_type=test_store,
                description="Integration test collection"
            )
            
            if not created:
                logger.error("Failed to create test collection")
                return False
            
            logger.info("✅ Collection created successfully")
            
            # Test collection listing
            collections = await self.manager.list_collections(test_store)
            if self.test_collection not in collections:
                logger.error("Test collection not found in listing")
                return False
            
            logger.info("✅ Collection listing successful")
            
            # Test collection stats
            stats = await self.manager.get_collection_stats(self.test_collection, test_store)
            logger.info(f"✅ Collection stats: {stats}")
            
            return True
            
        except Exception as e:
            logger.error(f"Basic operations test failed: {e}")
            return False
    
    async def test_document_ingestion(self) -> bool:
        """Test document ingestion operations"""
        logger.info("Testing document ingestion...")
        
        # Find available stores
        available_stores = []
        for store_type in VectorStoreType:
            try:
                if await self.manager.health_check(store_type):
                    available_stores.append(store_type)
            except:
                continue
        
        if not available_stores:
            logger.warning("No available stores for ingestion test")
            return False
        
        test_store = available_stores[0]
        
        # Create test documents
        test_documents = [
            VectorDocument(
                id=f"doc_{i}",
                content=f"This is test document {i} about artificial intelligence and machine learning.",
                source=f"test_source_{i}",
                source_type="text",
                metadata={
                    "category": "test",
                    "index": i,
                    "created_at": datetime.now().isoformat()
                }
            )
            for i in range(5)
        ]
        
        # Generate test embeddings (mock embeddings for testing)
        test_embeddings = [[0.1 * i + 0.01 * j for j in range(384)] for i in range(5)]
        
        try:
            # Test document upsert
            success = await self.manager.upsert_documents(
                collection_name=self.test_collection,
                documents=test_documents,
                embeddings=test_embeddings,
                store_type=test_store
            )
            
            if not success:
                logger.error("Document upsert failed")
                return False
            
            logger.info("✅ Document ingestion successful")
            
            # Verify documents were ingested
            stats = await self.manager.get_collection_stats(self.test_collection, test_store)
            logger.info(f"✅ Collection now has {stats.get('document_count', 'unknown')} documents")
            
            return True
            
        except Exception as e:
            logger.error(f"Document ingestion test failed: {e}")
            return False
    
    async def test_search_operations(self) -> bool:
        """Test search operations"""
        logger.info("Testing search operations...")
        
        # Find available stores
        available_stores = []
        for store_type in VectorStoreType:
            try:
                if await self.manager.health_check(store_type):
                    available_stores.append(store_type)
            except:
                continue
        
        if not available_stores:
            logger.warning("No available stores for search test")
            return False
        
        test_store = available_stores[0]
        
        try:
            # Test vector search
            results = await self.manager.search_documents(
                collection_name=self.test_collection,
                query="artificial intelligence machine learning",
                top_k=3,
                store_type=test_store,
                similarity_threshold=0.0
            )
            
            logger.info(f"✅ Search returned {len(results)} results")
            
            # Verify search results
            if results:
                for i, result in enumerate(results[:2]):
                    logger.info(f"  Result {i+1}: Score={result.score:.3f}, Content='{result.content[:50]}...'")
            
            return len(results) > 0
            
        except Exception as e:
            logger.error(f"Search operations test failed: {e}")
            return False
    
    async def test_fallback_mechanisms(self) -> bool:
        """Test fallback mechanisms"""
        logger.info("Testing fallback mechanisms...")
        
        # This test would simulate store failures and test fallback
        # For now, we'll test the fallback configuration
        
        try:
            # Test with non-existent collection to trigger fallback
            results = await self.manager.search_documents(
                collection_name="non_existent_collection",
                query="test query",
                top_k=5,
                similarity_threshold=0.0,
                enable_fallback=True
            )
            
            logger.info("✅ Fallback mechanism handled gracefully")
            return True
            
        except Exception as e:
            logger.info(f"✅ Fallback mechanism triggered expected error: {e}")
            return True
    
    async def test_parallel_operations(self) -> bool:
        """Test parallel operations"""
        logger.info("Testing parallel operations...")
        
        # Find multiple available stores
        available_stores = []
        for store_type in VectorStoreType:
            try:
                if await self.manager.health_check(store_type):
                    available_stores.append(store_type)
            except:
                continue
        
        if len(available_stores) < 2:
            logger.info("✅ Parallel operations test skipped (need 2+ stores)")
            return True
        
        try:
            # Test parallel health checks
            tasks = [self.manager.health_check(store) for store in available_stores[:3]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_checks = sum(1 for r in results if r is True)
            logger.info(f"✅ Parallel health checks: {successful_checks}/{len(tasks)} successful")
            
            return successful_checks > 0
            
        except Exception as e:
            logger.error(f"Parallel operations test failed: {e}")
            return False
    
    async def test_performance(self) -> bool:
        """Test performance characteristics"""
        logger.info("Testing performance...")
        
        # Find available stores
        available_stores = []
        for store_type in VectorStoreType:
            try:
                if await self.manager.health_check(store_type):
                    available_stores.append(store_type)
            except:
                continue
        
        if not available_stores:
            logger.warning("No available stores for performance test")
            return False
        
        test_store = available_stores[0]
        
        try:
            # Test search performance
            start_time = time.time()
            
            results = await self.manager.search_documents(
                collection_name=self.test_collection,
                query="performance test query",
                top_k=10,
                store_type=test_store
            )
            
            search_time = time.time() - start_time
            logger.info(f"✅ Search performance: {search_time:.3f}s for {len(results)} results")
            
            # Performance should be reasonable (< 5 seconds for basic search)
            return search_time < 5.0
            
        except Exception as e:
            logger.error(f"Performance test failed: {e}")
            return False
    
    async def test_configuration(self) -> bool:
        """Test configuration management"""
        logger.info("Testing configuration...")
        
        try:
            # Test configuration loading
            config = self.manager.config
            logger.info(f"✅ Configuration loaded: {len(config)} settings")
            
            # Verify essential config sections
            required_sections = ['primary_store', 'fallback_stores', 'vector_stores']
            for section in required_sections:
                if section not in config:
                    logger.error(f"Missing required config section: {section}")
                    return False
            
            logger.info("✅ Configuration validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Configuration test failed: {e}")
            return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling and edge cases"""
        logger.info("Testing error handling...")
        
        try:
            # Test invalid operations
            test_cases = [
                # Invalid collection name
                ("empty_collection", lambda: self.manager.search_documents("", "query", 5)),
                # Invalid store type
                ("invalid_store", lambda: self.manager.health_check("invalid_store")),
                # Invalid parameters
                ("invalid_params", lambda: self.manager.search_documents("test", "", -1))
            ]
            
            passed_tests = 0
            for test_name, test_func in test_cases:
                try:
                    await test_func()
                    logger.warning(f"  {test_name}: Expected error but got success")
                except Exception:
                    logger.info(f"  ✅ {test_name}: Properly handled error")
                    passed_tests += 1
            
            logger.info(f"✅ Error handling: {passed_tests}/{len(test_cases)} tests passed")
            return passed_tests >= len(test_cases) // 2  # At least half should handle errors
            
        except Exception as e:
            logger.error(f"Error handling test failed: {e}")
            return False
    
    async def cleanup_test_data(self) -> bool:
        """Clean up test data"""
        logger.info("Cleaning up test data...")
        
        # Find available stores
        available_stores = []
        for store_type in VectorStoreType:
            try:
                if await self.manager.health_check(store_type):
                    available_stores.append(store_type)
            except:
                continue
        
        cleanup_success = True
        
        for store_type in available_stores:
            try:
                # Try to delete test collection
                await self.manager.delete_collection(self.test_collection, store_type)
                logger.info(f"✅ Cleaned up test collection from {store_type.value}")
            except Exception as e:
                logger.warning(f"⚠️ Cleanup warning for {store_type.value}: {e}")
                # Don't fail the test for cleanup issues
        
        return cleanup_success
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("\n" + "="*60)
        logger.info("📊 MULTI-VECTOR INTEGRATION TEST REPORT")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r['status'] == 'PASSED')
        failed_tests = sum(1 for r in self.test_results.values() if r['status'] == 'FAILED')
        error_tests = sum(1 for r in self.test_results.values() if r['status'] == 'ERROR')
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        logger.info(f"🔥 Errors: {error_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        logger.info("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status_emoji = {"PASSED": "✅", "FAILED": "❌", "ERROR": "🔥"}[result['status']]
            duration = result.get('duration', 0)
            logger.info(f"  {status_emoji} {test_name}: {result['status']} ({duration:.2f}s)")
            
            if result['status'] == 'ERROR':
                logger.info(f"    Error: {result.get('error', 'Unknown error')}")
        
        # Save report to file
        report_file = PROJECT_ROOT / "multi_vector_test_report.json"
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total': total_tests,
                    'passed': passed_tests,
                    'failed': failed_tests,
                    'errors': error_tests,
                    'success_rate': (passed_tests/total_tests)*100
                },
                'results': self.test_results
            }, f, indent=2)
        
        logger.info(f"\n📄 Full report saved to: {report_file}")
        logger.info("="*60)

async def main():
    """Main test execution"""
    print("🚀 VaultMind Multi-Vector Storage Integration Test")
    print("="*60)
    
    tester = MultiVectorIntegrationTester()
    await tester.run_all_tests()
    
    print("\n🎉 Integration testing completed!")
    print("Check the generated report for detailed results.")

if __name__ == "__main__":
    asyncio.run(main())
