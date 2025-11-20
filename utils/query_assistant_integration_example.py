"""
Example: Integrating Response Writer into Query Assistant
Shows how to add beautiful markdown formatting to query responses
"""

import streamlit as st
from utils.response_writer import rewrite_query_response
from utils.unified_document_retrieval import search_documents
import time


def render_query_assistant_with_writer():
    """
    Enhanced Query Assistant with Response Writer
    """
    st.title("🔍 Query Assistant with Beautiful Responses")
    
    # Query input
    query = st.text_area(
        "Enter your question:",
        height=100,
        placeholder="What are the governance powers?"
    )
    
    # Settings in sidebar or expander
    with st.sidebar:
        st.subheader("⚙️ Response Settings")
        
        # Index selection
        index = st.selectbox(
            "Select Index",
            ["default_faiss", "AWS_index", "ByLaw_index"],
            help="Choose which document index to search"
        )
        
        st.markdown("---")
        
        # Response formatting options
        st.subheader("📝 Response Formatting")
        
        use_formatted_response = st.checkbox(
            "Use formatted response",
            value=True,
            help="Rewrite response in beautiful markdown format"
        )
        
        if use_formatted_response:
            use_llm_rewrite = st.checkbox(
                "🤖 Use LLM enhancement",
                value=False,
                help="Better quality, uses OpenAI (slower, costs ~$0.002)"
            )
            
            add_enhancements = st.checkbox(
                "✨ Add enhancements",
                value=True,
                help="Table of contents, syntax highlighting, etc."
            )
            
            show_comparison = st.checkbox(
                "Show side-by-side comparison",
                value=False,
                help="Display both original and formatted versions"
            )
    
    # Search button
    if st.button("🔍 Search", type="primary"):
        if not query:
            st.warning("⚠️ Please enter a question")
            return
        
        # Show progress
        with st.spinner("🔎 Searching documents..."):
            start_time = time.time()
            
            # Perform search
            try:
                results = search_documents(query, index)
                
                # Calculate response time
                response_time = (time.time() - start_time) * 1000
                
                # Extract sources (mock example - implement based on your system)
                sources = extract_sources_from_results(results)
                
                # Calculate confidence (mock - implement based on your system)
                confidence = calculate_confidence(results)
                
            except Exception as e:
                st.error(f"❌ Search error: {str(e)}")
                return
        
        # Display results
        st.markdown("---")
        
        if show_comparison and use_formatted_response:
            # Side-by-side comparison
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📄 Original Response")
                with st.container():
                    st.markdown(results)
            
            with col2:
                st.subheader("📝 Formatted Response")
                with st.container():
                    formatted_response = rewrite_query_response(
                        raw_response=results,
                        query=query,
                        sources=sources,
                        metadata={
                            'confidence': confidence,
                            'response_time': response_time,
                            'sources_count': len(sources),
                            'index_used': index
                        },
                        use_llm=use_llm_rewrite,
                        enhance=add_enhancements
                    )
                    st.markdown(formatted_response)
        
        elif use_formatted_response:
            # Show only formatted response
            formatted_response = rewrite_query_response(
                raw_response=results,
                query=query,
                sources=sources,
                metadata={
                    'confidence': confidence,
                    'response_time': response_time,
                    'sources_count': len(sources),
                    'index_used': index
                },
                use_llm=use_llm_rewrite,
                enhance=add_enhancements
            )
            st.markdown(formatted_response)
        
        else:
            # Show original response
            st.markdown(results)
        
        # Add feedback buttons
        st.markdown("---")
        st.subheader("💬 Was this helpful?")
        
        col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
        
        with col1:
            if st.button("👍 Yes"):
                st.success("Thanks for your feedback!")
                # Log positive feedback
        
        with col2:
            if st.button("👎 No"):
                st.info("We'll work on improving this!")
                # Log negative feedback
        
        with col3:
            if st.button("📋 Copy"):
                st.info("Response copied to clipboard!")
                # Implement clipboard copy


def extract_sources_from_results(results: str) -> list:
    """
    Extract source information from results
    Implement based on your system's response format
    """
    # Mock implementation - replace with your actual logic
    sources = [
        {
            'document': 'bylaws.pdf',
            'page': 15,
            'section': 'Article 2',
            'relevance': 0.95
        },
        {
            'document': 'governance_guide.pdf',
            'page': 8,
            'section': 'Section 3',
            'relevance': 0.88
        }
    ]
    
    # TODO: Implement actual source extraction from your results
    # Example patterns to look for:
    # - "Source: document.pdf, Page 15"
    # - "[1] document.pdf (p. 15)"
    # - Extract from metadata if available
    
    return sources


def calculate_confidence(results: str) -> float:
    """
    Calculate confidence score for results
    Implement based on your system's scoring
    """
    # Mock implementation - replace with your actual logic
    # Could be based on:
    # - Relevance scores from vector search
    # - Number of matching sources
    # - Semantic similarity
    # - LLM confidence
    
    return 0.92  # Example confidence score


# ============================================
# Alternative: Minimal Integration
# ============================================

def minimal_integration_example():
    """
    Simplest way to add response writer to existing Query Assistant
    """
    import streamlit as st
    from utils.response_writer import rewrite_query_response
    
    # Your existing query code
    query = st.text_input("Enter question:")
    
    if st.button("Search"):
        # Your existing search logic
        results = search_documents(query, "default_faiss")
        
        # Add this single line to format the response
        formatted = rewrite_query_response(results, query)
        
        # Display formatted response instead of raw results
        st.markdown(formatted)


# ============================================
# Alternative: Add to Existing Tab
# ============================================

def add_to_existing_query_assistant():
    """
    How to add to your existing query_assistant.py
    """
    
    # At the top of your file, add:
    # from utils.response_writer import rewrite_query_response
    
    # Find where you display results, probably something like:
    # st.markdown(results)
    
    # Replace with:
    """
    # Add toggle
    use_formatted = st.checkbox("📝 Format response", value=True)
    
    if use_formatted:
        formatted_results = rewrite_query_response(
            raw_response=results,
            query=query,
            sources=sources if 'sources' in locals() else None
        )
        st.markdown(formatted_results)
    else:
        st.markdown(results)
    """


# ============================================
# Test Function
# ============================================

def test_response_writer():
    """
    Test the response writer with sample data
    """
    from utils.response_writer import rewrite_query_response
    
    # Sample raw response
    raw_response = """
    The governance framework establishes three core powers: legislative authority, 
    executive oversight, and judicial review. 
    
    Legislative powers include creating bylaws and budget approval. 
    Executive powers cover operational control and resource allocation.
    Judicial powers handle dispute resolution and compliance monitoring.
    
    Key Points:
    - Three-branch power structure
    - Clear accountability mechanisms
    - Regular audits required
    """
    
    # Sample query
    query = "What are the governance powers?"
    
    # Sample sources
    sources = [
        {
            'document': 'bylaws.pdf',
            'page': 15,
            'section': 'Article 2',
            'relevance': 0.95
        }
    ]
    
    # Sample metadata
    metadata = {
        'confidence': 0.92,
        'response_time': 1250.5,
        'sources_count': 1,
        'index_used': 'default_faiss'
    }
    
    # Test formatting
    print("Testing Response Writer...")
    print("=" * 60)
    
    formatted = rewrite_query_response(
        raw_response=raw_response,
        query=query,
        sources=sources,
        metadata=metadata,
        use_llm=False,
        enhance=True
    )
    
    print(formatted)
    print("=" * 60)
    print("✅ Test complete!")


if __name__ == "__main__":
    # Run test
    test_response_writer()
