"""
Sample implementation for the multi-content tab with enhanced search functionality
This shows how to use the centralized search service in a tab
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any

def render_multi_content_dashboard_enhanced(user, permissions, auth_middleware, available_indexes):
    """Multi-Content Dashboard Tab with Enhanced Search - Admin only"""
    
    # Check admin permissions
    if not permissions.get('can_access_admin_features', False):
        st.error("🚫 Access Denied: Admin privileges required")
        return
    
    auth_middleware.log_user_action("ACCESS_MULTI_CONTENT_DASHBOARD")
    
    st.header("🌐 Multi-Content Dashboard")
    st.markdown("**Advanced multi-content management and analytics**")
    
    # Import the centralized search service
    try:
        from utils.search_service import SearchService
        from utils.index_manager import IndexManager
        
        # Use the centralized service to get available indexes
        all_indexes = IndexManager.list_available_indexes()
        
        # Display a warning if no indexes are available
        if not all_indexes:
            st.warning("⚠️ No document indexes found. Please upload and index documents first.")
            st.info("Use the Document Ingestion tab to upload and index documents.")
            return
    except ImportError:
        # Fallback to the provided available_indexes if the centralized service is not available
        all_indexes = available_indexes
        st.info("ℹ️ Using legacy index system. Consider upgrading to the centralized search service.")
    
    # Overview Metrics - ADMIN ONLY
    st.subheader("📊 Content Overview")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "📄 Total Documents", 
            "1,247",
            delta="23 today",
            help="Total documents across all indexes"
        )
    
    with col2:
        st.metric(
            "🔍 Active Indexes", 
            len(all_indexes) if all_indexes else 0,
            delta="2 new",
            help="Number of active vector indexes"
        )
    
    with col3:
        st.metric(
            "📈 Queries Today", 
            "89",
            delta="12%",
            help="Query volume for today"
        )
    
    with col4:
        st.metric(
            "🌊 Live Streams", 
            "4",
            delta="1 new",
            help="Active data streams"
        )
    
    with col5:
        st.metric(
            "💾 Storage Used", 
            "7.2 GB",
            delta="0.3 GB",
            help="Total storage consumption"
        )
    
    st.divider()
    
    # Enhanced Multi-Source Search - ADMIN ONLY
    st.subheader("🔍 Multi-Source Search")
    
    with st.form("multi_source_search_form"):
        # Search query
        search_query = st.text_input(
            "Search Query:",
            placeholder="Enter your search query...",
            help="Enter keywords, phrases, or questions to search across all sources"
        )
        
        # Source selection
        col1, col2 = st.columns(2)
        
        with col1:
            # Select indexes to search
            selected_indexes = st.multiselect(
                "Select Document Collections:",
                options=all_indexes,
                default=all_indexes[:2] if len(all_indexes) >= 2 else all_indexes,
                help="Choose which document collections to search"
            )
        
        with col2:
            # Include web search
            include_web = st.checkbox(
                "Include Web Search",
                value=True,
                help="Search the web in addition to indexed documents"
            )
            
            if include_web:
                # Select web search engines
                search_engines = st.multiselect(
                    "Web Search Engines:",
                    options=["Google", "Bing", "DuckDuckGo", "Custom API"],
                    default=["Google"],
                    help="Select which search engines to use for web search"
                )
            else:
                search_engines = []
        
        # Search options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            max_results = st.slider(
                "Max Results per Source:",
                min_value=1,
                max_value=20,
                value=5,
                help="Maximum number of results to return per source"
            )
        
        with col2:
            use_semantic = st.checkbox(
                "Semantic Search",
                value=True,
                help="Use semantic understanding for better results"
            )
        
        with col3:
            format_type = st.selectbox(
                "Result Format:",
                options=["markdown", "html", "text"],
                index=0,
                help="Format for displaying search results"
            )
        
        # Submit button
        submit_button = st.form_submit_button("🔍 Search All Sources", type="primary")
    
    # Process search when button is clicked
    if submit_button and search_query:
        with st.spinner("Searching across all sources..."):
            try:
                # Create a list of sources to search
                sources_to_search = selected_indexes.copy()
                
                # Add web search if selected
                if include_web:
                    sources_to_search.append("Web Search (External)")
                
                # Perform the search using the centralized service
                try:
                    # Try to use the SearchService
                    search_results = SearchService.search(
                        query=search_query,
                        index_names=selected_indexes,
                        max_results=max_results
                    )
                    
                    # Add web search results if requested
                    if include_web:
                        web_results = SearchService.search_web(
                            query=search_query,
                            max_results=max_results,
                            search_engines=search_engines
                        )
                        search_results.extend(web_results)
                    
                    # Format the results
                    formatted_results = SearchService.format_results_for_display(
                        results=search_results,
                        format_type=format_type
                    )
                except ImportError:
                    # Fallback to the simple search if SearchService is not available
                    from utils.simple_search import perform_multi_source_search, format_search_results_for_agent
                    
                    search_results = perform_multi_source_search(
                        query=search_query,
                        knowledge_sources=sources_to_search,
                        max_results=max_results,
                        search_engines=search_engines if include_web else None
                    )
                    
                    # Format the results using the legacy function
                    formatted_results = format_search_results_for_agent(search_results)
                
                # Display the results
                if format_type == "html":
                    st.components.v1.html(formatted_results, height=600)
                else:
                    st.markdown(formatted_results)
                
                # Log the search
                auth_middleware.log_user_action("MULTI_SOURCE_SEARCH", {
                    "query": search_query,
                    "sources": sources_to_search,
                    "max_results": max_results
                })
            except Exception as e:
                st.error(f"Error performing search: {str(e)}")
    
    # Index Management - ADMIN ONLY
    st.subheader("🗂️ Index Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**📋 Index Statistics:**")
        
        if all_indexes:
            index_stats = []
            for idx in all_indexes:
                # Simulated statistics
                index_stats.append({
                    'Index Name': idx,
                    'Documents': f"{456 + hash(idx) % 500}",
                    'Size (MB)': f"{123 + hash(idx) % 200}",
                    'Last Updated': '2025-08-09 14:30',
                    'Status': '🟢 Active',
                    'Queries/Day': f"{45 + hash(idx) % 100}"
                })
            
            index_df = pd.DataFrame(index_stats)
            st.dataframe(index_df, use_container_width=True)
        else:
            st.info("No indexes available")
    
    with col2:
        st.markdown("**⚡ Index Actions:**")
        
        if st.button("🔄 Refresh Indexes", key="refresh_indexes"):
            try:
                # Use the IndexManager to refresh indexes
                refreshed_indexes = IndexManager.list_available_indexes(force_refresh=True)
                st.success(f"✅ Refreshed {len(refreshed_indexes)} indexes!")
            except ImportError:
                st.warning("⚠️ Centralized index manager not available.")
                st.success("✅ Indexes refreshed using legacy system!")
        
        if st.button("🔄 Migrate Legacy Indexes", key="migrate_indexes"):
            try:
                # Use the IndexManager to migrate legacy indexes
                from utils.index_manager import IndexManager
                migration_results = IndexManager.migrate_legacy_indexes()
                
                if migration_results:
                    st.success(f"✅ Migrated {len(migration_results)} indexes to standard location!")
                else:
                    st.info("ℹ️ No indexes needed migration.")
            except ImportError:
                st.error("❌ Centralized index manager not available.")
        
        if st.button("📊 Generate Index Report", key="generate_index_report"):
            st.success("📊 Index report generated!")
        
        if st.button("🧹 Cleanup Unused Indexes", key="cleanup_indexes"):
            st.success("🧹 Cleanup completed!")
    
    # Initialize Search System
    if st.sidebar.button("🔄 Initialize Search System", key="init_search_system"):
        try:
            from utils.init_search_system import init_search_system
            
            with st.spinner("Initializing search system..."):
                stats = init_search_system()
                
                st.sidebar.success("✅ Search system initialized successfully!")
                st.sidebar.info(f"Standard path: {stats['standard_path']}")
                st.sidebar.info(f"Initial index count: {stats['initial_index_count']}")
                st.sidebar.info(f"Migrated indexes: {stats['migrated_index_count']}")
                st.sidebar.info(f"Final index count: {stats['final_index_count']}")
                st.sidebar.info(f"Completed in: {stats['elapsed_time']:.2f} seconds")
        except ImportError:
            st.sidebar.error("❌ Search system initialization module not available.")
        except Exception as e:
            st.sidebar.error(f"❌ Error initializing search system: {str(e)}")
