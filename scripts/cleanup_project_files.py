"""
Manual Project Cleanup Script
Remove test files, debug files, and organize project structure
"""

import os
from pathlib import Path

def cleanup_files():
    """Remove test and debug files manually"""
    
    project_root = Path(__file__).parent.parent
    
    # Files to remove (exact names)
    files_to_remove = [
        # Test files in root
        "test_agent_improvement.py",
        "test_agent_search.py", 
        "test_all_indexes.py",
        "test_aws_document.py",
        "test_aws_improve.py",
        "test_aws_index.py",
        "test_comprehensive_retrieval.py",
        "test_content_generator.py",
        "test_direct_search.py",
        "test_document_fetch.py",
        "test_document_info.py",
        "test_document_list.py",
        "test_document_summary.py",
        "test_embeddings_integration.py",
        "test_enhanced_multicontent.py",
        "test_index_detection.py",
        "test_index_directories.py",
        "test_llm_config.py",
        "test_modules.py",
        "test_query_enhancement_system.py",
        "test_search.py",
        "test_system_status.py",
        "test_vector_db.py",
        "test_vector_db_fix.py",
        "test_vector_db_status.py",
        
        # Debug files
        "debug_fia_index.py",
        "debug_file_write.py",
        "debug_imports.py",
        "debug_python.py",
        "debug_query_assistant.py",
        "debug_search.py",
        "debug_torch.py",
        "debug_vector_db.py",
        
        # Cleanup files
        "add_embeddings_to_indexes.py",
        "generate_embeddings.py",
        "validate_query_system.py",
        "cleanup_project.py",
        "quick_test.py",
        
        # Test batch files
        "test_agent_improve.bat",
        "test_all_aws.bat",
        "test_aws_content.bat",
        "test_aws_improve.bat",
        "test_document_fetch.bat",
        "test_document_list.bat",
        "test_index_directories.bat",
        "test_query_tab.bat",
        "run_query_debug.bat",
        "run_test.bat",
        
        # Extra batch files
        "start_enhanced_agent.bat",
        "start_vaultmind_9000.bat",
        "start_vaultmind_9999.bat",
        "start_vaultmind_improved.bat",
        
        # Cleanup documentation
        "CLEANUP_FILES_TO_REMOVE.md"
    ]
    
    removed_count = 0
    
    print("🧹 CLEANING UP PROJECT FILES")
    print("=" * 40)
    
    for filename in files_to_remove:
        file_path = project_root / filename
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"✅ Removed: {filename}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Failed to remove {filename}: {e}")
        else:
            print(f"⚠️  Not found: {filename}")
    
    print(f"\n📊 Removed {removed_count} files")
    return removed_count

if __name__ == "__main__":
    cleanup_files()
