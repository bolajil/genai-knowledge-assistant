"""
Comprehensive Document Retrieval

Universal retrieval system that provides comprehensive results for ANY topic
"""

import logging
import re
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

def get_index_path(index_name: str) -> Path:
    """Get the path to an index directory."""
    base_path = Path(__file__).resolve().parent.parent / "data" / "indexes"
    index_path = base_path / index_name
    
    if index_path.exists():
        return index_path
    
    # Try alternative paths
    alt_paths = [
        base_path / f"{index_name}_index",
        base_path / index_name.replace("_index", ""),
    ]
    
    for alt_path in alt_paths:
        if alt_path.exists():
            return alt_path
    
    logger.warning(f"Index path not found for: {index_name}")
    return None

# Document chunking configuration
DOCUMENT_CHUNKING_OPTIONS = {
    "chunk_size": 1500,
    "chunk_overlap": 500,
    "respect_section_breaks": True,
    "extract_tables": True,
    "preserve_heading_structure": True
}

def retrieve_comprehensive_information(query: str, index_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Comprehensive retrieval for any query topic with embeddings support
    
    Args:
        query: User query about any topic
        index_name: Index to search
        max_results: Maximum results to return
        
    Returns:
        List of comprehensive results with structured content
    """
    try:
        # First try vector search with embeddings if available
        from utils.vector_search_with_embeddings import search_with_embeddings, validate_embeddings_available
        
        embeddings_available, message = validate_embeddings_available(index_name)
        
        if embeddings_available:
            logger.info(f"Using vector search with embeddings for {index_name}: {message}")
            
            # Use vector search for better accuracy
            vector_results = search_with_embeddings(query, index_name, max_results)
            
            if vector_results:
                # Enhanced processing with detailed section extraction
                try:
                    from utils.universal_section_extractor import extract_detailed_sections
                    
                    # Get the full document content for section extraction
                    index_path = Path(__file__).resolve().parent.parent / "data" / "indexes" / index_name
                    text_file = index_path / "extracted_text.txt"
                    
                    if text_file.exists():
                        with open(text_file, 'r', encoding='utf-8') as f:
                            full_content = f.read()
                        
                        # Extract detailed sections based on query intent
                        detailed_sections = extract_detailed_sections(full_content, query)
                        
                        if detailed_sections:
                            # Format detailed sections for response
                            formatted_results = []
                            for section in detailed_sections:
                                formatted_results.append({
                                    'content': section.get('content', ''),
                                    'source': f'{index_name}/extracted_text.txt',
                                    'page': section.get('page', 'N/A'),
                                    'section': section.get('title', 'N/A'),
                                    'confidence_score': section.get('relevance_score', 0.0),
                                    'metadata': {
                                        'section_type': section.get('section_type', 'general'),
                                        'word_count': section.get('word_count', 0),
                                        'has_procedures': section.get('has_procedures', False),
                                        'has_requirements': section.get('has_requirements', False),
                                        'document_type': section.get('document_type', 'general'),
                                        'query_intent': section.get('query_intent', {}),
                                        'detailed_extraction': True,
                                        'is_comprehensive': True
                                    }
                                })
                            
                            logger.info(f"Detailed section extraction returned {len(formatted_results)} results")
                            return formatted_results
                
                except ImportError:
                    logger.warning("Universal section extractor not available, using standard vector results")
        
        # First try document-aware chunking from PDF source
        from utils.document_aware_chunking import chunk_document_intelligently
        from utils.pdf_section_extractor import PDFSectionExtractor
        
        # Get the index path
        index_path = get_index_path(index_name)
        if index_path:
            pdf_path = index_path / "source_document.pdf"
            if pdf_path.exists():
                logger.info(f"Found PDF source document, using document-aware chunking")
                
                # Try document-aware chunking first
                try:
                    # Read PDF content
                    import PyPDF2
                    with open(pdf_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        full_text = ""
                        for page in pdf_reader.pages:
                            full_text += page.extract_text() + "\n"
                    
                    # Apply document-aware chunking
                    chunks = chunk_document_intelligently(full_text, str(pdf_path))
                    
                    if chunks:
                        logger.info(f"Document-aware chunking successful: {len(chunks)} chunks")
                        
                        # Filter chunks based on query relevance
                        query_lower = query.lower()
                        relevant_chunks = []
                        
                        for chunk in chunks:
                            content_lower = chunk['content'].lower()
                            section_lower = chunk['section'].lower()
                            
                            # Calculate relevance score
                            query_words = set(query_lower.split())
                            content_words = set(content_lower.split())
                            section_words = set(section_lower.split())
                            
                            content_matches = len(query_words.intersection(content_words))
                            section_matches = len(query_words.intersection(section_words))
                            
                            relevance_score = (section_matches * 2.0 + content_matches * 0.1) / len(query_words)
                            
                            if relevance_score > 0.1:  # Minimum relevance threshold
                                chunk['confidence_score'] = relevance_score
                                relevant_chunks.append(chunk)
                        
                        # Sort by relevance and return top results
                        relevant_chunks.sort(key=lambda x: x['confidence_score'], reverse=True)
                        return relevant_chunks[:max_results]
                
                except Exception as e:
                    logger.warning(f"Document-aware chunking failed: {e}")
                
                # Fallback to PDF section extractor
                extractor = PDFSectionExtractor()
                sections = extractor.find_section_content(str(pdf_path), query)
                
                if sections:
                    logger.info(f"PDF extraction successful: {len(sections)} sections found")
                    
                    # Format results for consistency
                    formatted_results = []
                    for section in sections[:max_results]:
                        formatted_results.append({
                            'content': f"**{section['section_title']}**\n\n{section['content']}",
                            'source': f"{index_name}/source_document.pdf",
                            'page': 'Multiple',
                            'section': section['section_title'],
                            'confidence_score': section['relevance_score'],
                            'word_count': section['word_count'],
                            'metadata': {
                                'extraction_method': 'pdf_direct',
                                'section_type': 'procedural' if 'procedure' in section['section_title'].lower() else 'general'
                            }
                        })
                    
                    return formatted_results
    
    except Exception as e:
        logger.warning(f"PDF direct extraction failed: {e}")
    
    try:
        # Import here to avoid circular imports
        from utils.enhanced_vector_integration import get_detailed_response_for_tab
        
        logger.info(f"Using enhanced vector integration for comprehensive retrieval")
        
        # Use enhanced vector integration for detailed section retrieval
        enhanced_response = get_detailed_response_for_tab(
            query=query,
            index_name=index_name,
            tab_name='comprehensive_retrieval',
            max_results=max_results
        )
        
        if enhanced_response and enhanced_response.get('source_documents'):
            logger.info(f"Enhanced vector integration successful: {len(enhanced_response['source_documents'])} results")
            return enhanced_response['source_documents']
    
    except Exception as e:
        logger.warning(f"Enhanced vector integration failed: {e}")
    
    # Fallback to original comprehensive retrieval
    logger.info(f"Retrieving comprehensive information for query: '{query}' from index: '{index_name}'")
    
    try:
        # Get the index path
        index_path = get_index_path(index_name)
        if not index_path:
            logger.error(f"Index '{index_name}' not found")
            return []
        
        # Load the index data
        extracted_text_path = index_path / "extracted_text.txt"
        if not extracted_text_path.exists():
            logger.error(f"No extracted text found for index '{index_name}'")
            return []
        
        # Read the content
        with open(extracted_text_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract key terms from query
        query_terms = extract_key_terms(query)
        logger.info(f"Extracted key terms: {query_terms}")
        
        # Find comprehensive sections related to the query using chunking options
        results = []
        
        # Method 1: Find sections containing query terms with proper chunking
        sections = find_relevant_sections_with_chunking(content, query_terms, DOCUMENT_CHUNKING_OPTIONS)
        
        for i, section in enumerate(sections):
            if len(section['content']) > DOCUMENT_CHUNKING_OPTIONS['chunk_size'] // 5:  # Minimum content threshold
                structured_content = structure_content_with_chunking(
                    section['content'], 
                    section['section_type'], 
                    query_terms, 
                    DOCUMENT_CHUNKING_OPTIONS
                )
                
                result = {
                    'content': structured_content,
                    'source': f'{index_name}/extracted_text.txt',
                    'page': section.get('page', 'N/A'),
                    'section': section.get('title', f'Section {i+1}'),
                    'confidence_score': section.get('relevance_score', 0.8),
                    'metadata': {
                        'section_type': section.get('section_type', 'general'),
                        'match_terms': section.get('matched_terms', []),
                        'content_length': len(structured_content),
                        'is_comprehensive': True,
                        'chunking_applied': True,
                        'chunk_size': DOCUMENT_CHUNKING_OPTIONS['chunk_size']
                    }
                }
                
                results.append(result)
        
        # Method 2: If no good sections found, use contextual search with chunking
        if not results:
            contextual_results = find_contextual_matches_with_chunking(content, query_terms, DOCUMENT_CHUNKING_OPTIONS)
            
            for i, context in enumerate(contextual_results):
                structured_content = structure_content_with_chunking(
                    context['content'], 
                    'contextual', 
                    query_terms, 
                    DOCUMENT_CHUNKING_OPTIONS
                )
                
                result = {
                    'content': structured_content,
                    'source': f'{index_name}/extracted_text.txt',
                    'page': context.get('page', 'N/A'),
                    'section': f'Related Content {i+1}',
                    'confidence_score': context.get('relevance_score', 0.6),
                    'metadata': {
                        'section_type': 'contextual',
                        'match_terms': context.get('matched_terms', []),
                        'content_length': len(structured_content),
                        'is_comprehensive': True,
                        'chunking_applied': True,
                        'chunk_size': DOCUMENT_CHUNKING_OPTIONS['chunk_size']
                    }
                }
                
                results.append(result)
        
        # Remove duplicates and sort by relevance
        unique_results = remove_duplicates(results)
        unique_results.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        logger.info(f"Found {len(unique_results)} comprehensive results")
        
        return unique_results[:max_results]
        
    except Exception as e:
        logger.error(f"Failed to retrieve comprehensive information: {e}")
        return []

def extract_key_terms(query: str) -> List[str]:
    """Extract key terms from the query"""
    try:
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'about', 'all', 'information', 'provide'}
        
        # Split and clean terms
        terms = re.findall(r'\b\w+\b', query.lower())
        key_terms = [term for term in terms if term not in stop_words and len(term) > 2]
        
        # Add variations and synonyms
        expanded_terms = key_terms.copy()
        
        # Add common legal/business synonyms
        synonyms = {
            'board': ['directors', 'governance', 'management'],
            'meeting': ['meetings', 'session', 'assembly'],
            'member': ['members', 'membership', 'owner', 'owners'],
            'vote': ['voting', 'ballot', 'election'],
            'fee': ['fees', 'assessment', 'charge', 'cost'],
            'rule': ['rules', 'regulation', 'bylaw', 'policy'],
            'committee': ['committees', 'group', 'panel'],
            'officer': ['officers', 'official', 'executive'],
            'property': ['properties', 'real estate', 'land'],
            'association': ['organization', 'corporation', 'entity']
        }
        
        for term in key_terms:
            if term in synonyms:
                expanded_terms.extend(synonyms[term])
        
        return list(set(expanded_terms))
        
    except Exception as e:
        logger.error(f"Failed to extract key terms: {e}")
        return [query.lower()]

def find_relevant_sections_with_chunking(content: str, query_terms: List[str], chunking_options: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Find sections relevant to the query terms"""
    try:
        sections = []
        
        # Split content into logical sections
        # Method 1: Split by Articles
        article_sections = re.split(r'(ARTICLE [IVX]+\..*?)(?=ARTICLE|\Z)', content, flags=re.IGNORECASE)
        
        for i, section in enumerate(article_sections):
            if len(section) > chunking_options['chunk_size'] // 10:  # Minimum size based on chunk size
                relevance_score, matched_terms = calculate_relevance(section, query_terms)
                
                if relevance_score > 0.1:  # Minimum relevance threshold
                    # Apply chunking if section is too large
                    chunked_sections = apply_intelligent_chunking(section, chunking_options)
                    
                    for chunk_idx, chunk in enumerate(chunked_sections):
                        # Extract page numbers
                        page_matches = re.findall(r'Page (\d+)', chunk)
                        page_range = f"{min(page_matches)}-{max(page_matches)}" if len(page_matches) > 1 else (page_matches[0] if page_matches else 'N/A')
                        
                        # Extract section title
                        title_match = re.search(r'ARTICLE [IVX]+\.\s*([^.]+)', chunk, re.IGNORECASE)
                        title = title_match.group(1).strip() if title_match else f'Section {i+1}'
                        if len(chunked_sections) > 1:
                            title += f' (Part {chunk_idx + 1})'
                        
                        sections.append({
                            'content': chunk.strip(),
                            'page': page_range,
                            'title': title,
                            'section_type': 'article',
                            'relevance_score': relevance_score,
                            'matched_terms': matched_terms,
                            'chunk_index': chunk_idx,
                            'total_chunks': len(chunked_sections)
                        })
        
        # Method 2: Split by major sections if no articles found
        if not sections:
            major_sections = re.split(r'([A-Z]\.\s+[A-Z][^.]+)', content)
            
            for i, section in enumerate(major_sections):
                if len(section) > 200:
                    relevance_score, matched_terms = calculate_relevance(section, query_terms)
                    
                    if relevance_score > 0.1:
                        page_matches = re.findall(r'Page (\d+)', section)
                        page_range = page_matches[0] if page_matches else 'N/A'
                        
                        sections.append({
                            'content': section.strip(),
                            'page': page_range,
                            'title': f'Section {i+1}',
                            'section_type': 'major_section',
                            'relevance_score': relevance_score,
                            'matched_terms': matched_terms
                        })
        
        return sections
        
    except Exception as e:
        logger.error(f"Failed to find relevant sections: {e}")
        return []

def apply_intelligent_chunking(content: str, chunking_options: Dict[str, Any]) -> List[str]:
    """Apply intelligent chunking with improved word boundary preservation"""
    try:
        from utils.improved_text_chunking import apply_improved_intelligent_chunking
        return apply_improved_intelligent_chunking(content, chunking_options)
        
    except ImportError:
        # Fallback to original chunking with word boundary fixes
        chunk_size = chunking_options['chunk_size']
        chunk_overlap = chunking_options['chunk_overlap']
        respect_section_breaks = chunking_options['respect_section_breaks']
        preserve_heading_structure = chunking_options['preserve_heading_structure']
        
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            if end >= len(content):
                chunks.append(content[start:].strip())
                break
            
            # Find word boundary to avoid cutting words
            original_end = end
            
            # Look backwards for word boundary (up to 100 chars)
            while end > start + chunk_size - 100 and end > 0:
                if content[end].isspace() or content[end] in '.,;:!?()[]{}':
                    break
                end -= 1
            
            # If no good boundary found, look forward
            if end <= start + chunk_size - 100:
                end = original_end
                while end < len(content) and end < start + chunk_size + 100:
                    if content[end].isspace() or content[end] in '.,;:!?()[]{}':
                        break
                    end += 1
            
            # Respect section breaks if enabled
            if respect_section_breaks:
                # Look for natural break points near the end
                break_patterns = [r'\n\n--- Page \d+ ---\n', r'\n\nARTICLE [IVX]+\.', r'\n\n[A-Z]\. ', r'\n\nSection \d+\.', r'\n\n']
                best_break = end
                best_score = 0
                
                search_start = max(start, end - 300)
                search_text = content[search_start:end + 200]
                
                for pattern in break_patterns:
                    matches = list(re.finditer(pattern, search_text))
                    for match in matches:
                        potential_break = search_start + match.end()
                        if start + 200 <= potential_break <= end + 100:
                            # Prefer breaks closer to target end
                            score = 1.0 - abs(potential_break - end) / 300
                            if score > best_score:
                                best_score = score
                                best_break = potential_break
                
                end = best_break
            
            chunk = content[start:end].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
            
            # Apply overlap with word boundary respect
            start = max(start + 1, end - chunk_overlap) if chunk_overlap > 0 else end
            
            # Ensure we don't start in middle of word
            while start < len(content) and not content[start].isspace() and start > 0:
                if content[start - 1].isspace():
                    break
                start -= 1
        
        # Remove any empty chunks
        chunks = [chunk for chunk in chunks if chunk.strip()]
        return chunks
        
    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        return [content]  # Return original content as fallback

def find_contextual_matches_with_chunking(content: str, query_terms: List[str], chunking_options: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Find contextual matches when no clear sections are found"""
    try:
        matches = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Check if line contains any query terms
            matched_terms = [term for term in query_terms if term in line_lower]
            
            if matched_terms:
                # Get context around the match (10 lines before and after)
                start_idx = max(0, i - 10)
                end_idx = min(len(lines), i + 15)
                
                context_lines = lines[start_idx:end_idx]
                context_text = '\n'.join(context_lines).strip()
                
                if len(context_text) > 100:
                    relevance_score = len(matched_terms) / len(query_terms)
                    
                    # Extract page number
                    page_match = re.search(r'Page (\d+)', context_text)
                    page_num = page_match.group(1) if page_match else 'N/A'
                    
                    matches.append({
                        'content': context_text,
                        'page': page_num,
                        'relevance_score': relevance_score,
                        'matched_terms': matched_terms
                    })
        
        # Remove duplicates and keep best matches
        unique_matches = []
        for match in matches:
            is_duplicate = False
            for existing in unique_matches:
                overlap = len(set(match['content'].split()) & set(existing['content'].split()))
                total_words = len(set(match['content'].split()) | set(existing['content'].split()))
                
                if total_words > 0 and overlap / total_words > 0.6:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_matches.append(match)
        
        return unique_matches[:10]
        
    except Exception as e:
        logger.error(f"Failed to find contextual matches: {e}")
        return []

def calculate_relevance(text: str, query_terms: List[str]) -> tuple:
    """Calculate relevance score and matched terms"""
    try:
        text_lower = text.lower()
        matched_terms = []
        term_counts = {}
        
        for term in query_terms:
            count = text_lower.count(term)
            if count > 0:
                matched_terms.append(term)
                term_counts[term] = count
        
        if not matched_terms:
            return 0.0, []
        
        # Calculate score based on term frequency and coverage
        total_matches = sum(term_counts.values())
        term_coverage = len(matched_terms) / len(query_terms)
        frequency_score = min(total_matches / 10, 1.0)  # Normalize frequency
        
        relevance_score = (term_coverage * 0.7) + (frequency_score * 0.3)
        
        return relevance_score, matched_terms
        
    except Exception as e:
        logger.error(f"Failed to calculate relevance: {e}")
        return 0.0, []

def structure_content_with_chunking(content: str, section_type: str, query_terms: List[str], chunking_options: Dict[str, Any]) -> str:
    """Structure content with chunking-aware formatting"""
    try:
        preserve_heading_structure = chunking_options.get('preserve_heading_structure', True)
        extract_tables = chunking_options.get('extract_tables', True)
        
        # Clean up content
        structured = content.strip()
        
        # Preserve heading structure if enabled
        if preserve_heading_structure:
            # Enhance headings with markdown
            structured = re.sub(r'^(ARTICLE [IVX]+\..*?)$', r'## \1', structured, flags=re.MULTILINE)
            structured = re.sub(r'^([A-Z]\d*\. [A-Z][^.]+)$', r'### \1', structured, flags=re.MULTILINE)
            structured = re.sub(r'^(\([a-z]\) [A-Z][^.]+)$', r'#### \1', structured, flags=re.MULTILINE)
        
        # Extract and format tables if enabled
        if extract_tables:
            # Look for tabular data patterns
            table_patterns = [
                r'((?:[A-Z][^\n]*\s+\$[\d,]+[^\n]*\n)+)',  # Financial tables
                r'((?:[^\n]*\|[^\n]*\n)+)',  # Pipe-separated tables
                r'((?:[A-Z][^\n]*\s+\d+%[^\n]*\n)+)'  # Percentage tables
            ]
            
            for pattern in table_patterns:
                structured = re.sub(pattern, r'\n**Table:**\n```\n\1```\n', structured, flags=re.MULTILINE)
        
        # Highlight query terms
        for term in query_terms:
            if len(term) > 2:  # Only highlight meaningful terms
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                structured = pattern.sub(f'**{term.upper()}**', structured)
        
        # Add section type indicator
        if section_type == 'article':
            structured = f"📋 **Article Section**\n\n{structured}"
        elif section_type == 'contextual':
            structured = f"🔍 **Related Content**\n\n{structured}"
        else:
            structured = f"📄 **Document Section**\n\n{structured}"
        
        return structured
        
    except Exception as e:
        logger.error(f"Content structuring failed: {e}")
        return content

def structure_content(content: str, section_type: str, query_terms: List[str]) -> str:
    """Structure content for better readability"""
    try:
        # Clean up the content
        content = re.sub(r'\n+', '\n', content)
        content = re.sub(r'\s+', ' ', content)
        
        # Create structured output based on content type
        if section_type == 'article':
            # Extract article title
            title_match = re.search(r'ARTICLE [IVX]+\.\s*([^.]+)', content, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else 'Article'
            
            structured = f"# {title.upper()}\n\n"
            
            # Extract main content after title
            main_content = re.sub(r'ARTICLE [IVX]+\..*?\n', '', content, flags=re.IGNORECASE)
            
            # Split into subsections
            subsections = re.split(r'([A-Z]\.\s+[A-Z][^.]+)', main_content)
            
            current_section = ""
            for part in subsections:
                if re.match(r'[A-Z]\.\s+[A-Z]', part):
                    if current_section:
                        structured += f"{current_section}\n\n"
                    structured += f"## {part.strip()}\n\n"
                    current_section = ""
                else:
                    current_section += part.strip()
            
            if current_section:
                structured += f"{current_section}\n\n"
            
            return structured
            
        elif section_type == 'major_section':
            # Extract section title
            title_match = re.search(r'([A-Z]\.\s+[A-Z][^.]+)', content)
            title = title_match.group(1).strip() if title_match else 'Section'
            
            structured = f"# {title.upper()}\n\n"
            
            # Add main content
            main_content = re.sub(r'[A-Z]\.\s+[A-Z][^.]+\n?', '', content, count=1)
            structured += f"{main_content.strip()}\n\n"
            
            return structured
            
        else:  # contextual
            # Highlight matched terms
            highlighted_content = content
            for term in query_terms:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                highlighted_content = pattern.sub(f"**{term.upper()}**", highlighted_content)
            
            structured = f"# RELEVANT INFORMATION\n\n{highlighted_content}\n\n"
            
            return structured
        
    except Exception as e:
        logger.error(f"Failed to structure content: {e}")
        return raw_content[:2000] + "..." if len(raw_content) > 2000 else raw_content

def remove_duplicates(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate results based on content similarity"""
    try:
        unique_results = []
        
        for result in results:
            is_duplicate = False
            for existing in unique_results:
                # Check for substantial overlap
                overlap = len(set(result['content'].split()) & set(existing['content'].split()))
                total_words = len(set(result['content'].split()) | set(existing['content'].split()))
                
                if total_words > 0 and overlap / total_words > 0.7:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_results.append(result)
        
        return unique_results
        
    except Exception as e:
        logger.error(f"Failed to remove duplicates: {e}")
        return results
