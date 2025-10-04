"""
Enterprise Structured LLM Output System

Implements structured LLM responses with citations using Pydantic models
for enterprise-grade answer formatting and verification.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import json
import re
from datetime import datetime

try:
    from pydantic import BaseModel, Field, validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Fallback BaseModel for when Pydantic is not available
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
        
        def dict(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        
        def json(self):
            return json.dumps(self.dict())

logger = logging.getLogger(__name__)

@dataclass
class Citation:
    """Citation with precise source reference"""
    source: str
    page: Optional[str] = None
    section: Optional[str] = None
    article: Optional[str] = None
    quote: Optional[str] = None
    confidence: float = 1.0
    
    def format_citation(self) -> str:
        """Format citation for display"""
        parts = [self.source]
        
        if self.article:
            parts.append(f"Article {self.article}")
        if self.section:
            parts.append(f"Section {self.section}")
        if self.page:
            parts.append(f"Page {self.page}")
        
        citation = ", ".join(parts)
        
        if self.quote:
            citation += f' - "{self.quote[:100]}..."' if len(self.quote) > 100 else f' - "{self.quote}"'
        
        return citation

class StructuredResponse(BaseModel):
    """Structured response model with citations"""
    direct_answer: str = Field(description="A concise, direct answer to the user's query")
    key_details: List[str] = Field(description="Bulleted list of the most important details from the sources")
    citations: List[str] = Field(description="List of precise source citations")
    confidence_score: float = Field(default=0.8, description="Confidence in the answer accuracy (0-1)")
    answer_type: str = Field(default="factual", description="Type of answer: factual, procedural, interpretive")
    sources_used: int = Field(default=0, description="Number of sources consulted")
    
    if PYDANTIC_AVAILABLE:
        @validator('confidence_score')
        def validate_confidence(cls, v):
            return max(0.0, min(1.0, v))
        
        @validator('key_details')
        def validate_details(cls, v):
            return [detail.strip() for detail in v if detail.strip()]

class LegalStructuredResponse(BaseModel):
    """Specialized structured response for legal documents"""
    direct_answer: str = Field(description="Direct legal answer based on document provisions")
    applicable_articles: List[str] = Field(description="Relevant articles and sections")
    key_provisions: List[str] = Field(description="Key legal provisions that apply")
    procedural_steps: List[str] = Field(default_factory=list, description="Required procedural steps if applicable")
    citations: List[str] = Field(description="Precise legal citations with article/section references")
    legal_interpretation: str = Field(description="Interpretation of how the provisions apply")
    compliance_requirements: List[str] = Field(default_factory=list, description="Compliance requirements if any")
    confidence_score: float = Field(default=0.8, description="Confidence in legal interpretation")

class TechnicalStructuredResponse(BaseModel):
    """Specialized structured response for technical documents"""
    direct_answer: str = Field(description="Direct technical answer")
    implementation_steps: List[str] = Field(default_factory=list, description="Step-by-step implementation guide")
    code_examples: List[str] = Field(default_factory=list, description="Relevant code examples")
    configuration_details: List[str] = Field(default_factory=list, description="Configuration requirements")
    citations: List[str] = Field(description="Technical documentation citations")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites or dependencies")
    troubleshooting: List[str] = Field(default_factory=list, description="Common issues and solutions")
    confidence_score: float = Field(default=0.8, description="Confidence in technical accuracy")

class EnterpriseOutputFormatter:
    """Enterprise-grade output formatter with structured responses"""
    
    def __init__(self):
        self.response_templates = {
            "general": StructuredResponse,
            "legal": LegalStructuredResponse,
            "technical": TechnicalStructuredResponse
        }
    
    def create_structured_prompt(self, query: str, context: str, response_type: str = "general") -> str:
        """Create a structured prompt that forces LLM to provide formatted output"""
        
        if response_type == "legal":
            return self._create_legal_prompt(query, context)
        elif response_type == "technical":
            return self._create_technical_prompt(query, context)
        else:
            return self._create_general_prompt(query, context)
    
    def _create_general_prompt(self, query: str, context: str) -> str:
        """Create general structured prompt"""
        return f"""You are an expert assistant. Answer the user's question based ONLY on the following context.
Your answer must be factual and extracted from the context. Do not speculate or use outside knowledge.

Provide your response in the following JSON format:
{{
    "direct_answer": "A concise, direct answer to the user's query",
    "key_details": ["List of the most important details from the sources"],
    "citations": ["List of precise source citations, e.g., 'Document Name, Page 5, Section 2'"],
    "confidence_score": 0.8,
    "answer_type": "factual",
    "sources_used": 3
}}

Context:
---
{context}
---

Question: {query}

Response (JSON format only):"""
    
    def _create_legal_prompt(self, query: str, context: str) -> str:
        """Create legal document structured prompt"""
        return f"""You are an expert legal assistant. Answer the user's question based ONLY on the following legal document context.
Your answer must be factual and extracted from the legal provisions. Do not speculate or provide legal advice.

Provide your response in the following JSON format:
{{
    "direct_answer": "Direct legal answer based on document provisions",
    "applicable_articles": ["List of relevant articles and sections"],
    "key_provisions": ["Key legal provisions that apply"],
    "procedural_steps": ["Required procedural steps if applicable"],
    "citations": ["Precise legal citations with article/section references"],
    "legal_interpretation": "Interpretation of how the provisions apply",
    "compliance_requirements": ["Compliance requirements if any"],
    "confidence_score": 0.8
}}

Legal Document Context:
---
{context}
---

Legal Question: {query}

Response (JSON format only):"""
    
    def _create_technical_prompt(self, query: str, context: str) -> str:
        """Create technical document structured prompt"""
        return f"""You are an expert technical assistant. Answer the user's question based ONLY on the following technical documentation.
Your answer must be factual and extracted from the documentation. Do not speculate or use outside knowledge.

Provide your response in the following JSON format:
{{
    "direct_answer": "Direct technical answer",
    "implementation_steps": ["Step-by-step implementation guide"],
    "code_examples": ["Relevant code examples"],
    "configuration_details": ["Configuration requirements"],
    "citations": ["Technical documentation citations"],
    "prerequisites": ["Prerequisites or dependencies"],
    "troubleshooting": ["Common issues and solutions"],
    "confidence_score": 0.8
}}

Technical Documentation Context:
---
{context}
---

Technical Question: {query}

Response (JSON format only):"""
    
    def parse_llm_response(self, response_text: str, response_type: str = "general") -> Union[StructuredResponse, Dict[str, Any]]:
        """Parse LLM response into structured format"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                return self._create_fallback_response(response_text, response_type)
            
            json_str = json_match.group()
            response_data = json.loads(json_str)
            
            # Create appropriate response model
            if PYDANTIC_AVAILABLE:
                response_class = self.response_templates.get(response_type, StructuredResponse)
                return response_class(**response_data)
            else:
                return response_data
                
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse structured response: {e}")
            return self._create_fallback_response(response_text, response_type)
    
    def _create_fallback_response(self, response_text: str, response_type: str) -> Dict[str, Any]:
        """Create fallback response when parsing fails"""
        # Extract key information from unstructured response
        sentences = [s.strip() for s in response_text.split('.') if s.strip()]
        
        fallback = {
            "direct_answer": sentences[0] if sentences else response_text[:200],
            "key_details": sentences[1:4] if len(sentences) > 1 else [response_text[:500]],
            "citations": self._extract_citations(response_text),
            "confidence_score": 0.6,  # Lower confidence for fallback
            "answer_type": "unstructured",
            "sources_used": len(self._extract_citations(response_text))
        }
        
        # Add type-specific fields
        if response_type == "legal":
            fallback.update({
                "applicable_articles": self._extract_articles(response_text),
                "key_provisions": sentences[1:3] if len(sentences) > 1 else [],
                "legal_interpretation": sentences[-1] if sentences else "",
                "procedural_steps": [],
                "compliance_requirements": []
            })
        elif response_type == "technical":
            fallback.update({
                "implementation_steps": self._extract_steps(response_text),
                "code_examples": self._extract_code(response_text),
                "configuration_details": [],
                "prerequisites": [],
                "troubleshooting": []
            })
        
        return fallback
    
    def _extract_citations(self, text: str) -> List[str]:
        """Extract potential citations from text"""
        citation_patterns = [
            r'(?:Page|p\.)\s*(\d+)',
            r'(?:Section|Sec\.)\s*(\d+)',
            r'(?:Article|Art\.)\s*([IVX]+|\d+)',
            r'(?:Chapter|Ch\.)\s*(\d+)'
        ]
        
        citations = []
        for pattern in citation_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                citations.append(f"Reference: {match}")
        
        return citations[:5]  # Limit to 5 citations
    
    def _extract_articles(self, text: str) -> List[str]:
        """Extract article references from legal text"""
        article_pattern = r'(?:Article|ARTICLE)\s+([IVX]+|\d+)(?:\.|,|\s)'
        matches = re.findall(article_pattern, text, re.IGNORECASE)
        return [f"Article {match}" for match in matches[:5]]
    
    def _extract_steps(self, text: str) -> List[str]:
        """Extract numbered steps from technical text"""
        step_patterns = [
            r'(?:^|\n)\s*(\d+\..*?)(?=\n\d+\.|\n\n|$)',
            r'(?:^|\n)\s*([•\-\*]\s*.*?)(?=\n[•\-\*]|\n\n|$)'
        ]
        
        steps = []
        for pattern in step_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            steps.extend([match.strip() for match in matches])
        
        return steps[:10]  # Limit to 10 steps
    
    def _extract_code(self, text: str) -> List[str]:
        """Extract code blocks from technical text"""
        code_patterns = [
            r'```[\w]*\n(.*?)\n```',
            r'`([^`\n]+)`'
        ]
        
        code_blocks = []
        for pattern in code_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            code_blocks.extend([match.strip() for match in matches if len(match.strip()) > 10])
        
        return code_blocks[:5]  # Limit to 5 code examples
    
    def format_for_display(self, structured_response: Union[StructuredResponse, Dict[str, Any]]) -> str:
        """Format structured response for user display"""
        if isinstance(structured_response, dict):
            data = structured_response
        else:
            data = structured_response.dict() if hasattr(structured_response, 'dict') else structured_response.__dict__
        
        output = []
        
        # Direct Answer
        output.append(f"## Answer\n{data.get('direct_answer', 'No answer available')}\n")
        
        # Key Details
        if data.get('key_details'):
            output.append("## Key Details")
            for detail in data['key_details']:
                output.append(f"• {detail}")
            output.append("")
        
        # Type-specific sections
        if 'applicable_articles' in data and data['applicable_articles']:
            output.append("## Applicable Articles")
            for article in data['applicable_articles']:
                output.append(f"• {article}")
            output.append("")
        
        if 'implementation_steps' in data and data['implementation_steps']:
            output.append("## Implementation Steps")
            for i, step in enumerate(data['implementation_steps'], 1):
                output.append(f"{i}. {step}")
            output.append("")
        
        if 'code_examples' in data and data['code_examples']:
            output.append("## Code Examples")
            for code in data['code_examples']:
                output.append(f"```\n{code}\n```")
            output.append("")
        
        # Citations
        if data.get('citations'):
            output.append("## Sources")
            for citation in data['citations']:
                output.append(f"• {citation}")
            output.append("")
        
        # Confidence and metadata
        confidence = data.get('confidence_score', 0.0)
        sources_used = data.get('sources_used', 0)
        output.append(f"**Confidence:** {confidence:.1%} | **Sources:** {sources_used}")
        
        return "\n".join(output)
    
    def export_to_json(self, structured_response: Union[StructuredResponse, Dict[str, Any]], filename: str = None) -> str:
        """Export structured response to JSON file"""
        if isinstance(structured_response, dict):
            data = structured_response
        else:
            data = structured_response.dict() if hasattr(structured_response, 'dict') else structured_response.__dict__
        
        # Add metadata
        export_data = {
            "response": data,
            "exported_at": datetime.now().isoformat(),
            "format_version": "1.0"
        }
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                return f"Exported to {filename}"
            except Exception as e:
                logger.error(f"Export failed: {e}")
                return f"Export failed: {e}"
        else:
            return json.dumps(export_data, indent=2, ensure_ascii=False)

def get_enterprise_output_formatter() -> EnterpriseOutputFormatter:
    """Get instance of enterprise output formatter"""
    return EnterpriseOutputFormatter()

def create_structured_response(query: str, context: str, response_type: str = "general") -> Union[StructuredResponse, Dict[str, Any]]:
    """Convenience function to create structured response"""
    formatter = get_enterprise_output_formatter()
    
    # This would typically be called with an LLM
    # For now, return a template response
    if response_type == "legal":
        return {
            "direct_answer": "Based on the legal provisions provided...",
            "applicable_articles": ["Article II", "Section 3"],
            "key_provisions": ["Key provision 1", "Key provision 2"],
            "citations": ["Legal Document, Article II, Section 3"],
            "legal_interpretation": "The provisions indicate that...",
            "confidence_score": 0.8
        }
    else:
        return {
            "direct_answer": "Based on the provided context...",
            "key_details": ["Key detail 1", "Key detail 2"],
            "citations": ["Source 1, Page 5", "Source 2, Section 3"],
            "confidence_score": 0.8,
            "answer_type": "factual",
            "sources_used": 2
        }
