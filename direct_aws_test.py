import os
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Path to the AWS index directory
AWS_INDEX_DIR = r"C:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant\data\indexes\AWS_index_index"

def read_aws_content():
    """Read content from the AWS index directory"""
    print("\n===== READING AWS CONTENT DIRECTLY =====\n")
    
    # Check if the directory exists
    if not os.path.exists(AWS_INDEX_DIR):
        print(f"❌ Directory not found: {AWS_INDEX_DIR}")
        return
    
    # Check for text_content.txt
    text_file = os.path.join(AWS_INDEX_DIR, "text_content.txt")
    if os.path.exists(text_file):
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"✅ Successfully read text_content.txt ({len(content)} characters)")
                print(f"Content preview: {content[:200]}...\n")
                return content
        except Exception as e:
            print(f"❌ Error reading text_content.txt: {str(e)}")
    else:
        print(f"❌ File not found: {text_file}")
    
    # If text_content.txt wasn't found or couldn't be read, try all txt files
    print("Searching for other text files...")
    for root, _, files in os.walk(AWS_INDEX_DIR):
        for file in files:
            if file.endswith('.txt'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        print(f"✅ Successfully read {file} ({len(content)} characters)")
                        print(f"Content preview: {content[:200]}...\n")
                        return content
                except Exception as e:
                    print(f"❌ Error reading {file}: {str(e)}")
    
    # If we still don't have content, look for PDF and try to extract info
    source_pdf = os.path.join(AWS_INDEX_DIR, "source_document.pdf")
    if os.path.exists(source_pdf):
        print(f"✅ Found source PDF: {source_pdf}")
        file_size = os.path.getsize(source_pdf) / 1024
        print(f"PDF size: {file_size:.2f} KB")
        print("Unable to extract text without PDF parser\n")
    
    print("No text content could be extracted")
    return None

def improve_document(content):
    """Simple document improvement function"""
    if not content:
        return None
    
    print("\n===== IMPROVING DOCUMENT CONTENT =====\n")
    
    # Split into lines
    lines = content.strip().split('\n')
    
    # Create improved document
    improved = []
    
    # Add title if missing
    if not lines[0].startswith('#'):
        improved.append("# AWS Documentation\n")
    
    # Add executive summary
    improved.append("## Executive Summary\n")
    improved.append("This document provides information on AWS services and security best practices. It covers key concepts, implementation details, and recommendations for effective usage of AWS cloud infrastructure.\n")
    
    # Add original content
    improved.append("## Document Content\n")
    improved.append(content)
    
    # Add conclusion
    improved.append("\n## Conclusion\n")
    improved.append("This document has presented key information about AWS services and security practices. The concepts and approaches outlined provide a foundation for effective implementation and usage of AWS cloud resources.")
    
    result = "\n".join(improved)
    print(f"✅ Document successfully improved ({len(result)} characters)")
    print(f"Improved preview: {result[:200]}...\n")
    
    return result

if __name__ == "__main__":
    content = read_aws_content()
    if content:
        improved = improve_document(content)
    else:
        print("❌ Cannot improve document - no content available")
