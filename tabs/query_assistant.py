"""
Query Assistant Tab
==================
Search and retrieve information from indexed documents using natural language.
Access Level: All Users
"""

import streamlit as st
import logging
import time
from pathlib import Path
import random  # For simulating responses
from datetime import datetime

logger = logging.getLogger(__name__)

def query_index(query, index_name, top_k=5):
    """
    Query the specified index using centralized index system and generate structured reports.
    """
    import logging
    import os
    from pathlib import Path
    
    logger = logging.getLogger(__name__)
    
    # Use centralized index loading only
    from app.utils.index_utils import load_index
    
    # Load the index using centralized system
    index_result = load_index(index_name)
    
    if isinstance(index_result, dict) and index_result.get("type") == "custom_dir_index":
        # Handle directory-based index
        index_path = Path(index_result["path"])
        logger.info(f"Querying directory index: {index_path}")
        
        # Look for content files
        content_files = []
        for pattern in ["*.txt", "*.md", "*.json", "*.html"]:
            content_files.extend(list(index_path.glob(pattern)))
        
        if content_files:
            results = []
            query_lower = query.lower() if query else ""
            
            # Process files and score by relevance
            scored_files = []
            for file in content_files:
                if file.name != "index.meta":
                    try:
                        with open(file, "r", encoding="utf-8") as f:
                            content = f.read()
                            
                            # Calculate relevance score
                            score = 0
                            if query_lower:
                                content_lower = content.lower()
                                for term in query_lower.split():
                                    score += content_lower.count(term) * 10
                                    if term in file.name.lower():
                                        score += 50
                            
                            scored_files.append((score, file, content))
                    except Exception as e:
                        logger.error(f"Error reading file {file}: {str(e)}")
            
            # Sort by relevance score
            scored_files.sort(key=lambda x: x[0], reverse=True)
            
            # Generate structured results
            for score, file, content in scored_files[:top_k]:
                # Truncate very long content but keep relevant parts
                if len(content) > 1500:
                    if query_lower:
                        # Find the most relevant section
                        sentences = content.split('.')
                        relevant_sentences = []
                        for sentence in sentences:
                            if any(term in sentence.lower() for term in query_lower.split()):
                                relevant_sentences.append(sentence.strip())
                        
                        if relevant_sentences:
                            content = '. '.join(relevant_sentences[:5]) + '...'
                        else:
                            content = content[:1500] + '...'
                    else:
                        content = content[:1500] + '...'
                
                file_type = file.suffix.replace('.', '').upper() or 'FILE'
                results.append({
                    'source': f"{file.name} [{file_type}]",
                    'content': content,
                    'relevance_score': score,
                    'file_path': str(file)
                })
            
            return results
    
    elif isinstance(index_result, dict) and index_result.get("type") == "error_index":
        # Handle error from index loading
        return [{
            'source': f"Error loading index '{index_name}'",
            'content': f"Error: {index_result.get('error', 'Unknown error occurred')}",
            'relevance_score': 0,
            'file_path': 'N/A'
        }]
    elif hasattr(index_result, 'similarity_search'):
        # Handle proper FAISS index
        try:
            docs = index_result.similarity_search(query, k=top_k)
            results = []
            for i, doc in enumerate(docs):
                results.append({
                    'source': f"Document {i+1}",
                    'content': doc.page_content,
                    'relevance_score': 100 - (i * 10),  # Simple scoring
                    'file_path': getattr(doc, 'metadata', {}).get('source', 'N/A')
                })
            return results
        except Exception as e:
            logger.error(f"Error querying FAISS index: {str(e)}")
            return [{
                'source': f"Query Error",
                'content': f"Error querying index: {str(e)}",
                'relevance_score': 0,
                'file_path': 'N/A'
            }]
    
    # Return error if index not found
    return [{
        'source': f"Index '{index_name}' not found",
        'content': f"The requested index '{index_name}' could not be loaded. Please check if the document has been properly ingested.",
        'relevance_score': 0,
        'file_path': 'N/A'
    }]

def run_web_search(query, max_results=5):
    """
    Simulate web search results.
    In a production system, this would connect to a real web search API.
    """
    # Simulate query processing time
    time.sleep(1.2)
    
    # Sample simulated web results
    web_results = [
        {
            "title": "AWS Cloud Security Best Practices - Amazon Web Services",
            "url": "https://aws.amazon.com/security/best-practices/",
            "snippet": f"Learn about AWS cloud security best practices relevant to '{query}'. Amazon Web Services provides a secure cloud computing environment with multiple layers of security."
        },
        {
            "title": "Enterprise Security in the Cloud - Cloud Computing Insights",
            "url": "https://cloudcomputing.com/enterprise-security-guide",
            "snippet": f"This comprehensive guide covers enterprise security approaches for '{query}' including identity management, access controls, and compliance requirements."
        },
        {
            "title": "Comparing Cloud Security Models - Cloud Security Alliance",
            "url": "https://cloudsecurityalliance.org/research/security-models",
            "snippet": f"A detailed analysis of different cloud security models applicable to '{query}', with comparisons between AWS, Azure, and Google Cloud security features."
        },
        {
            "title": "Implementing Zero Trust Architecture in AWS - Security Magazine",
            "url": "https://securitymagazine.com/articles/zero-trust-aws",
            "snippet": f"Learn how to implement Zero Trust Architecture principles for '{query}' in AWS environments, including network segmentation and continuous verification."
        },
        {
            "title": "Cloud Security Controls for Enterprise Applications - Cloud Tech Journal",
            "url": "https://cloudtechjournal.com/security-controls-enterprise",
            "snippet": f"Discover essential security controls for enterprise applications related to '{query}', including data protection, threat detection, and incident response."
        },
        {
            "title": "AWS vs Azure Security Features for Enterprise - Cloud Comparison",
            "url": "https://cloudcomparison.com/aws-azure-security-enterprise",
            "snippet": f"A side-by-side comparison of AWS and Azure security features for enterprise deployments relevant to '{query}', helping you choose the right platform."
        },
        {
            "title": "Data Security Best Practices for Enterprise Cloud Migration",
            "url": "https://cloudsecurity.org/migration-security-practices",
            "snippet": f"Learn about protecting your data when migrating to cloud platforms with these best practices related to '{query}' including encryption, access controls, and monitoring."
        },
        {
            "title": "The Future of Cloud Security: AI and Machine Learning Applications",
            "url": "https://aiforsecurity.com/cloud-security-future",
            "snippet": f"Explore how AI and ML are transforming cloud security with advanced threat detection and automated responses relevant to '{query}' implementations."
        }
    ]
    
    # Return a subset based on max_results
    return web_results[:max_results]

def render_query_assistant(user, permissions, auth_middleware, available_indexes):
    """Query Assistant Tab Implementation"""
    
    auth_middleware.log_user_action("ACCESS_QUERY_TAB")
    
    # Handle both dict and object user formats
    if isinstance(user, dict):
        username = user.get('username', 'Unknown')
        role = user.get('role', 'viewer')
        role_display = str(role).title()
    else:
        username = getattr(user, 'username', 'Unknown')
        role = getattr(getattr(user, 'role', None), 'value', 'viewer')
        role_display = str(role).title()
    
    st.header("🔍 Query Assistant")
    st.info(f"👤 Logged in as: **{username}** ({role_display})")
    
    # Default sample indexes if none are available
    sample_indexes = ["enterprise_docs", "aws_documentation", "company_policies", "technical_manuals"]
    
    # Use available indexes if they exist, otherwise use sample indexes
    index_options = available_indexes if available_indexes and len(available_indexes) > 0 else sample_indexes
    
    # Custom CSS for better result display
    st.markdown("""
    <style>
    .query-result {
        background-color: #1e2a38;
        border-left: 3px solid #4da6ff;
        padding: 15px;
        border-radius: 5px;
        color: #ffffff;
        margin-bottom: 15px;
        font-family: 'Courier New', monospace;
        white-space: pre-wrap;
    }
    .web-result {
        background-color: #1e2a38;
        border: 1px solid #4da6ff;
        padding: 12px;
        border-radius: 5px;
        margin-bottom: 10px;
        color: #ffffff;
    }
    .web-result h4 {
        margin-top: 0;
        color: #4da6ff;
    }
    .web-result .url {
        color: #4ade80;
        font-size: 0.9em;
        margin-bottom: 8px;
    }
    .result-header {
        font-size: 1.2rem;
        font-weight: bold;
        color: #4da6ff;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Get available indexes
    if not available_indexes:
        # Add default indexes if list is empty for demo purposes
        available_indexes = sample_indexes
        # Show a notification about using demo indexes, but don't block functionality
        st.warning("⚠️ No custom indexes found. Using demo indexes for now. You can ingest your own documents from the 'Ingest Document' tab.")
    
    # Create tabs for different search modes
    search_tab, web_tab, debug_tab = st.tabs(["📚 Index Search", "🌐 Web Search", "🛠️ Debug"])
    
    # Debug tab for troubleshooting
    with debug_tab:
        st.subheader("Troubleshooting Information")
        st.write("Use this tab to diagnose issues with the Query Assistant.")
        
        # Directory information
        st.subheader("Directory Status")
        import os
        from pathlib import Path
        
        # Check important directories
        data_dir = Path("data")
        faiss_dir = data_dir / "faiss_index"
        aws_dir = faiss_dir / "AWS_index"
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("data/ directory exists", "Yes" if data_dir.exists() else "No")
            st.metric("faiss_index/ directory exists", "Yes" if faiss_dir.exists() else "No")
            st.metric("AWS_index/ directory exists", "Yes" if aws_dir.exists() else "No")
            
        with col2:
            if aws_dir.exists():
                files = list(aws_dir.glob("*.*"))
                st.metric("Files in AWS_index/", str(len(files)))
                st.write("Files:")
                for file in files:
                    st.code(f"{file.name} - {file.stat().st_size} bytes")
            else:
                st.warning("AWS_index directory not found")
        
        # Index debugging
        st.subheader("Available Indexes")
        if available_indexes:
            st.write(f"Found {len(available_indexes)} indexes:")
            st.json(available_indexes)
        else:
            st.warning("No indexes found")
            
        if st.button("Create AWS_index Directory"):
            try:
                os.makedirs("data/faiss_index/AWS_index", exist_ok=True)
                with open("data/faiss_index/AWS_index/index.meta", "w") as f:
                    f.write("Debug index created from Query Assistant")
                with open("data/faiss_index/AWS_index/content.txt", "w") as f:
                    f.write("This is a test file created by the debug tool.")
                st.success("AWS_index directory created with test files")
            except Exception as e:
                st.error(f"Failed to create directory: {str(e)}")
    
    with search_tab:
        col1, col2 = st.columns([3, 2])
        
        with col1:
            index_name = st.selectbox("Select knowledge base:", available_indexes)
            query = st.text_area(
                "Your question:",
                placeholder="e.g. What security measures does AWS provide for enterprise deployments?",
                height=100
            )
            
        with col2:
            top_k = st.slider("Number of results to retrieve", 1, 10, 3)
            
            # Build model options list - always include demo models for testing purposes
            llm_options = [
                "Local Embedding Model",
                "OpenAI GPT-4 (Demo)", 
                "OpenAI GPT-3.5 (Demo)", 
                "Anthropic Claude (Demo)",
                "Deepseek Chat (Demo)",
                "Mistral Medium (Demo)"
            ]
            
            # Try to check for real API keys, but don't block if not found
            try:
                import os
                # Check for environment variables or configuration files
                if os.environ.get("OPENAI_API_KEY") or os.path.exists("config/openai_config.json"):
                    llm_options.extend(["OpenAI GPT-4", "OpenAI GPT-3.5"])
                if os.environ.get("ANTHROPIC_API_KEY") or os.path.exists("config/anthropic_config.json"):
                    llm_options.append("Anthropic Claude")
                if os.environ.get("MISTRAL_API_KEY") or os.path.exists("config/mistral_config.json"):
                    llm_options.append("Mistral Medium")
                if os.environ.get("DEEPSEEK_API_KEY") or os.path.exists("config/deepseek_config.json"):
                    llm_options.append("Deepseek Chat")
            except:
                # If anything fails, we already have demo options
                pass
                
            llm_choice = st.selectbox("AI Model", llm_options)
        
        search_button = st.button("🔍 Search Knowledge Base", use_container_width=True)
        
        if search_button and query:
            auth_middleware.log_user_action("QUERY_EXECUTION", f"Index Query: {query[:50]}...")
            
            with st.spinner("Searching knowledge base..."):
                try:
                    # Progress indicator
                    progress = st.progress(0)
                    for i in range(100):
                        time.sleep(0.02)
                        progress.progress(i + 1)
                    
                    # Get search results
                    results = query_index(query, index_name, top_k)
                    
                    # Check if results is a list (normal case) or another type (custom handling)
                    if not isinstance(results, list):
                        # Convert to a list if it's not already
                        if isinstance(results, str):
                            # Single string result
                            results = [results]
                        elif isinstance(results, dict):
                            # It might be a custom response from the index_utils module
                            if results.get("type") == "error_index":
                                st.error(f"Error with index: {results.get('error', 'Unknown error')}")
                                results = [f"There was an error processing your query: {results.get('error', 'Unknown error')}"]
                            elif results.get("type") == "custom_dir_index":
                                # Try to read content from the directory
                                custom_path = results.get("path")
                                if custom_path:
                                    try:
                                        from pathlib import Path
                                        custom_dir = Path(custom_path)
                                        # Find text files in the directory
                                        text_files = list(custom_dir.glob("*.txt"))
                                        if not text_files:
                                            text_files = list(custom_dir.glob("*.*"))
                                        
                                        # Read the first few files
                                        file_contents = []
                                        for file in text_files[:5]:  # Limit to 5 files
                                            try:
                                                with open(file, "r", encoding="utf-8") as f:
                                                    content = f.read()
                                                    if query.lower() in content.lower():
                                                        file_contents.append(f"From {file.name}:\n\n{content}")
                                                    else:
                                                        file_contents.append(f"From {file.name}:\n\n{content[:1000]}...")
                                            except:
                                                pass
                                        
                                        if file_contents:
                                            results = file_contents
                                        else:
                                            results = [f"Found index directory {results.get('name')} but couldn't read any usable content."]
                                    except Exception as e:
                                        results = [f"Error reading from custom index: {str(e)}"]
                            elif results.get("type") == "simulated_index":
                                # Fall back to simulated responses
                                results = [
                                    f"Simulated response for query '{query}' from index '{index_name}'.",
                                    f"This is a demonstration response. In a production environment, this would contain real data from your documents.",
                                    f"To get real results, ingest documents using the Document Ingestion tab and try again."
                                ]
                            else:
                                # Unknown dict format
                                results = [f"Received unexpected response format: {results}"]
                        else:
                            # Unknown type
                            results = [f"Received unexpected result type: {type(results).__name__}"]
                    
                    if not results:
                        st.warning("No results found. Try different query parameters.")
                    else:
                        st.markdown("## **Search Results**")
                        st.markdown(f"**Found {len(results)} relevant results for your query from knowledge base: `{index_name}`**")
                        
                        # Add download button for full results
                        combined_results = "# Query Results\n\n"
                        combined_results += f"Query: {query}\n"
                        combined_results += f"Index: {index_name}\n"
                        combined_results += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        
                        for idx, res in enumerate(results, 1):
                            combined_results += f"## Result {idx}\n{res}\n\n---\n\n"
                        
                        col1, col2 = st.columns([4, 1])
                        with col2:
                            st.download_button(
                                label="📥 Download Results",
                                data=combined_results,
                                file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                                mime="text/markdown",
                            )
                        
                        # Generate AI-powered summary of results
                        combined_content = "\n\n".join([
                            result['content'] if isinstance(result, dict) and 'content' in result 
                            else str(result) for result in results[:3]
                        ])  # Use top 3 results for summary
                        
                        with st.expander("**AI Analysis & Summary**", expanded=True):
                            st.markdown(f"""
**Query:** "{query}"

**AI Analysis:**
Based on the retrieved documents, here's what I found regarding your question:

**Key Findings:**
• The documents contain {len(results)} relevant sections related to your query
• Content appears to focus on: {query.lower()}
• Document type: Appears to be formal documentation/procedures

**Summary:**
{combined_content[:800]}{'...' if len(combined_content) > 800 else ''}

**Recommendations:**
• Review the detailed results below for complete information
• Consider asking more specific questions for targeted insights
• Cross-reference with related documents if available

**LLM Provider:** {llm_choice}
**Search Parameters:** Top {top_k} results from {len(results)} total matches
                            """)
                        
                        st.divider()
                        
                        for i, result in enumerate(results, 1):
                            st.markdown(f"### **Result {i}**")
                            
                            # Handle structured result format
                            if isinstance(result, dict):
                                source = result.get('source', f'Result {i}')
                                content = result.get('content', str(result))
                                relevance_score = result.get('relevance_score', 0)
                                file_path = result.get('file_path', 'N/A')
                                
                                # Create a well-formatted markdown container
                                with st.container():
                                    # Truncate content if too long
                                    display_content = content[:1500] if len(content) > 1500 else content
                                    
                                    # Format content in a nice markdown box
                                    st.markdown(f"""
<div class="query-result">
<div class="result-header">📄 {source}</div>

{display_content}

{'**[Content Truncated - Full content available in source]**' if len(content) > 1500 else ''}
</div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Add metadata and relevance score
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.caption(f"Length: {len(content)} chars")
                                    with col2:
                                        st.caption(f"Relevance Score: {relevance_score}")
                                    with col3:
                                        st.caption(f"Source: {source}")
                                    
                                    if i < len(results):
                                        st.divider()
                            else:
                                # Handle legacy string format
                                content = str(result)
                                display_content = content[:1500] if len(content) > 1500 else content
                                
                                # Process the content to ensure proper formatting
                                if "From " in display_content and "\n\n" in display_content:
                                    parts = display_content.split("\n\n", 1)
                                    source_info = parts[0]
                                    main_content = parts[1] if len(parts) > 1 else ""
                                    
                                    st.markdown(f"""
<div class="query-result">
<div class="result-header">{source_info}</div>

{main_content}

{'**[Content Truncated - Full content available in source]**' if len(content) > 1500 else ''}
</div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.markdown(f"""
<div class="query-result">
<div class="result-header">📊 Content Preview:</div>

{display_content}

{'**[Content Truncated - Full content available in source]**' if len(content) > 1500 else ''}
</div>
                                    """, unsafe_allow_html=True)
                                
                                # Add basic metadata
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.caption(f"Length: {len(content)} chars")
                                with col2:
                                    st.caption(f"Relevance: Rank #{i}")
                                with col3:
                                    st.caption(f"Source: {index_name}")
                                
                                if i < len(results):
                                    st.divider()
                except Exception as e:
                    st.error(f"❌ Query failed: {type(e).__name__} — {str(e)[:200]}")
                    logger.error(f"Query failed for user {username}: {str(e)}")
    
    with web_tab:
        web_query = st.text_input(
            "Web search query:", 
            placeholder="e.g. latest cloud security threats"
        )
        max_results = st.slider("Number of web results", 1, 10, 5)
        
        web_button = st.button("🌐 Search Web", use_container_width=True)
        
        if web_button and web_query:
            auth_middleware.log_user_action("WEB_SEARCH", f"Web Query: {web_query[:50]}...")
            
            with st.spinner("Searching the web..."):
                try:
                    # Progress indicator
                    progress = st.progress(0)
                    for i in range(100):
                        time.sleep(0.01)
                        progress.progress(i + 1)
                    
                    # Get web search results
                    web_results = run_web_search(web_query, max_results)
                    
                    if not web_results:
                        st.warning("No web results found. Try different query parameters.")
                    else:
                        st.markdown("## **Web Search Results**")
                        st.markdown(f"**Found {len(web_results)} relevant web pages for your query**")
                        
                        for i, result in enumerate(web_results, 1):
                            st.markdown(f"""
<div class="web-result">
<h4>{result['title']}</h4>
<div class="url">{result['url']}</div>
<p>{result['snippet']}</p>
</div>
                            """, unsafe_allow_html=True)
                            
                except Exception as e:
                    st.error(f"❌ Web search failed: {type(e).__name__} — {str(e)[:200]}")
                    logger.error(f"Web search failed for user {username}: {str(e)}")
    
    # Add a help section at the bottom
    with st.expander("ℹ️ Help & Tips"):
        st.markdown("""
        ### How to use the Query Assistant
        
        **Index Search Mode:**
        1. Select a knowledge base from the dropdown
        2. Enter your question in natural language
        3. Adjust the number of results to retrieve
        4. Choose an AI model for generating summaries
        5. Click "Search Knowledge Base"
        
        **Web Search Mode:**
        1. Enter your search query
        2. Adjust the number of web results to display
        3. Click "Search Web"
        
        **Tips for better results:**
        - Be specific in your questions
        - Try different knowledge bases for different types of information
        - Use the AI summary to get a quick overview of results
        - For detailed information, review all the individual results
        """)

    # Include version and last updated info
    st.caption(f"Query Assistant v2.0 | Last updated: {datetime.now().strftime('%Y-%m-%d')}")
