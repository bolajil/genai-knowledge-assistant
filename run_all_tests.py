#!/usr/bin/env python
"""
Master Test Runner Script

This script runs all the individual test scripts and provides a comprehensive summary of results.
It helps verify the overall functionality and integration of the VaultMIND Knowledge Assistant system.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure logging
log_dir = Path("test_logs")
log_dir.mkdir(exist_ok=True)

log_file = log_dir / f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add the current directory to the path
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

def run_test_script(script_path: str) -> bool:
    """Run a test script and return whether it passed"""
    logger.info(f"\nRunning test script: {script_path}")
    
    try:
        # Run the script as a subprocess
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=False
        )
        
        # Log the output
        logger.info(f"Output:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"Errors:\n{result.stderr}")
        
        # Check if the script passed
        passed = result.returncode == 0
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"Test script {os.path.basename(script_path)} {status} (Return code: {result.returncode})")
        
        return passed
    
    except Exception as e:
        logger.error(f"Error running test script {script_path}: {e}")
        return False

def main():
    """Main function"""
    logger.info("\n" + "*" * 80)
    logger.info("* VAULTMIND KNOWLEDGE ASSISTANT - MASTER TEST RUNNER *".center(78))
    logger.info("*" * 80 + "\n")
    
    # List of test scripts to run
    test_scripts = [
        "test_vector_db_functionality.py",
        "test_document_ingestion.py",
        "test_bylaw_content_access.py",
        "test_llm_integration.py",
        "test_system_integration.py",
        "test_weaviate_connection.py",
        "run_comprehensive_tests.py",
        "scripts/test_vector_db_connections.py",
        "scripts/test_multi_vector_connections.py",
        "scripts/test_mongodb_connection.py"
    ]
    
    # Add any existing test scripts that we might have missed
    for file in os.listdir(root_dir):
        if file.startswith("test_") and file.endswith(".py") and file not in test_scripts:
            test_scripts.append(file)
    
    # Run all test scripts
    results = {}
    
    for script in test_scripts:
        script_path = os.path.join(root_dir, script)
        if os.path.exists(script_path):
            results[script] = run_test_script(script_path)
        else:
            logger.warning(f"Test script {script} not found, skipping")
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY".center(80))
    logger.info("=" * 80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for script, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {script}")
    
    logger.info("\n" + "-" * 80)
    logger.info(f"OVERALL RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("✅ ALL TESTS PASSED")
    elif passed > 0:
        logger.info("⚠️ SOME TESTS FAILED")
    else:
        logger.info("❌ ALL TESTS FAILED")
    
    logger.info("-" * 80)
    logger.info(f"Detailed logs available at: {log_file}")
    
    # Return success if all tests passed
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)