"""
UI component for the enhanced research functionality.
This module provides a Streamlit UI to access the enhanced research capabilities.
"""

import streamlit as st
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
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

def render_research_ui():
    """Render the enhanced research UI components in Streamlit"""
    st.title("Enhanced Research Assistant")
    
    with st.expander("About Enhanced Research", expanded=False):
        st.markdown("""
        The Enhanced Research Assistant helps you generate comprehensive research content
        by leveraging multiple knowledge sources. It can perform different types of operations:
        
        - **Research Topic**: Generate detailed research reports on any topic
        - **Data Analysis**: Analyze data and identify patterns and insights
        - **Problem Solving**: Analyze problems and propose solutions
        - **Trend Identification**: Identify and analyze emerging trends
        
        Select your knowledge sources, specify your research task, and choose an operation
        to generate a detailed research report.
        """)
    
    # Import sources dynamically to avoid import errors if module is not available
    try:
        from utils.enhanced_multi_source_search import get_available_sources
        available_sources = get_available_sources()
    except Exception as e:
        logger.error(f"Error loading available sources: {str(e)}")
        available_sources = [
            "VaultMind Knowledge Base",
            "FAISS Vector Index",
            "Web Search (External)",
            "Technical Documentation",
            "Enterprise Wiki",
            "AWS Documentation (External)",
            "Cloud Provider APIs (External)"
        ]
    
    # UI Form for research configuration
    with st.form("research_form"):
        # Research task input
        task = st.text_area(
            "Research Task or Query",
            placeholder="Enter your research question or topic...",
            height=100
        )
        
        # Layout in columns for better UI organization
        col1, col2 = st.columns(2)
        
        with col1:
            # Operation selection
            operation = st.selectbox(
                "Research Operation",
                options=[
                    "Research Topic",
                    "Data Analysis",
                    "Problem Solving",
                    "Trend Identification"
                ],
                index=0
            )
        
        with col2:
            # Knowledge sources selection
            knowledge_sources = st.multiselect(
                "Knowledge Sources",
                options=available_sources,
                default=[available_sources[0]] if available_sources else []
            )
        
        # Advanced options
        with st.expander("Advanced Options", expanded=False):
            max_results = st.slider(
                "Max Results per Source",
                min_value=1,
                max_value=10,
                value=3
            )
            use_placeholders = st.checkbox(
                "Use Placeholder Data (Demo Mode)",
                value=True
            )
            st.markdown("---")
            official_priority = st.checkbox("Prioritize official websites of mentioned vendors/domains", value=True)
            domain_filters_input = st.text_input(
                "Domain filters (comma-separated)",
                placeholder="e.g., huggingface.co, weaviate.io, openai.com"
            )
            use_llm_answer = st.checkbox("Use LLM to compose answer (requires API key)", value=True)
            concise_mode = st.checkbox("Concise mode (Answer + Sources only)", value=True)
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
        submit_button = st.form_submit_button("Generate Research")
    
    # Handle form submission
    if submit_button:
        if not task:
            st.error("Please enter a research task or query.")
        elif not knowledge_sources:
            st.error("Please select at least one knowledge source.")
        else:
            # Show spinner while generating content
            with st.spinner("Generating enhanced research content..."):
                # Apply search overrides (domain filters and official priority)
                domain_list = [d.strip() for d in (domain_filters_input or "").split(",") if d.strip()]
                try:
                    # Local import to avoid hard dependency if module path changes
                    from utils.multi_source_search import set_search_overrides, clear_search_overrides
                except Exception:
                    set_search_overrides = None
                    clear_search_overrides = None
                try:
                    if set_search_overrides:
                        set_search_overrides(domains=domain_list, prioritize=official_priority)

                    # Generate research content
                    research_content = generate_research_content(
                        task=task,
                        operation=operation,
                        knowledge_sources=knowledge_sources,
                        max_results=max_results,
                        use_placeholders=use_placeholders,
                        ignore_cache=True,
                        use_llm_answer=use_llm_answer,
                        llm_model_name=llm_model_name,
                        concise_mode=concise_mode,
                        answer_style=answer_style
                    )

                    # Display the generated content
                    st.markdown("## Generated Research Content")
                    st.markdown(research_content)
                    
                    # Add download button for the content
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"research_{timestamp}.md"
                    
                    st.download_button(
                        label="Download Research Content",
                        data=research_content,
                        file_name=filename,
                        mime="text/markdown"
                    )
                    
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    logger.error(f"Error generating research content: {str(e)}")
                finally:
                    if clear_search_overrides:
                        try:
                            clear_search_overrides()
                        except Exception:
                            pass

def generate_research_content(
    task: str,
    operation: str,
    knowledge_sources: List[str],
    max_results: int = 3,
    use_placeholders: bool = False,
    ignore_cache: bool = True,
    use_llm_answer: bool = True,
    llm_model_name: Optional[str] = None,
    concise_mode: bool = True,
    answer_style: Optional[str] = None,
) -> str:
    """
    Generate enhanced research content using the specified parameters.
    
    Args:
        task: The research task or query
        operation: The type of operation
        knowledge_sources: List of knowledge sources to search
        max_results: Maximum number of results per source
        use_placeholders: Whether to use placeholder data
        
    Returns:
        Generated research content as markdown
    """
    try:
        # Import the modules
        from utils.enhanced_multi_source_search import perform_multi_source_search, format_search_results_for_agent
        from utils.new_enhanced_research import generate_enhanced_research_content
        
        # Log the research request
        logger.info(f"Generating research for task: {task}")
        logger.info(f"Operation: {operation}")
        logger.info(f"Knowledge sources: {', '.join(knowledge_sources)}")
        
        # Generate the research content
        content = generate_enhanced_research_content(
            task=task,
            operation=operation,
            knowledge_sources=knowledge_sources,
            ignore_cache=ignore_cache,
            use_llm_answer=use_llm_answer,
            llm_model_name=llm_model_name,
            concise_mode=concise_mode,
            answer_style=answer_style,
        )
        
        return content
        
    except ImportError as e:
        logger.error(f"Import error: {str(e)}")
        return f"""
        ## Module Import Error
        
        Could not import required modules for enhanced research. Please ensure that 
        `utils.enhanced_multi_source_search` and `utils.new_enhanced_research` are available.
        
        Error details: {str(e)}
        """
    except Exception as e:
        logger.error(f"Error generating research content: {str(e)}")
        return f"""
        ## Error Generating Research
        
        An error occurred while generating the research content:
        
        ```
        {str(e)}
        ```
        
        Please try again with different parameters or contact support if the issue persists.
        """

def add_to_dashboard(dashboard_page):
    """
    Add the enhanced research UI to an existing dashboard page.
    
    Args:
        dashboard_page: The Streamlit dashboard page to add the UI to
    """
    with dashboard_page:
        render_research_ui()

# Standalone app for testing
if __name__ == "__main__":
    st.set_page_config(
        page_title="Enhanced Research Assistant",
        page_icon="📚",
        layout="wide"
    )
    
    render_research_ui()
