"""
Organize Project Files Script
Move utility files to appropriate directories for better organization
"""

import shutil
from pathlib import Path

def organize_files():
    """Organize files into proper directory structure"""
    
    project_root = Path(__file__).parent.parent
    
    # Files to move to scripts/utilities/
    utility_files = [
        "analyze_document.py",
        "document_listing.py",
        "list_documents.py",
        "apply_vector_db_fix.py",
        "check_vector_db.py",
        "vector_db_fix.py",
        "fix_import_error.py",
        "fix_user_objects.py",
        "verify_packages.py",
        "direct_aws_test.py",
        "simple_aws_test.py"
    ]
    
    # Files to move to scripts/demos/
    demo_files = [
        "agent_assistant_console.py",
        "agent_assistant_demo.py", 
        "demo_enhanced_research.py",
        "simple_dashboard.py",
        "simple_tab_breakdown.py",
        "tab_breakdown_script.py"
    ]
    
    # Files to move to scripts/setup/
    setup_files = [
        "setup_enterprise.py",
        "run_enterprise.py"
    ]
    
    # Files to remove (temporary/obsolete)
    files_to_remove = [
        "vaultmind_agent_demo.html",
        "vaultmind_dashboard.html",
        "agent_integration_enhancement.md",
        "diagnose_query.ps1"
    ]
    
    moved_count = 0
    removed_count = 0
    
    print("🗂️  ORGANIZING PROJECT FILES")
    print("=" * 40)
    
    # Create directories
    utilities_dir = project_root / "scripts" / "utilities"
    demos_dir = project_root / "scripts" / "demos"
    setup_dir = project_root / "scripts" / "setup"
    
    utilities_dir.mkdir(parents=True, exist_ok=True)
    demos_dir.mkdir(parents=True, exist_ok=True)
    setup_dir.mkdir(parents=True, exist_ok=True)
    
    # Move utility files
    for filename in utility_files:
        source = project_root / filename
        if source.exists():
            target = utilities_dir / filename
            try:
                shutil.move(str(source), str(target))
                print(f"📁 Moved: {filename} → scripts/utilities/")
                moved_count += 1
            except Exception as e:
                print(f"❌ Failed to move {filename}: {e}")
    
    # Move demo files
    for filename in demo_files:
        source = project_root / filename
        if source.exists():
            target = demos_dir / filename
            try:
                shutil.move(str(source), str(target))
                print(f"📁 Moved: {filename} → scripts/demos/")
                moved_count += 1
            except Exception as e:
                print(f"❌ Failed to move {filename}: {e}")
    
    # Move setup files
    for filename in setup_files:
        source = project_root / filename
        if source.exists():
            target = setup_dir / filename
            try:
                shutil.move(str(source), str(target))
                print(f"📁 Moved: {filename} → scripts/setup/")
                moved_count += 1
            except Exception as e:
                print(f"❌ Failed to move {filename}: {e}")
    
    # Remove obsolete files
    for filename in files_to_remove:
        file_path = project_root / filename
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"🗑️  Removed: {filename}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Failed to remove {filename}: {e}")
    
    print(f"\n📊 Organization complete:")
    print(f"   📁 Files moved: {moved_count}")
    print(f"   🗑️  Files removed: {removed_count}")
    
    return moved_count, removed_count

if __name__ == "__main__":
    organize_files()
