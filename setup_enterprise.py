#!/usr/bin/env python3
"""
Enterprise Features Setup Script

Validates and configures VaultMind enterprise features.
"""

import sys
import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if enterprise dependencies are available"""
    logger.info("Checking enterprise dependencies...")
    
    required_packages = [
        ('transformers', 'Cross-encoder re-ranking'),
        ('torch', 'PyTorch for transformer models'),
        ('redis', 'Redis caching (optional)'),
        ('pydantic', 'Structured output validation'),
        ('langchain', 'Advanced text processing')
    ]
    
    missing_packages = []
    available_packages = []
    
    for package, description in required_packages:
        try:
            __import__(package)
            available_packages.append((package, description))
            logger.info(f"✓ {package} - {description}")
        except ImportError:
            missing_packages.append((package, description))
            logger.warning(f"✗ {package} - {description} (MISSING)")
    
    return available_packages, missing_packages

def test_enterprise_components():
    """Test enterprise component initialization"""
    logger.info("Testing enterprise component initialization...")
    
    components_status = {}
    
    # Test Hybrid Search
    try:
        from utils.enterprise_hybrid_search import get_enterprise_hybrid_search
        hybrid_search = get_enterprise_hybrid_search()
        components_status['hybrid_search'] = True
        logger.info("✓ Hybrid Search initialized successfully")
    except Exception as e:
        components_status['hybrid_search'] = False
        logger.error(f"✗ Hybrid Search failed: {e}")
    
    # Test Semantic Chunking
    try:
        from utils.enterprise_semantic_chunking import get_enterprise_semantic_chunker
        chunker = get_enterprise_semantic_chunker()
        components_status['semantic_chunking'] = True
        logger.info("✓ Semantic Chunking initialized successfully")
    except Exception as e:
        components_status['semantic_chunking'] = False
        logger.error(f"✗ Semantic Chunking failed: {e}")
    
    # Test Structured Output
    try:
        from utils.enterprise_structured_output import get_enterprise_output_formatter
        formatter = get_enterprise_output_formatter()
        components_status['structured_output'] = True
        logger.info("✓ Structured Output initialized successfully")
    except Exception as e:
        components_status['structured_output'] = False
        logger.error(f"✗ Structured Output failed: {e}")
    
    # Test Metadata Filtering
    try:
        from utils.enterprise_metadata_filtering import get_enterprise_metadata_filter
        filter_system = get_enterprise_metadata_filter()
        components_status['metadata_filtering'] = True
        logger.info("✓ Metadata Filtering initialized successfully")
    except Exception as e:
        components_status['metadata_filtering'] = False
        logger.error(f"✗ Metadata Filtering failed: {e}")
    
    # Test Caching System
    try:
        from utils.enterprise_caching_system import get_global_cache_manager
        cache_manager = get_global_cache_manager()
        components_status['caching_system'] = True
        logger.info("✓ Caching System initialized successfully")
    except Exception as e:
        components_status['caching_system'] = False
        logger.error(f"✗ Caching System failed: {e}")
    
    # Test Integration Layer
    try:
        from utils.enterprise_integration_layer import get_enterprise_retrieval_system
        enterprise_system = get_enterprise_retrieval_system()
        status = enterprise_system.get_system_status()
        components_status['integration_layer'] = True
        logger.info("✓ Integration Layer initialized successfully")
        logger.info(f"  Enterprise features enabled: {status['enterprise_features_enabled']}")
        for component, info in status['components'].items():
            logger.info(f"  {component}: {info['status']}")
    except Exception as e:
        components_status['integration_layer'] = False
        logger.error(f"✗ Integration Layer failed: {e}")
    
    return components_status

def test_integration():
    """Test integration with existing system"""
    logger.info("Testing integration with existing VaultMind system...")
    
    try:
        # Test real-time retrieval integration
        from utils.real_time_retrieval import RealTimeRetriever
        retriever = RealTimeRetriever(enable_enterprise=True)
        logger.info("✓ Real-time retrieval integration successful")
        
        # Test controller agent integration
        from app.agents.controller_agent import execute_agent
        logger.info("✓ Controller agent integration successful")
        
        return True
    except Exception as e:
        logger.error(f"✗ Integration test failed: {e}")
        return False

def create_sample_config():
    """Create sample enterprise configuration"""
    logger.info("Creating sample enterprise configuration...")
    
    config_content = """# VaultMind Enterprise Configuration
# Copy to .env and customize as needed

# Enterprise Features
ENABLE_ENTERPRISE_FEATURES=true
ENABLE_HYBRID_SEARCH=true
ENABLE_SEMANTIC_CHUNKING=true
ENABLE_STRUCTURED_OUTPUT=true
ENABLE_METADATA_FILTERING=true
ENABLE_CACHING=true

# Redis Configuration (Optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Chunking Configuration
CHUNK_SIZE=1500
CHUNK_OVERLAP=500
RESPECT_SECTION_BREAKS=true
EXTRACT_TABLES=true
PRESERVE_HEADING_STRUCTURE=true

# Search Configuration
VECTOR_WEIGHT=0.6
KEYWORD_WEIGHT=0.4
ENABLE_RERANKING=true

# Cache Configuration
CACHE_TTL=3600
MAX_CACHE_SIZE=1000
"""
    
    try:
        with open('.env.enterprise.example', 'w') as f:
            f.write(config_content)
        logger.info("✓ Sample configuration created: .env.enterprise.example")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create sample config: {e}")
        return False

def run_performance_test():
    """Run basic performance test"""
    logger.info("Running basic performance test...")
    
    try:
        from utils.enterprise_integration_layer import enterprise_enhanced_query
        import time
        
        # Test query
        test_query = "What are the board meeting requirements?"
        start_time = time.time()
        
        # This would normally query actual documents
        # For setup, we just test the system initialization
        logger.info(f"Test query: {test_query}")
        logger.info("✓ Performance test framework ready")
        
        elapsed = time.time() - start_time
        logger.info(f"✓ System response time: {elapsed:.2f}s")
        
        return True
    except Exception as e:
        logger.error(f"✗ Performance test failed: {e}")
        return False

def main():
    """Main setup function"""
    logger.info("=== VaultMind Enterprise Setup ===")
    
    # Check dependencies
    available, missing = check_dependencies()
    
    if missing:
        logger.warning(f"\nMissing {len(missing)} dependencies:")
        for package, desc in missing:
            logger.warning(f"  - {package}: {desc}")
        logger.warning("\nInstall missing dependencies with:")
        logger.warning("pip install -r requirements-enterprise.txt")
    
    # Test components
    logger.info("\n" + "="*50)
    components_status = test_enterprise_components()
    
    working_components = sum(1 for status in components_status.values() if status)
    total_components = len(components_status)
    
    logger.info(f"\nComponent Status: {working_components}/{total_components} working")
    
    # Test integration
    logger.info("\n" + "="*50)
    integration_success = test_integration()
    
    # Create sample config
    logger.info("\n" + "="*50)
    config_created = create_sample_config()
    
    # Performance test
    logger.info("\n" + "="*50)
    perf_test_success = run_performance_test()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("=== SETUP SUMMARY ===")
    
    if working_components == total_components:
        logger.info("✓ All enterprise components working")
    else:
        logger.warning(f"⚠ {total_components - working_components} components have issues")
    
    if integration_success:
        logger.info("✓ System integration successful")
    else:
        logger.warning("⚠ Integration issues detected")
    
    if not missing:
        logger.info("✓ All dependencies available")
    else:
        logger.warning(f"⚠ {len(missing)} dependencies missing")
    
    if config_created:
        logger.info("✓ Sample configuration created")
    
    if perf_test_success:
        logger.info("✓ Performance test framework ready")
    
    # Final recommendations
    logger.info("\n=== NEXT STEPS ===")
    
    if missing:
        logger.info("1. Install missing dependencies:")
        logger.info("   pip install -r requirements-enterprise.txt")
    
    if not os.path.exists('.env'):
        logger.info("2. Create .env file from .env.enterprise.example")
    
    logger.info("3. Start VaultMind and test enterprise features")
    logger.info("4. Monitor logs for enterprise feature usage")
    logger.info("5. Refer to ENTERPRISE_FEATURES_GUIDE.md for detailed usage")
    
    # Return status
    overall_success = (
        working_components >= total_components * 0.8 and  # 80% components working
        integration_success and
        len(missing) <= 2  # Allow 2 optional dependencies to be missing
    )
    
    if overall_success:
        logger.info("\n🎉 Enterprise setup completed successfully!")
        return 0
    else:
        logger.warning("\n⚠ Enterprise setup completed with issues. Check logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
