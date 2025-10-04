"""
Index Management Tab - Admin interface for managing document indexes
"""
import streamlit as st
import os
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def render_index_management():
    """Render the index management interface"""
    st.title("📁 Index Management")
    st.markdown("Manage your document indexes - view, delete, and get detailed information")
    
    try:
        from utils.index_manager import IndexManager
        
        # Initialize session state
        if 'refresh_indexes' not in st.session_state:
            st.session_state.refresh_indexes = False
        
        # Refresh button
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 Refresh", help="Refresh the index list"):
                st.session_state.refresh_indexes = True
                st.rerun()
        
        # Get all indexes
        all_indexes = IndexManager.list_all_indexes()
        
        # Display summary
        st.markdown("### 📊 Index Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("FAISS Indexes", len(all_indexes['faiss']))
        with col2:
            st.metric("Directory Indexes", len(all_indexes['directory']))
        with col3:
            st.metric("Unknown Type", len(all_indexes['unknown']))
        
        # Tabs for different index types
        tab1, tab2, tab3 = st.tabs(["🔍 FAISS Indexes", "📂 Directory Indexes", "❓ Unknown Type"])
        
        with tab1:
            render_index_list("FAISS", all_indexes['faiss'])
        
        with tab2:
            render_index_list("Directory", all_indexes['directory'])
        
        with tab3:
            render_index_list("Unknown", all_indexes['unknown'])
        
        # Bulk operations
        st.markdown("### 🔧 Bulk Operations")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🧹 Clean Empty Indexes", help="Remove indexes with no content"):
                clean_empty_indexes()
        
        with col2:
            if st.button("📊 Generate Report", help="Generate detailed index report"):
                generate_index_report(all_indexes)
        
    except Exception as e:
        st.error(f"Error loading index management: {str(e)}")
        logger.error(f"Index management error: {str(e)}")

def render_index_list(index_type: str, indexes: list):
    """Render a list of indexes with management options"""
    if not indexes:
        st.info(f"No {index_type.lower()} indexes found")
        return
    
    st.markdown(f"**{len(indexes)} {index_type} indexes found:**")
    
    # Create a container for the index list
    for i, index_name in enumerate(indexes):
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                st.write(f"**{index_name}**")
            
            with col2:
                # Get index info
                try:
                    from utils.index_manager import IndexManager
                    info = IndexManager().get_index_info(index_name)
                    
                    if info['size_bytes'] > 0:
                        size_mb = info['size_bytes'] / (1024 * 1024)
                        st.write(f"📦 {size_mb:.1f} MB ({info['file_count']} files)")
                    else:
                        st.write("📦 Size unknown")
                except:
                    st.write("📦 Info unavailable")
            
            with col3:
                if st.button("ℹ️", key=f"info_{index_name}_{i}", help="View details"):
                    show_index_details(index_name)
            
            with col4:
                if st.button("🗑️", key=f"delete_{index_name}_{i}", help="Delete index"):
                    confirm_delete_index(index_name)

def show_index_details(index_name: str):
    """Show detailed information about an index"""
    try:
        from utils.index_manager import IndexManager
        info = IndexManager().get_index_info(index_name)
        
        st.markdown(f"### 📋 Details for '{index_name}'")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Type:** {info['type'].upper()}")
            st.write(f"**Exists:** {'✅ Yes' if info['exists'] else '❌ No'}")
            st.write(f"**File Count:** {info['file_count']}")
        
        with col2:
            if info['size_bytes'] > 0:
                size_mb = info['size_bytes'] / (1024 * 1024)
                st.write(f"**Size:** {size_mb:.2f} MB")
            else:
                st.write("**Size:** Unknown")
            
            if info['created_date']:
                created = datetime.fromtimestamp(info['created_date'])
                st.write(f"**Created:** {created.strftime('%Y-%m-%d %H:%M')}")
        
        if info['locations']:
            st.write("**Locations:**")
            for location in info['locations']:
                st.code(location)
    
    except Exception as e:
        st.error(f"Error getting index details: {str(e)}")

def confirm_delete_index(index_name: str):
    """Show confirmation dialog for index deletion"""
    st.warning(f"⚠️ Are you sure you want to delete index '{index_name}'?")
    st.write("This action cannot be undone!")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("✅ Yes, Delete", key=f"confirm_delete_{index_name}"):
            delete_index(index_name)
    
    with col2:
        if st.button("❌ Cancel", key=f"cancel_delete_{index_name}"):
            st.rerun()

def delete_index(index_name: str):
    """Delete an index and show results"""
    try:
        from utils.index_manager import IndexManager
        
        with st.spinner(f"Deleting index '{index_name}'..."):
            result = IndexManager.delete_index(index_name)
        
        if result['success']:
            st.success(result['message'])
            
            if result['deleted_paths']:
                st.write("**Deleted paths:**")
                for path in result['deleted_paths']:
                    st.code(path)
            
            # Refresh the page
            st.session_state.refresh_indexes = True
            st.rerun()
        else:
            st.error(result['message'])
            
            if result['errors']:
                st.write("**Errors:**")
                for error in result['errors']:
                    st.error(error)
    
    except Exception as e:
        st.error(f"Error deleting index: {str(e)}")
        logger.error(f"Delete index error: {str(e)}")

def clean_empty_indexes():
    """Clean up empty or corrupted indexes"""
    try:
        from utils.index_manager import IndexManager
        
        all_indexes = IndexManager.list_all_indexes()
        empty_indexes = []
        
        # Check each index for content
        for index_type, indexes in all_indexes.items():
            for index_name in indexes:
                try:
                    info = IndexManager().get_index_info(index_name)
                    if info['file_count'] == 0 or info['size_bytes'] < 1024:  # Less than 1KB
                        empty_indexes.append(index_name)
                except:
                    empty_indexes.append(index_name)
        
        if empty_indexes:
            st.warning(f"Found {len(empty_indexes)} potentially empty indexes:")
            for index_name in empty_indexes:
                st.write(f"- {index_name}")
            
            if st.button("🗑️ Delete All Empty Indexes"):
                deleted_count = 0
                for index_name in empty_indexes:
                    result = IndexManager.delete_index(index_name)
                    if result['success']:
                        deleted_count += 1
                
                st.success(f"Deleted {deleted_count} empty indexes")
                st.rerun()
        else:
            st.info("No empty indexes found")
    
    except Exception as e:
        st.error(f"Error cleaning indexes: {str(e)}")

def generate_index_report(all_indexes: dict):
    """Generate a detailed report of all indexes"""
    try:
        from utils.index_manager import IndexManager
        
        report_lines = []
        report_lines.append("# VaultMind Index Report")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        total_size = 0
        total_files = 0
        
        for index_type, indexes in all_indexes.items():
            if indexes:
                report_lines.append(f"## {index_type.upper()} Indexes ({len(indexes)})")
                report_lines.append("")
                
                for index_name in indexes:
                    try:
                        info = IndexManager().get_index_info(index_name)
                        size_mb = info['size_bytes'] / (1024 * 1024) if info['size_bytes'] > 0 else 0
                        
                        report_lines.append(f"### {index_name}")
                        report_lines.append(f"- **Type:** {info['type']}")
                        report_lines.append(f"- **Size:** {size_mb:.2f} MB")
                        report_lines.append(f"- **Files:** {info['file_count']}")
                        report_lines.append(f"- **Locations:** {len(info['locations'])}")
                        
                        for location in info['locations']:
                            report_lines.append(f"  - `{location}`")
                        
                        report_lines.append("")
                        
                        total_size += info['size_bytes']
                        total_files += info['file_count']
                    
                    except Exception as e:
                        report_lines.append(f"### {index_name}")
                        report_lines.append(f"- **Error:** {str(e)}")
                        report_lines.append("")
        
        # Summary
        report_lines.append("## Summary")
        report_lines.append(f"- **Total Indexes:** {sum(len(indexes) for indexes in all_indexes.values())}")
        report_lines.append(f"- **Total Size:** {total_size / (1024 * 1024):.2f} MB")
        report_lines.append(f"- **Total Files:** {total_files}")
        
        report_text = "\n".join(report_lines)
        
        # Display report
        st.markdown("### 📄 Index Report")
        st.download_button(
            label="📥 Download Report",
            data=report_text,
            file_name=f"vaultmind_index_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
        
        with st.expander("📖 View Report", expanded=True):
            st.markdown(report_text)
    
    except Exception as e:
        st.error(f"Error generating report: {str(e)}")

if __name__ == "__main__":
    render_index_management()
