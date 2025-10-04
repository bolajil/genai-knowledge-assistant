"""
Regenerate ByLawS2 Index with Full Content
=========================================
The current ByLawS2_index only contains table of contents. This script extracts
the full content from the PDF and creates a proper index with actual section content.
"""

import os
import sys
from pathlib import Path
import PyPDF2
import pdfplumber
import re
import json
from datetime import datetime

def extract_full_pdf_content(pdf_path: str) -> str:
    """Extract full text content from PDF using multiple methods."""
    
    full_text = ""
    
    # Method 1: Try pdfplumber first (better for structured documents)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    full_text += f"\n--- Page {page_num} ---\n{page_text}\n"
        
        if len(full_text) > 1000:  # Good extraction
            print(f"✅ pdfplumber extraction successful: {len(full_text)} characters")
            return full_text
    
    except Exception as e:
        print(f"⚠️  pdfplumber failed: {e}")
    
    # Method 2: Fallback to PyPDF2
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    full_text += f"\n--- Page {page_num} ---\n{page_text}\n"
        
        print(f"✅ PyPDF2 extraction: {len(full_text)} characters")
        return full_text
    
    except Exception as e:
        print(f"❌ PyPDF2 also failed: {e}")
        return ""

def find_section_content(full_text: str) -> dict:
    """Find and extract actual section content from the full text."""
    
    sections = {}
    
    # Pattern to find board meeting sections
    board_patterns = [
        r'Section\s+2\.\s+BOARD\s+MEETINGS[;:]?\s*Action\s+[A-Z\s]*OUTSIDE\s+of\s+Meeting[s]?(.*?)(?=Section\s+\d+\.|$)',
        r'BOARD\s+MEETINGS[;:]?\s*Action\s+[A-Z\s]*OUTSIDE\s+of\s+Meeting[s]?(.*?)(?=Section\s+\d+\.|Notice\s+of\s+MEETINGS|$)',
    ]
    
    for pattern in board_patterns:
        matches = re.finditer(pattern, full_text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            content = match.group(1).strip() if match.groups() else match.group(0).strip()
            if len(content) > 100:  # Substantial content
                sections['Section 2. BOARD MEETINGS; Action Outside of Meeting'] = content
                print(f"✅ Found board meeting section: {len(content)} characters")
    
    # Pattern for notice of meetings
    notice_patterns = [
        r'Section\s+3\.\s+Notice\s+of\s+MEETINGS(.*?)(?=Section\s+\d+\.|$)',
        r'Notice\s+of\s+MEETINGS(.*?)(?=Section\s+\d+\.|Special\s+MEETINGS|$)',
    ]
    
    for pattern in notice_patterns:
        matches = re.finditer(pattern, full_text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            content = match.group(1).strip() if match.groups() else match.group(0).strip()
            if len(content) > 50:
                sections['Section 3. Notice of MEETINGS'] = content
                print(f"✅ Found notice section: {len(content)} characters")
    
    # Pattern for quorum
    quorum_patterns = [
        r'Section\s+6\.\s+Quorum\s+of\s+BOARD\s+of\s+DIRECTORS(.*?)(?=Section\s+\d+\.|$)',
        r'Quorum\s+of\s+BOARD\s+of\s+DIRECTORS(.*?)(?=Section\s+\d+\.|Compensation|$)',
    ]
    
    for pattern in quorum_patterns:
        matches = re.finditer(pattern, full_text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            content = match.group(1).strip() if match.groups() else match.group(0).strip()
            if len(content) > 50:
                sections['Section 6. Quorum of BOARD of DIRECTORS'] = content
                print(f"✅ Found quorum section: {len(content)} characters")
    
    return sections

def regenerate_bylaws_index():
    """Regenerate the ByLawS2_index with full content."""
    
    print("Regenerating ByLawS2_index with Full Content")
    print("=" * 50)
    
    # Paths
    index_dir = Path("data/indexes/ByLawS2_index")
    pdf_path = index_dir / "source_document.pdf"
    extracted_text_path = index_dir / "extracted_text.txt"
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return False
    
    print(f"📄 Processing PDF: {pdf_path}")
    
    # Extract full content
    full_text = extract_full_pdf_content(str(pdf_path))
    
    if not full_text:
        print("❌ Failed to extract PDF content")
        return False
    
    # Find specific sections
    sections = find_section_content(full_text)
    
    if not sections:
        print("⚠️  No specific sections found, using full text")
        # Use full text as fallback
        with open(extracted_text_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
    else:
        # Create enhanced extracted text with sections
        enhanced_content = f"""BYLAWS OF THE PECAN RIDGE COMMUNITY ASSOCIATION, INC.
Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

FULL DOCUMENT CONTENT:
{full_text}

EXTRACTED SECTIONS:
{'=' * 50}

"""
        
        for section_title, section_content in sections.items():
            enhanced_content += f"\n{section_title}\n{'-' * len(section_title)}\n{section_content}\n\n"
        
        # Write enhanced content
        with open(extracted_text_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_content)
    
    # Update index metadata
    meta_path = index_dir / "index.meta"
    meta_data = {
        "index_name": "ByLawS2_index",
        "created_date": datetime.now().isoformat(),
        "source_document": "source_document.pdf",
        "extraction_method": "enhanced_pdf_extraction",
        "content_type": "legal_bylaws",
        "sections_extracted": len(sections),
        "total_characters": len(full_text),
        "has_full_content": True
    }
    
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta_data, f, indent=2)
    
    print(f"✅ Successfully regenerated ByLawS2_index")
    print(f"   - Total content: {len(full_text)} characters")
    print(f"   - Sections extracted: {len(sections)}")
    print(f"   - Updated: {extracted_text_path}")
    print(f"   - Metadata: {meta_path}")
    
    return True

def test_regenerated_content():
    """Test the regenerated content to verify it contains actual sections."""
    
    print("\nTesting Regenerated Content")
    print("=" * 30)
    
    extracted_text_path = Path("data/indexes/ByLawS2_index/extracted_text.txt")
    
    if not extracted_text_path.exists():
        print("❌ Extracted text file not found")
        return
    
    with open(extracted_text_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Test for board meeting content
    board_meeting_found = "board meetings" in content.lower() and "action outside" in content.lower()
    
    # Test for actual procedural content (not just TOC)
    has_procedures = any(phrase in content.lower() for phrase in [
        "regular meetings of the board",
        "special meetings of the board", 
        "consent in writing",
        "majority of the directors"
    ])
    
    print(f"Content length: {len(content)} characters")
    print(f"Board meeting section found: {'✅' if board_meeting_found else '❌'}")
    print(f"Has procedural content: {'✅' if has_procedures else '❌'}")
    
    if has_procedures:
        print("🎉 SUCCESS: Index now contains actual section content!")
    else:
        print("⚠️  WARNING: Still appears to be table of contents")

if __name__ == "__main__":
    success = regenerate_bylaws_index()
    if success:
        test_regenerated_content()
    else:
        print("❌ Failed to regenerate index")
