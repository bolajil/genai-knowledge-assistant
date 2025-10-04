"""
Enhanced Research Tab for VaultMind Knowledge Assistant.
This module provides a standalone interface for the enhanced research capabilities.
"""

import streamlit as st
import os
import sys
import json
import time
import logging
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from utils.new_enhanced_research import clear_research_cache
try:
    from utils.llm_config import get_available_llm_models, get_default_llm_model
except Exception:
    # Graceful fallback if llm_config isn't available for any reason
    def get_available_llm_models():
        return []
    def get_default_llm_model():
        return ""

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize global variables
RESEARCH_OPERATIONS = [
    "Research Topic",
    "Data Analysis",
    "Problem Solving",
    "Trend Identification"
]

# Simple search result class for testing
class SimpleSearchResult:
    def __init__(self, content, source, relevance=0.0):
        self.content = content
        self.source = source
        self.relevance = relevance

# Mock search function for direct use without imports
def simple_search(query, sources, max_results=3):
    """Simple search function that returns mock results"""
    results = []
    
    # Check if query is about AWS security
    if "aws security" in query.lower() or ("aws" in query.lower() and "security" in query.lower()):
        # Predefined AWS security responses
        aws_responses = {
            "Indexed Documents": [
                "AWS security benefits include a comprehensive set of cloud security controls, reducing operational overhead compared to on-premises solutions. The AWS security infrastructure provides built-in protections against DDoS attacks, encryption capabilities, and compliance with major regulatory frameworks.",
                "AWS security features include Identity and Access Management (IAM) for fine-grained access control, AWS Shield for DDoS protection, and CloudTrail for audit logging. These services work together to create a defense-in-depth approach to cloud security.",
                "The AWS shared responsibility model clarifies security ownership between AWS and customers. AWS handles security OF the cloud, while customers manage security IN the cloud, allowing organizations to focus security efforts appropriately."
            ],
            "Web Search (External)": [
                "According to recent analyst reports, AWS security benefits include extensive compliance certifications (SOC, PCI DSS, HIPAA, FedRAMP) that help organizations meet regulatory requirements without managing compliance infrastructure themselves.",
                "AWS provides cost-effective security implementations by offering managed security services like GuardDuty, Inspector, and Security Hub, reducing capital expenditure on security infrastructure and lowering operational costs.",
                "Industry research shows that AWS security services can reduce security incident response time by up to 60% through automated threat detection and remediation capabilities."
            ],
            "Structured Data (External)": [
                "Statistical analysis of cloud security implementations shows AWS security controls offer 99.9% uptime for critical security services, with automated patching that reduces vulnerability windows by an average of 73% compared to on-premises solutions.",
                "Enterprise deployment metrics indicate AWS security implementations can reduce time-to-compliance by an average of 65% through pre-configured compliance frameworks and continuous compliance monitoring.",
                "Cost-benefit analysis of AWS security services shows an average ROI of 305% over three years, primarily through reduced security staffing requirements and lower capital expenses for security infrastructure."
            ]
        }
        
        # Add AWS-specific results for each source
        for source in sources:
            if source in aws_responses:
                source_responses = aws_responses[source]
                for i, content in enumerate(source_responses[:max_results]):
                    relevance = round(random.uniform(0.85, 0.98), 2)
                    result = SimpleSearchResult(
                        content=content,
                        source=source,
                        relevance=relevance
                    )
                    results.append(result)
    else:
        # Default generic results for other queries
        for source in sources:
            for i in range(max_results):
                relevance = round(random.uniform(0.7, 0.95), 2)
                content = f"Information about {query} from {source}. "
                content += f"This is result #{i+1} with relevance score {relevance}. "
                content += f"The query was: '{query}'"
                
                result = SimpleSearchResult(
                    content=content,
                    source=source,
                    relevance=relevance
                )
                results.append(result)
    
    return results

def get_available_knowledge_sources():
    """Get available knowledge sources from config or default list"""
    try:
        # Try to load from config
        from config.agent_config import KNOWLEDGE_SOURCES
        
        sources = []
        for source_name, source_info in KNOWLEDGE_SOURCES.items():
            if source_info.get("enabled", False):
                sources.append(source_name)
        
        return sources
    except ImportError:
        # Fallback to default sources
        return [
            "Indexed Documents",
            "Web Search (External)",
            "Structured Data (External)"
        ]

def render_enhanced_research():
    """Render the enhanced research tab in Streamlit with performance optimizations"""
    
    # Custom CSS for improved appearance and performance
    st.markdown("""
    <style>
    .research-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        color: white;
        will-change: transform;
    }
    
    .result-container {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 15px;
        margin-top: 20px;
        border-left: 4px solid #4CAF50;
        will-change: transform;
    }
    
    .source-item {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 8px 15px;
        margin: 5px 0;
        border-radius: 4px;
        display: inline-block;
        margin-right: 8px;
    }
    
    .status-message {
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    .success-message {
        background-color: rgba(76, 175, 80, 0.1);
        border-left: 4px solid #4CAF50;
    }
    
    .error-message {
        background-color: rgba(244, 67, 54, 0.1);
        border-left: 4px solid #F44336;
    }
    
    /* Animation for research in progress - optimized */
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.6; }
        100% { opacity: 1; }
    }
    
    .research-in-progress {
        animation: pulse 1.5s infinite;
        background-color: rgba(33, 150, 243, 0.1);
        border-left: 4px solid #2196F3;
        padding: 15px;
        border-radius: 5px;
        margin: 15px 0;
        will-change: opacity;
    }
    
    /* Performance optimization for large markdown content */
    .streamlit-expanderHeader {
        will-change: transform;
    }
    
    /* Optimize performance for research report container */
    .research-report-container {
        contain: content;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Enhanced header
    st.markdown("""
    <div class="research-header">
        <h1>📚 Enhanced Research Tool</h1>
        <p>Generate comprehensive research reports across multiple knowledge sources</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state for research
    if "research_history" not in st.session_state:
        st.session_state.research_history = []
    
    if "research_task" not in st.session_state:
        st.session_state.research_task = ""
    
    if "selected_operation" not in st.session_state:
        st.session_state.selected_operation = RESEARCH_OPERATIONS[0]
    
    if "selected_sources" not in st.session_state:
        st.session_state.selected_sources = []

    if "selected_llm_model" not in st.session_state:
        try:
            st.session_state.selected_llm_model = get_default_llm_model()
        except Exception:
            st.session_state.selected_llm_model = ""
    
    if "research_result" not in st.session_state:
        st.session_state.research_result = None
    
    if "research_in_progress" not in st.session_state:
        st.session_state.research_in_progress = False
    
    # Main input form
    with st.form(key="research_form"):
        # Research task input
        research_task = st.text_area(
            "Research Task or Query",
            value=st.session_state.research_task,
            placeholder="Enter your research question or topic...",
            height=100
        )
        
        # Side-by-side columns for operation and sources
        col1, col2 = st.columns(2)
        
        with col1:
            # Operation selection
            selected_operation = st.selectbox(
                "Research Operation",
                options=RESEARCH_OPERATIONS,
                index=RESEARCH_OPERATIONS.index(st.session_state.selected_operation) 
                if st.session_state.selected_operation in RESEARCH_OPERATIONS else 0
            )
        
        with col2:
            # Knowledge sources selection
            available_sources = get_available_knowledge_sources()
            selected_sources = st.multiselect(
                "Knowledge Sources",
                options=available_sources,
                default=st.session_state.selected_sources or available_sources[:1]
            )
        
        # Cache controls (allowed inside form)
        ignore_cache = st.checkbox("Bypass cache for this run", value=False)
        use_llm_answer = st.checkbox("Use LLM to compose answer (requires API key)", value=True)
        concise_mode = st.checkbox("Concise mode (Answer + Sources only)", value=True)

        # LLM model selection (shown only when using LLM)
        llm_model_name = ""
        answer_style = "Narrative paragraph"
        if use_llm_answer:
            models = get_available_llm_models()
            if models:
                llm_model_name = st.selectbox(
                    "LLM Model",
                    options=models,
                    index=models.index(st.session_state.selected_llm_model) if st.session_state.selected_llm_model in models else 0
                )
            else:
                st.info("No LLM models detected from .env. We'll use the default if available.")
                llm_model_name = st.session_state.selected_llm_model or ""
            answer_style = st.selectbox(
                "Answer format",
                options=["Narrative paragraph", "Concise bullet points"],
                index=0
            )
        
        # Submit button
        generate_button = st.form_submit_button("📝 Generate Research Report")
    
    # Outside the form: provide a clear-cache button
    cc1, cc2 = st.columns([1, 3])
    with cc1:
        if st.button("Clear cached results"):
            try:
                if "research_cache" in st.session_state:
                    st.session_state.research_cache.clear()
            except Exception:
                pass
            try:
                clear_research_cache()
            except Exception:
                pass
            st.success("Cleared cached research results")

    # Cache key for research results (to avoid redundant processing)
    def get_cache_key(task, operation, sources):
        """Generate a simple cache key"""
        sources_str = ",".join(sorted(sources))
        return f"{task}|{operation}|{sources_str}"
    
    # Initialize cache in session state if not exists
    if "research_cache" not in st.session_state:
        st.session_state.research_cache = {}
        
    # Handle form submission
    if generate_button:
        if not research_task:
            st.error("Please enter a research task or query.")
        elif not selected_sources:
            st.error("Please select at least one knowledge source.")
        else:
            # Update session state
            st.session_state.research_task = research_task
            st.session_state.selected_operation = selected_operation
            st.session_state.selected_sources = selected_sources
            st.session_state.research_in_progress = True
            
            # Generate the research
            try:
                # Check if we have this research cached
                cache_key = get_cache_key(research_task, selected_operation, selected_sources)
                
                # Use cache if available and less than 1 hour old
                if (not ignore_cache) and cache_key in st.session_state.research_cache:
                    cache_time, cached_result = st.session_state.research_cache[cache_key]
                    # Cache valid for 1 hour (3600 seconds)
                    if time.time() - cache_time < 3600:
                        st.session_state.research_result = cached_result
                        st.session_state.research_in_progress = False
                        st.success("⚡ Research loaded from cache")
                        st.rerun()
                        return
                
                with st.spinner("Generating research report..."):
                    # Show animated progress indicator with detailed steps
                    progress_placeholder = st.empty()
                    status_placeholder = st.empty()
                    
                    # Display initial progress
                    progress_placeholder.markdown("""
                    <div class="research-in-progress">
                        <h4>🔍 Researching...</h4>
                        <p>Initializing research process...</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Update status to show which modules are being loaded
                    status_placeholder.info("Loading research modules...")
                    
                    # Try to import the enhanced research module with proper error handling
                    start_time = time.time()
                    try:
                        # First try our optimized module
                        try:
                            from utils.new_enhanced_research import generate_enhanced_research_content
                            module_name = "optimized research"
                            module_found = True
                            logger.info("Using optimized enhanced research module")
                            
                            # Update progress
                            progress_placeholder.markdown("""
                            <div class="research-in-progress">
                                <h4>🔍 Researching...</h4>
                                <p>Optimized research module loaded. Gathering information from knowledge sources...</p>
                            </div>
                            """, unsafe_allow_html=True)
                            status_placeholder.success("✅ Loaded optimized research module")
                            
                        except ImportError:
                            # Try the original module
                            try:
                                from utils.enhanced_research import generate_enhanced_research_content
                                module_name = "standard research"
                                module_found = True
                                logger.info("Using standard enhanced research module")
                                
                                # Update progress
                                progress_placeholder.markdown("""
                                <div class="research-in-progress">
                                    <h4>🔍 Researching...</h4>
                                    <p>Standard research module loaded. Gathering information from knowledge sources...</p>
                                </div>
                                """, unsafe_allow_html=True)
                                status_placeholder.info("✓ Using standard research module")
                                
                            except ImportError:
                                # If both fail, use fallback implementation
                                module_found = False
                                raise ImportError("No research modules found")
                        
                    except Exception as e:
                        # Use a fallback function with improved error reporting
                        err_msg = str(e)
                        logger.error(f"Error loading research modules: {err_msg}")
                        status_placeholder.error(f"⚠️ Error loading research modules: {err_msg}")
                        module_name = "fallback"

                        def generate_enhanced_research_content(task, operation, knowledge_sources, **kwargs):
                            """Improved fallback research function when modules are not available"""
                            return f"""
                            ## Research Report: {task}
                            
                            ### Error: Research Module Unavailable
                            
                            The enhanced research module could not be loaded. This may be due to:
                            
                            1. Missing dependencies
                            2. Configuration issues
                            3. File path problems
                            
                            #### Technical Details
                            Error: {err_msg}
                            
                            #### Requested Research Parameters
                            - **Task:** {task}
                            - **Operation:** {operation}
                            - **Knowledge Sources:** {', '.join(knowledge_sources)}
                            
                            Please contact the system administrator for assistance.
                            """
                    
                    # Update progress before generating content
                    progress_placeholder.markdown("""
                    <div class="research-in-progress">
                        <h4>🔍 Researching...</h4>
                        <p>Generating comprehensive research content. This may take a moment...</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Generate the research content with performance timing
                    generation_start = time.time()
                    research_result = generate_enhanced_research_content(
                        task=research_task,
                        operation=selected_operation,
                        knowledge_sources=selected_sources,
                        ignore_cache=ignore_cache,
                        use_llm_answer=use_llm_answer,
                        llm_model_name=llm_model_name,
                        concise_mode=concise_mode,
                        answer_style=answer_style
                    )
                    generation_time = time.time() - generation_start
                    
                    # Calculate performance metrics
                    total_time = time.time() - start_time
                    performance_metrics = {
                        "total_time": total_time,
                        "generation_time": generation_time,
                        "module_used": module_name,
                        "sources_count": len(selected_sources)
                    }
                    
                    # Update progress to show completion
                    progress_placeholder.markdown("""
                    <div class="status-message success-message">
                        <h4>✅ Research Complete</h4>
                        <p>Your research report has been generated successfully.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show performance metrics
                    status_placeholder.success(f"✅ Research completed in {total_time:.2f}s using {module_name} module")
                    
                    # Update session state with result
                    st.session_state.research_result = research_result
                    
                    # Cache the research result with timestamp
                    st.session_state.research_cache[cache_key] = (time.time(), research_result)
                    
                    # Manage cache size (keep only the 10 most recent items if cache gets too large)
                    if len(st.session_state.research_cache) > 20:
                        # Sort by timestamp (oldest first)
                        sorted_cache = sorted(st.session_state.research_cache.items(), 
                                             key=lambda x: x[1][0])
                        # Remove oldest items
                        for old_key, _ in sorted_cache[:10]:
                            st.session_state.research_cache.pop(old_key, None)
                    
                    # Add to history with performance metrics
                    st.session_state.research_history.append({
                        "task": research_task,
                        "operation": selected_operation,
                        "sources": selected_sources,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "result": research_result,
                        "performance": performance_metrics
                    })
                    
            except Exception as e:
                logger.error(f"Error generating research: {str(e)}")
                st.error(f"An error occurred while generating research: {str(e)}")
                st.session_state.research_in_progress = False
            
            # Set research in progress to False after completion
            st.session_state.research_in_progress = False
    
    # Display research result if available
    if st.session_state.research_result:
        st.markdown("<hr>", unsafe_allow_html=True)
        
        # Display tabs for report and metadata
        tab1, tab2 = st.tabs(["📄 Research Report", "📊 Research Metadata"])
        
        with tab1:
            # Use container for better performance with large content
            with st.container():
                st.markdown("""
                <div class="result-container research-report-container">
                    <h3>Research Report</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Display the actual research content
                st.markdown(st.session_state.research_result)
                
                # Add download buttons for different formats
                col1, col2 = st.columns(2)
                
                with col1:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    report_filename = f"research_report_{timestamp}.md"
                    
                    st.download_button(
                        label="📥 Download as Markdown",
                        data=st.session_state.research_result,
                        file_name=report_filename,
                        mime="text/markdown"
                    )
                
                with col2:
                    # Add PDF download option (just prepare the button, actual PDF would require additional processing)
                    st.download_button(
                        label="📄 Download as PDF",
                        data=st.session_state.research_result,  # Would need conversion in a real implementation
                        file_name=f"research_report_{timestamp}.txt",
                        mime="text/plain",
                        disabled=True
                    )
                    st.caption("PDF download will be available in a future update")
        
        with tab2:
            # Display metadata about the research
            st.subheader("Research Parameters")
            
            # Create two columns for metadata display
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Query:** {st.session_state.research_task}")
                st.markdown(f"**Operation:** {st.session_state.selected_operation}")
                st.markdown(f"**Sources Used:** {len(st.session_state.selected_sources)}")
            
            with col2:
                # Get performance metrics if available
                current_item = st.session_state.research_history[-1] if st.session_state.research_history else None
                if current_item and "performance" in current_item:
                    perf = current_item["performance"]
                    st.markdown(f"**Processing Time:** {perf.get('total_time', 0):.2f} seconds")
                    st.markdown(f"**Module Used:** {perf.get('module_used', 'Unknown')}")
                    
                    # Display a performance chart if we have enough data
                    if len(st.session_state.research_history) > 1:
                        st.subheader("Performance Trends")
                        
                        # Get performance data from history
                        perf_data = {
                            "Query": [],
                            "Time (s)": []
                        }
                        
                        for item in st.session_state.research_history[-5:]:  # Last 5 items
                            if "performance" in item:
                                perf_data["Query"].append(item["task"][:20] + "...")
                                perf_data["Time (s)"].append(item["performance"].get("total_time", 0))
                        
                        if perf_data["Query"]:
                            import pandas as pd
                            chart_data = pd.DataFrame(perf_data)
                            st.bar_chart(chart_data.set_index("Query"))
            
            # Show all knowledge sources used
            st.subheader("Knowledge Sources")
            source_cols = st.columns(3)
            for i, source in enumerate(st.session_state.selected_sources):
                source_cols[i % 3].markdown(f"- {source}")
    
    # Display research history with improved UI
    if st.session_state.research_history and len(st.session_state.research_history) > 1:
        with st.expander("📚 Research History", expanded=False):
            # Create a more efficient layout for history items
            history_items = list(reversed(st.session_state.research_history[:-1]))  # Skip current result
            
            for i in range(0, len(history_items), 2):  # Process two items at a time
                col1, col2 = st.columns(2)
                
                # First item
                with col1:
                    if i < len(history_items):
                        item = history_items[i]
                        st.markdown(f"### {item['task'][:30]}...")
                        st.caption(f"{item['timestamp']} | {item['operation']}")
                        
                        # More efficient button handling
                        if st.button(f"📂 Load", key=f"reload_{i}"):
                            st.session_state.research_task = item['task']
                            st.session_state.selected_operation = item['operation']
                            st.session_state.selected_sources = item['sources']
                            st.session_state.research_result = item['result']
                            st.rerun()
                
                # Second item (if available)
                with col2:
                    if i + 1 < len(history_items):
                        item = history_items[i + 1]
                        st.markdown(f"### {item['task'][:30]}...")
                        st.caption(f"{item['timestamp']} | {item['operation']}")
                        
                        if st.button(f"📂 Load", key=f"reload_{i+1}"):
                            st.session_state.research_task = item['task']
                            st.session_state.selected_operation = item['operation']
                            st.session_state.selected_sources = item['sources']
                            st.session_state.research_result = item['result']
                            st.rerun()

if __name__ == "__main__":
    render_enhanced_research()
