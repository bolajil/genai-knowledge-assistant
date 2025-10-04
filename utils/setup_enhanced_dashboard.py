"""
Utility script to add the enhanced multi-content dashboard to the main application
"""
import logging
import importlib
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_enhanced_dashboard():
    """
    Set up the enhanced multi-content dashboard
    - Check if all required modules are available
    - Initialize the search system
    - Update main.py to include the enhanced dashboard
    """
    logger.info("Setting up enhanced multi-content dashboard...")
    
    # Check if required modules are available
    required_modules = [
        "utils.index_manager",
        "utils.search_service",
        "utils.init_search_system",
        "tabs.multi_content_dashboard_enhanced"
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            importlib.import_module(module)
            logger.info(f"✅ Module {module} is available")
        except ImportError as e:
            logger.error(f"❌ Module {module} is not available: {str(e)}")
            missing_modules.append(module)
    
    if missing_modules:
        logger.error(f"Missing required modules: {missing_modules}")
        return False
    
    # Initialize the search system
    try:
        from utils.init_search_system import init_search_system
        stats = init_search_system()
        logger.info(f"✅ Search system initialized with {stats['final_index_count']} indexes")
    except Exception as e:
        logger.error(f"❌ Error initializing search system: {str(e)}")
        return False
    
    # Check if main.py exists
    main_path = Path("main.py")
    if not main_path.exists():
        logger.error("❌ main.py not found")
        return False
    
    # Read main.py content
    with open(main_path, "r") as f:
        main_content = f.read()
    
    # Check if multi_content_dashboard_enhanced is already imported
    if "multi_content_dashboard_enhanced" in main_content:
        logger.info("✅ Enhanced dashboard already imported in main.py")
    else:
        # Look for the import section
        import_section = "from tabs import "
        if import_section not in main_content:
            logger.error("❌ Could not find import section in main.py")
            return False
        
        # Find the end of the import section
        lines = main_content.split("\n")
        for i, line in enumerate(lines):
            if import_section in line:
                # Add the new import
                if line.strip().endswith("\\"):
                    # Multi-line import
                    lines[i] = line + "\n    multi_content_dashboard_enhanced, \\"
                else:
                    # Single-line import
                    module_list = line.split("import ")[1].strip()
                    new_module_list = module_list + ", multi_content_dashboard_enhanced"
                    lines[i] = line.replace(module_list, new_module_list)
                
                logger.info("✅ Added import for enhanced dashboard")
                break
        
        # Look for the dashboard section
        dashboard_section = "# Multi-Content Dashboard (Admin)"
        if dashboard_section not in main_content:
            logger.warning("⚠️ Could not find dashboard section in main.py")
        else:
            # Find the dashboard section and add the enhanced version
            for i, line in enumerate(lines):
                if dashboard_section in line and "multi_content_dashboard.render" in lines[i+1]:
                    # Add the enhanced dashboard with a toggle
                    new_lines = [
                        "",
                        "    # Option to use enhanced dashboard",
                        "    use_enhanced_dashboard = st.sidebar.checkbox('Use Enhanced Dashboard', value=True)",
                        "    if use_enhanced_dashboard:",
                        "        multi_content_dashboard_enhanced.render_multi_content_dashboard_enhanced(",
                        "            user=user,",
                        "            permissions=permissions,",
                        "            auth_middleware=auth_middleware,",
                        "            available_indexes=available_indexes",
                        "        )",
                        "    else:"
                    ]
                    
                    # Indent the original dashboard code
                    lines[i+1] = "        " + lines[i+1]
                    if i+2 < len(lines) and "multi_content_dashboard.render" in lines[i+1]:
                        for j in range(i+2, i+7):
                            if j < len(lines) and ")" not in lines[j]:
                                lines[j] = "        " + lines[j]
                    
                    # Insert the new lines before the original dashboard code
                    lines[i:i+1] = [line] + new_lines
                    
                    logger.info("✅ Added enhanced dashboard to main.py")
                    break
        
        # Write the updated content
        with open(main_path, "w") as f:
            f.write("\n".join(lines))
        
        logger.info("✅ Updated main.py with enhanced dashboard")
    
    logger.info("✅ Enhanced multi-content dashboard setup complete")
    return True

if __name__ == "__main__":
    """Run the setup directly when executed as a script"""
    success = setup_enhanced_dashboard()
    
    if success:
        logger.info("")
        logger.info("Enhanced multi-content dashboard setup complete")
        logger.info("You can now run the application with the enhanced dashboard")
    else:
        logger.error("")
        logger.error("Enhanced multi-content dashboard setup failed")
        logger.error("Please check the logs for details")
