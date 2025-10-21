"""
<<<<<<< HEAD
Text Cleaning Utilities for Document Processing

Provides enterprise-grade text cleaning and normalization for document content
before LLM processing. Handles common document formatting issues and improves
response quality.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class DocumentTextCleaner:
    """
    Enterprise document text cleaner with comprehensive formatting fixes.

    Handles:
    - Legal document formatting (page breaks, headers, footers)
    - OCR artifacts and scanning errors
    - Inconsistent whitespace and line breaks
    - Special characters and encoding issues
    - Citation and reference cleanup
    """

    def __init__(self):
        # Common patterns to clean
        self.page_break_patterns = [
            r'---\s*Page\s+\d+\s*---',
            r'Page\s+\d+',
            r'\n\s*\n\s*\n+',  # Multiple blank lines
            # Numeric page-stamp artifacts like: "2022136118 of 28 C"
            r'\b\d{6,}\s+of\s+\d+\s*[A-Z]?\b',
        ]

        self.header_footer_patterns = [
            r'\bconfidential\b',
            r'\bdraft\b',
            r'\binternal\s+use\s+only\b',
            r'\bcopyright\b',              # Generic copyright marker
            r'©\s*\d{4}',                   # Copyright with year
            r'\ball\s+rights\s+reserved\b',
            # County recorder and filing stamps commonly found on first pages
            r'\belectronically\s+recorded\b',
            r'\bofficial\s+public\s+records\b',
            r'\bcounty\s+clerk\b',
            r'\bafter\s+recording\s+please\s+return\b',
            r'\bpost\s+oak\s+blvd\b',
            r'\broberts\s+markel\s+weinberg\s+butler\s+hailey\b',
            r'\bpages:\s*fee:\b',
        ]
        
        # Full-line recorder/stamp patterns to DROP entirely (not just substring removal)
        self.recorder_line_patterns = [
            # Docket + date/time + county/clerk/record
            r'^\s*\d{6,}\b.*\b\d{1,2}/\d{1,2}/\d{2,4}\b.*\b(county|clerk|record)\b',
            # Known county/official markers
            r'\bFort\s+Bend\s+County\b',
            r'\bLaura\s+Richard\b',
            # Fee stamp lines
            r'\bPages?\s*:\s*Fee\b',
            # Title line combined with recorder/stamp artifacts
            r'\bBYLAWS\s+OF\s+THE\b.*\bASSOCIATION\b.*(county|clerk|record|pages?\s*:\s*fee|electronically|official)',
        ]
        
        self.ocr_artifacts = [
            r'[|]{2,}',  # Multiple pipes from table borders
            r'[_\s]{3,}',  # Underscore lines
            r'[•●○▪▫]',  # Bullet points that might be OCR artifacts
        ]

        self.whitespace_patterns = [
            r'\n\s*\n\s*\n+',  # Multiple newlines
            r'[ \t]+',  # Multiple spaces/tabs
            r'^\s+',  # Leading whitespace per line
            r'\s+$',  # Trailing whitespace per line
        ]

    def clean_document_text(self, text: str) -> str:
        """
        Clean document text for LLM processing.

        Args:
            text: Raw document text

        Returns:
            Cleaned and normalized text
        """
        if not text or not isinstance(text, str):
            return ""

        try:
            # Start with the original text
            cleaned = text

            # Remove page breaks and page numbers
            for pattern in self.page_break_patterns:
                cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE | re.MULTILINE)

            # Remove common headers/footers inline; keep rest of the line
            lines = cleaned.split('\n')
            filtered_lines = []

            for line in lines:
                original_line = line
                tmp = original_line
                # Remove header/footer substrings but preserve other content
                for pattern in self.header_footer_patterns:
                    try:
                        tmp = re.sub(pattern, ' ', tmp, flags=re.IGNORECASE)
                    except re.error:
                        pass
                # Drop entire line if it matches recorder/stamp patterns
                try:
                    if any(re.search(p, tmp, flags=re.IGNORECASE) for p in self.recorder_line_patterns):
                        continue
                except re.error:
                    pass
                # Remove leftover multiple spaces
                tmp = re.sub(r'[ \t]{2,}', ' ', tmp)
                tmp = tmp.strip()

                # Drop lines that are now empty or contain no alphanumeric content
                if not tmp or not any(c.isalnum() for c in tmp):
                    continue
                # Drop isolated short numeric-only tokens (e.g., "13") stemming from page stamps
                if tmp.isdigit() and len(tmp) <= 3:
                    continue

                filtered_lines.append(tmp)

            cleaned = '\n'.join(filtered_lines)

            # Remove OCR artifacts
            for pattern in self.ocr_artifacts:
                cleaned = re.sub(pattern, ' ', cleaned)

            # Normalize whitespace
            for pattern in self.whitespace_patterns:
                if '\n' in pattern:
                    cleaned = re.sub(pattern, '\n\n', cleaned)
                else:
                    cleaned = re.sub(pattern, ' ', cleaned)

            # Final cleanup
            cleaned = cleaned.strip()

            # If cleaning removed most content, prefer empty/cleaned over noisy original
            if len(cleaned) < 10:
                logger.warning("Text cleaning resulted in very short content; returning cleaned text")
                return cleaned

            return cleaned

        except Exception as e:
            logger.error(f"Text cleaning failed: {e}")
            return text  # Return original on error

    def extract_sections(self, text: str) -> dict:
        """
        Extract document sections for better context.

        Args:
            text: Cleaned document text

        Returns:
            Dictionary of sections
        """
        sections = {}

        try:
            # Look for common section patterns
            section_patterns = [
                r'^(ARTICLE|SECTION|CHAPTER)\s+[IVXLCDM\d]+.*$',
                r'^\d+\.\s+[A-Z][^.!?]*$',
                r'^[A-Z][A-Z\s]{2,}[A-Z]$',  # ALL CAPS headers
            ]

            lines = text.split('\n')
            current_section = "Main Content"
            current_content = []

            for line in lines:
                line_stripped = line.strip()

                # Check if this looks like a section header
                is_header = False
                for pattern in section_patterns:
                    if re.match(pattern, line_stripped, re.IGNORECASE):
                        is_header = True
                        break

                if is_header and len(line_stripped) < 100:  # Reasonable header length
                    # Save previous section
                    if current_content:
                        sections[current_section] = '\n'.join(current_content).strip()
                        current_content = []

                    current_section = line_stripped
                else:
                    current_content.append(line)

            # Save final section
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()

            return sections

        except Exception as e:
            logger.error(f"Section extraction failed: {e}")
            return {"Full Text": text}

    def summarize_content(self, text: str, max_length: int = 500) -> str:
        """
        Create a summary of the content for context.

        Args:
            text: Document text
            max_length: Maximum summary length

        Returns:
            Content summary
        """
        try:
            if len(text) <= max_length:
                return text

            # Simple extractive summarization
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]

            # Take first and last sentences, plus middle ones if needed
            summary_parts = []

            if sentences:
                summary_parts.append(sentences[0])  # First sentence

                # Add middle sentences if we have room
                middle_start = max(1, len(sentences) // 3)
                middle_end = min(len(sentences) - 1, 2 * len(sentences) // 3)

                for i in range(middle_start, middle_end + 1):
                    if i < len(sentences):
                        summary_parts.append(sentences[i])

                # Add last sentence if different from first
                if len(sentences) > 1 and sentences[-1] != sentences[0]:
                    summary_parts.append(sentences[-1])

            summary = '. '.join(summary_parts)

            # Truncate if still too long
            if len(summary) > max_length:
                summary = summary[:max_length - 3] + "..."

            return summary

        except Exception as e:
            logger.error(f"Content summarization failed: {e}")
            return text[:max_length] + "..." if len(text) > max_length else text


# Global instance for convenience
_text_cleaner = DocumentTextCleaner()

def clean_document_text(text: str) -> str:
    """
    Convenience function to clean document text.

    Args:
        text: Raw document text

    Returns:
        Cleaned text
    """
    return _text_cleaner.clean_document_text(text)

def extract_document_sections(text: str) -> dict:
    """
    Convenience function to extract document sections.

    Args:
        text: Document text

    Returns:
        Dictionary of sections
    """
    return _text_cleaner.extract_sections(text)

def summarize_document_content(text: str, max_length: int = 500) -> str:
    """
    Convenience function to summarize document content.

    Args:
        text: Document text
        max_length: Maximum summary length

    Returns:
        Content summary
    """
    return _text_cleaner.summarize_content(text, max_length)

def is_noise_text(text: str) -> bool:
    """Heuristic to detect boilerplate or artifact lines/sentences.

    Returns True when the text is likely noise (copyright/footer/page markers,
    numeric-only stamps, very short or truncated fragments).
    """
    try:
        if not text or not isinstance(text, str):
            return True
        t = text.strip()
        if not t:
            return True
        tl = t.lower()
        # No alphabetic characters -> likely noise
        if not any(c.isalpha() for c in tl):
            return True
        # Common boilerplate and page markers
        noise_patterns = [
            r"\bcopyright\b",
            r"©\s*\d{4}",
            r"\ball\s+rights\s+reserved\b",
            r"\bpage\s+\d+\b",
            r"\bpage\s+\d+\s+of\s+\d+\b",
            r"\b\d{6,}\s+of\s+\d+\b",
            r"\.{3,}\s*\d+$",            # dotted leader ending with page number
            r"^\s*(section|article)\s+\d+[\w.\-]*\b.*$",  # bare section/article headers
            r"^\s*##+\s*[\dA-Za-z].*$",  # markdown headings
            r"^[IVXLCDM]+\s+[A-Z][A-Z\s,:;\-\.\d]+$",  # Roman numeral all-caps headings
        ]
        for pat in noise_patterns:
            if re.search(pat, tl, re.IGNORECASE):
                return True
        # Truncated-start heuristic: e.g., "rs", "bed"
        first = t.split()[0]
        if first and first.islower() and len(first) <= 3:
            return True
        # Overly short fragments
        if len(t) < 10:
            return True
        
        # Heuristic: heading/ToC-like lines without verbs
        # If line has no common verb and looks short-ish, treat as noise
        verb_re = re.compile(r"\b(is|are|shall|must|may|will|has|have|does|do|provide|provides|include|includes|appoint|appoints|elect|elects|vote|votes|conduct|conducts|comply|complies|adopt|adopts|keep|keeps|record|records|preside|presides|delegate|delegates|authorize|authorizes|determine|determines|manage|manages)\b", re.IGNORECASE)
        if not verb_re.search(t):
            # Consider TOC-like sequences: multiple short title segments separated by . or ; and no verbs
            if re.search(r"\.{3,}", t):
                return True
            # Multiple titled segments (., ;), no verbs
            segs = re.split(r"[.;]", t)
            segs = [s.strip() for s in segs if s.strip()]
            if len(segs) >= 2 and all(len(s.split()) <= 8 for s in segs):
                return True
            # Single short title-like line
            if len(t.split()) <= 8:
                return True
        
        # All-caps headings (no lowercase present), likely noise
        # Keep extremely short acronyms (<= 4 chars) but drop multi-word all-caps lines
        if not any(c.islower() for c in t) and any(c.isupper() for c in t):
            if len(t.split()) >= 2 and len(t) <= 120:
                return True
    except Exception:
        return False
    return False
=======
Text Cleaning Utility - With Improved Formatting
Removes PDF artifacts and adds proper paragraph breaks for readability.
"""

import re

def clean_document_text(text: str) -> str:
    """Clean raw text from documents and add proper formatting.

    - Removes page break markers like '--- Page X ---'
    - Removes obvious PDF headers (all-caps lines)
    - Adds paragraph breaks where appropriate
    - Normalizes whitespace
    - Preserves sentence structure and content
    """
    if not text:
        return ""

    # Remove page break markers
    cleaned_text = re.sub(r'\s*--- Page \d+ ---\s*', ' ', text, flags=re.IGNORECASE)

    # Split into lines to process headers
    lines = cleaned_text.split('\n')
    filtered_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Skip obvious PDF headers (all caps, short, no spaces or minimal spaces)
        if (len(line) > 10 and
            re.match(r'^[A-Z0-9\?\.\-]{15,}$', line) and
            line.count(' ') < 3 and
            not re.search(r'[a-z]', line)):  # No lowercase letters
            continue

        # Skip lines that are just numbers or very short all-caps
        if len(line) < 6 and re.match(r'^[A-Z0-9\s]+$', line):
            continue

        filtered_lines.append(line)

    cleaned_text = '\n'.join(filtered_lines)

    # Add paragraph breaks before sentences that start with uppercase letters
    # This helps break up long text blocks where paragraph breaks were lost
    cleaned_text = re.sub(r'([.!?])\s+([A-Z])', r'\1\n\n\2', cleaned_text)

    # Normalize whitespace (but preserve paragraph breaks)
    cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)  # Multiple spaces to single
    cleaned_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_text)  # Multiple newlines to double

    return cleaned_text.strip()

def test_cleaning():
    """Test the cleaning function"""
    test_text = """structuredpromptwithintheirownapplications,especiallythoseinvolvingAIandnaturallanguageprocessingtaskswherecontext-basedanswersarenecessary. 115
--- Page 116 ---
DOYOUSPEAKGENERATIVEAI?THEPROMPTENGINEERINGBEGINNER’SGUIDE PracticalApplications The"rag-prompt"isinvaluableinapplicationssuchascustomer
lytechnicalinitscommunication.ThisGPTisequippedtohandletaskslikewritingandoptimizingcode,implementingCSS,debugging,andtranslatingfeaturespecificationsintopracticalcodesolutions.Itprovidesprecise,technicalguidanceandcodeexamples,adheringtothelatestindustrystandardsandbestpractices. CodeMavenfocuseson
forstatemanagement,andtipsonminimizingre-renders. PracticalUsage CodeMavenisparticularlyusefulforexperienceddeveloperswhorequireadvanced,technicalassistancewithouttheneedforsimplifiedexplanations.Thissystemisadeptatnavigatingcomplexprojectrequirementsanddeliveringsolutionsthatarebothpracticalandalig
les.ThisGPTavoidsgeneralizationsorsimplisticexplanations,aiminginsteadtoprovidedetailed,technicalinsightssuitableforexperienceddevelopers.Itshouldnotofferadviceoutsidetherealmoffrontenddevelopmentanditsspecifiedtechnologies. 93
--- Page 94 ---
DOYOUSPEAKGENERATIVEAI?THEPROMPTENGINEERINGBEGINNER’SGUIDE
guages,whichenablesthemtoassistdevelopersbyautomatingcodingtasks.ThissectionexploresthepracticaluseofLLMsforgeneratingcodesnippets,whichcanimproveproductivityandaccuracyinsoftwaredevelopment. PromptDesign ExamplePrompt:/Asktheuserfortheirnameandsay"Hello"/ PromptExplanation:Thepromptisstructuredas"""

    print("=== BEFORE ===")
    print(repr(test_text))
    print("\n=== AFTER ===")
    cleaned = clean_document_text(test_text)
    print(repr(cleaned))
    print("\n=== FORMATTED ===")
    print(cleaned)

if __name__ == "__main__":
    test_cleaning()
>>>>>>> clean-master
