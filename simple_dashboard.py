"""
Simplified VaultMind Dashboard
This version has minimal dependencies to make it run more easily.
"""

import streamlit as st
import datetime
import random

# Set page config
st.set_page_config(
    page_title="VaultMind GenAI Knowledge Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS for styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #4a4a4a;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Mock user data
user = {
    "username": "demo_user",
    "role": "admin",
    "email": "demo@example.com"
}

# Header with title
st.markdown('<h1 class="main-header">🧠 VaultMind GenAI Knowledge Assistant</h1>', unsafe_allow_html=True)

# Welcome message
st.markdown(f"**Welcome back, {user['username']}!** | Role: {user['role'].title()} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

# Available mock indexes
available_indexes = ["enterprise_docs", "aws_documentation", "company_policies"]

# Simple tab configuration
tabs = [
    "🔍 Query Assistant",
    "🔎 Multi-Source Search",
    "📚 Enhanced Research"
]

# Create tabs
tab_objects = st.tabs(tabs)

# Query Assistant Tab
with tab_objects[0]:
    st.header("🔍 Query Assistant")
    st.info(f"Logged in as: **{user['username']}** ({user['role'].title()})")
    
    selected_index = st.selectbox("Select index:", available_indexes)
    query = st.text_input("Enter your question:")
    
    if st.button("Search") and query:
        st.info("Searching...")
        st.success(f"Searching '{query}' in {selected_index}")
        
        # Mock results
        st.markdown("### Results")
        for i in range(3):
            with st.expander(f"Result {i+1}"):
                st.write(f"This is a mock result for query: '{query}' from index: {selected_index}")
                st.write(f"Relevance score: {random.uniform(0.7, 0.95):.2f}")

# Multi-Source Search Tab
with tab_objects[1]:
    st.header("🔎 Multi-Source Search")
    st.write("Search and retrieve information from multiple knowledge sources")
    
    # Main query form
    col1, col2 = st.columns([3, 1])
    
    with col1:
        multi_query = st.text_input(
            "Enter your question or search query",
            placeholder="e.g., What are the best practices for AWS deployment?"
        )
    
    with col2:
        search_button = st.button("🔍 Search", use_container_width=True)
    
    # Source selection
    source_options = [
        "VaultMind Knowledge Base",
        "Web Search",
        "Document Repository",
        "Code Repository",
        "Enterprise Data"
    ]
    selected_sources = st.multiselect(
        "Select sources to search",
        options=source_options,
        default=source_options[:2]
    )
    
    # Handle search button click
    if search_button:
        if not multi_query:
            st.error("Please enter a query to search for.")
        elif not selected_sources:
            st.error("Please select at least one source to search.")
        else:
            # Perform search
            with st.spinner("Searching across sources..."):
                st.success(f"Found results for '{multi_query}' across {len(selected_sources)} sources")
                
                # Display mock results
                st.markdown("## Search Results")
                
                for i, source in enumerate(selected_sources):
                    relevance = round(random.uniform(0.6, 0.98), 2)
                    with st.expander(f"Result #{i+1} from {source} (Relevance: {relevance})"):
                        st.write(f"Mock result for '{multi_query}' from {source}. ")
                        st.write(f"This is search result #{i+1} with relevance score {relevance}. ")
                        st.write(f"The data was retrieved at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")

# Enhanced Research Tab
with tab_objects[2]:
    st.header("📚 Enhanced Research Tool")
    st.write("Generate comprehensive research reports across multiple knowledge sources")
    
    # Main input form
    with st.form(key="research_form"):
        # Research task input
        research_task = st.text_area(
            "Research Task or Query",
            placeholder="Enter your research question or topic...",
            height=100
        )
        
        # Side-by-side columns for operation and sources
        col1, col2 = st.columns(2)
        
        with col1:
            # Operation selection
            selected_operation = st.selectbox(
                "Research Operation",
                options=[
                    "Research Topic",
                    "Data Analysis",
                    "Problem Solving",
                    "Trend Identification"
                ]
            )
        
        with col2:
            # Knowledge sources selection
            selected_research_sources = st.multiselect(
                "Knowledge Sources",
                options=source_options,
                default=source_options[:1]
            )
        
        # Submit button
        generate_button = st.form_submit_button("📝 Generate Research Report")
    
    # Handle form submission
    if generate_button:
        if not research_task:
            st.error("Please enter a research task or query.")
        elif not selected_research_sources:
            st.error("Please select at least one knowledge source.")
        else:
            # Generate the research
            with st.spinner("Generating research report..."):
                st.success("Research report generated successfully!")
                
                # Display mock research result
                st.markdown("## Research Results")
                
                st.markdown(f"""
                ### Research Report: {research_task}
                
                **Operation:** {selected_operation}
                **Sources:** {', '.join(selected_research_sources)}
                **Generated at:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                
                #### Summary
                This is a mock summary of research on '{research_task}' using the {selected_operation} operation.
                
                #### Key Findings
                1. First mock finding about {research_task}
                2. Second mock finding about {research_task}
                3. Third mock finding about {research_task}
                
                #### Recommendations
                - Recommendation 1 for '{research_task}'
                - Recommendation 2 for '{research_task}'
                - Recommendation 3 for '{research_task}'
                """)
                
                # Download button
                st.download_button(
                    label="📥 Download Report as Markdown",
                    data=f"# Research Report: {research_task}\n\n",
                    file_name=f"research_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
