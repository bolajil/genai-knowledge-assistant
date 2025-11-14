"""
Image LLM Query System - Multi-Modal AI for Image Understanding
================================================================
Supports three modes:
1. RAG (Retrieval-Augmented Generation) - OCR + Vector Search + LLM
2. Vision LLM - Direct image understanding with GPT-4V/Claude
3. Hybrid - Combines both approaches for best results
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import base64
import io

logger = logging.getLogger(__name__)

# Try to import LLM providers
try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available")

try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic not available")

try:
    from utils.llm_config import get_llm
    LLM_CONFIG_AVAILABLE = True
except ImportError:
    LLM_CONFIG_AVAILABLE = False
    logger.warning("LLM config not available")


class ImageLLMQuery:
    """Multi-modal LLM query system for images"""
    
    def __init__(self, mode: str = "rag", llm_provider: str = "openai", model_name: Optional[str] = None):
        """
        Initialize Image LLM Query system
        
        Args:
            mode: 'rag', 'vision', or 'hybrid'
            llm_provider: 'openai', 'anthropic', etc.
            model_name: Specific model (e.g., 'gpt-4o', 'claude-3-opus')
        """
        self.mode = mode
        self.llm_provider = llm_provider
        self.model_name = model_name
        
        # Initialize LLM
        self.llm = self._init_llm()
        self.vision_llm = self._init_vision_llm() if mode in ['vision', 'hybrid'] else None
    
    def _init_llm(self):
        """Initialize text LLM for RAG"""
        try:
            if LLM_CONFIG_AVAILABLE:
                # Use existing LLM config
                return get_llm(provider=self.llm_provider, model=self.model_name)
            elif OPENAI_AVAILABLE and self.llm_provider == "openai":
                model = self.model_name or "gpt-4o-mini"
                return ChatOpenAI(model=model, temperature=0)
            elif ANTHROPIC_AVAILABLE and self.llm_provider == "anthropic":
                model = self.model_name or "claude-3-5-sonnet-20241022"
                return ChatAnthropic(model=model, temperature=0)
            else:
                logger.error("No LLM provider available")
                return None
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            return None
    
    def _init_vision_llm(self):
        """Initialize vision LLM for direct image understanding"""
        try:
            if self.llm_provider == "openai" and OPENAI_AVAILABLE:
                # GPT-4V models
                model = self.model_name or "gpt-4o"
                return ChatOpenAI(model=model, temperature=0)
            elif self.llm_provider == "anthropic" and ANTHROPIC_AVAILABLE:
                # Claude 3 models with vision
                model = self.model_name or "claude-3-5-sonnet-20241022"
                return ChatAnthropic(model=model, temperature=0)
            else:
                logger.warning("Vision LLM not available for this provider")
                return None
        except Exception as e:
            logger.error(f"Error initializing vision LLM: {e}")
            return None
    
    def _encode_image(self, image_bytes: bytes) -> str:
        """Encode image to base64 for vision LLM"""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def query_rag(self, 
                  query: str, 
                  retrieved_chunks: List[str], 
                  metadata: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        RAG Mode: Use OCR text + vector search + LLM
        
        Args:
            query: User's question
            retrieved_chunks: Text chunks from vector search
            metadata: Optional metadata about chunks
        
        Returns:
            Dict with answer, sources, confidence
        """
        if not self.llm:
            return {
                'answer': "LLM not available",
                'mode': 'rag',
                'success': False,
                'error': 'LLM not initialized'
            }
        
        try:
            # Build context from retrieved chunks
            context = "\n\n".join([
                f"Source {i+1}:\n{chunk}" 
                for i, chunk in enumerate(retrieved_chunks)
            ])
            
            # Create prompt
            prompt = f"""You are an AI assistant analyzing text extracted from images using OCR.
Based on the following extracted text, answer the user's question accurately and concisely.

Extracted Text from Images:
{context}

User Question: {query}

Instructions:
1. Provide a clear, direct answer based on the extracted text
2. If the answer is not in the text, say so
3. Cite which source(s) you used
4. Be concise but complete

Answer:"""
            
            # Get LLM response
            response = self.llm.invoke(prompt)
            
            # Extract answer
            answer = response.content if hasattr(response, 'content') else str(response)
            
            return {
                'answer': answer,
                'mode': 'rag',
                'success': True,
                'sources': retrieved_chunks,
                'metadata': metadata,
                'prompt_tokens': getattr(response, 'usage', {}).get('prompt_tokens', 0) if hasattr(response, 'usage') else 0,
                'completion_tokens': getattr(response, 'usage', {}).get('completion_tokens', 0) if hasattr(response, 'usage') else 0
            }
        
        except Exception as e:
            logger.error(f"RAG query error: {e}")
            return {
                'answer': f"Error: {str(e)}",
                'mode': 'rag',
                'success': False,
                'error': str(e)
            }
    
    def query_vision(self, 
                     query: str, 
                     image_bytes: bytes,
                     image_filename: str = "image") -> Dict[str, Any]:
        """
        Vision Mode: Direct image understanding with vision LLM
        
        Args:
            query: User's question
            image_bytes: Raw image bytes
            image_filename: Image filename for reference
        
        Returns:
            Dict with answer, confidence, metadata
        """
        if not self.vision_llm:
            return {
                'answer': "Vision LLM not available",
                'mode': 'vision',
                'success': False,
                'error': 'Vision LLM not initialized'
            }
        
        try:
            # Encode image
            image_base64 = self._encode_image(image_bytes)
            
            # Create vision prompt
            if self.llm_provider == "openai":
                # OpenAI format
                from langchain_core.messages import HumanMessage
                
                message = HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": f"""Analyze this image and answer the following question:

Question: {query}

Provide a clear, accurate answer based on what you see in the image."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                )
                
                response = self.vision_llm.invoke([message])
            
            elif self.llm_provider == "anthropic":
                # Anthropic format
                from langchain_core.messages import HumanMessage
                
                message = HumanMessage(
                    content=[
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": f"""Analyze this image and answer the following question:

Question: {query}

Provide a clear, accurate answer based on what you see in the image."""
                        }
                    ]
                )
                
                response = self.vision_llm.invoke([message])
            
            else:
                return {
                    'answer': "Unsupported vision provider",
                    'mode': 'vision',
                    'success': False,
                    'error': f'Provider {self.llm_provider} not supported for vision'
                }
            
            # Extract answer
            answer = response.content if hasattr(response, 'content') else str(response)
            
            return {
                'answer': answer,
                'mode': 'vision',
                'success': True,
                'image_filename': image_filename,
                'provider': self.llm_provider,
                'model': self.model_name or 'default',
                'prompt_tokens': getattr(response, 'usage', {}).get('prompt_tokens', 0) if hasattr(response, 'usage') else 0,
                'completion_tokens': getattr(response, 'usage', {}).get('completion_tokens', 0) if hasattr(response, 'usage') else 0
            }
        
        except Exception as e:
            logger.error(f"Vision query error: {e}")
            return {
                'answer': f"Error: {str(e)}",
                'mode': 'vision',
                'success': False,
                'error': str(e)
            }
    
    def query_hybrid(self,
                     query: str,
                     image_bytes: bytes,
                     retrieved_chunks: List[str],
                     metadata: Optional[List[Dict]] = None,
                     image_filename: str = "image") -> Dict[str, Any]:
        """
        Hybrid Mode: Combines RAG and Vision for best results
        
        Args:
            query: User's question
            image_bytes: Raw image bytes
            retrieved_chunks: Text chunks from OCR + vector search
            metadata: Optional metadata
            image_filename: Image filename
        
        Returns:
            Dict with combined answer, sources, confidence
        """
        if not self.llm or not self.vision_llm:
            return {
                'answer': "Hybrid mode requires both text and vision LLM",
                'mode': 'hybrid',
                'success': False,
                'error': 'LLMs not fully initialized'
            }
        
        try:
            # Get both RAG and Vision responses
            rag_result = self.query_rag(query, retrieved_chunks, metadata)
            vision_result = self.query_vision(query, image_bytes, image_filename)
            
            # Combine results with meta-LLM
            synthesis_prompt = f"""You are synthesizing information from two sources to answer a question about an image:

1. OCR-extracted text analysis: {rag_result.get('answer', 'N/A')}
2. Direct visual analysis: {vision_result.get('answer', 'N/A')}

User Question: {query}

Instructions:
1. Combine insights from both sources
2. Resolve any conflicts by favoring the more reliable source
3. Provide a comprehensive, accurate answer
4. Mention if the sources agree or disagree

Synthesized Answer:"""
            
            synthesis_response = self.llm.invoke(synthesis_prompt)
            final_answer = synthesis_response.content if hasattr(synthesis_response, 'content') else str(synthesis_response)
            
            return {
                'answer': final_answer,
                'mode': 'hybrid',
                'success': True,
                'rag_answer': rag_result.get('answer'),
                'vision_answer': vision_result.get('answer'),
                'sources': retrieved_chunks,
                'metadata': metadata,
                'image_filename': image_filename,
                'total_tokens': (
                    rag_result.get('prompt_tokens', 0) + 
                    rag_result.get('completion_tokens', 0) +
                    vision_result.get('prompt_tokens', 0) +
                    vision_result.get('completion_tokens', 0)
                )
            }
        
        except Exception as e:
            logger.error(f"Hybrid query error: {e}")
            return {
                'answer': f"Error: {str(e)}",
                'mode': 'hybrid',
                'success': False,
                'error': str(e)
            }
    
    def query(self,
              query: str,
              image_bytes: Optional[bytes] = None,
              retrieved_chunks: Optional[List[str]] = None,
              metadata: Optional[List[Dict]] = None,
              image_filename: str = "image") -> Dict[str, Any]:
        """
        Main query method - routes to appropriate mode
        
        Args:
            query: User's question
            image_bytes: Raw image bytes (required for vision/hybrid)
            retrieved_chunks: Text chunks (required for rag/hybrid)
            metadata: Optional metadata
            image_filename: Image filename
        
        Returns:
            Dict with answer and metadata
        """
        if self.mode == "rag":
            if not retrieved_chunks:
                return {
                    'answer': "RAG mode requires retrieved chunks",
                    'mode': 'rag',
                    'success': False,
                    'error': 'No chunks provided'
                }
            return self.query_rag(query, retrieved_chunks, metadata)
        
        elif self.mode == "vision":
            if not image_bytes:
                return {
                    'answer': "Vision mode requires image bytes",
                    'mode': 'vision',
                    'success': False,
                    'error': 'No image provided'
                }
            return self.query_vision(query, image_bytes, image_filename)
        
        elif self.mode == "hybrid":
            if not image_bytes or not retrieved_chunks:
                return {
                    'answer': "Hybrid mode requires both image and chunks",
                    'mode': 'hybrid',
                    'success': False,
                    'error': 'Missing image or chunks'
                }
            return self.query_hybrid(query, image_bytes, retrieved_chunks, metadata, image_filename)
        
        else:
            return {
                'answer': f"Unknown mode: {self.mode}",
                'mode': self.mode,
                'success': False,
                'error': 'Invalid mode'
            }


def create_image_query_system(mode: str = "rag", 
                              provider: str = "openai",
                              model: Optional[str] = None) -> ImageLLMQuery:
    """
    Factory function to create Image LLM Query system
    
    Args:
        mode: 'rag', 'vision', or 'hybrid'
        provider: 'openai' or 'anthropic'
        model: Specific model name
    
    Returns:
        ImageLLMQuery instance
    """
    return ImageLLMQuery(mode=mode, llm_provider=provider, model_name=model)
