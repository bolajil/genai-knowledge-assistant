import os
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_document(doc_name):
    """Analyze a document from the index and provide a structured report"""
    # Fix the path to ensure parent directory is in the Python path
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    try:
        # Import the document fetching function
        from tabs.agent_assistant_enhanced import fetch_document_content
        
        # Fetch the document content
        content = fetch_document_content(doc_name)
        
        if not content:
            print(f"Document '{doc_name}' not found in the index.")
            return
            
        # Print basic document information
        print(f"\n{'=' * 50}")
        print(f"DOCUMENT ANALYSIS: {doc_name.upper()}")
        print(f"{'=' * 50}\n")
        
        # Content stats
        lines = content.strip().split('\n')
        words = sum(len(line.split()) for line in lines if line.strip())
        chars = len(content)
        
        print(f"Content Statistics:")
        print(f"- Lines: {len(lines)}")
        print(f"- Words: {words}")
        print(f"- Characters: {chars}")
        
        # Structure analysis
        headings = [line.strip() for line in lines if line.strip().startswith('#')]
        bullet_points = [line.strip() for line in lines if line.strip().startswith('-') or line.strip().startswith('*')]
        
        print(f"\nDocument Structure:")
        print(f"- Headings: {len(headings)}")
        print(f"- Bullet Points: {len(bullet_points)}")
        
        # Show document outline
        if headings:
            print(f"\nDocument Outline:")
            for heading in headings[:10]:  # Show first 10 headings
                print(f"  {heading}")
            if len(headings) > 10:
                print(f"  ... and {len(headings) - 10} more headings")
        
        # Show content preview
        print(f"\nContent Preview:")
        preview_length = min(200, len(content))
        print(f"{content[:preview_length]}...")
        
        print(f"\n{'=' * 50}\n")
        
    except Exception as e:
        print(f"Error analyzing document: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        doc_name = sys.argv[1]
        analyze_document(doc_name)
    else:
        print("Please provide a document name to analyze.")
        print("Usage: python analyze_document.py <document_name>")
        print("Example: python analyze_document.py AWS")
