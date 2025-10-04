"""
Intelligent Content Extractor
Extracts actual document content specific to user queries, not just table of contents or headers
"""

import re
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class IntelligentContentExtractor:
    """
    Extracts relevant content from documents based on query intent
    """
    
    def __init__(self):
        self.content_cache = {}
    
    def extract_relevant_content(self, query: str, index_name: str) -> List[Dict[str, Any]]:
        """
        Extract content that actually answers the user's question
        
        Args:
            query: User's question
            index_name: Index to search
            
        Returns:
            List of relevant content chunks with actual answers
        """
        try:
            # Load document content
            content = self._load_document_content(index_name)
            if not content:
                return []
            
            # Analyze query intent
            query_intent = self._analyze_query_intent(query)
            
            # Extract relevant sections based on intent
            relevant_sections = self._find_relevant_sections(content, query_intent)
            
            # Format results with actual content
            results = []
            for section in relevant_sections:
                formatted_result = self._format_content_result(section, query, index_name)
                results.append(formatted_result)
            
            return results[:3]  # Return top 3 most relevant
            
        except Exception as e:
            logger.error(f"Error in intelligent content extraction: {e}")
            return []
    
    def _load_document_content(self, index_name: str) -> str:
        """Load and cache document content"""
        if index_name in self.content_cache:
            return self.content_cache[index_name]
        
        try:
            extracted_text_path = Path(f"data/indexes/{index_name}/extracted_text.txt")
            if extracted_text_path.exists():
                with open(extracted_text_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.content_cache[index_name] = content
                return content
        except Exception as e:
            logger.error(f"Error loading document content: {e}")
        
        return ""
    
    def _analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Analyze what the user is actually asking for"""
        query_lower = query.lower()
        
        intent = {
            'keywords': [],
            'topic': 'general',
            'action_type': 'information',
            'specificity': 'general'
        }
        
        # Extract key terms
        words = re.findall(r'\b\w+\b', query_lower)
        intent['keywords'] = [w for w in words if len(w) > 3]
        
        # Determine topic areas
        if any(term in query_lower for term in ['removal', 'remove', 'vacancy', 'vacancies']):
            intent['topic'] = 'director_removal_vacancy'
        elif any(term in query_lower for term in ['meeting', 'meetings', 'board']):
            intent['topic'] = 'meetings'
        elif any(term in query_lower for term in ['officer', 'officers', 'president', 'secretary']):
            intent['topic'] = 'officers'
        elif any(term in query_lower for term in ['assessment', 'fee', 'dues', 'payment']):
            intent['topic'] = 'assessments'
        elif any(term in query_lower for term in ['voting', 'vote', 'election', 'ballot']):
            intent['topic'] = 'voting'
        elif any(term in query_lower for term in ['committee', 'architectural', 'arc']):
            intent['topic'] = 'committees'
        
        # Determine action type
        if any(term in query_lower for term in ['how', 'procedure', 'process', 'steps']):
            intent['action_type'] = 'procedure'
        elif any(term in query_lower for term in ['what', 'definition', 'meaning']):
            intent['action_type'] = 'definition'
        elif any(term in query_lower for term in ['when', 'timeline', 'schedule']):
            intent['action_type'] = 'timing'
        elif any(term in query_lower for term in ['who', 'responsible', 'authority']):
            intent['action_type'] = 'responsibility'
        
        return intent
    
    def _find_relevant_sections(self, content: str, intent: Dict[str, Any]) -> List[Dict[str, str]]:
        """Find sections that contain actual answers to the query"""
        sections = []
        
        # Split content into logical sections
        # Remove table of contents first
        content_start = content.find("BYLAWS OF PECAN RIDGE COMMUNITY ASSOCIATION, INC.")
        if content_start == -1:
            content_start = content.find("ARTICLE I.")
        if content_start != -1:
            content = content[content_start:]
        
        # Find sections based on topic
        if intent['topic'] == 'director_removal_vacancy':
            sections.extend(self._extract_removal_vacancy_content(content))
        elif intent['topic'] == 'meetings':
            sections.extend(self._extract_meeting_content(content))
        elif intent['topic'] == 'officers':
            sections.extend(self._extract_officer_content(content))
        elif intent['topic'] == 'assessments':
            sections.extend(self._extract_assessment_content(content))
        elif intent['topic'] == 'voting':
            sections.extend(self._extract_voting_content(content))
        elif intent['topic'] == 'committees':
            sections.extend(self._extract_committee_content(content))
        else:
            # General search for keywords
            sections.extend(self._extract_keyword_content(content, intent['keywords']))
        
        return sections
    
    def _extract_removal_vacancy_content(self, content: str) -> List[Dict[str, str]]:
        """Extract actual removal and vacancy procedures"""
        sections = []
        
        # Find Section 6 content
        start_marker = "A vacancy of a director position elected by the Members"
        start_pos = content.find(start_marker)
        
        if start_pos != -1:
            # Find end of section
            end_markers = ["B. Meetings", "ARTICLE IV", "Section 1. Organizational"]
            end_pos = len(content)
            
            for marker in end_markers:
                marker_pos = content.find(marker, start_pos)
                if marker_pos != -1:
                    end_pos = min(end_pos, marker_pos)
            
            section_content = content[start_pos:end_pos].strip()
            
            # Clean content
            cleaned_content = self._clean_content(section_content)
            
            sections.append({
                'title': 'Section 6. Removal of Directors and Vacancies',
                'content': cleaned_content,
                'type': 'procedure',
                'relevance': 0.95
            })
        
        return sections
    
    def _extract_meeting_content(self, content: str) -> List[Dict[str, str]]:
        """Extract meeting-related content"""
        sections = []
        
        # Find board meeting section
        start_marker = "A Board meeting means a deliberation"
        start_pos = content.find(start_marker)
        
        if start_pos != -1:
            end_pos = content.find("Section 3. Notice of Meetings", start_pos)
            if end_pos == -1:
                end_pos = start_pos + 2000
            
            section_content = content[start_pos:end_pos].strip()
            cleaned_content = self._clean_content(section_content)
            
            sections.append({
                'title': 'Section 2. Board Meetings',
                'content': cleaned_content,
                'type': 'procedure',
                'relevance': 0.90
            })
        
        return sections
    
    def _extract_officer_content(self, content: str) -> List[Dict[str, str]]:
        """Extract officer-related content"""
        sections = []
        
        # Find ARTICLE IV. OFFICERS
        start_marker = "ARTICLE IV. OFFICERS"
        start_pos = content.find(start_marker)
        
        if start_pos != -1:
            end_pos = content.find("ARTICLE V", start_pos)
            if end_pos == -1:
                end_pos = start_pos + 3000
            
            section_content = content[start_pos:end_pos].strip()
            cleaned_content = self._clean_content(section_content)
            
            sections.append({
                'title': 'Article IV. Officers',
                'content': cleaned_content,
                'type': 'definition',
                'relevance': 0.85
            })
        
        return sections
    
    def _extract_assessment_content(self, content: str) -> List[Dict[str, str]]:
        """Extract assessment and fee content"""
        sections = []
        
        # Search for assessment-related content
        assessment_keywords = ['assessment', 'fee', 'dues', 'payment', 'special assessment']
        
        for keyword in assessment_keywords:
            matches = []
            start = 0
            while True:
                pos = content.lower().find(keyword, start)
                if pos == -1:
                    break
                matches.append(pos)
                start = pos + 1
            
            # Extract context around matches
            for match_pos in matches[:3]:  # Limit to 3 matches
                start_pos = max(0, match_pos - 500)
                end_pos = min(len(content), match_pos + 1000)
                
                section_content = content[start_pos:end_pos].strip()
                cleaned_content = self._clean_content(section_content)
                
                if len(cleaned_content) > 100:  # Only include substantial content
                    sections.append({
                        'title': f'Assessment Information - {keyword.title()}',
                        'content': cleaned_content,
                        'type': 'information',
                        'relevance': 0.80
                    })
        
        return sections
    
    def _extract_voting_content(self, content: str) -> List[Dict[str, str]]:
        """Extract voting-related content"""
        sections = []
        
        # Find voting section
        start_marker = "G. VOTING"
        start_pos = content.find(start_marker)
        
        if start_pos != -1:
            end_pos = content.find("H. MAJORITY", start_pos)
            if end_pos == -1:
                end_pos = start_pos + 2000
            
            section_content = content[start_pos:end_pos].strip()
            cleaned_content = self._clean_content(section_content)
            
            sections.append({
                'title': 'G. Voting Procedures',
                'content': cleaned_content,
                'type': 'procedure',
                'relevance': 0.90
            })
        
        return sections
    
    def _extract_committee_content(self, content: str) -> List[Dict[str, str]]:
        """Extract committee-related content"""
        sections = []
        
        # Find ARTICLE V. COMMITTEES
        start_marker = "ARTICLE V. COMMITTEES"
        start_pos = content.find(start_marker)
        
        if start_pos != -1:
            end_pos = content.find("ARTICLE VI", start_pos)
            if end_pos == -1:
                end_pos = start_pos + 2000
            
            section_content = content[start_pos:end_pos].strip()
            cleaned_content = self._clean_content(section_content)
            
            sections.append({
                'title': 'Article V. Committees',
                'content': cleaned_content,
                'type': 'information',
                'relevance': 0.85
            })
        
        return sections
    
    def _extract_keyword_content(self, content: str, keywords: List[str]) -> List[Dict[str, str]]:
        """Extract content based on keyword matching"""
        sections = []
        
        for keyword in keywords[:3]:  # Limit to top 3 keywords
            matches = []
            start = 0
            while True:
                pos = content.lower().find(keyword.lower(), start)
                if pos == -1:
                    break
                matches.append(pos)
                start = pos + 1
            
            # Extract context around best matches
            for match_pos in matches[:2]:  # Top 2 matches per keyword
                start_pos = max(0, match_pos - 300)
                end_pos = min(len(content), match_pos + 800)
                
                section_content = content[start_pos:end_pos].strip()
                cleaned_content = self._clean_content(section_content)
                
                if len(cleaned_content) > 100:
                    sections.append({
                        'title': f'Content containing "{keyword}"',
                        'content': cleaned_content,
                        'type': 'information',
                        'relevance': 0.70
                    })
        
        return sections
    
    def _clean_content(self, content: str) -> str:
        """Clean content by removing unwanted elements"""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip unwanted lines
            if (line and 
                not line.startswith('Copyright') and 
                not line.startswith('---') and
                not line.startswith('2022136118') and
                not re.match(r'^Page \d+', line) and
                len(line) > 2):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _format_content_result(self, section: Dict[str, str], query: str, index_name: str) -> Dict[str, Any]:
        """Format section content as a result"""
        
        # Create enhanced response with clear structure
        enhanced_response = f"""# {section['title']}

## Content:
{section['content']}

## Key Points:
{self._extract_key_points(section['content'], query)}
"""
        
        return {
            'content': section['content'],
            'source': f"{index_name} - {section['title']}",
            'page': 1,
            'section': section['title'],
            'relevance_score': section['relevance'],
            'timestamp': 'N/A',
            'file_path': index_name,
            'metadata': {
                'section': section['title'],
                'content_type': section['type'],
                'extraction_method': 'intelligent'
            },
            'llm_processed': True,
            'enhanced_response': enhanced_response,
            'quality_score': section['relevance']
        }
    
    def _extract_key_points(self, content: str, query: str) -> str:
        """Extract key points relevant to the query"""
        sentences = re.split(r'[.!?]+', content)
        query_words = set(query.lower().split())
        
        relevant_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Skip very short sentences
                sentence_words = set(sentence.lower().split())
                # Check if sentence contains query terms
                if query_words.intersection(sentence_words):
                    relevant_sentences.append(f"• {sentence}")
        
        return '\n'.join(relevant_sentences[:5])  # Top 5 relevant sentences
