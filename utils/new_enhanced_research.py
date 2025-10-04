"""
High-Performance Enhanced Research Module
========================================

This module provides optimized research capabilities with:
- Multi-source parallel search
- Efficient caching
- Performance monitoring
- Memory optimization
"""

import logging
import random
import time
import threading
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
import hashlib
import re
import html as htmlmod

# Set up logging
logger = logging.getLogger(__name__)

# Constants for caching
CACHE_EXPIRY_SECONDS = 3600  # 1 hour cache expiry
MAX_CACHE_SIZE = 50  # Maximum number of research items to cache

# In-memory cache for research results
search_cache = {}

def clear_research_cache():
    """Clear all cached enhanced research entries."""
    try:
        search_cache.clear()
        logger.info("Enhanced research cache cleared")
    except Exception as _:
        # Be robust; cache clearing should never hard-fail the UI
        pass

def generate_paragraphs(count, topic, style="Professional"):
    """Generate placeholder paragraphs for research content"""
    paragraphs = []
    for i in range(count):
        paragraph = f"This paragraph discusses {topic[:30]}... "
        paragraph += f"It provides detailed information about various aspects and considerations. "
        paragraph += f"Multiple perspectives are considered with supporting evidence. "
        if style == "Technical":
            paragraph += "Technical specifications and methodologies are included with appropriate citations."
        elif style == "Academic":
            paragraph += "Research findings and academic perspectives are thoroughly referenced according to standards."
        else:
            paragraph += "Practical implications and business considerations are highlighted for decision-making."
        paragraphs.append(paragraph)
    return "\n\n".join(paragraphs)

def cache_key(task, operation, knowledge_sources):
    """Generate a unique cache key based on input parameters"""
    # Sort knowledge sources to ensure consistent key regardless of order
    sources_str = ",".join(sorted(knowledge_sources))
    # Create a string that uniquely identifies this research request
    key_str = f"{task}|{operation}|{sources_str}"
    # Hash the string to create a fixed-length key that's safe for any input
    return hashlib.md5(key_str.encode()).hexdigest()

def clean_cache():
    """Clean expired items from cache"""
    current_time = time.time()
    keys_to_remove = []
    
    for key, cache_item in search_cache.items():
        if current_time - cache_item["timestamp"] > CACHE_EXPIRY_SECONDS:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        search_cache.pop(key, None)
    
    # If cache is still too big, remove oldest items
    if len(search_cache) > MAX_CACHE_SIZE:
        # Sort by timestamp (oldest first)
        sorted_cache = sorted(search_cache.items(), key=lambda x: x[1]["timestamp"])
        # Remove oldest items until we're back to max size
        for key, _ in sorted_cache[:len(sorted_cache) - MAX_CACHE_SIZE]:
            search_cache.pop(key, None)

def extract_key_points(search_results: List[Any], max_points: int = 5) -> List[str]:
    """Extract key points from search results with optimized processing"""
    # Use set for deduplication
    key_points = set()
    
    for result in search_results:
        # Extract content from result object or dict
        content = ""
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
        elif hasattr(result, "content"):
            content = result.content
        else:
            content = str(result)
        
        # Split into sentences
        sentences = [s.strip() + "." for s in content.split('.') if s.strip()]
        
        # Take first sentence if it's meaningful (more than 30 chars)
        if sentences and len(sentences[0]) > 30:
            key_points.add(sentences[0])
            
        # Also try to find sentences with keywords like "important", "key", "significant"
        keywords = ["important", "key", "significant", "critical", "essential", "major"]
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in keywords) and len(sentence) > 30:
                key_points.add(sentence)
                
        # Stop if we have enough key points
        if len(key_points) >= max_points:
            break
    
    return list(key_points)[:max_points]

def strip_html_tags(text: str) -> str:
    """Remove HTML tags and unescape entities for cleaner display."""
    if not text:
        return ""
    # Remove tags
    no_tags = re.sub(r"<[^>]+>", " ", text)
    # Unescape
    clean = htmlmod.unescape(no_tags)
    # Collapse whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def format_source_attribution(source_name: str, source_type: str) -> str:
    """Format source attribution for inclusion in research"""
    if "web" in source_type.lower():
        return f"Web search results from {source_name}"
    elif "api" in source_type.lower():
        return f"API data from {source_name}"
    elif "docs" in source_type.lower():
        return f"Technical documentation from {source_name}"
    elif "index" in source_type.lower():
        return f"Knowledge base indexed in {source_name}"
    else:
        return f"Information from {source_name}"

def format_results_without_links(results: List[Any]) -> str:
    """Format retrieved information without embedding URLs; include source names/titles only."""
    if not results:
        return ""

    output = "### Retrieved Information\n\n"
    # Group by source name for readability
    for i, r in enumerate(results, 1):
        # Extract fields safely
        content = getattr(r, "content", None)
        if content is None and isinstance(r, dict):
            content = r.get("content")
        content = strip_html_tags((content or "No content available").strip())

        source_name = getattr(r, "source_name", None)
        if source_name is None and isinstance(r, dict):
            source_name = r.get("source") or r.get("source_name")
        source_name = source_name or "Unknown Source"

        metadata = getattr(r, "metadata", None)
        if metadata is None and isinstance(r, dict):
            metadata = r.get("metadata", {})
        title = strip_html_tags((metadata or {}).get("title") or "") or None

        # Build item without URLs
        output += f"**Source {i}: {source_name}**\n\n"
        if title:
            output += f"*Title: {title}*\n\n"
        output += f"{_truncate(content, 220)}\n\n"

    return output

def format_sources_list(results: List[Any]) -> str:
    """Create a Sources section with clickable links as citations only."""
    if not results:
        return ""

    # Collect unique sources by URL or normalized title
    def _norm_title(txt: str) -> str:
        t = (txt or "").strip().lower()
        # Remove common publisher suffixes like " - cnn" or " | cnn" or " - cnn politics"
        t = re.sub(r"\s*(\||-)\s*cnn(\s*politics)?\s*$", "", t)
        # Collapse whitespace
        t = re.sub(r"\s+", " ", t)
        return t

    seen = set()
    seen_titles = set()
    lines = []
    for r in results:
        metadata = getattr(r, "metadata", None)
        if metadata is None and isinstance(r, dict):
            metadata = r.get("metadata", {})
        url = (metadata or {}).get("url")
        raw_title = (metadata or {}).get("title") or getattr(r, "source_name", None) or (isinstance(r, dict) and (r.get("source") or r.get("source_name"))) or "Source"
        title = strip_html_tags(raw_title)
        title_key = _norm_title(title)
        if url:
                # Deduplicate by URL or normalized title
            if url in seen or title_key in seen_titles:
                continue
            seen.add(url)
            seen_titles.add(title_key)
            lines.append(f"- [{title}]({url})")
        else:
            # No URL available; cite name only once
            key = f"no-url::{title_key}"
            if key in seen:
                continue
            seen.add(key)
            seen_titles.add(title_key)
            lines.append(f"- {title}")

    if not lines:
        return ""

    return "\n\n### Sources\n" + "\n".join(lines)

def _truncate(text: str, max_chars: int = 220) -> str:
    """Safely truncate text at word boundary for display."""
    if not text:
        return ""
    t = text.strip()
    if len(t) <= max_chars:
        return t
    cut = t[:max_chars]
    # try not to cut mid-word
    sp = cut.rfind(" ")
    if sp > 120:
        cut = cut[:sp]
    return cut + "…"

def generate_answer_section(results: List[Any], query: str, max_items: int = 5) -> str:
    """Generate a concise answer summary from search results without embedding links.
    Returns a Markdown bullet list summarizing the top items.
    """
    if not results:
        return ""

    # Normalize results with score, title, snippet
    items = []
    seen_titles = set()
    for r in results:
        score = getattr(r, "relevance_score", 0.0)
        content = getattr(r, "content", None)
        if content is None and isinstance(r, dict):
            content = r.get("content")
        content = content or ""
        metadata = getattr(r, "metadata", None)
        if metadata is None and isinstance(r, dict):
            metadata = r.get("metadata", {})
        title = (metadata or {}).get("title") or ""
        # Prefer title for display; fall back to first sentence of content
        display_title = title.strip() or _truncate(content.strip().split(".")[0], 100)
        if display_title in seen_titles:
            continue
        seen_titles.add(display_title)
        items.append((score, display_title, content.strip()))

    if not items:
        return ""

    # Sort by relevance score desc and take top N
    items.sort(key=lambda x: x[0], reverse=True)
    top = items[:max_items]

    # Build bullet list
    bullets = []
    for _, title, content in top:
        snippet = _truncate(content, 220)
        if title and snippet and title not in snippet:
            bullets.append(f"- {title}: {snippet}")
        elif title:
            bullets.append(f"- {title}")
        else:
            bullets.append(f"- {_truncate(snippet, 200)}")

    return "\n".join(bullets)

def generate_llm_answer_from_results(results: List[Any], query: str) -> str:
    """Use EnhancedLLMProcessor (LangChain OpenAI) to compose an answer from web results.
    Returns empty string if LLM not available or on error.
    """
    try:
        from utils.enhanced_llm_integration import EnhancedLLMProcessor
        # Normalize results to retrieval-style dicts expected by the processor
        retrieval_results: List[Dict[str, Any]] = []
        for r in results:
            content = getattr(r, "content", None)
            if content is None and isinstance(r, dict):
                content = r.get("content")
            content = content or ""
            source_name = getattr(r, "source_name", None)
            if source_name is None and isinstance(r, dict):
                source_name = r.get("source") or r.get("source_name")
            metadata = getattr(r, "metadata", None)
            if metadata is None and isinstance(r, dict):
                metadata = r.get("metadata", {})
            title = (metadata or {}).get("title") or source_name or "Web Source"
            retrieval_results.append({
                "content": content,
                "source": title,
                "page": (metadata or {}).get("page", "N/A"),
                "section": (metadata or {}).get("section", "N/A"),
            })

        processor = EnhancedLLMProcessor()
        if not getattr(processor, "available", False):
            raise RuntimeError("LLM not available (missing API key)")
        response = processor.process_retrieval_results(query, retrieval_results, index_name="web_sources", model_name=getattr(processor, "model_name", None))
        return response.get("result", "")
    except Exception as e:
        logger.warning(f"LLM answer generation unavailable: {e}")
        return ""

def _compose_answer_via_openai(base_results: List[Any], task: str, answer_style: Optional[str] = None, model: Optional[str] = None) -> str:
    """Compose an answer directly via OpenAI (bypass LangChain) using provided results.
    Returns empty string on any failure.
    """
    try:
        # Local imports and env guard to avoid 'project' kwarg issues
        import os
        try:
            os.environ.pop("OPENAI_PROJECT", None)
        except Exception:
            pass
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return ""

        client = OpenAI(api_key=api_key)

        # Build concise context from top results without URLs
        lines = []
        for r in base_results[:5]:
            metadata = getattr(r, "metadata", None)
            if metadata is None and isinstance(r, dict):
                metadata = r.get("metadata", {})
            title = (metadata or {}).get("title") or getattr(r, "source_name", None) or (isinstance(r, dict) and (r.get("source") or r.get("source_name"))) or "Source"
            content = getattr(r, "content", None)
            if content is None and isinstance(r, dict):
                content = r.get("content")
            snippet = _truncate(strip_html_tags(content or ""), 300)
            lines.append(f"- Title: {strip_html_tags(title)}\n  Snippet: {snippet}")

        context_block = "\n".join(lines) if lines else "(No snippets available)"
        style_note = "concise bullet points (3-6 bullets)" if (answer_style or "").lower().startswith("concise") else "a concise paragraph"

        messages = [
            {"role": "system", "content": "You are VaultMind Research Assistant. Provide accurate, concise answers. Do not include inline URLs or 'Source' lines; citations will be added separately by the application."},
            {"role": "user", "content": f"""
Research Query: {task}

Relevant Snippets (titles + content excerpts):
{context_block}

Instructions:
- Write {style_note} synthesizing the snippets above.
- Keep under ~350 words.
- Do NOT include any inline links or a Sources section in the body.
- Use only information present in the snippets.
"""},
        ]

        model_id = model or os.getenv("OPENAI_MODEL") or "gpt-3.5-turbo"
        resp = client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=400,
            temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logger.warning(f"OpenAI direct compose failed: {e}")
        return ""

def remove_inline_urls(text: str) -> str:
    """Remove inline URLs and anchor remnants from text."""
    if not text:
        return ""
    # Remove anchor tags entirely
    txt = re.sub(r"<a\s+[^>]*>(.*?)</a>", r"\1", text, flags=re.IGNORECASE)
    # Remove raw URLs
    txt = re.sub(r"https?://\S+", "", txt)
    # Collapse whitespace
    return re.sub(r"\s+", " ", txt).strip()

def clean_answer_text(text: str) -> str:
    """Sanitize LLM or heuristic answer by removing HTML, URLs, and noisy 'Source' lines."""
    if not text:
        return ""
    t = strip_html_tags(text)
    t = remove_inline_urls(t)
    # Remove parenthetical references like "(Document 1)" or "(Documents 1, 2 and 3)"
    t = re.sub(r"\s*\((?:Doc(?:ument)?s?)\s*[^)]*\)", "", t, flags=re.IGNORECASE)
    # Remove inline labels like "Document 1:" at the start of a line
    t = re.sub(r"(?mi)^\s*Doc(?:ument)?\s+\d+\s*:\s*", "", t)
    # Remove lines that are just 'Source' or 'Source Link' noise
    lines = [ln for ln in t.splitlines() if not re.match(r"^\s*(Source|Source Link)\b", ln, flags=re.IGNORECASE)]
    return "\n".join(lines).strip()

def enhance_markdown_readability(text: str) -> str:
    """Improve readability by converting inline bullets to proper Markdown lists and headings.
    - Break inline " - " items into real list items
    - Ensure 'Limitations:' becomes a heading and starts a new section
    - Normalize bullet symbols to '- '
    """
    if not text:
        return ""
    s = text
    # Normalize non-breaking spaces to regular spaces
    s = s.replace("\xa0", " ")
    # If a sentence ends with ':' followed by inline bullets, break to newlines
    s = re.sub(r":\s*-\s+", ":\n\n- ", s)
    s = re.sub(r":\s*•\s+", ":\n\n- ", s)
    # Turn inline bullets into separate lines (avoid if already at line start)
    s = re.sub(r"(?<!\n)\s-\s+", "\n- ", s)
    # Normalize dot bullets
    s = s.replace("•", "- ")
    # Promote 'Limitations:' to a subheading
    s = re.sub(r"\bLimitations:\s*", "\n\n#### Limitations\n\n", s)
    # Collapse excess blank lines
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def filter_real_web_results(results: List[Any]) -> List[Any]:
    """Filter out placeholder or non-informative search results (e.g., DDG placeholder).
    Conservative tightening: also drop generic news items without technical keywords.
    Returns a list of results that have real content and are not generic placeholders.
    """
    if not results:
        return []

    # Common general-news domains that frequently surface unrelated headlines
    news_domains = (
        "bbc.co.uk", "bbc.com", "cnn.com", "edition.cnn.com", "nytimes.com", "theguardian.com",
        "foxnews.com", "dailymail.co.uk", "telegraph.co.uk", "mirror.co.uk", "independent.co.uk",
        "news.yahoo.com", "reuters.com", "apnews.com"
    )
    # Technical relevance keywords (safe, broad set)
    tech_keywords = (
        "vector", "embedding", "embeddings", "semantic", "similarity", "rag", "retrieval",
        "hugging face", "huggingface", "dataset", "model", "faiss", "weaviate", "qdrant",
        "opensearch", "pinecone", "pgvector", "milvus", "index"
    )

    def _host_from_url(u: str) -> str:
        try:
            from urllib.parse import urlparse
            return urlparse(u).netloc.lower()
        except Exception:
            return ""

    filtered: List[Any] = []
    for r in results:
        # Extract fields
        content = getattr(r, "content", None)
        if content is None and isinstance(r, dict):
            content = r.get("content")
        content = (content or "").strip()
        metadata = getattr(r, "metadata", None)
        if metadata is None and isinstance(r, dict):
            metadata = r.get("metadata", {})
        title = (metadata or {}).get("title", "").strip()
        url = (metadata or {}).get("url", "")
        host = _host_from_url(url)

        # Heuristics to drop placeholders/no-content items
        lower_c = content.lower()
        lower_t = title.lower()
        if (
            not content
            or lower_c.startswith("no api search available")
            or "view live results" in lower_c
            or lower_c.startswith("error searching")
            or lower_t.startswith("search results for")
            or ("duckduckgo.com/?q=" in url)
        ):
            continue

        # Conservative drop of generic news domains if no technical signal in title/content
        if host and any(host.endswith(nd) for nd in news_domains):
            tech_signal = any(k in lower_t or k in lower_c for k in tech_keywords)
            if not tech_signal:
                # Skip unrelated newsy items
                continue

        filtered.append(r)
    return filtered

def generate_enhanced_research_content(task, operation, knowledge_sources, provided_search_results=None, ignore_cache: bool = False, use_llm_answer: bool = False, llm_model_name: Optional[str] = None, concise_mode: bool = False, answer_style: Optional[str] = None):
    """
    Generate research content with optimized performance
    
    Args:
        task: The research task or query
        operation: The type of research operation
        knowledge_sources: List of knowledge sources to search
        provided_search_results: Optional pre-fetched search results
        
    Returns:
        Formatted research content as a string
    """
    # Check cache first
    cache_id = f"{task}|{operation}|{','.join(sorted(knowledge_sources))}"
    cache_key = hashlib.md5(cache_id.encode()).hexdigest()
    
    if (not ignore_cache) and cache_key in search_cache and time.time() - search_cache[cache_key]["timestamp"] < CACHE_EXPIRY_SECONDS:
        logger.info(f"Cache hit for research: {task[:30]}...")
        return search_cache[cache_key]["content"]
    
    # Start timing the operation
    start_time = time.time()
    
    # Initialize variables
    knowledge_reference = ""
    search_results_content = ""
    sources_section = ""
    answer_body = ""
    key_points = []
    errors = []
    # Ensure search_results is defined for error paths
    search_results = []
    
    # Use ThreadPoolExecutor for parallelization
    if knowledge_sources and provided_search_results is None:
        try:
            # Try to use multi_source_search if available
            try:
                from utils.multi_source_search import perform_multi_source_search, format_search_results_for_agent
                
                # Extract base source names (remove the "(External)" suffix if present)
                source_names = [source.split(" (External)")[0] for source in knowledge_sources]
                
                # Perform parallel search across sources with official-site prioritization
                # Apply search overrides centrally so all UIs benefit
                try:
                    from utils.multi_source_search import set_search_overrides, clear_search_overrides
                except Exception:
                    set_search_overrides = None
                    clear_search_overrides = None
                try:
                    if set_search_overrides:
                        # Turn on prioritization; vendor/domain detection happens inside search_web_api
                        set_search_overrides(prioritize=True)
                    search_results = perform_multi_source_search(
                        query=task,
                        knowledge_sources=source_names,
                        max_results=5,
                        use_placeholders=False
                    )
                finally:
                    if 'clear_search_overrides' in locals() and clear_search_overrides:
                        try:
                            clear_search_overrides()
                        except Exception:
                            pass
                
                # Prefer filtered real results. If none remain, avoid falling back to noisy items
                filtered_results = filter_real_web_results(search_results)
                base_results = filtered_results
                # Format search results for inclusion in response (no inline URLs)
                search_results_content = format_results_without_links(base_results)
                sources_section = format_sources_list(base_results)
                key_points = extract_key_points(base_results)
                # Prefer LLM answer if requested and available
                if use_llm_answer:
                    try:
                        from utils.enhanced_llm_integration import EnhancedLLMProcessor
                        processor = EnhancedLLMProcessor(model_name=llm_model_name)
                        if getattr(processor, "available", False):
                            # Build retrieval-style input and call with model
                            retrieval_results: List[Dict[str, Any]] = []
                            for r in base_results:
                                content = getattr(r, "content", None)
                                if content is None and isinstance(r, dict):
                                    content = r.get("content")
                                content = content or ""
                                metadata = getattr(r, "metadata", None)
                                if metadata is None and isinstance(r, dict):
                                    metadata = r.get("metadata", {})
                                title = (metadata or {}).get("title") or getattr(r, "source_name", None) or "Web Source"
                                retrieval_results.append({
                                    "content": strip_html_tags(content),
                                    "source": strip_html_tags(title),
                                    "page": (metadata or {}).get("page", "N/A"),
                                    "section": (metadata or {}).get("section", "N/A"),
                                })
                            resp = processor.process_retrieval_results(task, retrieval_results, index_name="web_sources", model_name=llm_model_name, answer_style=answer_style)
                            answer_body = resp.get("result", "")
                        else:
                            answer_body = generate_answer_section(base_results, task)
                    except Exception:
                        answer_body = _compose_answer_via_openai(base_results, task, answer_style=answer_style, model=llm_model_name) or generate_answer_section(base_results, task)

                else:
                    answer_body = generate_answer_section(base_results, task)

                # If LLM produced an error-string or empty output, try direct OpenAI compose, then heuristic summary
                if not answer_body or answer_body.strip().lower().startswith("error generating response"):
                    composed = _compose_answer_via_openai(base_results, task, answer_style=answer_style, model=llm_model_name)
                    answer_body = composed or generate_answer_section(base_results, task)

                # Clean and enhance Markdown for readability
                answer_body = enhance_markdown_readability(clean_answer_text(answer_body))

                if concise_mode:
                    # Return a minimal report: Answer + Sources only
                    answer_line = answer_body if answer_body else "A concise summary could not be constructed from the selected sources."
                    return f"""
## Research Report: {task[:50]}

### Answer
{answer_line}
{sources_section}
"""
                
            except ImportError:
                # If multi_source_search is not available, use our parallel implementation
                logger.info("Using optimized parallel search implementation")
                
                # Define a function to search a single source
                def search_source(source):
                    try:
                        from utils.simple_search import perform_multi_source_search
                        return perform_multi_source_search(task, [source], max_results=3)
                    except Exception as e:
                        errors.append(f"Error searching {source}: {str(e)}")
                        return []
                
                # Use ThreadPoolExecutor for parallel execution
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(knowledge_sources), 5)) as executor:
                    future_to_source = {executor.submit(search_source, source): source for source in knowledge_sources}
                    all_results = []
                    
                    for future in concurrent.futures.as_completed(future_to_source):
                        source_results = future.result()
                        all_results.extend(source_results)
                
                # Helper function to format search results
                def format_results(results):
                    if not results:
                        return ""
                    
                    formatted = "### Search Results\n\n"
                    for i, result in enumerate(results, 1):
                        content = ""
                        if hasattr(result, "content"):
                            content = result.content
                        elif isinstance(result, dict) and "content" in result:
                            content = result["content"]
                        else:
                            content = str(result)
                        
                        formatted += f"{i}. {content}\n\n"
                    
                    return formatted
                
                # Prefer filtered real results. If none remain, avoid falling back to noisy items
                filtered_results = filter_real_web_results(all_results)
                base_results = filtered_results
                # Format the results (no inline URLs)
                search_results_content = format_results(base_results)
                sources_section = format_sources_list(base_results)
                key_points = extract_key_points(base_results)
                if use_llm_answer:
                    try:
                        from utils.enhanced_llm_integration import EnhancedLLMProcessor
                        processor = EnhancedLLMProcessor(model_name=llm_model_name)
                        if getattr(processor, "available", False):
                            retrieval_results: List[Dict[str, Any]] = []
                            for r in base_results:
                                content = getattr(r, "content", None)
                                if content is None and isinstance(r, dict):
                                    content = r.get("content")
                                content = content or ""
                                metadata = getattr(r, "metadata", None)
                                if metadata is None and isinstance(r, dict):
                                    metadata = r.get("metadata", {})
                                title = (metadata or {}).get("title") or getattr(r, "source_name", None) or "Web Source"
                                retrieval_results.append({
                                    "content": strip_html_tags(content),
                                    "source": strip_html_tags(title),
                                    "page": (metadata or {}).get("page", "N/A"),
                                    "section": (metadata or {}).get("section", "N/A"),
                                })
                            resp = processor.process_retrieval_results(task, retrieval_results, index_name="web_sources", model_name=llm_model_name, answer_style=answer_style)
                            answer_body = resp.get("result", "")
                        else:
                            answer_body = generate_answer_section(base_results, task)
                    except Exception:
                        answer_body = generate_answer_section(base_results, task)
                else:
                    answer_body = generate_answer_section(base_results, task)

                # If LLM produced an error-string or empty output, try direct OpenAI compose, then heuristic summary
                if not answer_body or answer_body.strip().lower().startswith("error generating response"):
                    composed = _compose_answer_via_openai(base_results, task, answer_style=answer_style, model=llm_model_name)
                    answer_body = composed or generate_answer_section(base_results, task)

                # Clean and enhance Markdown for readability
                answer_body = enhance_markdown_readability(clean_answer_text(answer_body))

                if concise_mode:
                    answer_line = answer_body if answer_body else "A concise summary could not be constructed from the selected sources."
                    return f"""
## Research Report: {task[:50]}

### Answer
{answer_line}
{sources_section}
"""
                
        except Exception as e:
            logger.error(f"Error in search process: {str(e)}")
            search_results_content = f"**Note:** Search process encountered an error: {str(e)}"
            errors.append(f"Search error: {str(e)}")
            
            # Extract key points from search results for findings section
            key_points = extract_key_points(search_results)
        
        # Create knowledge reference section with more detailed information
        if knowledge_sources:
            knowledge_reference = f"\n\n### Knowledge Sources Used\n"
            for source in knowledge_sources:
                if "(External)" in source:
                    knowledge_reference += f"- **{source}**: Provided external information not found in indexed documents\n"
                else:
                    knowledge_reference += f"- **{source}**: Searched for relevant information on the topic\n"
            
            # Add timestamp for when the search was performed
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            knowledge_reference += f"\n*Information retrieved on: {current_time}*"
    
    if operation == "Research Topic":
        # Generate research findings based on key points if available
        findings_section = ""
        if key_points:
            findings_section = "### Key Findings\n"
            for i, point in enumerate(key_points, 1):
                findings_section += f"{i}. **Finding {i}**: {point}\n"
                findings_section += f"   - Supporting evidence from multiple sources\n"
                findings_section += f"   - Implications for {task.split()[0] if task.split() else 'related'} sector\n\n"
        else:
            # Fallback findings if no key points available
            findings_section = """### Key Findings
1. **Finding One**: Detailed explanation of the first major discovery
   - Supporting evidence point A
   - Supporting evidence point B

2. **Finding Two**: Explanation of the second significant finding
   - Related implications
   - Statistical relevance

3. **Finding Three**: Description of the third important insight
   - Contextual factors
   - Comparative analysis
"""

        answer_line = answer_body if answer_body else "A concise summary could not be constructed from the selected sources."
        return f"""
## Research Report: {task[:50]}

### Executive Summary
This research report investigates {task[:30]}, examining current trends, key factors, and implications.
The findings suggest several important considerations for future direction.

### Answer
{answer_line}

### Introduction
{generate_paragraphs(1, task, "Academic")}

### Methodology
This research utilized a comprehensive approach including:
- Literature review of existing publications
- Analysis of data from multiple sources
- Comprehensive web search for latest developments
- Synthesis of findings from all available knowledge sources

{search_results_content}

{findings_section}

### Analysis
{generate_paragraphs(2, task, "Technical")}

### Conclusions
The research indicates that there are significant implications for this topic.
Further investigation is recommended in related areas to expand understanding.

### Recommendations
1. Primary recommendation based on findings
2. Secondary action item with implementation notes
3. Long-term strategy suggestion{knowledge_reference}{sources_section}
"""
    elif operation == "Data Analysis":
        extra_ext = " from external sources" if search_results_content else ""
        return f"""
## Data Analysis Report: {task[:50]}

### Overview
This analysis examines {task[:30]}, identifying patterns, trends, and insights.

### Data Sources
The following data sources were analyzed:
- Primary data sets related to the topic
- Secondary supporting information
- Comparative benchmarks{extra_ext}

{search_results_content}

### Data Visualization
*[This section would contain relevant charts and graphs in a real implementation]*

### Statistical Analysis
{generate_paragraphs(1, task, "Technical")}

### Insights & Patterns
1. **Primary Pattern**: Description of the most significant pattern observed
2. **Secondary Trend**: Analysis of another important trend
3. **Outliers**: Discussion of notable exceptions or anomalies

### Conclusions
The data analysis reveals important correlations and suggests several actionable insights.

### Recommendations
- Recommendation 1 based on data findings
- Recommendation 2 with supporting evidence
- Long-term data collection strategy{knowledge_reference}{sources_section}
"""
    elif operation == "Problem Solving":
        return f"""
## Problem Analysis: {task[:50]}

### Problem Statement
This analysis addresses {task[:30]}, examining causes, factors, and potential solutions.

### Background
{generate_paragraphs(1, task, "Professional")}

{search_results_content}

### Root Cause Analysis
1. **Primary Factor**: Description of the main contributing factor
2. **Secondary Factor**: Analysis of another important element
3. **Contextual Elements**: Discussion of environmental or situational aspects

### Solution Options
| Solution | Pros | Cons | Feasibility |
|----------|------|------|------------|
| Option A | • Pro 1<br>• Pro 2 | • Con 1<br>• Con 2 | High |
| Option B | • Pro 1<br>• Pro 2 | • Con 1<br>• Con 2 | Medium |
| Option C | • Pro 1<br>• Pro 2 | • Con 1<br>• Con 2 | Low |

### Recommended Approach
Based on the analysis, Option [A/B/C] is recommended because [reasoning].

### Implementation Plan
1. First step in the solution process
2. Second step with key stakeholders
3. Timeline and resource requirements{knowledge_reference}{sources_section}
"""
    elif operation == "Trend Identification":
        return f"""
## Trend Analysis: {task[:50]}

### Overview
This analysis identifies and evaluates key trends related to {task[:30]}.

### Current Landscape
{generate_paragraphs(1, task, "Professional")}

{search_results_content}

### Emerging Trends
1. **Primary Trend**: Description and trajectory of the main trend
   - Impact factors
   - Growth indicators

2. **Secondary Trend**: Analysis of another significant development
   - Market segments affected
   - Adoption timeline

3. **Disruptive Elements**: Potential game-changers in the space
   - Innovation factors
   - Competitive landscape

### Comparative Analysis
| Trend | Current Impact | Future Potential | Risk Level |
|-------|--------------|-----------------|------------|
| Trend A | Medium | High | Low |
| Trend B | Low | High | Medium |
| Trend C | High | Medium | High |

### Strategic Implications
{generate_paragraphs(1, task, "Business")}

### Recommendations
- Short-term adjustments to leverage current trends
- Mid-term strategic positioning
- Long-term innovation directions{knowledge_reference}{sources_section}
"""
    else:
        # Default research format for any other operation type
        return f"""
## Analysis Report: {task[:50]}

### Overview
This analysis explores {task[:30]}, examining key factors and implications.

{search_results_content}

### Key Points
1. **Point One**: Detailed explanation of the first major consideration
2. **Point Two**: Description of another important aspect
3. **Point Three**: Analysis of a third critical element

### Detailed Examination
{generate_paragraphs(2, task, "Professional")}

### Conclusions
The analysis indicates several important considerations and potential next steps.

### Recommendations
- Primary recommendation based on findings
- Secondary action items
- Areas for further investigation{knowledge_reference}{sources_section}
"""
