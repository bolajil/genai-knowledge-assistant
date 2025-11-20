"""
Streamlit Demo App for Response Formatter
Interactive testing of all formatter features
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.universal_response_formatter import format_and_display, add_formatter_settings
from utils.response_writer import rewrite_query_response


def main():
    st.set_page_config(
        page_title="Response Formatter Demo",
        page_icon="📝",
        layout="wide"
    )
    
    st.title("📝 Response Formatter Demo")
    st.markdown("Interactive demo of the Universal Response Formatter")
    
    # Add formatter settings
    add_formatter_settings(tab_name="Demo", location="sidebar")
    
    # Tabs for different demos
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Basic Demo",
        "📚 With Sources",
        "ℹ️ With Metadata",
        "🎨 Complete Example"
    ])
    
    # Tab 1: Basic Demo
    with tab1:
        st.header("Basic Response Formatting")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Input")
            
            query = st.text_area(
                "Query:",
                value="What are the governance powers?",
                height=100,
                key="basic_query"
            )
            
            raw_response = st.text_area(
                "Raw Response:",
                value="""The governance framework establishes three core powers: legislative authority, executive oversight, and judicial review. 

Legislative powers include creating bylaws and budget approval. Executive powers cover operational control and resource allocation. Judicial powers handle dispute resolution and compliance monitoring.

Key Points:
- Three-branch power structure
- Clear accountability mechanisms
- Regular audits required""",
                height=300,
                key="basic_response"
            )
            
            if st.button("Format Response", type="primary", key="basic_format"):
                st.session_state.basic_formatted = True
        
        with col2:
            st.subheader("Formatted Output")
            
            if st.session_state.get('basic_formatted'):
                format_and_display(
                    raw_response=raw_response,
                    query=query,
                    tab_name="Demo"
                )
            else:
                st.info("👈 Click 'Format Response' to see the formatted output")
    
    # Tab 2: With Sources
    with tab2:
        st.header("Response with Source Citations")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Input")
            
            query2 = st.text_area(
                "Query:",
                value="What are the review requirements?",
                height=100,
                key="sources_query"
            )
            
            raw_response2 = st.text_area(
                "Raw Response:",
                value="The policy requires annual reviews of all governance procedures. Reviews must be comprehensive and include stakeholder input. Documentation must be maintained for audit purposes.",
                height=200,
                key="sources_response"
            )
            
            st.subheader("Sources")
            
            num_sources = st.number_input("Number of sources:", 1, 5, 2, key="num_sources")
            
            sources = []
            for i in range(num_sources):
                with st.expander(f"Source {i+1}"):
                    doc = st.text_input(f"Document:", f"policy_manual.pdf", key=f"doc_{i}")
                    page = st.number_input(f"Page:", 1, 1000, 15+i*5, key=f"page_{i}")
                    section = st.text_input(f"Section:", f"Section {i+1}", key=f"section_{i}")
                    relevance = st.slider(f"Relevance:", 0.0, 1.0, 0.95-i*0.05, key=f"rel_{i}")
                    
                    sources.append({
                        'document': doc,
                        'page': page,
                        'section': section,
                        'relevance': relevance
                    })
            
            if st.button("Format with Sources", type="primary", key="sources_format"):
                st.session_state.sources_formatted = True
                st.session_state.sources_data = sources
        
        with col2:
            st.subheader("Formatted Output")
            
            if st.session_state.get('sources_formatted'):
                format_and_display(
                    raw_response=raw_response2,
                    query=query2,
                    tab_name="Demo",
                    sources=st.session_state.sources_data
                )
            else:
                st.info("👈 Click 'Format with Sources' to see the output")
    
    # Tab 3: With Metadata
    with tab3:
        st.header("Response with Metadata")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Input")
            
            query3 = st.text_area(
                "Query:",
                value="Explain the compliance requirements",
                height=100,
                key="meta_query"
            )
            
            raw_response3 = st.text_area(
                "Raw Response:",
                value="Compliance requirements include regular reporting, audit trails, and documentation standards. All activities must be logged and reviewed quarterly.",
                height=200,
                key="meta_response"
            )
            
            st.subheader("Metadata")
            
            confidence = st.slider("Confidence Score:", 0.0, 1.0, 0.92, key="confidence")
            response_time = st.number_input("Response Time (ms):", 0.0, 10000.0, 1250.5, key="resp_time")
            sources_count = st.number_input("Sources Count:", 0, 100, 3, key="src_count")
            index_used = st.selectbox("Index Used:", ["default_faiss", "AWS_index", "ByLaw_index"], key="index")
            
            metadata = {
                'confidence': confidence,
                'response_time': response_time,
                'sources_count': sources_count,
                'index_used': index_used
            }
            
            if st.button("Format with Metadata", type="primary", key="meta_format"):
                st.session_state.meta_formatted = True
                st.session_state.meta_data = metadata
        
        with col2:
            st.subheader("Formatted Output")
            
            if st.session_state.get('meta_formatted'):
                format_and_display(
                    raw_response=raw_response3,
                    query=query3,
                    tab_name="Demo",
                    metadata=st.session_state.meta_data
                )
            else:
                st.info("👈 Click 'Format with Metadata' to see the output")
    
    # Tab 4: Complete Example
    with tab4:
        st.header("Complete Example (All Features)")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Input")
            
            query4 = st.text_area(
                "Query:",
                value="Provide a comprehensive analysis of the governance framework",
                height=100,
                key="complete_query"
            )
            
            raw_response4 = st.text_area(
                "Raw Response:",
                value="""Executive Summary: The governance framework establishes a comprehensive system of oversight and accountability through three distinct branches of power.

Detailed Analysis:

Legislative Powers:
The legislative branch holds primary authority for policy creation and amendment. This includes the power to create bylaws, approve budgets, and establish committees. All legislative actions require proper documentation and stakeholder consultation.

Executive Powers:
Executive authority covers day-to-day operational control, resource allocation, and policy implementation. The executive branch ensures that approved policies are effectively executed and maintains operational efficiency.

Judicial Powers:
The judicial function provides oversight through dispute resolution, compliance monitoring, and enforcement of governance standards. This ensures accountability and adherence to established policies.

Key Findings:
- Balanced power distribution prevents concentration of authority
- Clear accountability mechanisms ensure transparency
- Regular audits maintain system integrity
- Stakeholder input is integrated at all levels

Recommendations:
1. Maintain quarterly review cycles
2. Enhance documentation standards
3. Strengthen stakeholder engagement
4. Implement continuous improvement processes""",
                height=400,
                key="complete_response"
            )
            
            show_comparison = st.checkbox("Show side-by-side comparison", key="show_comp")
            
            if st.button("Format Complete Example", type="primary", key="complete_format"):
                st.session_state.complete_formatted = True
        
        with col2:
            st.subheader("Formatted Output")
            
            if st.session_state.get('complete_formatted'):
                complete_sources = [
                    {
                        'document': 'governance_framework.pdf',
                        'page': 12,
                        'section': 'Chapter 2: Power Structure',
                        'relevance': 0.98
                    },
                    {
                        'document': 'bylaws.pdf',
                        'page': 15,
                        'section': 'Article 2',
                        'relevance': 0.95
                    },
                    {
                        'document': 'compliance_guide.pdf',
                        'page': 8,
                        'section': 'Section 3.1',
                        'relevance': 0.88
                    }
                ]
                
                complete_metadata = {
                    'confidence': 0.96,
                    'response_time': 2150.3,
                    'sources_count': 3,
                    'index_used': 'default_faiss',
                    'model_used': 'gpt-4',
                    'tokens_used': 1850
                }
                
                format_and_display(
                    raw_response=raw_response4,
                    query=query4,
                    tab_name="Demo",
                    sources=complete_sources,
                    metadata=complete_metadata,
                    show_comparison=show_comparison
                )
            else:
                st.info("👈 Click 'Format Complete Example' to see the output")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    ### 📚 Documentation
    - **RESPONSE_WRITER_QUICK_START.md** - Quick start guide
    - **RESPONSE_WRITER_GUIDE.md** - Complete documentation
    - **CROSS_TAB_FORMATTER_INTEGRATION.md** - Integration guide
    
    ### 🧪 Testing
    - Run: `python formatter_test_suite.py` for automated tests
    - Run: `python scripts/integrate_formatter_all_tabs.py` to integrate into tabs
    
    ### ⚙️ Settings
    Use the sidebar to control formatting options:
    - **Enable formatted responses** - Toggle formatting on/off
    - **LLM enhancement** - Use AI for better formatting (slower, costs ~$0.002)
    - **Enhancements** - Add table of contents, syntax highlighting, etc.
    - **Show sources** - Display source citations
    - **Show metadata** - Display query information
    """)


if __name__ == "__main__":
    main()
