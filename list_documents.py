import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def list_available_documents():
    """List all available documents in the index directories"""
    print("\n===== AVAILABLE DOCUMENTS =====\n")
    
    # Define paths to check
    index_paths = [
        os.path.join(os.getcwd(), "data", "indexes"),
        os.path.join(os.getcwd(), "vector_store"),
        r"C:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant\data\indexes",
        r"C:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant\vector_store"
    ]
    
    available_docs = []
    
    # Check each path
    for path in index_paths:
        if os.path.exists(path):
            print(f"Checking {path}:")
            try:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        if "_index" in item:
                            base_name = item.replace("_index", "").replace("FIA_", "").replace("AWS_", "")
                            available_docs.append((base_name, item_path))
                            print(f"  ✅ Found document: {base_name} ({item})")
            except Exception as e:
                print(f"  Error reading directory: {str(e)}")
    
    print("\nThe following documents are available for improvement:")
    for i, (doc_name, _) in enumerate(available_docs, 1):
        print(f"{i}. {doc_name}")
    
    if available_docs:
        print("\nTo use these documents in the agent assistant, try:")
        print(f"- Improve {available_docs[0][0]} document")
    else:
        print("\nNo documents found in the indexes.")

if __name__ == "__main__":
    list_available_documents()
