"""
Extract actual content from the ByLaw PDF document
"""
import os
import sys
from pathlib import Path

def extract_pdf_content():
    """Extract actual content from the PDF"""
    try:
        import PyPDF2
        
        pdf_path = Path("data/indexes/ByLawS2_index/source_document.pdf")
        if not pdf_path.exists():
            print(f"PDF not found at {pdf_path}")
            return None
        
        print(f"Extracting content from: {pdf_path}")
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            print(f"PDF has {len(pdf_reader.pages)} pages")
            
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                text += f"\n--- Page {page_num + 1} ---\n"
                text += page_text
                print(f"Extracted page {page_num + 1}: {len(page_text)} characters")
        
        print(f"Total extracted: {len(text)} characters")
        
        # Save to extracted_text.txt
        output_path = Path("data/indexes/ByLawS2_index/extracted_text.txt")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        print(f"Saved extracted content to: {output_path}")
        
        # Show first 2000 characters
        print("\nFirst 2000 characters of extracted content:")
        print("=" * 50)
        print(text[:2000])
        print("=" * 50)
        
        return text
        
    except ImportError:
        print("PyPDF2 not installed. Installing...")
        os.system("pip install PyPDF2")
        return extract_pdf_content()
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return None

if __name__ == "__main__":
    extract_pdf_content()
