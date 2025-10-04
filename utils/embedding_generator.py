"""
Embedding Generator for Vector Databases

Generates embeddings for document content to enable proper vector search
and retrieval functionality.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import pickle
import faiss
from sentence_transformers import SentenceTransformer
import json
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """
    Generates and manages embeddings for document content
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding generator
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self.model = None
        self.embedding_dimension = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the sentence transformer model"""
        try:
            # Prefer local model directory if available to avoid network fetch
            local_dir_candidates = [
                Path("models") / self.model_name,
                Path("models") / "all-minLM-L6-v2",
            ]
            for p in local_dir_candidates:
                if p.exists():
                    self.model = SentenceTransformer(str(p))
                    break
            if self.model is None:
                self.model = SentenceTransformer(self.model_name)
            # Get embedding dimension by encoding a test sentence
            test_embedding = self.model.encode(["test"])
            self.embedding_dimension = test_embedding.shape[1]
            logger.info(f"Initialized embedding model: {self.model_name} (dim: {self.embedding_dimension})")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for a list of texts
        
        Args:
            texts: List of text strings to embed
            batch_size: Batch size for processing
            
        Returns:
            NumPy array of embeddings
        """
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        if not texts:
            return np.array([])
        
        try:
            # Process in batches to manage memory
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = self.model.encode(batch_texts, show_progress_bar=True)
                all_embeddings.append(batch_embeddings)
            
            # Concatenate all batches
            embeddings = np.vstack(all_embeddings)
            logger.info(f"Generated {embeddings.shape[0]} embeddings of dimension {embeddings.shape[1]}")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def chunk_text(self, text: str, chunk_size: int = 1500, chunk_overlap: int = 500) -> List[Dict[str, Any]]:
        """
        Chunk text into smaller pieces for embedding
        
        Args:
            text: Input text to chunk
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of chunk dictionaries with metadata
        """
        if not text or len(text.strip()) == 0:
            return []
        
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Don't go beyond text length
            if end >= len(text):
                chunk_text = text[start:]
            else:
                # Try to break at a sentence or paragraph boundary
                chunk_text = text[start:end]
                
                # Look for natural break points
                break_points = ['. ', '\n\n', '\n']
                best_break = end
                
                for break_point in break_points:
                    last_break = chunk_text.rfind(break_point)
                    if last_break > chunk_size * 0.7:  # At least 70% of chunk size
                        best_break = start + last_break + len(break_point)
                        break
                
                if best_break != end:
                    chunk_text = text[start:best_break]
            
            # Create chunk metadata
            chunk = {
                'id': chunk_id,
                'text': chunk_text.strip(),
                'start_pos': start,
                'end_pos': start + len(chunk_text),
                'length': len(chunk_text.strip())
            }
            
            if chunk['length'] > 50:  # Only include substantial chunks
                chunks.append(chunk)
                chunk_id += 1
            
            # Move to next chunk with overlap
            if end >= len(text):
                break
            
            start = max(start + chunk_size - chunk_overlap, start + 100)  # Ensure progress
        
        logger.info(f"Created {len(chunks)} chunks from text of length {len(text)}")
        return chunks

def create_vector_index_from_text(text_file_path: Path, index_name: str, 
                                output_dir: Path, chunk_size: int = 1500, 
                                chunk_overlap: int = 500) -> Dict[str, Any]:
    """
    Create a FAISS vector index from a text file
    
    Args:
        text_file_path: Path to the text file
        index_name: Name for the index
        output_dir: Directory to save the index
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
        
    Returns:
        Dictionary with index creation results
    """
    try:
        # Initialize embedding generator
        embedding_gen = EmbeddingGenerator()
        
        # Read the text file
        with open(text_file_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
        
        logger.info(f"Read text file: {text_file_path} ({len(text_content)} characters)")
        
        # Chunk the text
        chunks = embedding_gen.chunk_text(text_content, chunk_size, chunk_overlap)
        
        if not chunks:
            raise ValueError("No valid chunks created from text")
        
        # Extract text from chunks
        chunk_texts = [chunk['text'] for chunk in chunks]
        
        # Generate embeddings
        embeddings = embedding_gen.generate_embeddings(chunk_texts)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)  # Inner product similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add embeddings to index
        index.add(embeddings.astype('float32'))
        
        # Create metadata
        metadata = {
            'documents': chunk_texts,
            'metadatas': [
                {
                    'source': str(text_file_path),
                    'chunk_id': chunk['id'],
                    'start_pos': chunk['start_pos'],
                    'end_pos': chunk['end_pos'],
                    'length': chunk['length']
                }
                for chunk in chunks
            ],
            'ids': [f"{index_name}_{i}" for i in range(len(chunks))],
            'embedding_model': embedding_gen.model_name,
            'dimension': dimension,
            'total_chunks': len(chunks),
            'created_at': datetime.now().isoformat(),
            'source_file': str(text_file_path),
            'chunk_size': chunk_size,
            'chunk_overlap': chunk_overlap
        }
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss_path = output_dir / "index.faiss"
        faiss.write_index(index, str(faiss_path))
        
        # Save metadata
        metadata_path = output_dir / "index.pkl"
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        
        # Save human-readable metadata
        info_path = output_dir / "index_info.json"
        with open(info_path, 'w') as f:
            json.dump({
                'index_name': index_name,
                'source_file': str(text_file_path),
                'total_chunks': len(chunks),
                'embedding_dimension': dimension,
                'embedding_model': embedding_gen.model_name,
                'created_at': metadata['created_at'],
                'chunk_size': chunk_size,
                'chunk_overlap': chunk_overlap
            }, f, indent=2)
        
        result = {
            'success': True,
            'index_path': output_dir,
            'faiss_path': faiss_path,
            'metadata_path': metadata_path,
            'total_chunks': len(chunks),
            'embedding_dimension': dimension,
            'index_size': index.ntotal
        }
        
        logger.info(f"Successfully created vector index: {output_dir}")
        logger.info(f"Index contains {index.ntotal} vectors of dimension {dimension}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to create vector index: {e}")
        return {
            'success': False,
            'error': str(e),
            'index_path': output_dir
        }

def add_embeddings_to_existing_indexes(base_dir: Path) -> Dict[str, Any]:
    """
    Add embeddings to existing text-based indexes
    
    Args:
        base_dir: Base directory containing indexes
        
    Returns:
        Results of embedding generation for each index
    """
    results = {}
    
    # Find all existing indexes
    if not base_dir.exists():
        logger.error(f"Base directory does not exist: {base_dir}")
        return {'error': f'Base directory not found: {base_dir}'}
    
    for index_dir in base_dir.iterdir():
        if not index_dir.is_dir():
            continue
        
        # Check if it has extracted_text.txt but no FAISS index
        text_file = index_dir / "extracted_text.txt"
        faiss_file = index_dir / "index.faiss"
        
        if text_file.exists() and not faiss_file.exists():
            logger.info(f"Adding embeddings to index: {index_dir.name}")
            
            try:
                result = create_vector_index_from_text(
                    text_file_path=text_file,
                    index_name=index_dir.name,
                    output_dir=index_dir
                )
                results[index_dir.name] = result
                
            except Exception as e:
                logger.error(f"Failed to add embeddings to {index_dir.name}: {e}")
                results[index_dir.name] = {
                    'success': False,
                    'error': str(e)
                }
        elif faiss_file.exists():
            logger.info(f"Index {index_dir.name} already has embeddings")
            results[index_dir.name] = {
                'success': True,
                'status': 'already_exists',
                'message': 'FAISS index already exists'
            }
        else:
            logger.warning(f"Index {index_dir.name} has no extracted_text.txt file")
            results[index_dir.name] = {
                'success': False,
                'error': 'No extracted_text.txt file found'
            }
    
    return results

def validate_vector_index(index_dir: Path) -> Dict[str, Any]:
    """
    Validate a vector index to ensure it's properly constructed
    
    Args:
        index_dir: Directory containing the index
        
    Returns:
        Validation results
    """
    validation = {
        'valid': False,
        'issues': [],
        'info': {}
    }
    
    try:
        faiss_path = index_dir / "index.faiss"
        metadata_path = index_dir / "index.pkl"
        
        # Check if files exist
        if not faiss_path.exists():
            validation['issues'].append("FAISS index file missing")
            return validation
        
        if not metadata_path.exists():
            validation['issues'].append("Metadata file missing")
            return validation
        
        # Load and validate FAISS index
        index = faiss.read_index(str(faiss_path))
        validation['info']['total_vectors'] = index.ntotal
        validation['info']['dimension'] = index.d
        
        if index.ntotal == 0:
            validation['issues'].append("FAISS index is empty")
        
        # Load and validate metadata
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
        
        validation['info']['metadata_chunks'] = len(metadata.get('documents', []))
        validation['info']['embedding_model'] = metadata.get('embedding_model', 'unknown')
        
        # Check consistency
        if index.ntotal != len(metadata.get('documents', [])):
            validation['issues'].append("Mismatch between FAISS index size and metadata")
        
        # If no issues found, mark as valid
        if not validation['issues']:
            validation['valid'] = True
        
    except Exception as e:
        validation['issues'].append(f"Validation error: {str(e)}")
    
    return validation
