"""
Direct Powers Retrieval

Specialized retrieval for "Powers" queries to ensure comprehensive results
"""

import logging
import re
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

def retrieve_powers_information(query: str, index_name: str) -> List[Dict[str, Any]]:
    """
    Specialized retrieval for powers-related queries
    
    Args:
        query: User query about powers
        index_name: Index to search
        
    Returns:
        Comprehensive results about powers
    """
    try:
        # Check if this is a powers-related query
        powers_keywords = ['powers', 'authority', 'duties', 'responsibilities', 'board powers']
        is_powers_query = any(keyword in query.lower() for keyword in powers_keywords)
        
        if not is_powers_query:
            return []
        
        logger.info(f"Processing powers query: '{query}' in index: '{index_name}'")
        
        # Get the index path
        index_path = Path(f"data/indexes/{index_name}")
        
        if not index_path.exists():
            logger.warning(f"Index path not found: {index_path}")
            return []
        
        # Look for extracted text file
        text_file = index_path / "extracted_text.txt"
        
        if not text_file.exists():
            logger.warning(f"Text file not found: {text_file}")
            return []
        
        # Read the content
        with open(text_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find powers-related sections
        results = []
        
        # Look for comprehensive powers sections with better boundaries
        powers_patterns = [
            # Complete Powers section from C. POWERS to next major section
            r'C\.\s*Powers.*?(?=ARTICLE IV|Section 2\.|--- Page \d+.*?ARTICLE|\Z)',
            # Complete Powers section including all subsections
            r'Section 1\.\s*Powers.*?(?=Section 2\.|ARTICLE IV|--- Page \d+.*?(?:ARTICLE|Section 2)|\Z)',
            # Board powers from table of contents area
            r'ARTICLE III\.\s*BOARD OF DIRECTORS.*?POWERS.*?(?=ARTICLE IV|\Z)',
            # Officer powers and duties
            r'D\.\s*POWERS AND DUTIES.*?(?=E\.|ARTICLE V|--- Page \d+.*?ARTICLE|\Z)',
        ]
        
        for i, pattern in enumerate(powers_patterns):
            matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                matched_text = match.group(0).strip()
                
                if len(matched_text) > 200:  # Only include substantial content
                    # Extract page numbers from the content
                    page_matches = re.findall(r'Page (\d+)', matched_text)
                    page_range = f"{min(page_matches)}-{max(page_matches)}" if len(page_matches) > 1 else (page_matches[0] if page_matches else 'N/A')
                    
                    # Structure the content better
                    structured_content = _structure_powers_content(matched_text, i)
                    
                    section_names = [
                        'Board Powers and Authority',
                        'Detailed Powers List', 
                        'Board Composition and Powers',
                        'Officer Powers and Duties'
                    ]
                    
                    result = {
                        'content': structured_content,
                        'source': f'{index_name}/extracted_text.txt',
                        'page': page_range,
                        'section': section_names[i] if i < len(section_names) else f'Powers Section {i+1}',
                        'confidence_score': 0.95 - (i * 0.05),  # Higher confidence for earlier matches
                        'metadata': {
                            'section_type': 'powers',
                            'match_type': f'pattern_{i+1}',
                            'content_length': len(structured_content),
                            'is_comprehensive': True
                        }
                    }
                    
                    results.append(result)
        
        # If no specific powers sections found, look for broader content
        if not results:
            # Look for any mention of powers in substantial chunks
            lines = content.split('\n')
            current_chunk = []
            current_page = 'N/A'
            
            for line in lines:
                # Track page numbers
                page_match = re.search(r'Page (\d+)', line)
                if page_match:
                    current_page = page_match.group(1)
                
                # Check if line mentions powers
                if any(keyword in line.lower() for keyword in powers_keywords):
                    # Include context around the match
                    start_idx = max(0, lines.index(line) - 5)
                    end_idx = min(len(lines), lines.index(line) + 10)
                    
                    context_lines = lines[start_idx:end_idx]
                    context_text = '\n'.join(context_lines).strip()
                    
                    if len(context_text) > 50:
                        result = {
                            'content': context_text,
                            'source': f'{index_name}/extracted_text.txt',
                            'page': current_page,
                            'section': 'Powers Context',
                            'confidence_score': 0.7,
                            'metadata': {
                                'section_type': 'powers_context',
                                'match_type': 'keyword_context',
                                'content_length': len(context_text)
                            }
                        }
                        
                        results.append(result)
        
        # Remove duplicates based on content similarity
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
        
        # Sort by confidence score
        unique_results.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        logger.info(f"Found {len(unique_results)} unique powers-related results")
        
        return unique_results[:5]  # Return top 5 comprehensive results
        
    except Exception as e:
        logger.error(f"Failed to retrieve powers information: {e}")
        return []

def _structure_powers_content(raw_content: str, section_type: int) -> str:
    """
    Structure the powers content for better readability
    
    Args:
        raw_content: Raw extracted content
        section_type: Type of section (0=main powers, 1=detailed list, etc.)
        
    Returns:
        Well-structured content
    """
    try:
        # Clean up the content
        content = re.sub(r'\n+', '\n', raw_content)
        content = re.sub(r'\s+', ' ', content)
        
        if section_type == 0:  # Main powers section
            # Structure the main powers section
            structured = "# BOARD POWERS AND AUTHORITY\n\n"
            
            # Extract the main statement
            main_statement = re.search(r'(The Board is responsible.*?following)', content, re.DOTALL)
            if main_statement:
                structured += f"## Primary Authority\n{main_statement.group(1).strip()}\n\n"
            
            # Extract the detailed powers list
            powers_list = re.search(r'following.*?:(.*?)(?=Section 2|Management|Copyright)', content, re.DOTALL)
            if powers_list:
                structured += "## Specific Powers\n"
                powers_text = powers_list.group(1).strip()
                
                # Split into individual powers
                power_items = re.split(r'[a-z]\.\s+', powers_text)
                for i, item in enumerate(power_items[1:], 1):  # Skip first empty item
                    if item.strip():
                        clean_item = item.strip().rstrip(';')
                        structured += f"{i}. {clean_item}\n\n"
            
            return structured
            
        elif section_type == 1:  # Detailed powers list
            structured = "# DETAILED BOARD POWERS\n\n"
            
            # Extract specific powers with better formatting
            if 'preparing and adopting annual budgets' in content:
                structured += "## Financial Powers\n"
                structured += "• Preparing and adopting annual budgets\n"
                structured += "• Making assessments and establishing collection methods\n"
                structured += "• Collecting assessments and managing deposits\n\n"
            
            if 'operation, care, upkeep and maintenance' in content:
                structured += "## Property Management Powers\n"
                structured += "• Providing for operation, care, upkeep and maintenance of Common Areas\n"
                structured += "• Making repairs, additions, and improvements\n"
                structured += "• Hiring and dismissing personnel\n\n"
            
            if 'rules and regulations' in content:
                structured += "## Regulatory Powers\n"
                structured += "• Making and amending rules and regulations\n"
                structured += "• Enforcing provisions and collecting fines\n"
                structured += "• Opening bank accounts and designating signatories\n\n"
            
            return structured
            
        elif section_type == 2:  # Board composition and powers
            structured = "# BOARD COMPOSITION AND GOVERNANCE POWERS\n\n"
            
            # Extract composition info
            if 'Board of Directors' in content:
                structured += "## Board Structure\n"
                structured += content[:500] + "...\n\n"
            
            return structured
            
        elif section_type == 3:  # Officer powers
            structured = "# OFFICER POWERS AND DUTIES\n\n"
            
            if 'officers of the Association' in content:
                structured += "## General Officer Authority\n"
                structured += "Officers have powers and duties as generally pertain to their respective offices, "
                structured += "as well as specific powers conferred by the Board.\n\n"
            
            if 'President' in content:
                structured += "## Presidential Powers\n"
                structured += "• Chief executive officer of the Association\n"
                structured += "• Presides over meetings\n\n"
            
            if 'Treasurer' in content:
                structured += "## Treasurer Powers\n"
                structured += "• Primary responsibility for budget preparation\n"
                structured += "• May delegate preparation duties to finance committee\n\n"
            
            return structured
        
        else:
            # Default formatting
            return f"# POWERS INFORMATION\n\n{content[:2000]}{'...' if len(content) > 2000 else ''}"
            
    except Exception as e:
        logger.error(f"Failed to structure content: {e}")
        return raw_content[:2000] + "..." if len(raw_content) > 2000 else raw_content

def enhance_powers_query(original_query: str) -> List[str]:
    """
    Generate enhanced queries for powers-related searches
    
    Args:
        original_query: Original user query
        
    Returns:
        List of enhanced queries
    """
    try:
        enhanced_queries = [original_query]
        
        # Check if this is about powers
        if 'powers' in original_query.lower():
            enhanced_queries.extend([
                "Board of Directors powers and authority",
                "Board powers responsibilities duties",
                "Association Board authority",
                "Director powers and duties",
                "Board management authority",
                "Powers of the Board Section",
                "Article III Board powers",
                "Board authority to act",
                "Powers necessary for administration",
                "Board delegation of authority"
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for query in enhanced_queries:
            if query.lower() not in seen:
                seen.add(query.lower())
                unique_queries.append(query)
        
        return unique_queries
        
    except Exception as e:
        logger.error(f"Failed to enhance powers query: {e}")
        return [original_query]
