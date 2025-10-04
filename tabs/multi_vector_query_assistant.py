"""
Multi-Vector Query Assistant Tab
Enhanced query interface with multi-vector storage support and advanced search capabilities
"""

import streamlit as st
import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from datetime import datetime
import json

from utils.multi_vector_storage_manager import get_multi_vector_manager
from utils.multi_vector_storage_interface import VectorStoreType, VectorSearchResult as SearchResult, batch_embeddings
from utils.multi_vector_ui_components import (
    render_vector_store_selector, render_collection_selector, 
    render_vector_store_status, render_search_results
)

# Import existing utilities if available
try:
    from utils.query_enhancement import QueryEnhancer
    from utils.enhanced_hybrid_retrieval import EnhancedHybridRetriever
    from utils.advanced_reranker import AdvancedReranker, rerank_documents_with_threshold
    ENHANCED_SEARCH_AVAILABLE = True
except ImportError:
    ENHANCED_SEARCH_AVAILABLE = False

try:
    from utils.llm_config import get_llm_client
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

logger = logging.getLogger(__name__)

def render_multi_vector_query_assistant():
    """Render the multi-vector query assistant interface"""
    
    st.title("🔍 Multi-Vector Query Assistant")
    st.markdown("Advanced document search across multiple vector storage backends with intelligent query processing.")
    
    # Vector store status
    with st.expander("Vector Store Status", expanded=False):
        render_vector_store_status(key_prefix="query_status")
    
    # Main query interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Query Configuration")
        
        # Query input
        query = st.text_area(
            "Enter your query",
            height=100,
            placeholder="Ask a question about your documents...",
            help="Enter a natural language query to search your document collections",
            key="mvqa_query"
        )
        
        # Advanced query options
        with st.expander("Advanced Query Options"):
            query_enhancement = st.checkbox(
                "Enable Query Enhancement",
                value=ENHANCED_SEARCH_AVAILABLE,
                disabled=not ENHANCED_SEARCH_AVAILABLE,
                help="Use AI to expand and improve your query"
            )
            
            hybrid_search = st.checkbox(
                "Enable Hybrid Search",
                value=True,
                help="Combine vector similarity with keyword matching"
            )
            
            rerank_results = st.checkbox(
                "Enable Result Re-ranking",
                value=ENHANCED_SEARCH_AVAILABLE,
                disabled=not ENHANCED_SEARCH_AVAILABLE,
                help="Use advanced AI to re-rank search results"
            )
            # Embedding model for query vectorization (should match ingestion model's dimension)
            embedding_model = st.selectbox(
                "Query Embedding Model",
                ["all-MiniLM-L6-v2", "all-mpnet-base-v2", "sentence-t5-base"],
                index=0,
                help="Model used to embed queries for vector search (MiniLM=384 dims)"
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                top_k = st.slider(
                    "Number of Results",
                    min_value=1,
                    max_value=50,
                    value=10,
                    help="Maximum number of results to return"
                )
                
                similarity_threshold = st.slider(
                    "Similarity Threshold",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.7,
                    step=0.05,
                    help="Minimum similarity score for results"
                )
            
            with col_b:
                search_timeout = st.number_input(
                    "Search Timeout (seconds)",
                    min_value=5,
                    max_value=120,
                    value=30,
                    help="Maximum time to wait for search results"
                )
                
                enable_fallback = st.checkbox(
                    "Enable Fallback Search",
                    value=True,
                    help="Try alternative vector stores if primary fails"
                )
    
    with col2:
        st.subheader("Search Configuration")
        
        # Vector store selection
        selected_stores = render_multi_store_selector()
        
        if selected_stores:
            # Collection selection for each store
            collection_configs = {}
            for store in selected_stores:
                with st.expander(f"{store.value} Collections"):
                    collections = render_multi_collection_selector(store)
                    if collections:
                        collection_configs[store] = collections
        
        # Search mode
        st.subheader("Search Mode")
        search_mode = st.radio(
            "Select search mode",
            ["Document Search", "Q&A with Context", "Comparative Analysis"],
            help="Choose how to process and present results"
        )
        
        if search_mode == "Q&A with Context" and LLM_AVAILABLE:
            llm_model = st.selectbox(
                "LLM Model",
                ["gpt-3.5-turbo", "gpt-4", "claude-3-sonnet", "mistral-large"],
                help="Language model for generating answers"
            )
        
        # Metadata filters
        with st.expander("Metadata Filters"):
            render_metadata_filters()
    
    # Execute search
    st.subheader("Search Results")
    with st.expander("Display Options", expanded=False):
        st.checkbox("Show technical details (store, IDs, metadata)", value=False, key="show_result_details")
        st.slider("Snippet length (characters)", min_value=500, max_value=2000, step=100, value=1200, key="snippet_len")
        st.checkbox("Enterprise formatting (cleaned excerpts + key points)", value=True, key="enterprise_format")
        st.checkbox("Unified view (single-page comprehensive answer)", value=True, key="unified_view", help="Combine results into a detailed, well-formatted answer")
    
    # Action buttons
    btn_col1, btn_col2 = st.columns([1, 1])
    search_clicked = btn_col1.button("🔎 Search", type="primary")
    clear_clicked = btn_col2.button("🧹 Clear", help="Clear query, filters, and results")

    if clear_clicked:
        # Clear only non-widget session state values
        if 'metadata_filters' in st.session_state:
            st.session_state.metadata_filters = []
        if 'mvqa_results' in st.session_state:
            del st.session_state.mvqa_results
        # Note: Widget values (like mvqa_query) will be cleared on rerun
        st.rerun()

    if search_clicked:
        if query and selected_stores:
            execute_multi_vector_search(
                query=query,
                store_configs=collection_configs if 'collection_configs' in locals() else {},
                search_mode=search_mode,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                query_enhancement=query_enhancement,
                hybrid_search=hybrid_search,
                rerank_results=rerank_results,
                enable_fallback=enable_fallback,
                search_timeout=search_timeout,
                embedding_model=embedding_model,
                llm_model=llm_model if search_mode == "Q&A with Context" and LLM_AVAILABLE else None
            )
        else:
            missing_items = []
            if not query:
                missing_items.append("query")
            if not selected_stores:
                missing_items.append("vector stores")
            st.info(f"Please provide: {', '.join(missing_items)}")
    
    # Search history
    render_search_history()

def render_multi_store_selector() -> List[VectorStoreType]:
    """Render multi-select vector store selector"""
    
    manager = get_multi_vector_manager()
    # Use manager-reported statuses to determine connected stores
    store_infos = manager.get_available_stores()
    connected_types = [VectorStoreType(info['type']) for info in store_infos if info.get('connected')]
    
    if not connected_types:
        st.warning("No vector stores available")
        return []
    
    selected = st.multiselect(
        "Select Vector Stores",
        options=connected_types,
        default=connected_types[:1],  # Select first available by default
        format_func=lambda x: x.value,
        help="Choose which vector stores to search"
    )
    
    return selected

def render_multi_collection_selector(store_type: VectorStoreType) -> List[str]:
    """Render collection selector for a specific store"""
    
    try:
        manager = get_multi_vector_manager()
        collections = asyncio.run(manager.list_collections(store_type))
        
        if not collections:
            st.info(f"No collections found in {store_type.value}")
            return []
        
        selected = st.multiselect(
            f"Collections",
            options=collections,
            default=collections,  # Select all by default
            key=f"collections_{store_type.value}",
            help=f"Choose collections to search in {store_type.value}"
        )
        
        return selected
        
    except Exception as e:
        st.error(f"Error loading collections: {e}")
        return []

def render_metadata_filters():
    """Render metadata filtering interface"""
    
    if 'metadata_filters' not in st.session_state:
        st.session_state.metadata_filters = []
    
    # Add filter button
    if st.button("Add Filter"):
        st.session_state.metadata_filters.append({
            'field': '',
            'operator': 'eq',
            'value': ''
        })
    
    # Render existing filters
    for i, filter_config in enumerate(st.session_state.metadata_filters):
        col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
        
        with col1:
            filter_config['field'] = st.text_input(
                "Field",
                value=filter_config['field'],
                key=f"filter_field_{i}",
                placeholder="e.g., source_type"
            )
        
        with col2:
            filter_config['operator'] = st.selectbox(
                "Op",
                ["eq", "ne", "gt", "lt", "contains", "regex"],
                index=["eq", "ne", "gt", "lt", "contains", "regex"].index(filter_config['operator']),
                key=f"filter_op_{i}"
            )
        
        with col3:
            filter_config['value'] = st.text_input(
                "Value",
                value=filter_config['value'],
                key=f"filter_value_{i}",
                placeholder="Filter value"
            )
        
        with col4:
            if st.button("🗑️", key=f"remove_filter_{i}"):
                st.session_state.metadata_filters.pop(i)
                st.rerun()

def execute_multi_vector_search(
    query: str,
    store_configs: Dict[VectorStoreType, List[str]],
    search_mode: str,
    top_k: int,
    similarity_threshold: float,
    query_enhancement: bool,
    hybrid_search: bool,
    rerank_results: bool,
    enable_fallback: bool,
    search_timeout: int,
    embedding_model: str = "all-MiniLM-L6-v2",
    llm_model: Optional[str] = None
):
    """Execute multi-vector search across configured stores"""
    
    try:
        manager = get_multi_vector_manager()
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Query enhancement
        enhanced_queries = [query]
        if query_enhancement and ENHANCED_SEARCH_AVAILABLE:
            status_text.text("Enhancing query...")
            try:
                enhancer = QueryEnhancer()
                enhanced_obj = enhancer.enhance_query(query)
                # Expect EnhancedQuery dataclass with .expanded_queries
                candidate_list = getattr(enhanced_obj, "expanded_queries", None)
                if isinstance(candidate_list, list) and candidate_list:
                    enhanced_queries = candidate_list
                    st.info(f"Generated {len(enhanced_queries)} enhanced queries")
                else:
                    enhanced_queries = [query]
                    st.info("Using original query (no expansions returned)")
            except Exception as e:
                st.warning(f"Query enhancement failed: {e}")
                enhanced_queries = [query]
        
        # Prepare query embeddings for each enhanced query
        try:
            query_embeddings = batch_embeddings(enhanced_queries, model_name=embedding_model)
        except Exception:
            query_embeddings = []
        
        if not query_embeddings:
            status_text.empty()
            st.error("Could not generate query embeddings. Ensure 'sentence-transformers' is installed and select a supported model.")
            st.caption("Tip: Use 'all-MiniLM-L6-v2' to match 384-dimension Pinecone indexes created by the ingest tab.")
            return
        
        # Execute searches
        all_results = []
        total_searches = sum(len(collections) for collections in store_configs.values())
        current_search = 0
        
        for store_type, collections in store_configs.items():
            for collection in collections:
                current_search += 1
                progress_bar.progress(current_search / total_searches)
                status_text.text(f"Searching {store_type.value}/{collection}...")
                
                try:
                    # Search with each enhanced query
                    # Optional: validate index dimension to help avoid silent mismatches
                    try:
                        stats = asyncio.run(manager.get_collection_stats(collection, store_type))
                        index_dim = stats.get('dimension') or stats.get('vector_dimension')
                    except Exception:
                        index_dim = None
                    if index_dim and len(query_embeddings[0]) != int(index_dim):
                        st.warning(f"Index '{collection}' expects dimension {index_dim}, but the selected embedding model outputs {len(query_embeddings[0])}. Choose a matching model (e.g., MiniLM=384). Skipping this collection.")
                        continue

                    for i, enhanced_query in enumerate(enhanced_queries):
                        results = asyncio.run(manager.search(
                            collection_name=collection,
                            query=enhanced_query,
                            query_embedding=(query_embeddings[i] if i < len(query_embeddings) else None),
                            filters=get_active_metadata_filters(),
                            limit=top_k,
                            store_type=store_type
                        ))
                        
                        # Add source information
                        for result in results:
                            result.metadata['vector_store'] = store_type.value
                            result.metadata['collection'] = collection
                            result.metadata['enhanced_query'] = enhanced_query
                        
                        all_results.extend(results)
                
                except Exception as e:
                    st.warning(f"Search failed for {store_type.value}/{collection}: {e}")
                    if not enable_fallback:
                        continue
        
        progress_bar.progress(1.0)
        status_text.text("Processing results...")
        
        # Deduplicate and merge results
        unique_results = deduplicate_results(all_results)
        
        # Re-ranking
        if rerank_results and ENHANCED_SEARCH_AVAILABLE and unique_results:
            try:
                # Convert results to simple dicts for the reranker
                docs_for_rerank = [
                    {
                        'content': r.content,
                        'source': r.metadata.get('source', r.source),
                        'metadata': r.metadata
                    }
                    for r in unique_results
                ]
                ranked, _meta = rerank_documents_with_threshold(query, docs_for_rerank, threshold=0.7)
                # Reorder original results based on ranked order by content match
                ordered: List[SearchResult] = []
                for rr in ranked:
                    for r in unique_results:
                        if r.content == rr.content and r not in ordered:
                            ordered.append(r)
                            break
                # Append any leftovers
                for r in unique_results:
                    if r not in ordered:
                        ordered.append(r)
                unique_results = ordered
                st.info("Results re-ranked using advanced AI")
            except Exception as e:
                st.warning(f"Re-ranking failed: {e}")
        
        # Apply final filtering
        filtered_results = [r for r in unique_results if r.score >= similarity_threshold][:top_k]
        
        status_text.empty()
        
        # Display results based on search mode
        if search_mode == "Document Search":
            display_document_results(filtered_results, query)
        elif search_mode == "Q&A with Context" and LLM_AVAILABLE:
            display_qa_results(filtered_results, query, llm_model)
        elif search_mode == "Comparative Analysis":
            display_comparative_results(filtered_results, query, store_configs)
        
        # Save to search history
        save_search_history(query, len(filtered_results), store_configs)
        
    except Exception as e:
        st.error(f"Search execution failed: {e}")
        logger.error(f"Multi-vector search error: {e}", exc_info=True)

def get_active_metadata_filters() -> Dict[str, Any]:
    """Get active metadata filters"""
    filters = {}
    
    if 'metadata_filters' in st.session_state:
        for filter_config in st.session_state.metadata_filters:
            if filter_config['field'] and filter_config['value']:
                filters[filter_config['field']] = {
                    'operator': filter_config['operator'],
                    'value': filter_config['value']
                }
    
    return filters

def deduplicate_results(results: List[SearchResult]) -> List[SearchResult]:
    """Remove duplicate results based on content similarity"""
    if not results:
        return []
    
    unique_results = []
    seen_content = set()
    
    for result in sorted(results, key=lambda x: x.score, reverse=True):
        # Simple deduplication based on content hash
        content_hash = hash(result.content[:200])  # Use first 200 chars
        
        if content_hash not in seen_content:
            seen_content.add(content_hash)
            unique_results.append(result)
    
    return unique_results

def display_document_results(results: List[SearchResult], query: str):
    """Display document search results"""
    if not results:
        st.info("No results found")
        return
    
    # Display results with unified view option
    render_search_results(results, query)

def display_qa_results(results: List[SearchResult], query: str, llm_model: str):
    """Display Q&A results with LLM-generated answers"""
    if not results:
        st.info("No context found for generating answer")
        return
    
    try:
        # Prepare context
        context_parts = []
        for i, result in enumerate(results[:5]):  # Use top 5 results for context
            context_parts.append(f"[{i+1}] {result.content}")
        
        context = "\n\n".join(context_parts)
        
        # Generate answer
        llm_client = get_llm_client(llm_model)
        
        prompt = f"""Based on the following context, answer the user's question. If the context doesn't contain enough information, say so clearly.

Context:
{context}

Question: {query}

Answer:"""
        
        with st.spinner("Generating answer..."):
            response = llm_client.chat.completions.create(
                model=llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            answer = response.choices[0].message.content
        
        # Display answer
        st.subheader("AI-Generated Answer")
        st.markdown(answer)
        
        # Display source documents
        st.subheader("Source Documents")
        render_search_results(results[:5], query)
        
    except Exception as e:
        st.error(f"Failed to generate answer: {e}")
        display_document_results(results, query)

def display_comparative_results(results: List[SearchResult], query: str, store_configs: Dict):
    """Display comparative analysis across vector stores"""
    if not results:
        st.info("No results found for comparison")
        return
    
    # Group results by vector store
    store_results = {}
    for result in results:
        store = result.metadata.get('vector_store', 'Unknown')
        if store not in store_results:
            store_results[store] = []
        store_results[store].append(result)
    
    st.subheader("Comparative Analysis")
    
    # Summary statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Results", len(results))
    with col2:
        st.metric("Vector Stores", len(store_results))
    with col3:
        avg_score = sum(r.score for r in results) / len(results) if results else 0
        st.metric("Avg Similarity", f"{avg_score:.3f}")
    
    # Results by store
    for store, store_res in store_results.items():
        with st.expander(f"{store} ({len(store_res)} results)"):
            avg_store_score = sum(r.score for r in store_res) / len(store_res)
            st.write(f"**Average Score:** {avg_store_score:.3f}")
            
            for result in store_res[:3]:  # Show top 3 per store
                st.write(f"**Score:** {result.score:.3f}")
                st.write(f"**Collection:** {result.metadata.get('collection', 'Unknown')}")
                st.write(f"**Content:** {result.content[:200]}...")
                st.divider()

def save_search_history(query: str, result_count: int, store_configs: Dict):
    """Save search to history"""
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []
    
    history_entry = {
        'timestamp': datetime.now().isoformat(),
        'query': query,
        'result_count': result_count,
        'stores': list(store_configs.keys()),
        'collections': {store.value: collections for store, collections in store_configs.items()}
    }
    
    st.session_state.search_history.insert(0, history_entry)
    st.session_state.search_history = st.session_state.search_history[:20]  # Keep last 20

def render_search_history():
    """Render search history"""
    st.subheader("Search History")
    right = st.columns([1,1,6])[1]
    with right:
        if st.button("🧹 Clear History"):
            st.session_state.search_history = []
            st.rerun()
    
    if 'search_history' not in st.session_state or not st.session_state.search_history:
        st.info("No search history")
        return
    
    for i, entry in enumerate(st.session_state.search_history[:5]):  # Show last 5
        with st.expander(f"{entry['query'][:50]}... - {entry['timestamp'][:19]}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Results:** {entry['result_count']}")
                st.write(f"**Stores:** {', '.join([s.value if hasattr(s, 'value') else str(s) for s in entry['stores']])}")
            
            with col2:
                if st.button("Repeat Search", key=f"repeat_{i}"):
                    st.session_state.repeat_query = entry['query']
                    st.rerun()

# Main function for tab integration
def main():
    """Main function for standalone testing"""
    render_multi_vector_query_assistant()

if __name__ == "__main__":
    main()
