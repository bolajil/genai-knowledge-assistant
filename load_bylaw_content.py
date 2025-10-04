"""
ByLaw Content Direct Loader

This script directly injects the ByLaw content by patching the necessary modules.
Run this script after the VaultMIND system has started to apply the patches.
"""

import os
import sys
import logging
import importlib.util
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_if_module_exists(module_name):
    """Check if a module exists without importing it"""
    return importlib.util.find_spec(module_name) is not None

def load_module(module_path):
    """Load a module from a file path"""
    try:
        module_name = os.path.basename(module_path).replace('.py', '')
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error(f"Error loading module {module_path}: {e}")
        return None

def apply_patches():
    """Apply all ByLaw content patches"""
    logger.info("Applying ByLaw content patches...")
    
    # Current directory is the parent directory of this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load the ByLaw query patch
    bylaw_query_patch_path = os.path.join(current_dir, 'utils', 'bylaw_query_patch.py')
    if os.path.exists(bylaw_query_patch_path):
        logger.info(f"Loading ByLaw query patch from {bylaw_query_patch_path}")
        bylaw_query_patch = load_module(bylaw_query_patch_path)
        if bylaw_query_patch:
            logger.info("ByLaw query patch loaded successfully")
    else:
        logger.warning(f"ByLaw query patch not found at {bylaw_query_patch_path}")
    
    # Load the enhanced LLM ByLaw patch
    enhanced_llm_patch_path = os.path.join(current_dir, 'utils', 'enhanced_llm_bylaw_patch.py')
    if os.path.exists(enhanced_llm_patch_path):
        logger.info(f"Loading enhanced LLM ByLaw patch from {enhanced_llm_patch_path}")
        enhanced_llm_patch = load_module(enhanced_llm_patch_path)
        if enhanced_llm_patch:
            logger.info("Enhanced LLM ByLaw patch loaded successfully")
    else:
        logger.warning(f"Enhanced LLM ByLaw patch not found at {enhanced_llm_patch_path}")
    
    # Load the direct ByLaws retriever
    bylaws_retriever_path = os.path.join(current_dir, 'utils', 'direct_bylaws_retriever.py')
    if os.path.exists(bylaws_retriever_path):
        logger.info(f"Loading direct ByLaws retriever from {bylaws_retriever_path}")
        bylaws_retriever = load_module(bylaws_retriever_path)
        if bylaws_retriever:
            logger.info("Direct ByLaws retriever loaded successfully")
    else:
        logger.warning(f"Direct ByLaws retriever not found at {bylaws_retriever_path}")
    
    # Test if patches are working
    logger.info("Testing ByLaw query patch...")
    
    try:
        from utils.bylaw_query_patch import is_bylaw_query
        
        test_query = "Tell me about board meetings"
        is_bylaw = is_bylaw_query(test_query, "ByLawS2_index")
        
        if is_bylaw:
            logger.info(f"ByLaw query patch working: Correctly identified '{test_query}' as a ByLaw query")
        else:
            logger.warning(f"ByLaw query patch may not be working: Did not identify '{test_query}' as a ByLaw query")
    except ImportError:
        logger.error("Could not import bylaw_query_patch, patch may not be working")
    except Exception as e:
        logger.error(f"Error testing ByLaw query patch: {e}")
    
    logger.info("All patches applied")

def patch_sys_path():
    """Ensure the utils directory is in sys.path"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    utils_dir = os.path.join(current_dir, 'utils')
    
    if utils_dir not in sys.path:
        sys.path.insert(0, utils_dir)
        logger.info(f"Added {utils_dir} to sys.path")

def main():
    """Main function"""
    logger.info("Starting ByLaw Content Direct Loader")
    
    # Patch sys.path
    patch_sys_path()
    
    # Apply patches
    apply_patches()
    
    logger.info("ByLaw Content Direct Loader complete")
    logger.info("The VaultMIND system should now correctly display ByLaw content")

if __name__ == "__main__":
    main()
