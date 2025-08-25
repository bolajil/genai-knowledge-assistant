#!/usr/bin/env python
# Script to provide document listing functionality for the agent assistant
import os
import logging
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Fix the path to ensure parent directory is in the Python path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def list_documents_for_agent():
    """List all available documents in the index directories for the agent response"""
    
    # Define paths to check
    index_paths = [
        os.path.join(project_root, "data", "indexes"),
        os.path.join(project_root, "vector_store"),
        os.path.join(project_root, "vectorstores"),
        r"C:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant\data\indexes",
        r"C:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant\vector_store",
        r"C:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant\vectorstores"
    ]
    
    # Track documents found
    available_docs = []
    categories = {}
    
    # Check each path
    for path in index_paths:
        if os.path.exists(path):
            logger.info(f"Checking for documents in {path}")
            try:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        # Process directory name to get a clean document name
                        doc_name = item.replace("_index", "").replace("_index_index", "")
                        doc_name = doc_name.replace("FIA_", "").replace("AWS_", "")
                        
                        # Skip if already found
                        if doc_name.lower() in [d.lower() for d in available_docs]:
                            continue
                            
                        # Categorize document
                        category = "General"
                        if "aws" in doc_name.lower() or "amazon" in doc_name.lower():
                            category = "AWS Documentation"
                        elif "fia" in doc_name.lower() or "financial" in doc_name.lower():
                            category = "Financial Industry Analysis"
                            
                        # Add to category
                        if category not in categories:
                            categories[category] = []
                        categories[category].append(doc_name)
                        
                        # Add to overall list
                        available_docs.append(doc_name)
                        logger.info(f"Found document: {doc_name} ({item_path})")
            except Exception as e:
                logger.error(f"Error reading directory {path}: {str(e)}")
    
    # Create response content
    content = """
## 📚 Available Documents in Knowledge Base

The following documents are available in your indexed knowledge base:
"""
    
    # Add categorized documents
    if not categories:
        content += "\n**No indexed documents found.** Please check your document indexing process."
    else:
        for category, docs in categories.items():
            content += f"\n### {category}\n"
            for doc in docs:
                # Format the document name nicely
                display_name = " ".join(word.capitalize() for word in doc.replace("_", " ").split())
                content += f"- **{display_name}**: Indexed document available for operations\n"
    
    # Add usage instructions
    content += """
### 🔍 Working with Documents

You can perform the following operations on these documents:

1. **View/Summarize**: `Summarize [document name]`
2. **Improve**: `Improve [document name]`
3. **Ask Questions**: `What does [document name] say about [topic]?`
4. **Extract Information**: `List key points from [document name]`

For example:
- `Summarize AWS documentation`
- `Improve Financial Industry Analysis document`
- `What does AWS say about security?`
"""
    
    return content

if __name__ == "__main__":
    # Print the documents when run directly
    document_listing = list_documents_for_agent()
    print(document_listing)
