"""
Enhanced Research Tab for VaultMind Knowledge Assistant - Performance Optimized Version
This module provides a standalone interface for the enhanced research capabilities with performance optimizations.
"""

import streamlit as st
import os
import sys
import json
import time
import logging
import random
import hashlib
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any, Optional
try:
    from utils.llm_config import get_available_llm_models, get_default_llm_model
except Exception:
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

# Constants for caching
CACHE_EXPIRY_SECONDS = 3600  # 1 hour cache expiry
MAX_CACHE_SIZE = 20  # Maximum number of research items to cache
MAX_HISTORY_ITEMS = 20  # Maximum number of history items to keep

# Simple search result class for testing
class SimpleSearchResult:
    def __init__(self, content, source, relevance=0.0):
        self.content = content
        self.source = source
        self.relevance = relevance

# Efficient caching function with TTL
def get_cache_key(task, operation, sources):
    """Generate a consistent hash-based cache key"""
    # Sort sources to ensure consistent key regardless of order
    sources_str = ",".join(sorted(sources))
    key_str = f"{task}|{operation}|{sources_str}"
    return hashlib.md5(key_str.encode()).hexdigest()

def clean_cache():
    """Remove expired and excess cache items"""
    if "research_cache" not in st.session_state:
        st.session_state.research_cache = {}
        return
        
    current_time = time.time()
    # Remove expired items
    expired_keys = [k for k, v in st.session_state.research_cache.items() 
                   if current_time - v["timestamp"] > CACHE_EXPIRY_SECONDS]
    for key in expired_keys:
        st.session_state.research_cache.pop(key, None)
    
    # If still too large, remove oldest items
    if len(st.session_state.research_cache) > MAX_CACHE_SIZE:
        sorted_items = sorted(st.session_state.research_cache.items(), 
                             key=lambda x: x[1]["timestamp"])
        for key, _ in sorted_items[:len(sorted_items) - MAX_CACHE_SIZE]:
            st.session_state.research_cache.pop(key, None)

# Parallel search function for multi-source queries
def parallel_search(query, sources, max_results=3):
    """Search multiple knowledge sources in parallel for improved performance"""
    
    # Helper function to search a single source
    def search_single_source(source):
        """Search a single knowledge source"""
        try:
            # Use our simple search implementation
            return simple_search(query, [source], max_results)
        except Exception as e:
            logger.error(f"Error searching {source}: {str(e)}")
            return []
    
    # Use ThreadPoolExecutor for parallel execution
    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(sources), 5)) as executor:
        # Submit all search tasks
        future_to_source = {executor.submit(search_single_source, source): source 
                           for source in sources}
        
        # Collect results as they complete with timeout
        for future in concurrent.futures.as_completed(future_to_source, timeout=10):
            source = future_to_source[future]
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Error processing {source}: {str(e)}")
    
    return all_results

# Mock search function with AWS security specific responses
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

# Memory-optimized history functions
def optimize_history_item(item):
    """Optimize a history item to reduce memory usage"""
    # Create a lightweight version for storage
    return {
        "task": item["task"],
        "operation": item["operation"],
        "sources": item["sources"],
        "timestamp": item["timestamp"],
        # Store only first 1000 chars of result for preview
        "result_preview": item["result"][:1000] + "..." if len(item["result"]) > 1000 else item["result"],
        # Store the full result hash for retrieval
        "result_hash": hashlib.md5(item["result"].encode()).hexdigest(),
        "performance": item.get("performance", {})
    }

def save_to_history(task, operation, sources, result, performance):
    """Save research to history with optimization"""
    # Create history item
    history_item = {
        "task": task,
        "operation": operation,
        "sources": sources,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "result": result,
        "performance": performance
    }
    
    # Optimize for storage
    optimized_item = optimize_history_item(history_item)
    
    # Save to history
    if "research_history" not in st.session_state:
        st.session_state.research_history = []
    
    st.session_state.research_history.insert(0, optimized_item)
    
    # Limit history size
    if len(st.session_state.research_history) > MAX_HISTORY_ITEMS:
        st.session_state.research_history = st.session_state.research_history[:MAX_HISTORY_ITEMS]
    
    # Also save full result to cache
    if "research_cache" not in st.session_state:
        st.session_state.research_cache = {}
        
    cache_key = get_cache_key(task, operation, sources)
    st.session_state.research_cache[cache_key] = {
        "content": result,
        "timestamp": time.time()
    }

def progressive_research_steps(progress_placeholder, status_placeholder, steps=None):
    """Show progressive research steps with smooth animation"""
    
    if steps is None:
        steps = [
            ("🔍 Initializing Research", "Loading research modules..."),
            ("📚 Gathering Information", "Searching knowledge sources..."),
            ("🧠 Processing Data", "Analyzing information..."),
            ("📊 Synthesizing Results", "Generating insights..."),
            ("📝 Formatting Report", "Creating final document..."),
        ]
    
    for step_title, step_desc in steps:
        # Update progress indicator
        progress_placeholder.markdown(f"""
        <div class="research-in-progress">
            <h4>{step_title}</h4>
            <p>{step_desc}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Update status message
        status_placeholder.info(f"Step: {step_desc}")
        
        # Add small delay for visual feedback
        time.sleep(0.3)

def render_enhanced_research():
    """Render the enhanced research tab in Streamlit with performance optimizations"""
    
    # Clean cache on page load to prevent memory issues
    clean_cache()
    
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
        contain: content;
    }
    
    .result-container {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 15px;
        margin-top: 20px;
        border-left: 4px solid #4CAF50;
        will-change: transform;
        contain: content;
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
        contain: content;
    }
    
    /* Performance optimization for large markdown content */
    .streamlit-expanderHeader {
        will-change: transform;
    }
    
    /* Optimize performance for research report container */
    .research-report-container {
        contain: content;
    }
    
    /* Virtualized list for history items */
    .history-list {
        contain: content;
        height: 100%;
    }
    
    /* Optimize tab rendering */
    .stTabs [data-baseweb="tab-panel"] {
        contain: content;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Enhanced header with content containment for better performance
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
        
        # Options for cleaner output and LLM synthesis
        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            use_llm_answer = st.checkbox("Use LLM to compose answer (requires API key)", value=True)
            concise_mode = st.checkbox("Concise mode (Answer + Sources only)", value=True)
        with col_b:
            answer_style = st.selectbox("Answer format", ["Narrative paragraph", "Concise bullet points"], index=0)
            llm_model_name = ""
            if use_llm_answer:
                models = get_available_llm_models()
                if models:
                    default_model = get_default_llm_model()
                    default_index = models.index(default_model) if default_model in models else 0
                    llm_model_name = st.selectbox("LLM Model", options=models, index=default_index)
                else:
                    st.info("No LLM models detected from .env. Default will be used if available.")
                    llm_model_name = ""

        # Submit button
        generate_button = st.form_submit_button("📝 Generate Research Report")
        
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
                
                # Initialize cache if needed
                if "research_cache" not in st.session_state:
                    st.session_state.research_cache = {}
                
                # Use cache if available and less than cache expiry time
                if (cache_key in st.session_state.research_cache and 
                    time.time() - st.session_state.research_cache[cache_key]["timestamp"] < CACHE_EXPIRY_SECONDS):
                    st.session_state.research_result = st.session_state.research_cache[cache_key]["content"]
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
                            
                            # Update progress with progressive steps
                            research_steps = [
                                ("🔍 Initializing Research", "Loaded optimized research module"),
                                ("📚 Gathering Information", f"Searching {len(selected_sources)} knowledge sources"),
                                ("🧠 Processing Data", "Analyzing search results"),
                                ("📊 Synthesizing Results", "Generating insights and findings"),
                                ("📝 Formatting Report", "Creating final research document")
                            ]
                            progressive_research_steps(progress_placeholder, status_placeholder, research_steps)
                            
                        except ImportError:
                            # Try the original module
                            try:
                                from utils.enhanced_research import generate_enhanced_research_content
                                module_name = "standard research"
                                module_found = True
                                logger.info("Using standard enhanced research module")
                                
                                # Update progress with progressive steps
                                research_steps = [
                                    ("🔍 Initializing Research", "Loaded standard research module"),
                                    ("📚 Gathering Information", f"Searching {len(selected_sources)} knowledge sources"),
                                    ("🧠 Processing Data", "Processing search results"),
                                    ("📊 Analyzing Content", "Analyzing research content"),
                                    ("📝 Formatting Report", "Finalizing research document")
                                ]
                                progressive_research_steps(progress_placeholder, status_placeholder, research_steps)
                                
                            except ImportError:
                                # If both fail, use fallback implementation
                                module_found = False
                                raise ImportError("No research modules found")
                        
                    except Exception as e:
                        # Use a fallback function with improved error reporting
                        logger.error(f"Error loading research modules: {str(e)}")
                        status_placeholder.error(f"⚠️ Error loading research modules: {str(e)}")
                        module_name = "fallback"
                        
                        def generate_enhanced_research_content(task, operation, knowledge_sources):
                            """Improved fallback research function when modules are not available"""
                            return f"""
                            ## Research Report: {task}
                            
                            ### Error: Research Module Unavailable
                            
                            The enhanced research module could not be loaded. This may be due to:
                            
                            1. Missing dependencies
                            2. Configuration issues
                            3. File path problems
                            
                            #### Technical Details
                            Error: {str(e)}
                            
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
                        ignore_cache=True,
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
                    
                    # Save to optimized history with performance metrics
                    save_to_history(
                        task=research_task,
                        operation=selected_operation,
                        sources=selected_sources,
                        result=research_result,
                        performance=performance_metrics
                    )
                    
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
                
                # Optimization: Split large content into sections for better rendering
                content = st.session_state.research_result
                
                # Display the actual research content
                st.markdown(content)
                
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
                current_item = st.session_state.research_history[0] if st.session_state.research_history else None
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
                        
                        for item in st.session_state.research_history[:5]:  # Last 5 items
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
    
    # Display research history with improved UI and virtualization
    if st.session_state.research_history and len(st.session_state.research_history) >= 1:
        with st.expander("📚 Research History", expanded=False):
            # Process two items at a time for efficiency
            history_items = st.session_state.research_history
            
            # More efficient rendering by processing items in batches
            for i in range(0, len(history_items), 2):
                col1, col2 = st.columns(2)
                
                # First item
                with col1:
                    if i < len(history_items):
                        item = history_items[i]
                        st.markdown(f"### {item['task'][:30]}...")
                        st.caption(f"{item['timestamp']} | {item['operation']}")
                        
                        # Display button for loading the result
                        if st.button(f"📂 Load", key=f"reload_{i}"):
                            st.session_state.research_task = item['task']
                            st.session_state.selected_operation = item['operation']
                            st.session_state.selected_sources = item['sources']
                            
                            # Get full result from cache if available
                            cache_key = get_cache_key(item['task'], item['operation'], item['sources'])
                            if "research_cache" in st.session_state and cache_key in st.session_state.research_cache:
                                st.session_state.research_result = st.session_state.research_cache[cache_key]["content"]
                            else:
                                # Fallback to stored preview if full result not in cache
                                st.session_state.research_result = item.get('result_preview', 'Full content not available')
                            
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
                            
                            # Get full result from cache if available
                            cache_key = get_cache_key(item['task'], item['operation'], item['sources'])
                            if "research_cache" in st.session_state and cache_key in st.session_state.research_cache:
                                st.session_state.research_result = st.session_state.research_cache[cache_key]["content"]
                            else:
                                # Fallback to stored preview if full result not in cache
                                st.session_state.research_result = item.get('result_preview', 'Full content not available')
                            
                            st.rerun()

if __name__ == "__main__":
    render_enhanced_research()
