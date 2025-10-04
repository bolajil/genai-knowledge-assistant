"""
Enterprise Hybrid Search & Re-Ranking System

Implements hybrid search combining vector similarity and keyword search with
cross-encoder re-ranking for enterprise-grade retrieval accuracy.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json
import re
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Enhanced search result with scoring metadata"""
    content: str
    source: str
    page: Optional[str] = None
    section: Optional[str] = None
    vector_score: float = 0.0
    keyword_score: float = 0.0
    rerank_score: float = 0.0
    final_score: float = 0.0
    metadata: Dict[str, Any] = None

class BM25Retriever:
    """Simple BM25 keyword retriever implementation"""
    
    def __init__(self, documents: List[Dict[str, Any]], k1: float = 1.2, b: float = 0.75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.doc_lengths = [len(doc['content'].split()) for doc in documents]
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if documents else 0
        self.term_frequencies = self._build_term_frequencies()
        self.document_frequencies = self._build_document_frequencies()
        self.num_docs = len(documents)
    
    def _build_term_frequencies(self) -> List[Dict[str, int]]:
        """Build term frequency maps for each document"""
        tf_maps = []
        for doc in self.documents:
            words = doc['content'].lower().split()
            tf_map = {}
            for word in words:
                tf_map[word] = tf_map.get(word, 0) + 1
            tf_maps.append(tf_map)
        return tf_maps
    
    def _build_document_frequencies(self) -> Dict[str, int]:
        """Build document frequency map for all terms"""
        df_map = {}
        for tf_map in self.term_frequencies:
            for term in tf_map.keys():
                df_map[term] = df_map.get(term, 0) + 1
        return df_map
    
    def search(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        """Search documents using BM25 scoring"""
        query_terms = query.lower().split()
        scores = []
        
        for doc_idx, (doc, tf_map, doc_length) in enumerate(zip(
            self.documents, self.term_frequencies, self.doc_lengths
        )):
            score = 0.0
            
            for term in query_terms:
                if term in tf_map:
                    tf = tf_map[term]
                    df = self.document_frequencies.get(term, 0)
                    
                    # BM25 formula
                    idf = max(0.01, (self.num_docs - df + 0.5) / (df + 0.5))
                    tf_component = (tf * (self.k1 + 1)) / (
                        tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))
                    )
                    score += idf * tf_component
            
            scores.append((doc_idx, score))
        
        # Sort by score and return top k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]

class CrossEncoderReranker:
    """Cross-encoder re-ranker for improving search precision"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load the cross-encoder model"""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.torch = torch
            logger.info(f"Loaded cross-encoder model: {self.model_name}")
        except ImportError:
            logger.warning("Transformers not available, re-ranking will use fallback scoring")
        except Exception as e:
            logger.error(f"Failed to load cross-encoder model: {e}")
    
    def rerank(self, query: str, results: List[SearchResult], top_k: int = 10) -> List[SearchResult]:
        """Re-rank search results using cross-encoder"""
        if not self.model or not results:
            return results[:top_k]
        
        try:
            # Prepare query-document pairs
            pairs = [[query, result.content] for result in results]
            
            # Tokenize
            features = self.tokenizer(
                pairs, 
                padding=True, 
                truncation=True, 
                return_tensors="pt", 
                max_length=512
            )
            
            # Get scores
            with self.torch.no_grad():
                scores = self.model(**features).logits.squeeze()
            
            # Update results with rerank scores
            for i, result in enumerate(results):
                result.rerank_score = float(scores[i]) if scores.dim() > 0 else float(scores)
            
            # Sort by rerank score
            reranked = sorted(results, key=lambda x: x.rerank_score, reverse=True)
            return reranked[:top_k]
            
        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            return results[:top_k]

class EnterpriseHybridSearch:
    """Enterprise hybrid search combining vector and keyword search with re-ranking"""
    
    def __init__(self, vector_weight: float = 0.6, keyword_weight: float = 0.4):
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.reranker = CrossEncoderReranker()
        self.bm25_retrievers = {}  # Cache BM25 retrievers per index
    
    def search(self, query: str, index_name: str, max_results: int = 10) -> List[SearchResult]:
        """Perform hybrid search with re-ranking"""
        try:
            # Step 1: Get documents from index
            documents = self._load_documents_from_index(index_name)
            if not documents:
                return []
            
            # Step 2: Vector search
            vector_results = self._vector_search(query, documents, max_results * 2)
            
            # Step 3: Keyword search
            keyword_results = self._keyword_search(query, index_name, documents, max_results * 2)
            
            # Step 4: Combine results
            combined_results = self._combine_results(vector_results, keyword_results)
            
            # Step 5: Re-rank using cross-encoder
            final_results = self.reranker.rerank(query, combined_results, max_results)
            
            # Step 6: Calculate final scores
            for result in final_results:
                result.final_score = (
                    self.vector_weight * result.vector_score +
                    self.keyword_weight * result.keyword_score +
                    0.3 * result.rerank_score  # Re-rank boost
                )
            
            logger.info(f"Hybrid search completed: {len(final_results)} results for '{query}'")
            return final_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []
    
    def _load_documents_from_index(self, index_name: str) -> List[Dict[str, Any]]:
        """Load documents from the specified index"""
        try:
            from utils.simple_vector_manager import get_simple_index_path
            
            index_path = get_simple_index_path(index_name)
            if not index_path:
                return []
            
            index_path = Path(index_path)
            documents = []
            
            # Load from extracted_text.txt if available
            extracted_text_path = index_path / "extracted_text.txt"
            if extracted_text_path.exists():
                documents.extend(self._load_from_extracted_text(extracted_text_path))
            
            # Load from other text files
            for file_path in index_path.glob("*.txt"):
                if file_path.name != "extracted_text.txt" and file_path.name != "index.meta":
                    documents.extend(self._load_from_text_file(file_path))
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to load documents from {index_name}: {e}")
            return []
    
    def _load_from_extracted_text(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load documents from extracted text file"""
        documents = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by pages
            pages = re.split(r'--- Page (\d+) ---', content)
            
            for i in range(1, len(pages), 2):
                if i + 1 < len(pages):
                    page_num = int(pages[i])
                    page_content = pages[i + 1].strip()
                    
                    if page_content:
                        # Further split page into paragraphs
                        paragraphs = [p.strip() for p in page_content.split('\n\n') if p.strip()]
                        
                        for para_num, paragraph in enumerate(paragraphs, 1):
                            if len(paragraph) > 100:  # Only substantial paragraphs
                                documents.append({
                                    'content': paragraph,
                                    'source': f"Page {page_num}, Paragraph {para_num}",
                                    'page': page_num,
                                    'section': f"Paragraph {para_num}",
                                    'file_path': str(file_path)
                                })
        
        except Exception as e:
            logger.error(f"Error loading extracted text: {e}")
        
        return documents
    
    def _load_from_text_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load documents from a single text file"""
        documents = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into chunks
            chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]
            
            for i, chunk in enumerate(chunks, 1):
                if len(chunk) > 100:
                    documents.append({
                        'content': chunk,
                        'source': f"{file_path.name}, Section {i}",
                        'page': i,
                        'section': f"Section {i}",
                        'file_path': str(file_path)
                    })
        
        except Exception as e:
            logger.error(f"Error loading text file {file_path}: {e}")
        
        return documents
    
    def _vector_search(self, query: str, documents: List[Dict[str, Any]], k: int) -> List[SearchResult]:
        """Perform vector similarity search"""
        results = []
        
        try:
            # Simple TF-IDF based similarity for now
            # In production, you'd use proper embeddings
            query_words = set(query.lower().split())
            
            for doc in documents:
                doc_words = set(doc['content'].lower().split())
                
                # Jaccard similarity as a simple vector score
                intersection = len(query_words & doc_words)
                union = len(query_words | doc_words)
                similarity = intersection / union if union > 0 else 0
                
                if similarity > 0:
                    results.append(SearchResult(
                        content=doc['content'],
                        source=doc['source'],
                        page=doc.get('page'),
                        section=doc.get('section'),
                        vector_score=similarity,
                        metadata=doc
                    ))
            
            # Sort by vector score
            results.sort(key=lambda x: x.vector_score, reverse=True)
            return results[:k]
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _keyword_search(self, query: str, index_name: str, documents: List[Dict[str, Any]], k: int) -> List[SearchResult]:
        """Perform BM25 keyword search"""
        try:
            # Get or create BM25 retriever for this index
            if index_name not in self.bm25_retrievers:
                self.bm25_retrievers[index_name] = BM25Retriever(documents)
            
            bm25 = self.bm25_retrievers[index_name]
            bm25_results = bm25.search(query, k)
            
            results = []
            for doc_idx, score in bm25_results:
                if doc_idx < len(documents):
                    doc = documents[doc_idx]
                    results.append(SearchResult(
                        content=doc['content'],
                        source=doc['source'],
                        page=doc.get('page'),
                        section=doc.get('section'),
                        keyword_score=score,
                        metadata=doc
                    ))
            
            return results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    def _combine_results(self, vector_results: List[SearchResult], keyword_results: List[SearchResult]) -> List[SearchResult]:
        """Combine vector and keyword search results"""
        # Create a map to merge results by content
        result_map = {}
        
        # Add vector results
        for result in vector_results:
            key = result.content[:100]  # Use first 100 chars as key
            result_map[key] = result
        
        # Merge keyword results
        for result in keyword_results:
            key = result.content[:100]
            if key in result_map:
                # Merge scores
                result_map[key].keyword_score = max(result_map[key].keyword_score, result.keyword_score)
            else:
                result_map[key] = result
        
        return list(result_map.values())

def get_enterprise_hybrid_search(vector_weight: float = 0.6, keyword_weight: float = 0.4) -> EnterpriseHybridSearch:
    """Get instance of enterprise hybrid search"""
    return EnterpriseHybridSearch(vector_weight, keyword_weight)
