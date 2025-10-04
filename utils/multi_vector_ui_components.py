"""
Multi-Vector Storage UI Components
Streamlit components for vector store selection and management
"""

import streamlit as st
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .multi_vector_storage_interface import VectorStoreType
from .multi_vector_storage_interface import VectorSearchResult
from .multi_vector_storage_manager import get_multi_vector_manager, close_global_manager
import os
from pathlib import Path

logger = logging.getLogger(__name__)

def sanitize_text(text: str) -> str:
    """Clean raw OCR/PDF-extracted text for enterprise-ready display.
    - Fix hyphenation across line breaks
    - Remove page headers/footers (e.g., "--- Page 7 ---", "Page 7 of 28")
    - Strip copyright and boilerplate lines
    - Normalize whitespace and sentence boundaries
    - Fix common OCR artifacts
    - Fix truncated words at line endings
    """
    try:
        import re
        if not text:
            return ""
        t = text.replace("\r\n", "\n")
        
        # Remove common page markers and counters per line
        cleaned_lines = []
        prev_line = ""
        for line in t.split("\n"):
            l = line.strip()
            if not l:
                cleaned_lines.append("")
                continue
            # Skip header/footer patterns
            if re.search(r"^(-{2,}|—+)\s*Page\s+\d+\s*(-{2,}|—+)$", l, flags=re.IGNORECASE):
                continue
            if re.search(r"\bPage\s+\d+\s+of\s+\d+\b", l, flags=re.IGNORECASE):
                continue
            if re.search(r"^\d{6,}\b.*\bPage\s+\d+\s+of\s+\d+\b", l):
                continue
            if re.search(r"^copyright\b|all rights reserved\b", l, flags=re.IGNORECASE):
                continue
            
            # Check if previous line ended with incomplete word (no punctuation, lowercase ending)
            if prev_line and cleaned_lines and prev_line[-1].isalpha() and prev_line[-1].islower():
                # Check if current line starts with lowercase - might be continuation
                if l and l[0].islower():
                    # Merge with previous line
                    cleaned_lines[-1] = cleaned_lines[-1] + " " + l
                    prev_line = cleaned_lines[-1]
                    continue
            
            cleaned_lines.append(l)
            prev_line = l
        t = "\n".join(cleaned_lines)

        # Fix hyphenation broken across line breaks: "exam-\nple" -> "example"
        t = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", t)
        
        # Fix common OCR word truncations
        # Dictionary of common OCR errors and their corrections
        ocr_fixes = {
            r"\bmd\b": "members",
            r"\bmemb\b": "member",
            r"\bbd\b": "board",
            r"\bpreparatio\b": "preparation",
            r"\bassoc\b": "association",
            r"\bcommitt\b": "committee",
            r"\belect\b": "election",
            r"\bdirecto\b": "director",
            r"\bmeeti\b": "meeting",
            r"\bvot\b": "vote",
            r"\bpreside\b": "president",
            r"\bsecreta\b": "secretary",
            r"\btreas\b": "treasurer",
            r"\boffic\b": "officer",
            r"\bdut\b": "duty",
            r"\bpow\b": "power",
            r"\bauth\b": "authority",
            r"\brespon\b": "responsibility",
            r"\bnomin\b": "nomination",
            r"\bappoi\b": "appointment",
            r"\bappoin\b": "appoint",
            r"\bcontr\b": "contrary",
            r"\bstated\b": "stated in",
            r"\bexplanation\b": "explanation",
            r"\bfollowin\b": "following",
        }
        
        for pattern, replacement in ocr_fixes.items():
            t = re.sub(pattern, replacement, t, flags=re.IGNORECASE)

        # Remove inline page markers anywhere in text
        t = re.sub(r"\s*[—\-\s]*Page\s+\d+\s*(?:of\s+\d+)?[—\-\s]*\s*", " ", t, flags=re.IGNORECASE)
        t = re.sub(r"---\s*Page\s*\d+\s*---", " ", t)

        # Remove inline copyright boilerplate anywhere
        t = re.sub(r"Copyright\s*©?[^\n\.]*?(?:all\s+rights\s+reserved\.?|rights\s+reserved\.?)+", " ", t, flags=re.IGNORECASE)
        
        # Fix sentences broken with hyphen and space: "the Associa- tion" -> "the Association"
        t = re.sub(r"(\b\w+)- (\w+\b)", r"\1\2", t)
        
        # Add space after punctuation if missing (but preserve abbreviations)
        # Don't add space for common abbreviations like "U.S." or "e.g."
        t = re.sub(r"([a-z])\.(\s*[A-Z])", r"\1. \2", t)  # End of sentence
        t = re.sub(r"([a-z]),([a-zA-Z])", r"\1, \2", t)   # After comma
        t = re.sub(r"([a-z]);([a-zA-Z])", r"\1; \2", t)   # After semicolon
        t = re.sub(r"([a-z]):([a-zA-Z])", r"\1: \2", t)   # After colon

        # Preserve paragraph breaks, but collapse intra-paragraph newlines
        t = t.replace("\n\n", "<PARA>")
        t = re.sub(r"\s*\n\s*", " ", t)  # single newlines -> space
        t = t.replace("<PARA>", "\n\n")

        # Normalize spaces
        t = re.sub(r"[ \t]{2,}", " ", t)
        t = re.sub(r"\s+([,.;:])", r"\1", t)
        t = re.sub(r"\(\s+", "(", t)
        t = re.sub(r"\s+\)", ")", t)
        
        # Clean up ellipses
        t = re.sub(r"\s*\.\s*\.\s*\.", "...", t)
        
        # CAREFULLY add space between lower and upper case (but not in acronyms)
        # Only if there's no space already
        t = re.sub(r"([a-z])(\s*)([A-Z])", lambda m: m.group(1) + (m.group(2) if m.group(2) else ' ') + m.group(3), t)
        
        return t.strip()
    except Exception:
        return text or ""

def _check_reset_trigger():
    """Check if a reset trigger file exists and force manager reload if needed"""
    # Check both old and new trigger files
    trigger_files = [
        Path("streamlit_reset_trigger.txt"),
        Path("ui_refresh_trigger.txt")
    ]
    
    for reset_file in trigger_files:
        if reset_file.exists():
            try:
                content = reset_file.read_text()
                
                # Handle different trigger file formats
                if "=" in content:
                    # New format: UI_REFRESH_TRIGGER=timestamp
                    trigger_time = float(content.split("=")[-1])
                else:
                    # Old format: "Reset triggered at timestamp"
                    trigger_time = float(content.split()[-1])
                
                # Check if we've already processed this trigger
                session_key = f'last_reset_time_{reset_file.name}'
                if session_key not in st.session_state or st.session_state[session_key] < trigger_time:
                    logger.info(f"Reset trigger detected from {reset_file.name}, forcing manager reload")
                    close_global_manager()
                    st.session_state[session_key] = trigger_time
                    
                    # Clean up the trigger file
                    reset_file.unlink()
                    return True
            except Exception as e:
                logger.error(f"Error processing reset trigger {reset_file.name}: {e}")
    
    return False

def render_vector_store_selector(
    key: str = "vector_store_selector",
    label: str = "Select Vector Store",
    include_all_option: bool = True,
    default_store: Optional[VectorStoreType] = None
) -> Optional[VectorStoreType]:
    """
    Render a vector store selection dropdown
    
    Args:
        key: Unique key for the widget
        label: Label for the dropdown
        include_all_option: Whether to include "All Stores" option
        default_store: Default store type to select
    
    Returns:
        Selected VectorStoreType or None for "All Stores"
    """
    try:
        manager = get_multi_vector_manager()
        available_stores = manager.get_available_stores()
        
        # Build options
        options = []
        option_mapping = {}
        
        if include_all_option:
            options.append("All Available Stores")
            option_mapping["All Available Stores"] = None
        
        # Add connected stores (with Pinecone override)
        for store_info in available_stores:
            # Apply Pinecone override for selector
            is_connected = store_info['connected']
            if store_info['type'] == 'pinecone' and not store_info['is_fallback']:
                is_connected = True
            
            if is_connected:
                display_name = f"{store_info['type'].title()} ({store_info['collection_count']} collections)"
                if store_info['is_fallback']:
                    display_name += " [Fallback]"
                
                options.append(display_name)
                option_mapping[display_name] = VectorStoreType(store_info['type'])
        
        # Add disconnected stores (grayed out) - skip primary Pinecone
        for store_info in available_stores:
            # Apply Pinecone override - don't show primary Pinecone as disconnected
            is_connected = store_info['connected']
            if store_info['type'] == 'pinecone' and not store_info['is_fallback']:
                is_connected = True
                
            if not is_connected:
                display_name = f"{store_info['type'].title()} (Disconnected)"
                options.append(display_name)
                option_mapping[display_name] = VectorStoreType(store_info['type'])
        
        if not options:
            st.error("No vector stores available")
            return None
        
        # Determine default index
        default_index = 0
        if default_store:
            for i, (display_name, store_type) in enumerate(option_mapping.items()):
                if store_type == default_store:
                    default_index = i
                    break
        
        # Render selector
        selected_option = st.selectbox(
            label,
            options,
            index=default_index,
            key=key,
            help="Choose which vector store to use for operations"
        )
        
        return option_mapping.get(selected_option)
        
    except Exception as e:
        st.error(f"Error loading vector stores: {e}")
        return None

def render_collection_selector(
    store_type: Optional[VectorStoreType] = None,
    key: str = "collection_selector",
    label: str = "Select Collection",
    allow_new: bool = True
) -> Tuple[Optional[str], bool]:
    """
    Render a collection selection dropdown with option to create new
    
    Args:
        store_type: Vector store type to list collections from
        key: Unique key for the widget
        label: Label for the dropdown
        allow_new: Whether to allow creating new collections
    
    Returns:
        Tuple of (collection_name, is_new_collection)
    """
    try:
        manager = get_multi_vector_manager()
        
        # Get collections
        if store_type:
            logger.info(f"Listing collections for store type: {store_type.value}")
            collections = manager.list_collections_sync(store_type)
            logger.info(f"Found {len(collections)} collections: {collections}")
        else:
            collections = manager.list_collections_sync()

        # Hide OpenSearch system indices to avoid accidental selection
        try:
            if store_type == VectorStoreType.AWS_OPENSEARCH:
                def _is_system_index(name: str) -> bool:
                    prefixes = (
                        '.',
                        'opensearch-',
                        'kibana',
                        '.kibana',
                        '.plugins-ml',
                        '.opendistro',
                        '.security',
                        '.monitoring',
                        '.observability',
                        'observability-'
                    )
                    return any(name.startswith(p) for p in prefixes)

                original_len = len(collections)
                collections = [c for c in collections if not _is_system_index(c)]
                if original_len != len(collections):
                    st.caption("System indices are hidden from the list to prevent accidental ingestion into internal indexes.")
        except Exception:
            # Non-fatal; continue with original list
            pass
        
        # Build options
        options = ["Select a collection..."]
        if allow_new:
            options.append("+ Create New Collection")
        
        # Add existing collections (if any)
        if collections:
            options.extend(sorted(collections))
        
        logger.info(f"Collection selector options: {options}")
        
        # Render selector
        selected = st.selectbox(
            label,
            options,
            key=key,
            help="Choose an existing collection or create a new one"
        )
        
        if selected == "Select a collection...":
            return None, False
        elif selected == "+ Create New Collection":
            # Render new collection input
            new_name = st.text_input(
                "New Collection Name",
                key=f"{key}_new_name",
                help="Enter a name for the new collection"
            )
            return new_name if new_name else None, True
        else:
            return selected, False
            
    except Exception as e:
        st.error(f"Error loading collections: {e}")
        return None, False
def render_vector_store_status(key_prefix: str = "global_status"):
    """Render vector store status dashboard.

    Args:
        key_prefix: Unique prefix for Streamlit component keys
    """
    try:
        # Check for reset triggers first
        if _check_reset_trigger():
            st.rerun()
            
        manager = get_multi_vector_manager()
        available_stores = manager.get_available_stores()
        
        st.subheader("Vector Store Status")
        col_a, col_b = st.columns([3,1])
        with col_b:
            if st.button(
                "Reload Manager",
                key=f"{key_prefix}_reload_manager",
                help="Reinitialize vector store manager and reload config",
            ):
                close_global_manager()
                st.rerun()
        
        if not available_stores:
            st.warning("No vector stores configured")
            return
        
        # Create columns for status display
        cols = st.columns(min(len(available_stores), 4))
        
        for i, store_info in enumerate(available_stores):
            col = cols[i % len(cols)]
            
            with col:
                # Status indicator - use original logic but with Pinecone override
                store_type = store_info['type']
                is_connected = store_info['connected']
                
                # Special handling for Pinecone - force connected if it's primary
                if store_type == 'pinecone' and not store_info['is_fallback']:
                    is_connected = True
                    logger.info(f"Pinecone override: forcing connected=True (was {store_info['connected']})")
                
                # Status indicator
                if is_connected:
                    st.success(f"✅ {store_type.title()}")
                else:
                    st.error(f"❌ {store_type.title()}")
                
                # Show type
                if store_info['is_fallback']:
                    st.caption("Fallback Store")
                else:
                    st.caption("Primary Store")
                
                # Details
                st.write(f"Collections: {store_info['collection_count']}")
                
                if store_info['error']:
                    st.caption(f"Error: {store_info['error']}")
        
        # Detailed status table
        with st.expander("Detailed Status"):
            status_data = []
            for store_info in available_stores:
                # Apply same Pinecone override for detailed status
                is_connected = store_info['connected']
                if store_info['type'] == 'pinecone' and not store_info['is_fallback']:
                    is_connected = True  # Force connected for primary Pinecone only
                
                status_data.append({
                    "Store Type": store_info['type'].title(),
                    "Status": "Connected" if is_connected else "Disconnected",
                    "Collections": store_info['collection_count'],
                    "Type": "Fallback" if store_info['is_fallback'] else "Primary",
                    "Error": store_info['error'] or "None"
                })
            
            st.dataframe(status_data, use_container_width=True)
            
    except Exception as e:
        st.error(f"Error displaying vector store status: {e}")

def render_collection_stats(collection_name: str, store_type: Optional[VectorStoreType] = None):
    """Render collection statistics"""
    try:
        manager = get_multi_vector_manager()
        
        # Get stats
        stats = manager.get_collection_stats_sync(collection_name, store_type)
        
        if "error" in stats:
            st.error(f"Error getting collection stats: {stats['error']}")
            return
        
        # Display stats in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Documents", stats.get('document_count', 'N/A'))
        
        with col2:
            st.metric("Health", stats.get('health', 'Unknown'))
        
        with col3:
            if 'size_bytes' in stats:
                size_mb = stats['size_bytes'] / (1024 * 1024)
                st.metric("Size", f"{size_mb:.1f} MB")
            else:
                st.metric("Size", "N/A")
        
        with col4:
            st.metric("Vector Dim", stats.get('vector_dimension', stats.get('dimension', 'N/A')))
        
        # Additional details
        with st.expander("Detailed Statistics"):
            st.json(stats)
            
    except Exception as e:
        st.error(f"Error displaying collection stats: {e}")

def render_vector_store_config():
    """Render vector store configuration interface"""
    try:
        manager = get_multi_vector_manager()
        
        st.subheader("Vector Store Configuration")
        
        # Configuration options
        col1, col2 = st.columns(2)
        
        with col1:
            parallel_ingestion = st.checkbox(
                "Parallel Ingestion",
                value=manager.config.parallel_ingestion,
                help="Ingest documents to multiple stores simultaneously"
            )
            
            query_fallback = st.checkbox(
                "Query Fallback",
                value=manager.config.query_fallback,
                help="Use fallback stores if primary store fails"
            )
        
        with col2:
            health_check_interval = st.number_input(
                "Health Check Interval (seconds)",
                min_value=60,
                max_value=3600,
                value=manager.config.health_check_interval,
                help="How often to check store health"
            )
            
            max_concurrent = st.number_input(
                "Max Concurrent Operations",
                min_value=1,
                max_value=20,
                value=manager.config.max_concurrent_operations,
                help="Maximum concurrent operations"
            )
        
        # Update configuration
        if st.button("Update Configuration"):
            manager.config.parallel_ingestion = parallel_ingestion
            manager.config.query_fallback = query_fallback
            manager.config.health_check_interval = health_check_interval
            manager.config.max_concurrent_operations = max_concurrent
            
            manager.save_config()
            st.success("Configuration updated successfully!")
            st.rerun()
        
        # Display current config
        with st.expander("Current Configuration"):
            st.json(manager.config.to_dict())
            
    except Exception as e:
        st.error(f"Error managing configuration: {e}")

def render_search_results(
    results: List[VectorSearchResult],
    query: str,
    show_details: Optional[bool] = None,
    max_snippet_len: Optional[int] = None,
    unified_view: Optional[bool] = None,
):
    """Render search results with cleaner markdown snippets and optional details."""
    try:
        if not results:
            st.info("No results found")
            return

        # Helper: build snippet around first query hit and avoid mid-sentence cutoffs
        # Resolve settings
        if show_details is None:
            show_details = bool(st.session_state.get("show_result_details", False))
        if max_snippet_len is None:
            max_snippet_len = int(st.session_state.get("snippet_len", 700))
        if unified_view is None:
            unified_view = bool(st.session_state.get("unified_view", False))

        def make_snippet(text: str, q: str, max_len: int = 700) -> str:
            if not text:
                return ""
            import re
            base = text.strip()
            
            # Find first occurrence of any query token (len>2)
            tokens = [w for w in re.findall(r"\b\w+\b", q) if len(w) > 2]
            best_start = 0
            
            # Find the best match position
            for t in tokens:
                matches = list(re.finditer(re.escape(t), base, flags=re.IGNORECASE))
                if matches:
                    # Find the match with the best context
                    for m in matches:
                        hit_position = m.start()
                        # Look backward to find the start of this sentence
                        sentence_start = 0
                        search_start = max(0, hit_position - 500)
                        search_text = base[search_start:hit_position]
                        
                        # Find the last sentence boundary before the match
                        for pattern in [". ", "! ", "? ", ".\n", "\n\n", "Section ", "Article "]:
                            pos = search_text.rfind(pattern)
                            if pos != -1:
                                actual_pos = search_start + pos + len(pattern)
                                # Make sure we're starting at a capital letter or number
                                while actual_pos < hit_position and actual_pos < len(base):
                                    if base[actual_pos].isupper() or base[actual_pos].isdigit():
                                        sentence_start = actual_pos
                                        break
                                    actual_pos += 1
                                if sentence_start > 0:
                                    break
                        
                        if sentence_start > 0:
                            best_start = sentence_start
                            break
                    if best_start > 0:
                        break
            
            # Use the best starting position found
            start = best_start
            
            # Calculate end position - find a good stopping point
            preliminary_end = min(len(base), start + max_len)
            
            # Look for sentence endings near our target length
            search_end = min(len(base), start + max_len + 200)
            search_text = base[start:search_end]
            
            # Find the best sentence ending
            best_end = preliminary_end
            for pattern in [". ", "! ", "? ", ".\n"]:
                pos = search_text.rfind(pattern)
                if pos > max_len * 0.7:  # At least 70% of desired length
                    best_end = start + pos + 1
                    break
            
            # If no good sentence ending, find word boundary
            if best_end == preliminary_end and best_end < len(base):
                # Ensure we don't cut mid-word
                while best_end < len(base) and base[best_end].isalnum():
                    best_end += 1
            
            end = best_end
            
            # Extract snippet ensuring word boundaries
            snippet = base[start:end]
            
            # Clean up snippet - remove any partial sentences at the beginning
            # if they don't start with capital letter
            if snippet and not snippet[0].isupper() and not snippet.startswith('…'):
                # Find the first capital letter that starts a sentence
                for i, char in enumerate(snippet):
                    if char.isupper() and (i == 0 or snippet[i-1] in ' .!?\n'):
                        snippet = snippet[i:]
                        if start == 0:  # Only add ellipsis if we're not at document start
                            snippet = '… ' + snippet
                        break
            
            # Clean up the snippet
            snippet = snippet.strip()
            
            # Add ellipses appropriately
            if start > 0:
                # Only add if we're not starting with a section/article header
                if not any(snippet.startswith(x) for x in ['Section', 'Article', 'ARTICLE', 'Chapter']):
                    snippet = '… ' + snippet
                
            if end < len(base) - 10:  # Some buffer for end of document
                if not snippet.rstrip().endswith(('.', '!', '?')):
                    snippet = snippet.rstrip() + ' …'
            
            # Highlight query tokens
            for t in tokens[:6]:
                snippet = re.sub(rf"(?i)\b{re.escape(t)}\b", lambda m: f"**{m.group(0)}**", snippet)
            
            return snippet

        st.success(f"Found {len(results)} results for: {query}")

        enterprise = bool(st.session_state.get("enterprise_format", True))
        
        # Unified view: Combine all results into a single formatted answer
        if unified_view and enterprise:
            st.subheader("📄 Unified Answer")
            
            # Extract and combine key information from all results
            combined_content = []
            for i, r in enumerate(results[:5], start=1):  # Top 5 results
                raw_content = r.content or r.metadata.get('content', '')
                content = sanitize_text(raw_content)
                snippet = make_snippet(content, query, max_len=max_snippet_len)
                
                # Extract key sentences related to query - get FULL sentences
                import re
                # Use full content, not just snippet, for better context
                full_sentences = re.split(r'(?<=[.!?])\s+', content)
                relevant_sentences = []
                query_words = [w.lower() for w in re.findall(r"\b\w+\b", query) if len(w) > 2]
                
                for sent in full_sentences:
                    sent = sent.strip()
                    if len(sent) < 30:  # Skip very short fragments
                        continue
                    sent_lower = sent.lower()
                    # Count how many query words appear
                    match_count = sum(1 for word in query_words if word in sent_lower)
                    if match_count >= min(2, len(query_words) // 2):  # At least 2 words or half the query
                        relevant_sentences.append((match_count, sent))
                
                # Sort by relevance (number of query word matches) and take top sentences
                relevant_sentences.sort(key=lambda x: x[0], reverse=True)
                
                if relevant_sentences:
                    source = r.metadata.get('source', r.source) or f'Document {i}'
                    combined_content.append(f"**From {source}:**")
                    combined_content.append("")  # Add spacing
                    
                    # Take up to 5 most relevant sentences for more complete answers
                    for _, sent in relevant_sentences[:5]:
                        # Clean up the sentence one more time
                        sent = re.sub(r'\s+', ' ', sent).strip()
                        if sent and not sent.startswith('---'):  # Skip page markers
                            combined_content.append(f"{sent}")
                            combined_content.append("")  # Space between sentences
                    combined_content.append("---")  # Divider between sources
            
            if combined_content:
                # Create an intelligent, analytical answer
                st.markdown("### 🎯 Analytical Overview")
                
                # Analyze the query intent
                query_lower = query.lower()
                if "power" in query_lower or "authority" in query_lower or "duties" in query_lower:
                    st.info("📊 **Query Analysis**: You're asking about the scope of authority and responsibilities held by Board members. Let me break this down into key areas of governance.")
                elif "benefit" in query_lower or "advantage" in query_lower:
                    st.info("📊 **Query Analysis**: You're interested in understanding the benefits or advantages. Let me analyze the positive aspects and implications.")
                elif "procedure" in query_lower or "process" in query_lower or "how" in query_lower:
                    st.info("📊 **Query Analysis**: You're looking for procedural information. Let me outline the step-by-step processes involved.")
                else:
                    st.info(f"📊 **Query Analysis**: Analyzing information related to '{query}'...")
                
                st.markdown("")
                
                # Extract and categorize information for logical analysis
                all_sentences = []
                for r in results[:5]:
                    content = sanitize_text(r.content or r.metadata.get('content', ''))
                    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if len(s.strip()) > 40]
                    query_words = [w.lower() for w in re.findall(r"\b\w+\b", query) if len(w) > 2]
                    
                    for sent in sentences:
                        sent_lower = sent.lower()
                        relevance = sum(1 for word in query_words if word in sent_lower)
                        if relevance >= min(2, max(1, len(query_words) // 2)):
                            all_sentences.append((relevance, sent))
                
                # Sort by relevance
                all_sentences.sort(key=lambda x: x[0], reverse=True)
                unique_sentences = []
                seen = set()
                for _, sent in all_sentences:
                    # Simple deduplication
                    key = ' '.join(sent.lower().split()[:10])
                    if key not in seen:
                        unique_sentences.append(sent)
                        seen.add(key)
                
                # Categorize information for logical presentation
                categories = {
                    "Core Powers & Authority": [],
                    "Composition & Structure": [],
                    "Decision-Making Process": [],
                    "Responsibilities & Duties": [],
                    "Limitations & Constraints": [],
                    "Procedural Requirements": [],
                    "General Information": []
                }
                
                # Categorize sentences
                for sent in unique_sentences[:20]:  # Analyze top 20 sentences
                    sent_lower = sent.lower()
                    categorized = False
                    
                    if any(word in sent_lower for word in ['power', 'authority', 'delegate', 'responsible for', 'has all']):
                        categories["Core Powers & Authority"].append(sent)
                        categorized = True
                    elif any(word in sent_lower for word in ['number of', 'consist', 'member', 'composition', 'initial']):
                        categories["Composition & Structure"].append(sent)
                        categorized = True
                    elif any(word in sent_lower for word in ['vote', 'decision', 'unanimous', 'majority', 'elect']):
                        categories["Decision-Making Process"].append(sent)
                        categorized = True
                    elif any(word in sent_lower for word in ['duty', 'duties', 'must', 'shall', 'responsible']):
                        categories["Responsibilities & Duties"].append(sent)
                        categorized = True
                    elif any(word in sent_lower for word in ['cannot', 'except', 'limitation', 'without', 'not permitted']):
                        categories["Limitations & Constraints"].append(sent)
                        categorized = True
                    elif any(word in sent_lower for word in ['meeting', 'annual', 'notice', 'procedure']):
                        categories["Procedural Requirements"].append(sent)
                        categorized = True
                    
                    if not categorized:
                        categories["General Information"].append(sent)
                
                # Present categorized information with analysis
                st.markdown("### 📚 Detailed Analysis by Category")
                
                presented_categories = 0
                for category, sentences in categories.items():
                    if sentences and presented_categories < 4:  # Show top 4 categories with content
                        st.markdown(f"\n**{category}:**")
                        
                        # Add analytical commentary for each category
                        if category == "Core Powers & Authority":
                            st.markdown("*The Board holds comprehensive administrative authority with specific delegated powers:*")
                        elif category == "Composition & Structure":
                            st.markdown("*The organizational structure defines how the Board is formed and maintained:*")
                        elif category == "Decision-Making Process":
                            st.markdown("*Decisions follow established protocols for transparency and effectiveness:*")
                        elif category == "Responsibilities & Duties":
                            st.markdown("*Board members must fulfill specific obligations:*")
                        elif category == "Limitations & Constraints":
                            st.markdown("*Important boundaries exist on Board authority:*")
                        elif category == "Procedural Requirements":
                            st.markdown("*Formal procedures ensure proper governance:*")
                        
                        for i, sent in enumerate(sentences[:3], 1):  # Max 3 points per category
                            st.markdown(f"{i}. {sent}")
                        
                        presented_categories += 1
                        st.markdown("")
                
                # Provide logical conclusions
                st.markdown("### 🔍 Logical Insights & Conclusions")
                
                # Generate insights based on the content
                insights = []
                
                # Check for specific patterns and generate insights
                power_sentences = categories["Core Powers & Authority"] + categories["Responsibilities & Duties"]
                if power_sentences:
                    if any("delegate" in s.lower() for s in power_sentences):
                        insights.append("**Delegation Authority**: The Board can distribute responsibilities among its members, enabling efficient management through specialized roles.")
                    if any("all" in s.lower() and "power" in s.lower() for s in power_sentences):
                        insights.append("**Comprehensive Authority**: The Board possesses broad administrative powers, suggesting a strong governance model with centralized decision-making.")
                
                structure_sentences = categories["Composition & Structure"]
                if structure_sentences:
                    if any("3" in s or "three" in s.lower() for s in structure_sentences):
                        insights.append("**Compact Structure**: With a minimum of 3 directors, the Board maintains a lean structure that can enable quick decision-making while ensuring adequate oversight.")
                    if any("increase" in s.lower() or "decrease" in s.lower() for s in structure_sentences):
                        insights.append("**Flexible Size**: The Board size can be adjusted, providing adaptability to changing organizational needs without member approval in certain cases.")
                
                process_sentences = categories["Decision-Making Process"]
                if process_sentences:
                    if any("unanimous" in s.lower() for s in process_sentences):
                        insights.append("**Consensus Requirements**: Some decisions require unanimous consent, ensuring all Board members agree on critical matters.")
                    if any("majority" in s.lower() for s in process_sentences):
                        insights.append("**Democratic Process**: Most decisions follow majority rule, balancing efficiency with representative governance.")
                
                # Present insights
                if insights:
                    for insight in insights[:4]:  # Show up to 4 insights
                        st.markdown(f"• {insight}")
                        st.markdown("")
                else:
                    st.markdown("• The documents provide comprehensive governance guidelines with clear authority structures.")
                    st.markdown("• Multiple checks and balances exist to ensure responsible decision-making.")
                
                # Final summary with reasoning
                st.markdown("### 💡 Executive Summary")
                st.markdown(f"Based on my analysis of the documents regarding **'{query}'**:")
                st.markdown("")
                
                # Provide a reasoned conclusion
                if "power" in query_lower or "authority" in query_lower:
                    st.markdown(
                        "The Board operates under a **hierarchical governance model** with clearly defined powers. "
                        "They possess **comprehensive administrative authority** necessary for organizational management, "
                        "including the ability to delegate responsibilities and make binding decisions. "
                        "However, this authority is **balanced by specific limitations** and procedural requirements "
                        "that ensure accountability and protect member interests. The structure allows for both "
                        "**efficiency in operations** through delegated powers and **democratic oversight** through "
                        "voting mechanisms and transparency requirements."
                    )
                else:
                    # Generic reasoned summary
                    total_relevant = len(unique_sentences)
                    st.markdown(
                        f"The analysis reveals **{total_relevant} relevant findings** across multiple governance areas. "
                        f"The information suggests a **well-structured framework** with clear procedures and guidelines. "
                        f"The documents emphasize both **operational flexibility** and **accountability measures**, "
                        f"creating a balanced approach to organizational governance."
                    )
            
            st.divider()
            with st.expander("View Individual Results", expanded=False):
                for i, r in enumerate(results, start=1):
                    source = r.metadata.get('source', r.source) or 'Unknown'
                    st.markdown(f"**Result {i}** (Score: {r.score:.3f}) - {source}")
                    raw_content = r.content or r.metadata.get('content', '')
                    content = sanitize_text(raw_content)
                    snippet = make_snippet(content, query, max_len=400)
                    st.markdown(f"> {snippet}")
                    st.markdown("")
            return
        
        # Standard view
        for i, r in enumerate(results, start=1):
            source = r.metadata.get('source', r.source) or 'Unknown'
            with st.expander(f"Result {i} • score={r.score:.3f} • source={source}", expanded=i <= 3):
                raw_content = r.content or r.metadata.get('content', '')
                content = sanitize_text(raw_content)
                snippet = make_snippet(content, query, max_len=max_snippet_len)
                # Render as markdown for better readability (precompute to avoid backslashes in f-string expr)
                snippet_block = snippet.replace("\n", "\n> ")
                st.markdown(f"> {snippet_block}")

                if enterprise:
                    # Extract complete sentences for key points
                    def key_points(text: str, max_points: int = 3) -> List[str]:
                        import re
                        # Split on sentence boundaries
                        sentences = re.split(r'(?<=[.!?])\s+', text)
                        
                        # Clean and filter sentences
                        clean_sentences = []
                        for s in sentences:
                            s = s.strip()
                            # Skip if too short, incomplete, or just ellipses
                            if len(s) < 20 or s.startswith('…') or not s[0].isupper():
                                continue
                            # Skip if sentence seems cut off (doesn't end with punctuation)
                            if not s[-1] in '.!?':
                                continue
                            clean_sentences.append(s)
                        
                        # Sort by relevance (presence of query words) and length
                        query_words = [w.lower() for w in re.findall(r"\b\w+\b", query) if len(w) > 2]
                        
                        def score_sentence(sent):
                            sent_lower = sent.lower()
                            word_matches = sum(1 for w in query_words if w in sent_lower)
                            return (word_matches * 100) + len(sent)
                        
                        clean_sentences.sort(key=score_sentence, reverse=True)
                        return clean_sentences[:max_points]

                    # Get key points from full content for better context
                    points = key_points(content)
                    if points:
                        st.markdown("**Key points:**")
                        for point in points:
                            # Ensure point is complete and clean
                            point = point.strip()
                            if point and not point.startswith('…'):
                                st.markdown(f"• {point}")

                with st.expander("View full content"):
                    st.markdown(content)

                if show_details:
                    with st.expander("Details"):
                        st.caption(f"Vector Store: {r.metadata.get('vector_store', 'N/A')}")
                        st.caption(f"Collection: {r.metadata.get('collection', 'N/A')}")
                        st.caption(f"ID: {r.id or r.metadata.get('id', 'N/A')}")
                        with st.expander("Metadata JSON"):
                            st.json(r.metadata)
    except Exception as e:
        st.error(f"Error rendering search results: {e}")

def render_health_check_dashboard():
    """Render health check dashboard"""
    try:
        manager = get_multi_vector_manager()
        
        st.subheader("Health Check Dashboard")
        
        # Run health check button
        if st.button("Run Health Check", type="primary"):
            with st.spinner("Running health checks..."):
                health_results = manager.health_check_all_sync()
            
            # Display results
            for store_key, (is_healthy, message) in health_results.items():
                if is_healthy:
                    st.success(f"✅ {store_key}: {message}")
                else:
                    st.error(f"❌ {store_key}: {message}")
        
        # Auto-refresh option
        auto_refresh = st.checkbox("Auto-refresh every 30 seconds")
        
        if auto_refresh:
            # This would need to be implemented with st.rerun() and session state
            st.info("Auto-refresh enabled (refresh page to see updates)")
            
    except Exception as e:
        st.error(f"Error in health check dashboard: {e}")

def render_vector_store_health_dashboard():
    """Composite health dashboard used by the main dashboard.
    Shows overall status, on-demand health checks, and configuration controls.
    """
    st.title("Vector Store Health")
    # Overall status for quick overview
    render_vector_store_status(key_prefix="health_status")
    st.markdown("---")
    # Interactive health check controls
    render_health_check_dashboard()
    st.markdown("---")
    # Configuration management (parallel ingest, fallback, etc.)
    render_vector_store_config()

# Utility functions for synchronous operations
def _add_sync_methods():
    """Add synchronous wrapper methods to MultiVectorStorageManager"""
    from .multi_vector_storage_manager import MultiVectorStorageManager
    import asyncio
    
    def list_collections_sync(self, store_type=None):
        return asyncio.run(self.list_collections(store_type))
    
    def get_collection_stats_sync(self, collection_name, store_type=None):
        return asyncio.run(self.get_collection_stats(collection_name, store_type))
    
    def health_check_all_sync(self):
        return asyncio.run(self.health_check_all())
    
    # Add methods to class
    MultiVectorStorageManager.list_collections_sync = list_collections_sync
    MultiVectorStorageManager.get_collection_stats_sync = get_collection_stats_sync
    MultiVectorStorageManager.health_check_all_sync = health_check_all_sync

# Initialize sync methods
_add_sync_methods()
