"""
Semantic document ingestion with:
- Page-based chunking
- Header preservation
- Weaviate integration
"""

import re
from pathlib import Path
from typing import List, Dict, Any

from utils.weaviate_manager import get_weaviate_manager

# Page break pattern (customize based on document format)
PAGE_BREAK = r'\n--- Page \d+ ---\n'

class SemanticIngester:
    def __init__(self):
        self.wm = get_weaviate_manager()
    
    def process_document(self, file_path: Path, collection_name: str) -> bool:
        """Process a document with semantic chunking"""
        try:
            text = file_path.read_text(encoding='utf-8')
            
            # Split by pages first
            pages = re.split(PAGE_BREAK, text)
            documents = []
            
            for page_num, page_content in enumerate(pages, 1):
                # Split each page into sections
                sections = re.split(r'\n([A-Z][A-Z\s,:]+)\n', page_content)
                
                # Combine headers with their content
                for i in range(1, len(sections), 2):
                    header = sections[i]
                    content = sections[i+1]
                    
                    documents.append({
                        "content": f"{header}\n{content}",
                        "source": file_path.name,
                        "page": page_num,
                        "section": header.strip(),
                        "source_type": "semantic"
                    })
            
            # Create collection if needed
            if collection_name not in self.wm.list_collections():
                self.wm.create_collection(collection_name, f"Semantic documents from {file_path.name}")
            
            # Batch insert
            batch_size = 50
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                self.wm.add_documents(collection_name, batch)
            
            return True
            
        except Exception as e:
            print(f"Error processing {file_path.name}: {str(e)}")
            return False
