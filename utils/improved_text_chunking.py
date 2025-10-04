"""
Improved Text Chunking with Word Boundary Preservation

Enhanced chunking that prevents words from being cut off mid-word
and preserves document structure better.
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def apply_improved_intelligent_chunking(content: str, chunking_options: Dict[str, Any]) -> List[str]:
    """
    Apply intelligent chunking with improved word boundary preservation
    
    Args:
        content: Text content to chunk
        chunking_options: Chunking configuration
        
    Returns:
        List of text chunks with preserved word boundaries
    """
    try:
        chunk_size = chunking_options.get('chunk_size', 1500)
        chunk_overlap = chunking_options.get('chunk_overlap', 500)
        respect_section_breaks = chunking_options.get('respect_section_breaks', True)
        preserve_heading_structure = chunking_options.get('preserve_heading_structure', True)
        
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            if end >= len(content):
                chunks.append(content[start:].strip())
                break
            
            # Find the best break point to preserve word boundaries
            best_break = find_optimal_break_point(
                content, start, end, 
                respect_section_breaks, 
                preserve_heading_structure
            )
            
            chunk = content[start:best_break].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
            
            # Apply overlap with word boundary respect
            start = max(start + 1, best_break - chunk_overlap) if chunk_overlap > 0 else best_break
            
            # Ensure we don't start in the middle of a word
            start = find_word_start(content, start)
        
        # Remove any empty chunks
        chunks = [chunk for chunk in chunks if chunk.strip()]
        
        logger.info(f"Created {len(chunks)} chunks with improved word boundary preservation")
        return chunks
        
    except Exception as e:
        logger.error(f"Improved chunking failed: {e}")
        return [content]  # Return original content as fallback

def find_optimal_break_point(content: str, start: int, preferred_end: int, 
                           respect_sections: bool, preserve_headings: bool) -> int:
    """
    Find the optimal break point that preserves word and section boundaries
    
    Args:
        content: Full text content
        start: Start position of current chunk
        preferred_end: Preferred end position
        respect_sections: Whether to respect section breaks
        preserve_headings: Whether to preserve heading structure
        
    Returns:
        Optimal break point position
    """
    
    # Define search window for break points (look back up to 300 chars)
    search_window = min(300, preferred_end - start - 100)
    search_start = max(start, preferred_end - search_window)
    search_text = content[search_start:preferred_end + 200]  # Look ahead a bit too
    
    # Priority order of break patterns (higher priority first)
    break_patterns = []
    
    if respect_sections:
        # Major section breaks (highest priority)
        break_patterns.extend([
            (r'\n\n--- Page \d+ ---\n\n', 100),  # Page breaks
            (r'\n\nARTICLE [IVX]+\.', 95),       # Article starts
            (r'\n\n[A-Z]\. [A-Z][A-Z ]+\n', 90), # Major sections
            (r'\n\nSection \d+\.', 85),          # Numbered sections
        ])
    
    if preserve_headings:
        # Heading preservation
        break_patterns.extend([
            (r'\n[A-Z]\. [A-Z][A-Z ]+\.+', 80),  # Lettered headings
            (r'\n\([a-z]\) [A-Z]', 75),          # Subsection starts
        ])
    
    # Natural text breaks
    break_patterns.extend([
        (r'\n\n', 70),                    # Paragraph breaks
        (r'\. \n', 65),                   # Sentence ends with newline
        (r'\.\s+[A-Z]', 60),             # Sentence boundaries
        (r';\s+', 50),                    # Semicolon breaks
        (r',\s+', 30),                    # Comma breaks (last resort)
    ])
    
    best_break = preferred_end
    best_score = 0
    
    # Find the best break point
    for pattern, score in break_patterns:
        matches = list(re.finditer(pattern, search_text))
        
        for match in matches:
            break_pos = search_start + match.end()
            
            # Must be within reasonable range
            if start + 200 <= break_pos <= preferred_end + 100:
                # Prefer breaks closer to the preferred end but not too close to start
                distance_factor = 1.0 - abs(break_pos - preferred_end) / search_window
                final_score = score * distance_factor
                
                if final_score > best_score:
                    best_score = final_score
                    best_break = break_pos
    
    # Ensure we don't break in the middle of a word
    best_break = find_word_boundary(content, best_break)
    
    return best_break

def find_word_boundary(content: str, position: int) -> int:
    """
    Find the nearest word boundary to avoid cutting words in half
    
    Args:
        content: Text content
        position: Current position
        
    Returns:
        Position at word boundary
    """
    if position >= len(content):
        return len(content)
    
    # If we're at whitespace, we're already at a boundary
    if content[position].isspace():
        return position
    
    # Look backwards for word boundary (up to 50 chars)
    for i in range(position, max(0, position - 50), -1):
        if i < len(content) and (content[i].isspace() or content[i] in '.,;:!?()[]{}'):
            return i + 1 if content[i].isspace() else i
    
    # Look forwards for word boundary (up to 50 chars)
    for i in range(position, min(len(content), position + 50)):
        if content[i].isspace() or content[i] in '.,;:!?()[]{}':
            return i + 1 if content[i].isspace() else i
    
    # If no boundary found, return original position
    return position

def find_word_start(content: str, position: int) -> int:
    """
    Find the start of the word at the given position
    
    Args:
        content: Text content
        position: Current position
        
    Returns:
        Position at start of word
    """
    if position >= len(content) or content[position].isspace():
        return position
    
    # Move to start of current word
    while position > 0 and not content[position - 1].isspace():
        position -= 1
    
    return position

def validate_chunk_quality(chunks: List[str]) -> Dict[str, Any]:
    """
    Validate the quality of generated chunks
    
    Args:
        chunks: List of text chunks
        
    Returns:
        Quality metrics dictionary
    """
    if not chunks:
        return {'valid': False, 'issues': ['No chunks generated']}
    
    issues = []
    warnings = []
    
    for i, chunk in enumerate(chunks):
        chunk_stripped = chunk.strip()
        
        # Check for empty chunks
        if not chunk_stripped:
            issues.append(f'Chunk {i+1} is empty')
            continue
        
        # Check for very short chunks (might indicate poor splitting)
        if len(chunk_stripped) < 100:
            warnings.append(f'Chunk {i+1} is very short ({len(chunk_stripped)} chars)')
        
        # Check for broken words at start/end
        words = chunk_stripped.split()
        if words:
            first_word = words[0]
            last_word = words[-1]
            
            # Check if first word looks incomplete (starts with lowercase after space)
            if i > 0 and first_word[0].islower() and not first_word[0].isdigit():
                warnings.append(f'Chunk {i+1} may start with incomplete word: "{first_word}"')
            
            # Check if last word looks incomplete (ends abruptly)
            if i < len(chunks) - 1 and len(last_word) > 1 and last_word[-1].isalpha():
                next_chunk_words = chunks[i+1].strip().split()
                if next_chunk_words and next_chunk_words[0][0].islower():
                    warnings.append(f'Chunk {i+1} may end with incomplete word: "{last_word}"')
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'total_chunks': len(chunks),
        'avg_chunk_size': sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0
    }
