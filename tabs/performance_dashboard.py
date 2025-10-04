"""
Performance Monitoring Dashboard
Tracks Weaviate usage across all tabs
"""
from datetime import datetime
import streamlit as st
from utils.weaviate_manager import get_weaviate_manager


def show_performance_dashboard():
    """Display performance metrics"""
    wm = get_weaviate_manager()
    stats = wm.get_performance_stats()
    
    st.title("Weaviate Performance Dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Cache Hit Rate", 
                 f"{stats.get('cache_hits', 0)} hits")
    
    with col2:
        st.metric("Average Query Time", 
                 f"{sum(stats.get('query_times', [])) / len(stats.get('query_times', [1])):.2f} ms")
    
    st.subheader("Recent Activity")
    st.json(stats)


if __name__ == "__main__":
    show_performance_dashboard()
