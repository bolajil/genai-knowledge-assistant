"""
Weaviate Collection Selector UI Component
========================================
Reusable UI component for selecting Weaviate collections across tabs
"""

import streamlit as st
from typing import List, Optional, Dict, Any
import logging
import time
from utils.weaviate_manager import get_weaviate_manager
from utils.schema_sync_guard import refresh_sdk_schema

logger = logging.getLogger(__name__)

def render_collection_selector(
    key: str = "weaviate_collection",
    label: str = "Select Weaviate Collection",
    help_text: str = "Choose a Weaviate collection to search",
    include_all_option: bool = True,
    show_stats: bool = True,
    allow_refresh: bool = True,
) -> Optional[str]:
    """
    Render a collection selector UI component
    
    Args:
        key: Unique key for the selectbox
        label: Label for the selectbox
        help_text: Help text for the selectbox
        include_all_option: Whether to include "All Collections" option
        show_stats: Whether to show collection statistics
    
    Returns:
        Selected collection name or None
    """
    try:
        weaviate_manager = get_weaviate_manager()

        # Optional: quick refresh button to mitigate SDK schema lag
        if allow_refresh:
            col_a, col_b = st.columns([1, 3])
            with col_a:
                if st.button("🔄 Refresh", key=f"{key}_refresh_btn", help="Refresh collection list (forces SDK schema refresh)"):
                    try:
                        refresh_sdk_schema(weaviate_manager.client)
                    except Exception as e:
                        logger.debug(f"SDK schema refresh failed: {e}")
                    # Small delay to allow SDK to sync
                    time.sleep(0.3)
                    st.rerun()

        collections = weaviate_manager.list_collections()
        
        if not collections:
            st.warning("⚠️ No Weaviate collections found. Please ingest some documents first.")
            return None
        
        # Prepare options
        options = []
        if include_all_option:
            options.append("All Collections")
        options.extend(collections)
        
        # Collection selector
        selected = st.selectbox(
            label,
            options=options,
            key=key,
            help=help_text
        )
        
        # Diagnostic: if some classes are REST-only (SDK lag), hint to user
        try:
            sdk_names = set(weaviate_manager._list_collections_via_sdk())  # type: ignore[attr-defined]
            rest_names = set(weaviate_manager._list_collections_via_schema())  # type: ignore[attr-defined]
            missing_in_sdk = sorted(list(rest_names - sdk_names))
            if missing_in_sdk:
                st.info(
                    "Some collections are currently visible via REST but not yet via the SDK: "
                    + ", ".join(missing_in_sdk)
                )
        except Exception:
            pass

        # Show collection statistics
        if show_stats and selected and selected != "All Collections":
            try:
                stats = weaviate_manager.get_collection_stats(selected)
                if stats:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("📄 Documents", stats.get('total_objects', 0))
                    with col2:
                        st.metric("📅 Created", stats.get('created_at', 'Unknown')[:10] if stats.get('created_at') else 'Unknown')
            except Exception as e:
                logger.warning(f"Could not load stats for collection {selected}: {e}")
        
        return selected if selected != "All Collections" else None
        
    except Exception as e:
        st.error(f"❌ Error loading Weaviate collections: {e}")
        logger.error(f"Collection selector error: {e}")
        return None

def render_backend_selector(
    key: str = "search_backend",
    default: str = "Weaviate"
) -> str:
    """
    Render a backend selector for choosing between Weaviate and FAISS
    
    Args:
        key: Unique key for the radio button
        default: Default selection
    
    Returns:
        Selected backend ("Weaviate" or "FAISS")
    """
    return st.radio(
        "Search Backend:",
        ["Weaviate (Cloud Vector DB)", "FAISS (Local Index)"],
        horizontal=True,
        key=key,
        help="Choose between cloud-based Weaviate or local FAISS indexes"
    )

def get_available_collections() -> List[Dict[str, Any]]:
    """
    Get list of available collections with metadata
    
    Returns:
        List of collection info dictionaries
    """
    try:
        weaviate_manager = get_weaviate_manager()
        collections = weaviate_manager.list_collections()
        
        collection_info = []
        for collection_name in collections:
            try:
                stats = weaviate_manager.get_collection_stats(collection_name)
                collection_info.append({
                    "name": collection_name,
                    "total_objects": stats.get('total_objects', 0),
                    "created_at": stats.get('created_at', 'Unknown')
                })
            except Exception as e:
                logger.warning(f"Could not get stats for {collection_name}: {e}")
                collection_info.append({
                    "name": collection_name,
                    "total_objects": 0,
                    "created_at": 'Unknown'
                })
        
        return collection_info
        
    except Exception as e:
        logger.error(f"Error getting collection info: {e}")
        return []

def render_collection_overview() -> None:
    """Render an overview of all available collections"""
    try:
        collections = get_available_collections()
        
        if not collections:
            st.info("📝 No collections found. Upload documents in the Ingestion tab to create collections.")
            return
        
        st.subheader("📚 Available Collections")
        
        for collection in collections:
            with st.expander(f"🗄️ {collection['name']} ({collection['total_objects']} documents)"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Documents", collection['total_objects'])
                with col2:
                    st.metric("Created", collection['created_at'][:10] if collection['created_at'] != 'Unknown' else 'Unknown')
                
                # Quick search within collection
                if st.button(f"🔍 Search {collection['name']}", key=f"search_{collection['name']}"):
                    st.session_state[f"selected_collection"] = collection['name']
                    st.rerun()
                    
    except Exception as e:
        st.error(f"❌ Error displaying collections: {e}")
        logger.error(f"Collection overview error: {e}")
