"""
Agent Assistant with Hybrid Query Routing
Integrates LangGraph for complex queries and fast retrieval for simple queries
"""

import streamlit as st
import logging
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import hybrid system
from utils.hybrid_agent_integration import (
    initialize_hybrid_system,
    query_hybrid_system,
    get_hybrid_statistics,
    is_hybrid_available,
    reset_hybrid_metrics,
    export_hybrid_metrics,
    render_complexity_badge,
    render_approach_badge,
    format_reasoning_steps,
    get_available_indexes,
    validate_configuration
)


def render_agent_assistant_hybrid():
    """Render the hybrid agent assistant tab"""
    
    st.title("🤖 Agent Assistant (Hybrid Mode)")
    st.markdown("""
    **Intelligent Query Routing**: Automatically routes queries between fast retrieval and LangGraph agent based on complexity.
    - **Simple queries** → Fast retrieval (< 5s)
    - **Complex queries** → LangGraph agent with multi-step reasoning (< 30s)
    """)
    
    # Initialize session state
    if 'hybrid_initialized' not in st.session_state:
        st.session_state.hybrid_initialized = False
    if 'hybrid_chat_history' not in st.session_state:
        st.session_state.hybrid_chat_history = []
    if 'hybrid_config' not in st.session_state:
        st.session_state.hybrid_config = {
            'complexity_threshold': 50.0,
            'use_langgraph_for_moderate': False,
            'show_reasoning': True,
            'show_complexity': True
        }
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Hybrid Configuration")
        
        # Validate configuration
        config_status = validate_configuration()
        
        with st.expander("📊 System Status", expanded=True):
            st.write("**Configuration Status:**")
            st.write(f"✓ OpenAI API Key: {'✅' if config_status['openai_api_key'] else '❌'}")
            st.write(f"✓ LangGraph Available: {'✅' if config_status['langgraph_available'] else '❌'}")
            st.write(f"✓ Available Indexes: {len(config_status['available_indexes'])}")
            st.write(f"✓ System Ready: {'✅' if config_status['ready'] else '❌'}")
            
            if is_hybrid_available():
                st.success("🟢 Hybrid System Active")
            else:
                st.warning("🟡 Hybrid System Not Initialized")
        
        # Index selection
        available_indexes = get_available_indexes()
        if available_indexes:
            selected_indexes = st.multiselect(
                "Select Indexes",
                options=available_indexes,
                default=available_indexes[:min(3, len(available_indexes))],
                help="Select indexes for LangGraph agent to search"
            )
        else:
            st.error("No indexes found!")
            selected_indexes = []
        
        # Complexity threshold
        st.session_state.hybrid_config['complexity_threshold'] = st.slider(
            "Complexity Threshold",
            min_value=0.0,
            max_value=100.0,
            value=st.session_state.hybrid_config['complexity_threshold'],
            step=5.0,
            help="Queries above this score use LangGraph"
        )
        
        # Moderate query handling
        st.session_state.hybrid_config['use_langgraph_for_moderate'] = st.checkbox(
            "Use LangGraph for Moderate Queries",
            value=st.session_state.hybrid_config['use_langgraph_for_moderate'],
            help="Route moderate complexity queries to LangGraph"
        )
        
        # Display options
        st.session_state.hybrid_config['show_reasoning'] = st.checkbox(
            "Show Reasoning Steps",
            value=st.session_state.hybrid_config['show_reasoning'],
            help="Display LangGraph reasoning process"
        )
        
        st.session_state.hybrid_config['show_complexity'] = st.checkbox(
            "Show Complexity Analysis",
            value=st.session_state.hybrid_config['show_complexity'],
            help="Display query complexity analysis"
        )
        
        # Initialize button
        if st.button("🚀 Initialize Hybrid System", type="primary", disabled=not config_status['ready']):
            if selected_indexes:
                with st.spinner("Initializing hybrid system..."):
                    success = initialize_hybrid_system(
                        index_names=selected_indexes,
                        complexity_threshold=st.session_state.hybrid_config['complexity_threshold'],
                        use_langgraph_for_moderate=st.session_state.hybrid_config['use_langgraph_for_moderate']
                    )
                    
                    if success:
                        st.session_state.hybrid_initialized = True
                        st.success("✅ Hybrid system initialized!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to initialize. Check logs.")
            else:
                st.error("Please select at least one index")
        
        # Statistics
        if is_hybrid_available():
            with st.expander("📈 Performance Statistics"):
                stats = get_hybrid_statistics()
                
                if "error" not in stats:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Queries", stats.get('total_queries', 0))
                        st.metric("Fast Queries", stats.get('fast_queries', 0))
                    with col2:
                        st.metric("LangGraph Queries", stats.get('langgraph_queries', 0))
                        st.metric("Fallbacks", stats.get('fallback_count', 0))
                    
                    st.write(f"**Avg Fast Time:** {stats.get('avg_fast_time', 0):.2f}s")
                    st.write(f"**Avg LangGraph Time:** {stats.get('avg_langgraph_time', 0):.2f}s")
                    st.write(f"**Success Rate:** {stats.get('success_rate', 0):.1f}%")
                    
                    if st.button("🔄 Reset Metrics"):
                        reset_hybrid_metrics()
                        st.success("Metrics reset!")
                        st.rerun()
                    
                    if st.button("💾 Export Metrics"):
                        export_path = "hybrid_metrics.json"
                        if export_hybrid_metrics(export_path):
                            st.success(f"Exported to {export_path}")
                        else:
                            st.error("Export failed")
    
    # Main content area
    if not config_status['ready']:
        st.error("⚠️ System not ready. Please check configuration:")
        if not config_status['openai_api_key']:
            st.warning("- Missing OPENAI_API_KEY environment variable")
        if not config_status['langgraph_available']:
            st.warning("- LangGraph not installed. Run: `pip install langgraph`")
        if not config_status['available_indexes']:
            st.warning("- No FAISS indexes found in data/faiss_index/")
        return
    
    if not is_hybrid_available():
        st.info("👈 Click 'Initialize Hybrid System' in the sidebar to start")
        
        # Show example queries
        st.subheader("📝 Example Queries")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Simple Queries (Fast Retrieval):**")
            st.code("What is the board structure?")
            st.code("List all board members")
            st.code("Define quorum")
        
        with col2:
            st.markdown("**Complex Queries (LangGraph):**")
            st.code("Compare AWS Bylaws vs ByLaw2000 governance")
            st.code("Analyze board powers and recommend improvements")
            st.code("Synthesize all information about voting procedures")
        
        return
    
    # Chat interface
    st.subheader("💬 Chat with Hybrid Agent")
    
    # Display chat history
    for i, msg in enumerate(st.session_state.hybrid_chat_history):
        if msg['role'] == 'user':
            with st.chat_message("user"):
                st.write(msg['content'])
        else:
            with st.chat_message("assistant"):
                st.write(msg['content'])
                
                # Show metadata
                if 'metadata' in msg:
                    meta = msg['metadata']
                    
                    # Approach and complexity badges
                    badges_html = render_approach_badge(meta.get('approach', 'unknown'))
                    if st.session_state.hybrid_config['show_complexity'] and meta.get('complexity_score'):
                        badges_html += " " + render_complexity_badge(meta['complexity_score'])
                    st.markdown(badges_html, unsafe_allow_html=True)
                    
                    # Execution time
                    exec_time = meta.get('execution_time', 0)
                    st.caption(f"⏱️ Execution time: {exec_time:.2f}s")
                    
                    # Complexity reasoning
                    if st.session_state.hybrid_config['show_complexity'] and meta.get('complexity_reasoning'):
                        with st.expander("🧠 Complexity Analysis"):
                            st.info(meta['complexity_reasoning'])
                    
                    # Reasoning steps
                    if st.session_state.hybrid_config['show_reasoning'] and meta.get('reasoning_steps'):
                        with st.expander("🔍 Reasoning Steps"):
                            steps_text = format_reasoning_steps(meta['reasoning_steps'])
                            st.markdown(steps_text)
    
    # Query input
    user_query = st.chat_input("Ask a question...")
    
    # Force approach selector
    col1, col2, col3 = st.columns([3, 1, 1])
    with col2:
        force_fast = st.button("⚡ Force Fast")
    with col3:
        force_langgraph = st.button("🧠 Force LangGraph")
    
    if user_query:
        # Determine forced approach
        force_approach = None
        if force_fast:
            force_approach = "fast"
        elif force_langgraph:
            force_approach = "langgraph"
        
        # Add user message
        st.session_state.hybrid_chat_history.append({
            'role': 'user',
            'content': user_query
        })
        
        # Display user message
        with st.chat_message("user"):
            st.write(user_query)
        
        # Query hybrid system
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                # Use first selected index for fast retrieval
                index_name = selected_indexes[0] if selected_indexes else "default_faiss"
                
                result = query_hybrid_system(
                    query=user_query,
                    index_name=index_name,
                    force_approach=force_approach
                )
                
                # Display response
                st.write(result['response'])
                
                # Display metadata
                badges_html = render_approach_badge(result['approach'])
                if st.session_state.hybrid_config['show_complexity'] and result.get('complexity_score'):
                    badges_html += " " + render_complexity_badge(result['complexity_score'])
                st.markdown(badges_html, unsafe_allow_html=True)
                
                exec_time = result.get('execution_time', 0)
                st.caption(f"⏱️ Execution time: {exec_time:.2f}s")
                
                # Complexity reasoning
                if st.session_state.hybrid_config['show_complexity'] and result.get('complexity_reasoning'):
                    with st.expander("🧠 Complexity Analysis"):
                        st.info(result['complexity_reasoning'])
                
                # Reasoning steps
                if st.session_state.hybrid_config['show_reasoning'] and result.get('reasoning_steps'):
                    with st.expander("🔍 Reasoning Steps"):
                        steps_text = format_reasoning_steps(result['reasoning_steps'])
                        st.markdown(steps_text)
                
                # Add to history
                st.session_state.hybrid_chat_history.append({
                    'role': 'assistant',
                    'content': result['response'],
                    'metadata': {
                        'approach': result['approach'],
                        'complexity_score': result.get('complexity_score'),
                        'complexity_reasoning': result.get('complexity_reasoning'),
                        'execution_time': result.get('execution_time'),
                        'reasoning_steps': result.get('reasoning_steps', [])
                    }
                })
        
        st.rerun()
    
    # Clear chat button
    if st.session_state.hybrid_chat_history:
        if st.button("🗑️ Clear Chat History"):
            st.session_state.hybrid_chat_history = []
            st.rerun()


# Main entry point
if __name__ == "__main__":
    render_agent_assistant_hybrid()
