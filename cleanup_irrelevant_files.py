"""
Project Cleanup Script
=====================
Remove files and folders not relevant to the VaultMind GenAI Knowledge Assistant project.
"""

import os
import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def cleanup_project():
    """Remove irrelevant files and folders from the project."""
    
    project_root = Path(__file__).parent
    
    # Files to remove (not relevant to VaultMind project)
    files_to_remove = [
        # Test and debug files
        "test_chunking_fix.py",
        "agent_assistant_console.py",
        "agent_assistant_demo.py", 
        "demo_enhanced_research.py",
        "direct_aws_test.py",
        "simple_aws_test.py",
        "simple_dashboard.py",
        "simple_tab_breakdown.py",
        "tab_breakdown_script.py",
        "document_listing.py",
        "fix_import_error.py",
        "fix_user_objects.py",
        "setup_enterprise.py",
        "verify_packages.py",
        "vector_db_fix.py",
        
        # Batch files (keep only essential ones)
        "analyze_document.bat",
        "list_available_documents.bat", 
        "list_documents.bat",
        "run_query_debug.bat",
        "run_test.bat",
        "start_enhanced_agent.bat",
        "start_vaultmind_9000.bat",
        "start_vaultmind_9999.bat", 
        "start_vaultmind_improved.bat",
        "diagnose_query.ps1",
        
        # Configuration files not needed
        "flowise.yml",
        "package-lock.json",
        "package.json",
        "constraints.txt",
        "cloud_requirements.txt",
        "simple_requirements.txt",
        
        # HTML files (likely demos)
        "vaultmind_agent_demo.html",
        "vaultmind_dashboard.html",
        "vaultmind_tabs.json",
        
        # Database files
        "mcp_logs.db",
        
        # Other files
        "agent_integration_enhancement.md",
        "notification_service.py",
        "schemas.py",
        "query_llm.py",
        "query_llm_streamlit.py",
        "check_vector_db.py",
        "apply_vector_db_fix.py",
        "main.py"  # Likely old entry point
    ]
    
    # Directories to remove (not relevant to VaultMind project)
    dirs_to_remove = [
        "__pycache__",
        "vaultmind_modular",
        "vector_store", 
        "vectorstores",
        "mcp-tracking-UI",
        "src",  # Likely old frontend
        "docker"  # Keep Dockerfile.production but remove docker folder
    ]
    
    # Remove files
    removed_files = []
    for file_name in files_to_remove:
        file_path = project_root / file_name
        if file_path.exists():
            try:
                file_path.unlink()
                removed_files.append(file_name)
                logger.info(f"Removed file: {file_name}")
            except Exception as e:
                logger.error(f"Failed to remove file {file_name}: {e}")
    
    # Remove directories
    removed_dirs = []
    for dir_name in dirs_to_remove:
        dir_path = project_root / dir_name
        if dir_path.exists() and dir_path.is_dir():
            try:
                shutil.rmtree(dir_path)
                removed_dirs.append(dir_name)
                logger.info(f"Removed directory: {dir_name}")
            except Exception as e:
                logger.error(f"Failed to remove directory {dir_name}: {e}")
    
    # Remove __pycache__ directories recursively
    pycache_removed = 0
    for pycache_dir in project_root.rglob("__pycache__"):
        try:
            shutil.rmtree(pycache_dir)
            pycache_removed += 1
            logger.info(f"Removed __pycache__: {pycache_dir}")
        except Exception as e:
            logger.error(f"Failed to remove __pycache__ {pycache_dir}: {e}")
    
    # Remove .pyc files
    pyc_removed = 0
    for pyc_file in project_root.rglob("*.pyc"):
        try:
            pyc_file.unlink()
            pyc_removed += 1
            logger.info(f"Removed .pyc file: {pyc_file}")
        except Exception as e:
            logger.error(f"Failed to remove .pyc file {pyc_file}: {e}")
    
    # Summary
    print("\n" + "="*50)
    print("PROJECT CLEANUP SUMMARY")
    print("="*50)
    print(f"Files removed: {len(removed_files)}")
    print(f"Directories removed: {len(removed_dirs)}")
    print(f"__pycache__ directories removed: {pycache_removed}")
    print(f".pyc files removed: {pyc_removed}")
    print("\nRemoved files:")
    for file in removed_files:
        print(f"  - {file}")
    print("\nRemoved directories:")
    for dir in removed_dirs:
        print(f"  - {dir}")
    print("="*50)
    print("Cleanup completed successfully!")

if __name__ == "__main__":
    cleanup_project()
