"""
Enhanced LLM Integration for Vector Retrieval

Fixes vector chunking and slicing issues by providing proper LLM integration
with comprehensive context management and response generation.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv
from .text_cleaning import clean_document_text

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class EnhancedLLMProcessor:
    """Enhanced LLM processor that properly handles vector retrieval results"""
    
    def __init__(self, model_name: Optional[str] = None):
        # Remove env var that can cause older SDKs to receive an unsupported 'project' kwarg
        try:
            os.environ.pop("OPENAI_PROJECT", None)
        except Exception:
            pass
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.available = any([
            os.getenv("OPENAI_API_KEY"),
            os.getenv("ANTHROPIC_API_KEY"),
            os.getenv("MISTRAL_API_KEY"),
            os.getenv("DEEPSEEK_API_KEY"),
            os.getenv("GROQ_API_KEY"),
            os.getenv("OLLAMA_BASE_URL"),
        ])
        self.model_name = model_name
        
    def process_retrieval_results(self, query: str, retrieval_results: List[Dict[str, Any]], 
                                index_name: str, model_name: Optional[str] = None, answer_style: Optional[str] = None) -> Dict[str, Any]:
        """
        Process vector retrieval results with proper LLM integration
        
        Args:
            query: User query
            retrieval_results: Results from vector retrieval
            index_name: Name of the index being queried
            
        Returns:
            Enhanced response with proper LLM processing
        """
        try:
            if not self.available:
                logger.warning("OpenAI API key not available, using fallback processing")
                return self._fallback_processing(query, retrieval_results)
            
            # Create comprehensive context from retrieval results
            context = self._build_comprehensive_context(retrieval_results)
            
            # Generate enhanced prompt
            enhanced_prompt = self._create_enhanced_prompt(query, context, index_name, answer_style=answer_style)
            
            # Get LLM response with proper context handling
            llm_response = self._get_llm_response(enhanced_prompt, model_name=(model_name or self.model_name))
            
            # Format final response
            return {
                "result": llm_response,
                "source_documents": retrieval_results,
                "context_used": len(retrieval_results),
                "processing_method": "enhanced_llm",
                "query_processed": query,
                "index_name": index_name
            }
            
        except Exception as e:
            logger.error(f"Enhanced LLM processing failed: {e}")
            return self._fallback_processing(query, retrieval_results)
    
    def _build_comprehensive_context(self, retrieval_results: List[Dict[str, Any]]) -> str:
        """Build comprehensive context from retrieval results"""
        try:
            if not retrieval_results:
                return "No relevant information found in the documents."
            
            context_parts = []
            
            for i, result in enumerate(retrieval_results[:3], 1):  # Limit to top 3 results for brevity
                content = result.get('content', '')
                source = result.get('source', 'Unknown')
                page = result.get('page', 'N/A')
                section = result.get('section', 'N/A')
                
                # Clean and format content using the dedicated utility
                if content:
                    content = clean_document_text(content)
                    
                    # Truncate if too long but preserve important information
                    if len(content) > 2000:
                        content = content[:1800] + "... [Content continues]"
                    
                    context_part = f"""
Document {i}:
Source: {source}
Page: {page}
Section: {section}
Content: {content}
"""
                    context_parts.append(context_part)
            
            return "\n" + "="*50 + "\n".join(context_parts) + "\n" + "="*50
            
        except Exception as e:
            logger.error(f"Context building failed: {e}")
            return "Error processing document context."
    
    def _create_enhanced_prompt(self, query: str, context: str, index_name: str, answer_style: Optional[str] = None) -> str:
        """Create enhanced prompt for better LLM responses with optional style control."""
        
        style_note = "Narrative paragraph" if (answer_style or "").lower().startswith("narr") else "Concise bullet points (3-6 bullets)"

        prompt = f"""You are an expert document analyst with access to comprehensive legal and corporate documents. 

USER QUERY: {query}

DOCUMENT CONTEXT FROM {index_name.upper()}:
{context}

INSTRUCTIONS:
1. Provide a comprehensive, well-structured answer based ONLY on the document content above
2. Include specific references to pages, sections, and sources where relevant
3. If the query asks for "all information" or "comprehensive details", provide thorough coverage
4. Structure your response with clear headings and bullet points for readability
5. If information is incomplete, clearly state what is available and what might be missing
6. Do not make assumptions beyond what is explicitly stated in the documents
7. Cite specific page numbers and sections for all claims
8. Do NOT include any "Source:" lines, raw URLs, or inline hyperlinks in the answer body. Keep all links exclusively for a separate "Sources" section handled by the application.
9. Do NOT refer to documents by labels like "Document 1", "Document 2", etc. Write naturally and cite information by topic/section rather than numbered document labels.

STYLE:
- {style_note}

RESPONSE FORMAT:
- Start with a brief summary
- Provide detailed information organized by topic
- Include relevant citations and references
- End with any limitations or additional context needed

Please provide your comprehensive response:"""

        return prompt
    
    def _get_llm_response(self, prompt: str, model_name: Optional[str] = None) -> str:
        """Get response from the selected LLM with robust fallbacks."""
        try:
            # Prefer configured model if provided
            if model_name:
                try:
                    from utils.llm_config import get_llm_model_config, validate_llm_setup
                    ok, _ = validate_llm_setup(model_name)
                    if ok:
                        cfg = get_llm_model_config(model_name)
                        provider = (cfg or {}).get("provider", "openai").lower()
                        model_id = (cfg or {}).get("model_id", "gpt-3.5-turbo")
                        temperature = 0.3
                        max_tokens = 900

                        if provider == "openai":
                            # Use direct OpenAI client to avoid LangChain version mismatches
                            try:
                                import os as _os
                                try:
                                    _os.environ.pop("OPENAI_PROJECT", None)
                                except Exception:
                                    pass
                                from openai import OpenAI as _OpenAI
                                api_key = _os.getenv("OPENAI_API_KEY")
                                if not api_key:
                                    raise RuntimeError("OPENAI_API_KEY not set")
                                client = _OpenAI(api_key=api_key)
                                messages = [
                                    {"role": "system", "content": "You are VaultMind Research Assistant. Provide accurate, concise answers. Do not include inline URLs or 'Source' lines."},
                                    {"role": "user", "content": prompt},
                                ]
                                resp = client.chat.completions.create(
                                    model=model_id,
                                    messages=messages,
                                    max_tokens=max_tokens,
                                    temperature=temperature,
                                )
                                text = (resp.choices[0].message.content or "").strip()
                                return text
                            except Exception as _e_openai:
                                # Fall back to LangChain OpenAI if direct client fails for any reason
                                from langchain_openai import ChatOpenAI
                                llm = ChatOpenAI(model=model_id, temperature=temperature, max_tokens=max_tokens, request_timeout=60)
                        elif provider == "anthropic":
                            try:
                                from langchain_anthropic import ChatAnthropic
                                llm = ChatAnthropic(model=model_id, temperature=temperature, max_tokens=max_tokens, request_timeout=60)
                            except Exception:
                                from langchain_openai import ChatOpenAI
                                llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=temperature, max_tokens=max_tokens, request_timeout=60)
                        elif provider == "mistral":
                            try:
                                from langchain_mistralai import ChatMistralAI as ChatMistral
                            except Exception:
                                try:
                                    from langchain_mistralai import ChatMistral
                                except Exception:
                                    ChatMistral = None
                            if ChatMistral:
                                llm = ChatMistral(model=model_id, temperature=temperature, max_tokens=max_tokens)
                            else:
                                from langchain_openai import ChatOpenAI
                                llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=temperature, max_tokens=max_tokens, request_timeout=60)
                        elif provider == "groq":
                            try:
                                from langchain_groq import ChatGroq
                                llm = ChatGroq(model=model_id, temperature=temperature, max_tokens=max_tokens)
                            except Exception:
                                from langchain_openai import ChatOpenAI
                                llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=temperature, max_tokens=max_tokens, request_timeout=60)
                        elif provider == "ollama":
                            try:
                                from langchain_community.chat_models import ChatOllama
                                llm = ChatOllama(model=model_id, temperature=temperature)
                            except Exception:
                                from langchain_openai import ChatOpenAI
                                llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=temperature, max_tokens=max_tokens, request_timeout=60)
                        else:
                            from langchain_openai import ChatOpenAI
                            llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=temperature, max_tokens=max_tokens, request_timeout=60)

                        response = llm.invoke(prompt)
                        return response.content if hasattr(response, "content") else str(response)
                except Exception as cfg_err:
                    logger.warning(f"LLM model config error: {cfg_err}; falling back to OpenAI")

            # Default fallback to OpenAI 3.5
            from langchain_openai import ChatOpenAI
            try:
                os.environ.pop("OPENAI_PROJECT", None)
            except Exception:
                pass
            llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3, max_tokens=900, request_timeout=60)
            response = llm.invoke(prompt)
            return response.content if hasattr(response, "content") else str(response)

        except Exception as e:
            logger.warning(f"LangChain LLM path failed, attempting direct OpenAI compose: {e}")
            # Direct OpenAI fallback (bypass LangChain) using chat.completions
            try:
                import os as _os
                try:
                    _os.environ.pop("OPENAI_PROJECT", None)
                except Exception:
                    pass
                from openai import OpenAI as _OpenAI
                api_key = _os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise RuntimeError("OPENAI_API_KEY not set for direct fallback")
                client = _OpenAI(api_key=api_key)
                model_id = _os.getenv("OPENAI_MODEL") or "gpt-3.5-turbo"
                messages = [
                    {"role": "system", "content": "You are VaultMind Research Assistant. Provide accurate, concise answers based only on the provided prompt. Do not include inline URLs or 'Source' lines."},
                    {"role": "user", "content": prompt},
                ]
                resp = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    max_tokens=800,
                    temperature=0.3,
                )
                return (resp.choices[0].message.content or "").strip()
            except Exception as e2:
                logger.error(f"Direct OpenAI fallback failed: {e2}")
                # Return empty string so upstream caller can apply its own fallback
                return ""
    
    def _fallback_processing(self, query: str, retrieval_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback processing when LLM is not available"""
        try:
            if not retrieval_results:
                response = f"No relevant information found for query: '{query}'"
            else:
                # Create a basic response from retrieval results
                response_parts = [f"Found {len(retrieval_results)} relevant results for: '{query}'\n"]
                
                for i, result in enumerate(retrieval_results[:3], 1):
                    content = result.get('content', 'No content')
                    source = result.get('source', 'Unknown')
                    page = result.get('page', 'N/A')
                    
                    # Truncate content for readability
                    if len(content) > 500:
                        content = content[:450] + "..."
                    
                    response_parts.append(f"\n{i}. Source: {source} (Page: {page})\n{content}")
                
                response = "\n".join(response_parts)
            
            return {
                "result": response,
                "source_documents": retrieval_results,
                "context_used": len(retrieval_results),
                "processing_method": "fallback",
                "query_processed": query
            }
            
        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            return {
                "result": f"Error processing query: {str(e)}",
                "source_documents": [],
                "context_used": 0,
                "processing_method": "error"
            }

def process_query_with_enhanced_llm(query: str, retrieval_results: List[Dict[str, Any]], 
                                  index_name: str) -> Dict[str, Any]:
    """
    Main function to process queries with enhanced LLM integration
    
    Args:
        query: User query
        retrieval_results: Results from vector retrieval system
        index_name: Name of the index
        
    Returns:
        Enhanced response with proper LLM processing
    """
    processor = EnhancedLLMProcessor()
    return processor.process_retrieval_results(query, retrieval_results, index_name)

def validate_retrieval_quality(retrieval_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate the quality of retrieval results before LLM processing
    
    Args:
        retrieval_results: Results from vector retrieval
        
    Returns:
        Quality assessment and recommendations
    """
    try:
        if not retrieval_results:
            return {
                "quality_score": 0.0,
                "issues": ["No results returned"],
                "recommendations": ["Check index availability", "Verify query terms", "Review chunking strategy"]
            }
        
        issues = []
        recommendations = []
        quality_factors = []
        
        # Check content quality
        total_content_length = 0
        empty_content_count = 0
        
        for result in retrieval_results:
            content = result.get('content', '')
            if not content or len(content.strip()) < 50:
                empty_content_count += 1
            else:
                total_content_length += len(content)
        
        # Assess content adequacy
        if empty_content_count > len(retrieval_results) * 0.5:
            issues.append("High proportion of empty or very short content")
            recommendations.append("Review chunking strategy and minimum content thresholds")
            quality_factors.append(0.3)
        else:
            quality_factors.append(0.8)
        
        # Check average content length
        avg_content_length = total_content_length / max(len(retrieval_results) - empty_content_count, 1)
        if avg_content_length < 200:
            issues.append("Content chunks are too small for comprehensive responses")
            recommendations.append("Increase chunk size or improve section detection")
            quality_factors.append(0.4)
        elif avg_content_length > 3000:
            issues.append("Content chunks may be too large")
            recommendations.append("Consider breaking down large sections")
            quality_factors.append(0.6)
        else:
            quality_factors.append(0.9)
        
        # Check metadata completeness
        metadata_complete = 0
        for result in retrieval_results:
            if result.get('source') and result.get('page') and result.get('section'):
                metadata_complete += 1
        
        metadata_ratio = metadata_complete / len(retrieval_results)
        if metadata_ratio < 0.7:
            issues.append("Incomplete metadata in retrieval results")
            recommendations.append("Improve metadata extraction during indexing")
            quality_factors.append(0.5)
        else:
            quality_factors.append(0.9)
        
        # Calculate overall quality score
        quality_score = sum(quality_factors) / len(quality_factors) if quality_factors else 0.0
        
        return {
            "quality_score": quality_score,
            "total_results": len(retrieval_results),
            "avg_content_length": avg_content_length,
            "metadata_completeness": metadata_ratio,
            "issues": issues,
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"Quality validation failed: {e}")
        return {
            "quality_score": 0.0,
            "issues": [f"Validation error: {str(e)}"],
            "recommendations": ["Check retrieval system configuration"]
        }
