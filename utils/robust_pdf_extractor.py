"""
Robust PDF Text Extraction
Uses multiple extraction methods with quality validation and text cleaning.
"""

import io
import re
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

def extract_text_from_pdf_robust(pdf_bytes: bytes, filename: str = "document.pdf") -> Tuple[str, str]:
    """
    Extract text from PDF using multiple methods with quality validation.
    
    Returns:
        Tuple of (extracted_text, method_used)
    """
    if not pdf_bytes:
        return "", "none"
    
    # Try methods in order of quality
    methods = [
        ("pdfplumber", extract_with_pdfplumber),
        ("pymupdf", extract_with_pymupdf),
        ("pypdf", extract_with_pypdf),
    ]
    
    best_text = ""
    best_method = "none"
    best_quality = 0.0
    
    for method_name, extractor_func in methods:
        try:
            text = extractor_func(pdf_bytes)
            if text:
                quality = assess_text_quality(text)
                logger.info(f"{method_name} extraction quality for {filename}: {quality:.2f}")
                
                if quality > best_quality:
                    best_text = text
                    best_method = method_name
                    best_quality = quality
                    
                # If we get good quality, stop trying
                if quality > 0.8:
                    break
        except Exception as e:
            logger.warning(f"{method_name} extraction failed for {filename}: {e}")
            continue
    
    if best_text:
        # Clean the text
        cleaned_text = clean_extracted_text(best_text)
        logger.info(f"Best extraction method for {filename}: {best_method} (quality: {best_quality:.2f})")
        return cleaned_text, best_method
    else:
        logger.error(f"All extraction methods failed for {filename}")
        return "", "failed"

def extract_with_pdfplumber(pdf_bytes: bytes) -> str:
    """Extract text using pdfplumber (best for preserving layout and spacing)"""
    import pdfplumber
    
    texts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                texts.append(f"--- Page {page_num} ---\n{page_text}\n")
    
    return "\n".join(texts)

def extract_with_pymupdf(pdf_bytes: bytes) -> str:
    """Extract text using PyMuPDF/fitz (good for complex PDFs)"""
    import fitz  # PyMuPDF
    
    texts = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text()
        if page_text.strip():
            texts.append(f"--- Page {page_num + 1} ---\n{page_text}\n")
    
    doc.close()
    return "\n".join(texts)

def extract_with_pypdf(pdf_bytes: bytes) -> str:
    """Extract text using pypdf/PyPDF2 (fallback, often has spacing issues)"""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    except ImportError:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
    
    texts = []
    for page_num, page in enumerate(reader.pages, 1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            texts.append(f"--- Page {page_num} ---\n{page_text}\n")
    
    return "\n".join(texts)

def assess_text_quality(text: str) -> float:
    """
    Assess the quality of extracted text.
    
    Returns a score from 0.0 to 1.0 based on:
    - Presence of spaces between words
    - Ratio of letters to total characters
    - Average word length
    - Presence of common words
    """
    if not text or len(text) < 50:
        return 0.0
    
    score = 0.0
    
    # Check 1: Space density (should have spaces between words)
    space_ratio = text.count(' ') / len(text)
    if 0.10 < space_ratio < 0.25:  # Typical English text has 15-20% spaces
        score += 0.3
    elif space_ratio > 0.05:
        score += 0.1
    
    # Check 2: Letter ratio (should be mostly letters)
    letter_count = sum(1 for c in text if c.isalpha())
    letter_ratio = letter_count / len(text)
    if letter_ratio > 0.6:
        score += 0.3
    elif letter_ratio > 0.4:
        score += 0.15
    
    # Check 3: Average word length (should be reasonable)
    words = text.split()
    if words:
        avg_word_len = sum(len(w) for w in words) / len(words)
        if 3 < avg_word_len < 8:  # Typical English: 4-6 characters
            score += 0.2
        elif 2 < avg_word_len < 12:
            score += 0.1
    
    # Check 4: Common English words present
    common_words = ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'for', 'on', 'with']
    text_lower = text.lower()
    common_word_count = sum(1 for word in common_words if f' {word} ' in text_lower)
    if common_word_count >= 5:
        score += 0.2
    elif common_word_count >= 3:
        score += 0.1
    
    return min(score, 1.0)

def clean_extracted_text(text: str) -> str:
    """
    Clean extracted PDF text to improve readability.
    
    - Removes page break markers
    - Normalizes whitespace
    - Fixes common PDF extraction issues
    - Preserves paragraph structure
    """
    if not text:
        return ""
    
    # Remove page break markers (we'll add them back in a cleaner format)
    text = re.sub(r'--- Page \d+ ---', '', text)
    
    # Fix common PDF issues
    # 1. Remove soft hyphens and line breaks within words
    text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)
    
    # 2. Normalize multiple spaces to single space
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 3. Normalize line breaks (max 2 consecutive)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # 4. Remove leading/trailing whitespace from lines
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # 5. Add paragraph breaks after sentences (helps with readability)
    text = re.sub(r'([.!?])\s+([A-Z])', r'\1\n\n\2', text)
    
    return text.strip()

def validate_extraction_quality(text: str, min_quality: float = 0.5) -> Tuple[bool, float, str]:
    """
    Validate if extracted text meets quality standards.
    
    Returns:
        Tuple of (is_valid, quality_score, message)
    """
    quality = assess_text_quality(text)
    
    if quality >= min_quality:
        return True, quality, f"Text quality is good ({quality:.2f})"
    else:
        issues = []
        
        if text.count(' ') / len(text) < 0.05:
            issues.append("Missing spaces between words")
        
        letter_count = sum(1 for c in text if c.isalpha())
        if letter_count / len(text) < 0.4:
            issues.append("Too few letters (possible encoding issue)")
        
        words = text.split()
        if words and sum(len(w) for w in words) / len(words) > 12:
            issues.append("Words are too long (possible concatenation)")
        
        message = f"Low quality ({quality:.2f}): {', '.join(issues)}"
        return False, quality, message
