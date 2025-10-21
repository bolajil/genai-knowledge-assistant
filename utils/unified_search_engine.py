"""
Unified Search Engine for VaultMind
Provides consistent document retrieval and LLM integration across all tabs
"""
import os
import logging
import pickle
import faiss
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
<<<<<<< HEAD
# Optional OpenAI SDK import (do not fail if missing)
try:
    from openai import OpenAI as _OpenAIClient  # new SDK client
    _OPENAI_SDK_AVAILABLE = True
except Exception:
    _OpenAIClient = None
    _OPENAI_SDK_AVAILABLE = False
from pathlib import Path

# Import text cleaning utility
from .text_cleaning import clean_document_text, is_noise_text
=======
import openai
from pathlib import Path

# Import text cleaning utility
from .text_cleaning import clean_document_text
>>>>>>> clean-master

logger = logging.getLogger(__name__)

class UnifiedSearchEngine:
    """
    Centralized search engine that connects indexes to actual document content
    and integrates with LLMs for intelligent responses
    """
    
    def __init__(self):
        self.model = None
        self.openai_client = None
        self.index_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize embedding model and OpenAI client"""
        try:
            # Initialize sentence transformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence transformer model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer: {str(e)}")
        
        try:
<<<<<<< HEAD
            # Initialize OpenAI client lazily and only if SDK is available
            self.openai_client = self._create_openai_client()
            if self.openai_client:
=======
            # Initialize OpenAI client
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                openai.api_key = openai_key
                self.openai_client = openai
>>>>>>> clean-master
                logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    
    def _create_openai_client(self):
        """Create an OpenAI client robustly, avoiding all unsupported parameters."""
        # Remove ALL problematic environment variables that might cause issues
        for key in ['OPENAI_PROJECT', 'OPENAI_PROXIES', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
            try:
                os.environ.pop(key, None)
            except:
                pass
        
        try:
            from openai import OpenAI
        except ImportError as e:
<<<<<<< HEAD
            logger.info(f"OpenAI library not installed; skipping client init: {e}")
=======
            logger.error(f"OpenAI library not installed: {e}")
>>>>>>> clean-master
            return None
        
        api_key = os.getenv("OPENAI_API_KEY")
        
        # Create client with ONLY api_key to avoid any parameter issues
        try:
            if api_key:
                return OpenAI(api_key=api_key)
            else:
<<<<<<< HEAD
                # Allow default env-driven init if supported
=======
>>>>>>> clean-master
                return OpenAI()
        except Exception as e:
            logger.error(f"Failed to create OpenAI client: {e}")
            return None
    
    def search_index(self, query: str, index_name: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search a specific index for documents matching the query
        """
        logger.info(f"Searching index '{index_name}' for query: {query}")
        
        # Try different index path patterns for both FAISS and directory indexes
        possible_paths = [
            # Directory-based indexes (like August_security)
            os.path.join(self.index_root, "indexes", f"{index_name}_index"),
            os.path.join(self.index_root, "indexes", index_name),
            # FAISS indexes
            os.path.join(self.index_root, "faiss_index", f"{index_name}_index"),
            os.path.join(self.index_root, "faiss_index", index_name),
            # Root level
            os.path.join(self.index_root, f"{index_name}_index"),
            os.path.join(self.index_root, index_name)
        ]
        
        for index_path in possible_paths:
            if os.path.exists(index_path):
                logger.info(f"Found index at: {index_path}")
                # Check if it's a directory-based index (has extracted_text.txt)
                if os.path.isdir(index_path):
                    text_file = os.path.join(index_path, "extracted_text.txt")
                    if os.path.exists(text_file):
                        return self._search_directory_index(query, index_path, top_k)
                    else:
                        # It's a FAISS directory
                        return self._search_faiss_index(query, index_path, top_k)
                else:
                    return self._search_faiss_index(query, index_path, top_k)
        
        logger.warning(f"Index '{index_name}' not found in any expected location")
        return self._fallback_search(query, index_name)
    
    def _search_faiss_index(self, query: str, index_path: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search a FAISS-based index
        """
        try:
            # Check if it's a directory with FAISS files inside
            if os.path.isdir(index_path):
                # Look for FAISS files inside the directory
                faiss_file = None
                for file in os.listdir(index_path):
                    if file.endswith('.faiss') or file.endswith('.index'):
                        faiss_file = os.path.join(index_path, file)
                        break
                
                if not faiss_file:
                    logger.error(f"No FAISS index file found in directory {index_path}")
                    return self._fallback_search(query, os.path.basename(index_path))
            else:
                # Look for FAISS index file with extensions
                faiss_file = None
                for ext in ['.faiss', '.index']:
                    potential_file = f"{index_path}{ext}"
                    if os.path.exists(potential_file):
                        faiss_file = potential_file
                        break
                
                if not faiss_file:
                    logger.error(f"No FAISS index file found for {index_path}")
                    return self._fallback_search(query, os.path.basename(index_path))
            
            import faiss
            faiss_index = faiss.read_index(str(faiss_file))
            
            # Load metadata from the same directory as FAISS file
            metadata_dir = os.path.dirname(faiss_file) if os.path.isfile(faiss_file) else index_path
            metadata = self._load_metadata(metadata_dir)
            if not metadata:
                logger.warning(f"No metadata found for {metadata_dir}")
                return self._fallback_search(query, os.path.basename(index_path))
            
            # Generate query embedding
            if not self.model:
                logger.error("Sentence transformer model not available")
                return self._fallback_search(query, os.path.basename(index_path))
            
            query_embedding = self.model.encode([query])
            
            # Search FAISS index
            scores, indices = faiss_index.search(query_embedding, top_k)
            
            # Format results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(metadata) and idx >= 0:
                    doc_metadata = metadata[idx]
                    # Convert FAISS distance to similarity score
                    similarity_score = 1.0 / (1.0 + float(score))
                    
                    result = {
                        'content': clean_document_text(doc_metadata.get('content', 'No content available')),
                        'score': similarity_score,
                        'source': doc_metadata.get('source', f'{os.path.basename(index_path)}.pdf'),
                        'page': doc_metadata.get('page', i + 1),
                        'index_name': os.path.basename(index_path),
                        'metadata': doc_metadata
                    }
                    results.append(result)
            
            logger.info(f"Found {len(results)} results for query '{query}' in index '{index_path}'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching FAISS index {index_path}: {str(e)}")
            return self._fallback_search(query, os.path.basename(index_path))
    
    def _load_metadata(self, index_path) -> Optional[List[Dict[str, Any]]]:
        """Load metadata from various possible files"""
        # Convert to Path object if it's a string
        if isinstance(index_path, str):
            index_path = Path(index_path)
            
        metadata_files = ['metadata.pkl', 'index.pkl']
        
        for meta_file in metadata_files:
            meta_path = index_path / meta_file
            if meta_path.exists():
                try:
                    with open(meta_path, 'rb') as f:
                        metadata = pickle.load(f)
                    logger.info(f"Loaded metadata from {meta_path}")
                    return metadata
                except Exception as e:
                    logger.error(f"Error loading metadata from {meta_path}: {str(e)}")
        
<<<<<<< HEAD
        # Compatibility: support documents.pkl produced by local FAISS ingestion
        docs_pkl = index_path / 'documents.pkl'
        if docs_pkl.exists():
            try:
                with open(docs_pkl, 'rb') as f:
                    payload = pickle.load(f)
                # Expected structure: {'documents': [text,...], 'metadatas': [{'source': ...}, ...]}
                docs_list = []
                documents = payload.get('documents') if isinstance(payload, dict) else None
                metadatas = payload.get('metadatas') if isinstance(payload, dict) else None
                if isinstance(documents, list):
                    for i, text in enumerate(documents):
                        md = {}
                        if isinstance(metadatas, list) and i < len(metadatas) and isinstance(metadatas[i], dict):
                            md = metadatas[i]
                        docs_list.append({
                            'content': text,
                            'source': md.get('source', f'{index_path.name}.pdf'),
                            'page': md.get('page') if isinstance(md.get('page'), (int, str)) else None,
                        })
                if docs_list:
                    logger.info(f"Constructed metadata from {docs_pkl} with {len(docs_list)} entries")
                    return docs_list
            except Exception as e:
                logger.error(f"Error adapting documents.pkl at {docs_pkl}: {str(e)}")
        
=======
>>>>>>> clean-master
        # Try to create metadata from text files
        text_file = index_path / "extracted_text.txt"
        if text_file.exists():
            try:
                with open(text_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Split into chunks
                chunk_size = 1000
                chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
                
                metadata = []
                for i, chunk in enumerate(chunks):
                    metadata.append({
                        'content': clean_document_text(chunk),
                        'source': f'{index_path.name}.pdf',
                        'page': i // 10 + 1,
                        'chunk_id': i
                    })
                
                logger.info(f"Created metadata from text file: {len(metadata)} chunks")
                return metadata
                
            except Exception as e:
                logger.error(f"Error creating metadata from text file: {str(e)}")
        
        return None
    
    def _search_directory_index(self, query: str, index_path: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search a directory-based index (like August_security)
        """
        logger.info(f"Searching directory index at: {index_path}")
        
        text_file = os.path.join(index_path, "extracted_text.txt")
        if not os.path.exists(text_file):
            logger.warning(f"No extracted_text.txt found in {index_path}")
            return []
        
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Clean the content immediately after reading
            content = clean_document_text(content)
            
            if not content.strip():
                logger.warning(f"Empty content in {text_file}")
                return [{
                    'content': f"Document found but appears to be empty. File: {text_file}",
                    'score': 0.1,
                    'metadata': {'source': 'directory_index', 'status': 'empty'}
                }]
            
            # Split content by pages
            pages = content.split("--- Page ")
            results = []
            
            # If no specific query terms, return general content from first few pages
            if not query.strip() or query.lower() in ['describe this document', 'what is this', 'summary', 'discribe this document']:
                logger.info(f"General query detected, returning document overview")
                
                # Get document overview from first few pages
                document_info = []
                for i, page in enumerate(pages[1:4]):  # First 3 pages
                    if page.strip():
                        # Clean up page content
                        page_lines = [line.strip() for line in page.split('\n') if line.strip()]
                        if page_lines:
                            # Take meaningful content, skip page numbers
                            meaningful_content = []
                            for line in page_lines:
                                if len(line) > 10 and not line.isdigit():
                                    meaningful_content.append(line)
                            
                            if meaningful_content:
                                page_summary = ' '.join(meaningful_content[:3])[:400]
                                document_info.append(f"Page {i+1}: {page_summary}")
                
                if document_info:
                    full_summary = '\n\n'.join(document_info)
                    results.append({
                        'content': f"Document Summary:\n\n{full_summary}",
                        'score': 1.0,
                        'metadata': {'source': 'directory_index', 'type': 'summary', 'pages': len(pages)-1}
                    })
                else:
                    # Fallback to raw content
                    raw_content = content[:500].replace('\n\n', ' ').strip()
                    results.append({
                        'content': f"Document content: {raw_content}",
                        'score': 0.8,
                        'metadata': {'source': 'directory_index', 'type': 'raw_content'}
                    })
            else:
                # Search for query terms in pages
                query_lower = query.lower()
                for i, page in enumerate(pages[1:]):
                    if query_lower in page.lower():
                        # Calculate relevance score based on query frequency
                        score = min(page.lower().count(query_lower) / max(len(page), 1) * 100, 1.0)
                        
                        # Extract relevant snippet
                        page_lines = page.split('\n')
                        relevant_lines = [line for line in page_lines if query_lower in line.lower()]
                        
                        if relevant_lines:
                            snippet = ' '.join(relevant_lines[:3])[:400]
                        else:
                            snippet = page[:400]
                        
                        results.append({
                            'content': f"Page {i+1}: {snippet}",
                            'score': score,
                            'metadata': {'page': i+1, 'source': 'directory_index'}
                        })
            
            if not results:
                results.append({
                    'content': f"Document found with {len(pages)-1} pages. Content: {content[:300]}...",
                    'score': 0.5,
                    'metadata': {'source': 'directory_index', 'pages': len(pages)-1}
                })
            
            # Sort by score and return top results
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error reading directory index {index_path}: {str(e)}")
            return [{
                'content': f"Error accessing document: {str(e)}",
                'score': 0.1,
                'metadata': {'source': 'directory_index', 'error': True}
            }]
    
    def _fallback_search(self, query: str, index_name: str) -> List[Dict[str, Any]]:
        """Fallback search when index is not accessible"""
        return [{
            'content': f"Index '{index_name}' is not accessible. Please check if documents have been properly ingested.",
            'score': 0.0,
            'source': 'System',
            'page': 0,
            'index_name': index_name,
            'metadata': {'error': True}
        }]
    
<<<<<<< HEAD
    def _generate_fallback_response(self, query: str, search_results: List[Dict[str, Any]]) -> str:
        """Generate fallback response when LLM is not available"""
        if not search_results:
            return f"No relevant documents found for query: '{query}'"
        
        # Clean and keep non-noise results
        kept: List[Dict[str, Any]] = []
        for r in search_results:
            cleaned = clean_document_text(r.get('content', '') or '')
            if not cleaned or is_noise_text(cleaned):
                continue
            kept.append({
                'content': cleaned,
                'source': r.get('source', 'Unknown'),
                'score': r.get('score', 0.0),
                'page': r.get('page', None),
            })
        if not kept:
            return f"Found {len(search_results)} result(s), but no clean content suitable for display. Please refine your query."
        
        parts: List[str] = [f"Found {len(kept)} relevant document(s) for your query: '{query}'", ""]
        for i, r in enumerate(kept, 1):
            page = r.get('page')
            page_seg = f" (Page {page})" if (isinstance(page, int) or (isinstance(page, str) and page.isdigit())) else ""
            snippet = r['content'][:500] + ('' if len(r['content']) <= 500 else '...')
            parts.append(f"**Result {i}** (Relevance: {r['score']:.2f}):")
            parts.append(f"Source: {r['source']}{page_seg}")
            parts.append(f"Content: {snippet}")
            parts.append("---")
        return "\n".join(parts)

=======
>>>>>>> clean-master
    def query_with_llm(self, query: str, index_name: str, model_name: str = None, top_k: int = 3) -> Dict[str, Any]:
        """
        Query index and generate LLM response based on retrieved content
        """
        # Get default model if none specified
        if model_name is None:
            try:
                from utils.llm_config import get_default_llm_model
                model_name = get_default_llm_model()
            except ImportError:
                model_name = "gpt-3.5-turbo"  # Fallback
        
        # First search for relevant documents
        search_results = self.search_index(query, index_name, top_k)
        
        if not search_results:
            return {
                'search_results': [],
                'llm_response': f"No relevant documents found in index '{index_name}' for query: {query}",
                'model_used': model_name,
                'query': query,
                'index_name': index_name
            }
        
<<<<<<< HEAD
        # Prepare a cleaner context from search results
        context_parts = []
        for result in search_results[:max(3, top_k)]:  # keep top few
            raw = result.get('content', '') or ''
            cleaned = clean_document_text(raw)
            if not cleaned or is_noise_text(cleaned):
                continue
            source = result.get('source', 'Unknown')
            score = result.get('score', 0.0)
            page = result.get('page', None)
            page_seg = f" (Page {page})" if (isinstance(page, int) or (isinstance(page, str) and page.isdigit())) else ""
            context_parts.append(f"Source: {source}{page_seg} (Relevance: {score:.3f})\n{cleaned}")
        
        context = "\n\n---\n\n".join(context_parts) if context_parts else ""
=======
        # Prepare context from search results
        context_parts = []
        for result in search_results:
            content = result.get('content', '')  # Get full content without truncation
            source = result.get('source', 'Unknown')
            score = result.get('score', 0.0)
            context_parts.append(f"Source: {source} (Relevance: {score:.3f})\n{content}")
        
        context = "\n\n---\n\n".join(context_parts)
>>>>>>> clean-master
        
        # Generate LLM response using unified config
        try:
            from utils.llm_config import get_llm_model_config
            model_config = get_llm_model_config(model_name)
            
            if not model_config:
                raise Exception(f"Model configuration not found for {model_name}")
            
            provider = model_config.get('provider', 'openai')
            model_id = model_config.get('model_id', model_name)
            
            if provider == 'openai':
                client = self._create_openai_client()
                
                messages = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based on provided document context. Use the context to provide accurate, detailed answers. If the context doesn't contain enough information to answer the question, say so clearly."
                    },
                    {
                        "role": "user",
                        "content": f"Context from documents:\n{context}\n\nQuestion: {query}\n\nPlease provide a comprehensive answer based on the context above."
                    }
                ]
                
                response = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                
                llm_response = response.choices[0].message.content
            
            elif provider == 'anthropic':
                import anthropic
                client = anthropic.Anthropic()
                
                response = client.messages.create(
                    model=model_id,
                    max_tokens=1000,
                    messages=[
                        {
                            "role": "user",
                            "content": f"Context from documents:\n{context}\n\nQuestion: {query}\n\nPlease provide a comprehensive answer based on the context above."
                        }
                    ]
                )
                
                llm_response = response.content[0].text
            
            elif provider == 'mistral':
                from mistralai.client import MistralClient
                from mistralai.models.chat_completion import ChatMessage
                
                client = MistralClient(api_key=os.getenv("MISTRAL_API_KEY"))
                
                messages = [
                    ChatMessage(role="user", content=f"Context from documents:\n{context}\n\nQuestion: {query}\n\nPlease provide a comprehensive answer based on the context above.")
                ]
                
                response = client.chat(
                    model=model_id,
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                
                llm_response = response.choices[0].message.content
            
            elif provider == 'ollama':
                import requests
                
                ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                
                payload = {
                    "model": model_id,
                    "prompt": f"Context from documents:\n{context}\n\nQuestion: {query}\n\nPlease provide a comprehensive answer based on the context above.",
                    "stream": False
                }
                
                response = requests.post(f"{ollama_url}/api/generate", json=payload)
                
                if response.status_code == 200:
                    llm_response = response.json().get("response", "No response from Ollama")
                else:
                    raise Exception(f"Ollama request failed: {response.status_code}")
            
            elif provider == 'deepseek':
                from openai import OpenAI
                # Prevent older SDKs from receiving unsupported 'project' kwarg via env
                try:
                    os.environ.pop("OPENAI_PROJECT", None)
                except Exception:
                    pass
                client = OpenAI(
                    api_key=os.getenv("DEEPSEEK_API_KEY"),
                    base_url="https://api.deepseek.com"
                )
                
                messages = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based on provided document context."
                    },
                    {
                        "role": "user",
                        "content": f"Context from documents:\n{context}\n\nQuestion: {query}\n\nPlease provide a comprehensive answer based on the context above."
                    }
                ]
                
                response = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                
                llm_response = response.choices[0].message.content
            
            elif provider == 'groq':
                from groq import Groq
                
                client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                
                messages = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based on provided document context."
                    },
                    {
                        "role": "user",
                        "content": f"Context from documents:\n{context}\n\nQuestion: {query}\n\nPlease provide a comprehensive answer based on the context above."
                    }
                ]
                
                response = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                
                llm_response = response.choices[0].message.content
            
            else:
                # Fallback for unsupported providers
                llm_response = f"Provider '{provider}' not yet supported. Here are the relevant document excerpts:\n\n{context[:2000]}"
            
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            llm_response = f"Error generating LLM response: {str(e)}. Here are the relevant document excerpts:\n\n{context[:2000]}"
        
        return {
            'search_results': search_results,
            'llm_response': llm_response,
            'model_used': model_name,
            'query': query,
            'index_name': index_name
        }
    
    def generate_llm_response(self, query: str, search_results: List[Dict[str, Any]], model_name: str = "gpt-3.5-turbo") -> str:
        """
        Generate LLM response based on search results
        
        Args:
            query: Original user query
            search_results: Results from document search
            model_name: LLM model to use
<<<<<<< HEAD
=======
            
>>>>>>> clean-master
        Returns:
            Generated response string
        """
        try:
            if not self.openai_client or not search_results:
                return self._generate_fallback_response(query, search_results)
<<<<<<< HEAD

            # Prepare context from search results
            context_parts = []
            for i, result in enumerate(search_results[:3]):  # Use top 3 results
                raw_content = result.get('content', '')
                cleaned = clean_document_text(raw_content)
                if not cleaned or is_noise_text(cleaned):
                    continue
                source = result.get('source', 'Unknown')
                page = result.get('page')
                page_seg = f", Page: {page}" if (isinstance(page, int) or (isinstance(page, str) and page.isdigit())) else ""
                context_parts.append(f"Document {i+1} (Source: {source}{page_seg}):\n{cleaned}")
            if not context_parts:
                return self._generate_fallback_response(query, search_results)
            context = "\n\n".join(context_parts)

=======
            
            # Prepare context from search results
            context_parts = []
            for i, result in enumerate(search_results[:3]):  # Use top 3 results
                content = result.get('content', '')  # Get full content without truncation
                source = result.get('source', 'Unknown')
                page = result.get('page', 0)
                
                context_parts.append(f"Document {i+1} (Source: {source}, Page: {page}):\n{content}")
            
            context = "\n\n".join(context_parts)
            
>>>>>>> clean-master
            # Create prompt
            prompt = f"""Based on the following document excerpts, please answer the user's question. If the information is not available in the documents, please say so clearly.

User Question: {query}

Document Context:
{context}

Please provide a comprehensive answer based on the document content above. Include specific references to the source documents when possible."""
<<<<<<< HEAD

            # New SDK path
            if hasattr(self.openai_client, "chat") and hasattr(self.openai_client.chat, "completions"):
                response = self.openai_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that answers questions based on provided document context. Always cite your sources and be accurate."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.3,
                )
                return response.choices[0].message.content

            # Legacy SDK path (if present)
            if hasattr(self.openai_client, "ChatCompletion"):
                response = self.openai_client.ChatCompletion.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that answers questions based on provided document context. Always cite your sources and be accurate."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.3,
                )
                return response.choices[0].message.content

            # If neither interface exists, fallback
            return self._generate_fallback_response(query, search_results)

        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return self._generate_fallback_response(query, search_results)
=======
            
            # Generate response
            response = self.openai_client.ChatCompletion.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on provided document context. Always cite your sources and be accurate."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return self._generate_fallback_response(query, search_results)
    
    def _generate_fallback_response(self, query: str, search_results: List[Dict[str, Any]]) -> str:
        """Generate fallback response when LLM is not available"""
        if not search_results:
            return f"No relevant documents found for query: '{query}'"
        
        response_parts = [f"Found {len(search_results)} relevant document(s) for your query: '{query}'\n"]
        
        for i, result in enumerate(search_results, 1):
            content = result.get('content', 'No content available')[:500]
            source = result.get('source', 'Unknown')
            score = result.get('score', 0.0)
            
            response_parts.append(f"**Result {i}** (Relevance: {score:.2f}):")
            response_parts.append(f"Source: {source}")
            response_parts.append(f"Content: {content}...")
            response_parts.append("---")
        
        return "\n".join(response_parts)
    
    def query_with_llm(self, query: str, index_name: str, model_name: str = "gpt-3.5-turbo", top_k: int = 5) -> Dict[str, Any]:
        """
        Complete query pipeline: search index + generate LLM response
        
        Args:
            query: User query
            index_name: Index to search
            model_name: LLM model to use
            top_k: Number of search results to retrieve
            
        Returns:
            Dictionary with search results and generated response
        """
        # Search the index
        search_results = self.search_index(query, index_name, top_k)
        
        # Generate LLM response
        llm_response = self.generate_llm_response(query, search_results, model_name)
        
        return {
            'query': query,
            'index_name': index_name,
            'search_results': search_results,
            'llm_response': llm_response,
            'model_used': model_name,
            'results_count': len(search_results)
        }
>>>>>>> clean-master

# Global instance
unified_search_engine = UnifiedSearchEngine()

def search_index_unified(query: str, index_name: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Unified search function for all tabs
    """
    return unified_search_engine.search_index(query, index_name, top_k)

def query_with_llm_unified(query: str, index_name: str, model_name: str = None, top_k: int = 3) -> Dict[str, Any]:
    """
    Unified query with LLM function for all tabs
    """
    return unified_search_engine.query_with_llm(query, index_name, model_name, top_k)
