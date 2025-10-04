"""
Tab Migration Utility for Vector Database Centralization

This script helps migrate existing tabs to use the centralized vector database solution.
It can be run in either:
1. Analysis mode - to scan tabs and identify those using direct vector database access
2. Migration mode - to update tabs to use the centralized solution
"""

import os
import sys
import re
import argparse
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

# Patterns to detect direct vector database access
VECTOR_DB_PATTERNS = [
    r'import\s+faiss',
    r'from\s+faiss\s+import',
    r'load_faiss_index',
    r'create_faiss_index',
    r'faiss\.read_index',
    r'faiss\.write_index',
    r'faiss\.IndexFlatL2',
    r'faiss\.IndexIVFFlat',
    r'\.vector_store',
    r'\.vectorstore',
    r'\.get_nearest_neighbors',
    r'search_documents_by_vector',
    r'search_vector_store',
    r'VectorStore\.',
    r'VectorStoreIndex',
    r'from\s+weaviate\s+import',
    r'import\s+weaviate',
    r'weaviate\.Client',
    r'weaviate_client',
    r'from\s+langchain\.vectorstores',
    r'from\s+langchain\.embeddings',
]

# Imports to add for using the centralized solution
CENTRALIZED_IMPORTS = """
# Import centralized vector database provider
try:
    from utils.vector_db_provider import get_vector_db_provider
    
    # Get the vector database provider
    db_provider = get_vector_db_provider()
    VECTOR_DB_AVAILABLE = True
    logger.info("Tab initialized with centralized DB integration")
except ImportError as e:
    VECTOR_DB_AVAILABLE = False
    db_provider = None
    logger.error(f"Error initializing tab with centralized DB: {e}")
"""

# Function to replace with centralized provider call
SEARCH_REPLACEMENT = '''
def search_documents(query, top_k=5):
    """Search documents using the centralized vector database provider"""
    try:
        if db_provider and VECTOR_DB_AVAILABLE:
            results = db_provider.search(query, max_results=top_k)
            return results
        else:
            logger.warning("Vector database provider not available. Using fallback.")
            return []
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return []
'''

def scan_tab_file(file_path: Path) -> Tuple[bool, List[str]]:
    """
    Scan a tab file for direct vector database access patterns
    
    Args:
        file_path: Path to the tab file
        
    Returns:
        Tuple containing:
        - Boolean indicating if the file uses direct vector DB access
        - List of matched patterns
    """
    if not file_path.exists():
        logger.warning(f"File does not exist: {file_path}")
        return False, []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        matches = []
        for pattern in VECTOR_DB_PATTERNS:
            if re.search(pattern, content):
                matches.append(pattern)
        
        return len(matches) > 0, matches
    
    except Exception as e:
        logger.error(f"Error scanning file {file_path}: {e}")
        return False, []

def scan_tabs_directory(tabs_dir: Path) -> Dict[str, List[str]]:
    """
    Scan the tabs directory for files using direct vector database access
    
    Args:
        tabs_dir: Path to the tabs directory
        
    Returns:
        Dictionary mapping file paths to lists of matched patterns
    """
    results = {}
    
    if not tabs_dir.exists() or not tabs_dir.is_dir():
        logger.error(f"Tabs directory does not exist: {tabs_dir}")
        return results
    
    # Scan Python files in the tabs directory
    for file_path in tabs_dir.glob('*.py'):
        uses_vector_db, matches = scan_tab_file(file_path)
        
        if uses_vector_db:
            results[str(file_path)] = matches
    
    return results

def create_backup(file_path: Path) -> Path:
    """
    Create a backup of a file before modifying it
    
    Args:
        file_path: Path to the file to back up
        
    Returns:
        Path to the backup file
    """
    backup_path = file_path.with_suffix(f'.py.bak')
    shutil.copy2(file_path, backup_path)
    logger.info(f"Created backup: {backup_path}")
    return backup_path

def update_tab_file(file_path: Path, dry_run: bool = True) -> bool:
    """
    Update a tab file to use the centralized vector database solution
    
    Args:
        file_path: Path to the tab file
        dry_run: If True, don't actually modify the file
        
    Returns:
        Boolean indicating if the file was updated
    """
    if not file_path.exists():
        logger.warning(f"File does not exist: {file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if the file already uses the centralized solution
        if "from utils.vector_db_provider import get_vector_db_provider" in content:
            logger.info(f"File already uses centralized solution: {file_path}")
            return False
        
        # Create a backup before modifying
        if not dry_run:
            create_backup(file_path)
        
        # Add imports for logging if not present
        if "import logging" not in content:
            import_section = "import logging\n\n# Configure logging\nlogging.basicConfig(level=logging.INFO)\nlogger = logging.getLogger(__name__)\n\n"
            content = import_section + content
        
        # Find the right position to add the centralized imports
        import_match = re.search(r'(^import.*?\n|^from.*?\n)+', content, re.MULTILINE)
        if import_match:
            import_end = import_match.end()
            content = content[:import_end] + CENTRALIZED_IMPORTS + content[import_end:]
        else:
            # If no imports found, add at the beginning
            content = CENTRALIZED_IMPORTS + content
        
        # Replace direct search functions with centralized version
        search_func_match = re.search(r'def\s+search_documents\s*\(.*?\):.*?(?=\n\w|\Z)', content, re.DOTALL)
        if search_func_match:
            start, end = search_func_match.span()
            content = content[:start] + SEARCH_REPLACEMENT + content[end:]
        
        # Write the updated content
        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Updated file: {file_path}")
        else:
            logger.info(f"Would update file (dry run): {file_path}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error updating file {file_path}: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Tab Migration Utility")
    parser.add_argument("--tabs-dir", default=str(parent_dir / "tabs"), 
                        help="Path to the tabs directory")
    parser.add_argument("--analyze", action="store_true", 
                        help="Only analyze tabs, don't modify them")
    parser.add_argument("--file", 
                        help="Path to a specific tab file to update")
    parser.add_argument("--all", action="store_true", 
                        help="Update all tab files even if they don't match patterns")
    args = parser.parse_args()
    
    tabs_dir = Path(args.tabs_dir)
    
    if args.file:
        # Update a specific file
        file_path = Path(args.file)
        uses_vector_db, matches = scan_tab_file(file_path)
        
        if uses_vector_db or args.all:
            if args.analyze:
                logger.info(f"File uses vector DB: {file_path}")
                logger.info(f"Matched patterns: {matches}")
            else:
                update_tab_file(file_path, dry_run=False)
        else:
            logger.info(f"File does not use vector DB: {file_path}")
    
    else:
        # Scan all tabs
        results = scan_tabs_directory(tabs_dir)
        
        if not results:
            logger.info("No tab files using direct vector DB access found")
            return 0
        
        logger.info(f"Found {len(results)} tab files using direct vector DB access:")
        for file_path, matches in results.items():
            logger.info(f"- {file_path}")
            logger.info(f"  Matched patterns: {matches}")
        
        # Update tabs if not in analyze mode
        if not args.analyze:
            for file_path in results:
                update_tab_file(Path(file_path), dry_run=False)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
