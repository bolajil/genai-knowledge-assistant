"""
Agent thinking visualization component for Agent Assistant.
This file provides functions to show the agent's thought process during multi-source search.
"""

import streamlit as st
import time
import random
from typing import List, Dict, Any, Optional

def display_agent_thinking(task: str, sources: List[str], operation: str):
    """
    Display a visual representation of the agent's thinking process
    
    Args:
        task: The research task
        sources: List of knowledge sources being searched
        operation: The type of operation being performed
    """
    with st.container(border=True):
        st.markdown("#### Agent Thinking Process")
        
        # Show task analysis
        st.markdown("##### 1. Task Analysis")
        st.markdown(f"**Understanding the request:** Analyzing '{task}'")
        st.progress(100)
        
        # Show source selection
        st.markdown("##### 2. Source Selection")
        st.markdown("**Selected knowledge sources:**")
        for source in sources:
            st.markdown(f"- {source}")
        st.progress(100)
        
        # Show search process with animation
        st.markdown("##### 3. Information Retrieval")
        search_container = st.container()
        with search_container:
            st.markdown("<div class='searching-animation'>Searching across multiple sources...</div>", unsafe_allow_html=True)
            
            # Show retrieval progress for each source
            for i, source in enumerate(sources):
                progress_key = f"progress_{i}"
                progress_bar = st.progress(0, key=progress_key)
                
                # Simulate search progress
                for percent in range(0, 101, 20):
                    time.sleep(0.1)  # Slight delay for visual effect
                    progress_bar.progress(percent)
                
                st.markdown(f"✅ Retrieved information from **{source}**")
        
        # Show processing
        st.markdown("##### 4. Information Processing")
        st.markdown("Synthesizing information and generating response...")
        synth_progress = st.progress(0)
        for percent in range(0, 101, 25):
            time.sleep(0.2)  # Slight delay for visual effect
            synth_progress.progress(percent)
        
        st.markdown("✅ **Processing complete.** Research results are ready.")

def display_agent_thinking_placeholder():
    """Show a placeholder for agent thinking when not actively running"""
    with st.container():
        st.markdown("#### Agent Thinking Process")
        st.markdown("The agent will show its reasoning process here when you submit a task.")
        st.markdown("Select your task details above and click **Execute** to begin.")
        
        # Add a visual indicator
        st.markdown("""
        <div style="text-align: center; padding: 20px; color: #666;">
            <svg width="100" height="100" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" stroke="#ddd" stroke-width="2" fill="none" />
                <path d="M50 10 A40 40 0 0 1 90 50" stroke="#4CAF50" stroke-width="4" fill="none" />
                <circle cx="50" cy="10" r="6" fill="#4CAF50" />
            </svg>
            <p>Ready to start multi-source search</p>
        </div>
        """, unsafe_allow_html=True)

def display_search_summary(sources_used: List[str], result_count: int):
    """Display a summary of search results"""
    with st.container():
        st.markdown("#### Search Summary")
        st.markdown(f"**Sources searched:** {len(sources_used)}")
        st.markdown(f"**Results found:** {result_count}")
        
        # Display source breakdown
        st.markdown("**Source breakdown:**")
        for source in sources_used:
            # Generate random result count for demonstration
            source_results = random.randint(1, 5)
            st.markdown(f"- {source}: {source_results} results")
