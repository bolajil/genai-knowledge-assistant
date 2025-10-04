"""
Enhanced PDF ingestion pipeline:
- Batch processing for Weaviate
- Progress tracking
- Error handling
"""

from pathlib import Path
import sys
from tqdm import tqdm
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from utils.weaviate_manager import get_weaviate_manager

DATA_DIR = Path("data/")
PDF_GLOB = "*.pdf"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
BATCH_SIZE = 50  # Optimal batch size for Weaviate

def ingest_all_pdfs():
    pdf_files = list(DATA_DIR.glob(PDF_GLOB))
    if not pdf_files:
        print("⚠️ No PDF files found in ./data")
        return

    wm = get_weaviate_manager()
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
        try:
            # Load and split documents
            loader = PyPDFLoader(str(pdf_path))
            docs = loader.load()
            chunks = splitter.split_documents(docs)
            
            # Prepare documents for Weaviate
            documents = []
            for chunk in chunks:
                documents.append({
                    "content": chunk.page_content,
                    "source": pdf_path.name,
                    "source_type": "pdf",
                    "metadata": {
                        "page": chunk.metadata.get("page", 0),
                        "total_pages": len(docs)
                    }
                })
            
            # Create collection if needed
            index_name = f"{pdf_path.stem}_index"
            if index_name not in wm.list_collections():
                wm.create_collection(index_name, f"PDF documents from {pdf_path.name}")
            
            # Batch insert
            for i in range(0, len(documents), BATCH_SIZE):
                batch = documents[i:i+BATCH_SIZE]
                wm.add_documents(index_name, batch)
                
            print(f"✅ Processed {pdf_path.name} ({len(documents)} chunks)")
            
        except Exception as e:
            print(f"❌ Failed to process {pdf_path.name}: {str(e)}")
            continue

    print("\n🎉 All documents processed")

if __name__ == "__main__":
    ingest_all_pdfs()
