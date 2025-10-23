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
from .text_cleaning import clean_document_text, is_noise_text

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
            # If LLM returned empty or too-short content, fall back to structured synthesis
            if not llm_response or len(str(llm_response).strip()) < 50:
                logger.warning("LLM returned empty/too-short response; using fallback_enhanced")
                fb = self._fallback_processing(query, retrieval_results)
                try:
                    # Preserve method label for UI
                    fb["processing_method"] = "fallback_enhanced"
                except Exception:
                    pass
                return fb
            
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
                content = result.get('content', '') or ''
                source = result.get('source', 'Unknown')
                page = result.get('page', None)
                section = result.get('section') or None
                
                # Clean and filter content
                content = clean_document_text(content)
                if not content or is_noise_text(content):
                    continue
                
                # Keep only meaningful complete sentences
                import re as _re
                sentences = [_s.strip() for _s in _re.split(r'(?<=[.!?])\s+', content) if _s.strip() and len(_s.strip()) > 20]
                # Drop noise/continuations; require uppercase start and no colon-intros
                sentences = [
                    _s for _s in sentences
                    if not is_noise_text(_s)
                    and (_s[:1].isupper())
                    and not _re.match(r'^(must|shall|should|may|will|has|have|does|do|is|are|and|or|including|such as|e\.g\.)\b', _s.strip(), _re.IGNORECASE)
                    and not _s.strip().endswith(':')
                ]
                if not sentences:
                    continue
                excerpt = ' '.join(sentences[:3])
                if len(excerpt) > 1800:
                    excerpt = excerpt[:1797] + '...'
                
                page_line = f"Page: {page}\n" if (isinstance(page, int) or (isinstance(page, str) and page.isdigit())) else ""
                section_line = f"Section: {section}\n" if section else ""
                
                context_part = f"""
Document {i}:
Source: {source}
{page_line}{section_line}Content: {excerpt}
"""
                context_parts.append(context_part)
            
            return "\n" + "="*50 + "\n".join(context_parts) + "\n" + "="*50
            
        except Exception as e:
            logger.error(f"Context building failed: {e}")
            return "Error processing document context."
    
    def _create_enhanced_prompt(self, query: str, context: str, index_name: str, answer_style: Optional[str] = None) -> str:
        """
        Create concise, effective prompt for LLM responses
        Optimized for speed and token efficiency while maintaining quality
        """
        
        # Natural prompt - let LLM analyze and respond intelligently
        prompt = f"""You are VaultMind Assistant, an intelligent document analyst. Read the documents carefully and answer the user's question with thorough analysis and proper citations.

DOCUMENTS:
{context}

USER QUESTION: {query}

Instructions:
1. Read and analyze the documents to understand what they say about the question
2. Provide a comprehensive answer using ONLY information from the documents
3. Cite your sources by referencing document numbers (e.g., "Document 1") or page numbers when available
4. Organize your response with clear sections: Executive Summary, Detailed Answer, and Key Points
5. Be thorough - include all relevant details, not just brief summaries
6. Write naturally - don't use placeholder text or templates

Analyze the documents and provide your answer:"""

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
                        max_tokens = 2000  # Increased for detailed responses

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
            llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3, max_tokens=2000, request_timeout=60)
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
                    max_tokens=2000,
                    temperature=0.3,
                )
                return (resp.choices[0].message.content or "").strip()
            except Exception as e2:
                logger.error(f"Direct OpenAI fallback failed: {e2}")
                # Return empty string so upstream caller can apply its own fallback
                return ""
    
    def _fallback_processing(self, query: str, retrieval_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback processing when LLM is not available - provides structured enterprise response"""
        try:
            # Import QueryResultFormatter for proper sentence extraction
            try:
                from utils.query_result_formatter import QueryResultFormatter
                formatter_available = True
            except ImportError:
                formatter_available = False
                logger.warning("QueryResultFormatter not available, using basic extraction")
            
            if not retrieval_results:
                response = f"""### Executive Summary
No relevant information found in the knowledge base for the query: "{query}"

### Detailed Answer
The search returned no results. This could mean:
- The query terms are too specific
- The requested information is not in the indexed documents
- There may be an issue with the search index

### Key Points
- No matching documents found
- Consider rephrasing the query or checking document availability

### Information Gaps
All requested information needs to be sourced from alternative documents or databases."""
            else:
                # Create enterprise-structured response from retrieval results
                response_parts = []

                # Executive Summary - Use QueryResultFormatter for complete sentences
                response_parts.append("### Executive Summary")
                top_content_raw = retrieval_results[0].get('content', '') or ''
                top_content = clean_document_text(top_content_raw)
                
                if formatter_available:
                    # Use QueryResultFormatter to extract complete sentences (no truncation)
                    summary_text = QueryResultFormatter.extract_complete_sentences(top_content, max_length=300)
                else:
                    # Fallback to basic extraction
                    import re
                    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', top_content) if s.strip() and len(s.strip()) > 20]
                    sentences = [s for s in sentences if not is_noise_text(s)]
                    summary_text = ' '.join(sentences[:2])
                    if summary_text and not summary_text.endswith(('.', '!', '?')):
                        summary_text += '.'
                
                if not summary_text or len(summary_text.strip()) < 20:
                    summary_text = "Information found in documents."
                response_parts.append(summary_text)
                response_parts.append("")

                # Detailed Answer - synthesize from top results with complete sentences
                response_parts.append("### Detailed Answer")
                combined_content = []
                for i, result in enumerate(retrieval_results[:3], 1):
                    content = clean_document_text(result.get('content', '') or '')
                    if not content or is_noise_text(content):
                        continue
                    source = result.get('source', 'Unknown')
                    page = result.get('page', None)
                    section = result.get('section')
                    
                    # Build citation
                    page_seg = f", Page {page}" if (isinstance(page, int) or (isinstance(page, str) and page.isdigit())) else ""
                    section_seg = f", Section: {section}" if section else ""
                    
                    # Extract complete sentences using QueryResultFormatter
                    if formatter_available:
                        excerpt = QueryResultFormatter.extract_complete_sentences(content, max_length=400)
                    else:
                        import re
                        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', content) if s.strip() and len(s.strip()) > 20]
                        sentences = [s for s in sentences if not is_noise_text(s)]
                        excerpt = ' '.join(sentences[:3])
                        if excerpt and not excerpt.endswith(('.', '!', '?')):
                            excerpt += '.'
                    
                    if excerpt:
                        combined_content.append(f"**From {source}{page_seg}{section_seg}:** {excerpt}")
                
                response_parts.extend(combined_content)
                response_parts.append("")

                # Key Points with citations - Use QueryResultFormatter
                response_parts.append("### Key Points")
                
                for i, result in enumerate(retrieval_results[:5], 1):
                    content = result.get('content', '')
                    source = result.get('source', 'Unknown')
                    page = result.get('page')
                    section = result.get('section')
                    
                    if formatter_available:
                        # Use QueryResultFormatter.format_key_point for professional formatting
                        formatted_point = QueryResultFormatter.format_key_point(
                            content=content,
                            source=source,
                            page=page,
                            section=section,
                            index=i
                        )
                        if formatted_point:
                            response_parts.append(formatted_point)
                    else:
                        # Fallback formatting
                        content_clean = clean_document_text(content)
                        if not content_clean or is_noise_text(content_clean):
                            continue
                        
                        import re
                        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', content_clean) if s.strip() and len(s.strip()) > 30]
                        sentences = [s for s in sentences if not is_noise_text(s)]
                        
                        if sentences:
                            key_point = sentences[0]
                            if not key_point.endswith(('.', '!', '?')):
                                key_point += '.'
                            
                            page_seg = f", Page {page}" if (isinstance(page, int) or (isinstance(page, str) and page.isdigit())) else ""
                            section_seg = f", Section: {section}" if section else ""
                            response_parts.append(f"{i}. **{key_point}** _(Source: {source}{page_seg}{section_seg})_")
                
                # Information Gaps
                response_parts.append("")
                response_parts.append("### Information Gaps")
                if len(retrieval_results) < 3:
                    response_parts.append("⚠️ Limited document coverage - only " + str(len(retrieval_results)) + " relevant section(s) found. Additional sources may provide more comprehensive information.")
                elif len(retrieval_results) >= 5:
                    response_parts.append("✅ Comprehensive information available across multiple document sections.")
                else:
                    response_parts.append("ℹ️ Moderate coverage - " + str(len(retrieval_results)) + " relevant sections found.")

                response = "\n".join(response_parts)

            return {
                "result": response,
                "source_documents": retrieval_results,
                "sources": [{"source": r.get('source', 'Unknown'), "page": r.get('page')} for r in retrieval_results[:5]],
                "context_used": len(retrieval_results),
                "processing_method": "fallback_enhanced",
                "query_processed": query
            }

        except Exception as e:
            logger.error(f"Fallback processing failed: {e}", exc_info=True)
            return {
                "result": f"""### Executive Summary
Query processing encountered an error.

### Detailed Answer
Unable to process query due to system error: {str(e)[:100]}

### Key Points
- System error occurred during processing
- Please try again or contact support

### Information Gaps
Unable to determine information gaps due to processing error""",
                "source_documents": retrieval_results or [],
                "context_used": len(retrieval_results) if retrieval_results else 0,
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
