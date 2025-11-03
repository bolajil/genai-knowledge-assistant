"""
Document Quality Checker and Cleaner
Analyzes and improves document quality before ingestion
"""

import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """Represents a quality issue found in text"""
    type: str
    severity: str  # 'low', 'medium', 'high'
    description: str
    count: int
    examples: List[str]


class DocumentQualityChecker:
    """Checks and reports on document text quality"""
    
    def __init__(self):
        # Patterns for detecting issues
        self.concatenated_words_pattern = re.compile(r'\b[a-z]{15,}\b')  # Very long lowercase words
        self.missing_spaces_pattern = re.compile(r'[a-z][A-Z]')  # lowercase followed by uppercase
        self.repeated_chars_pattern = re.compile(r'(.)\1{4,}')  # Same char 5+ times
        self.special_chars_pattern = re.compile(r'[^\w\s\-.,;:!?()\[\]{}\'\"]+')
        
    def analyze_text(self, text: str) -> Dict:
        """
        Analyze text quality and return detailed report
        
        Returns:
            dict with quality_score (0-1), issues list, and statistics
        """
        if not text or len(text.strip()) == 0:
            return {
                'quality_score': 0.0,
                'issues': [],
                'stats': {},
                'recommendations': ['Document is empty']
            }
        
        issues = []
        
        # 1. Check for concatenated words (missing spaces)
        concatenated = self.concatenated_words_pattern.findall(text)
        if concatenated:
            issues.append(QualityIssue(
                type='concatenated_words',
                severity='high',
                description='Very long words detected (possible missing spaces)',
                count=len(concatenated),
                examples=concatenated[:5]
            ))
        
        # 2. Check for missing spaces between words
        missing_spaces = self.missing_spaces_pattern.findall(text)
        if missing_spaces:
            issues.append(QualityIssue(
                type='missing_spaces',
                severity='high',
                description='Missing spaces between words',
                count=len(missing_spaces),
                examples=[f"...{text[max(0, m.start()-5):m.end()+5]}..." 
                         for m in list(self.missing_spaces_pattern.finditer(text))[:5]]
            ))
        
        # 3. Check for repeated characters
        repeated = self.repeated_chars_pattern.findall(text)
        if repeated:
            issues.append(QualityIssue(
                type='repeated_chars',
                severity='medium',
                description='Repeated characters (possible OCR errors)',
                count=len(repeated),
                examples=repeated[:5]
            ))
        
        # 4. Check for excessive special characters
        special_chars = self.special_chars_pattern.findall(text)
        special_char_ratio = len(special_chars) / len(text) if text else 0
        if special_char_ratio > 0.05:  # More than 5% special chars
            issues.append(QualityIssue(
                type='special_chars',
                severity='medium',
                description='Excessive special characters',
                count=len(special_chars),
                examples=special_chars[:10]
            ))
        
        # 5. Check average word length
        words = text.split()
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
        if avg_word_length > 12:  # Unusually long average
            issues.append(QualityIssue(
                type='long_words',
                severity='medium',
                description=f'Unusually long average word length ({avg_word_length:.1f} chars)',
                count=1,
                examples=[]
            ))
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(text, issues)
        
        # Generate statistics
        stats = {
            'total_chars': len(text),
            'total_words': len(words),
            'avg_word_length': avg_word_length,
            'special_char_ratio': special_char_ratio,
            'line_count': text.count('\n') + 1
        }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(issues, quality_score)
        
        return {
            'quality_score': quality_score,
            'issues': issues,
            'stats': stats,
            'recommendations': recommendations
        }
    
    def _calculate_quality_score(self, text: str, issues: List[QualityIssue]) -> float:
        """Calculate overall quality score (0-1)"""
        if not text:
            return 0.0
        
        # Start with perfect score
        score = 1.0
        
        # Deduct points for each issue
        for issue in issues:
            if issue.severity == 'high':
                penalty = min(0.3, issue.count / len(text) * 10)
            elif issue.severity == 'medium':
                penalty = min(0.2, issue.count / len(text) * 5)
            else:
                penalty = min(0.1, issue.count / len(text) * 2)
            
            score -= penalty
        
        return max(0.0, score)
    
    def _generate_recommendations(self, issues: List[QualityIssue], score: float) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if score >= 0.8:
            recommendations.append("✅ Document quality is good - ready for ingestion")
        elif score >= 0.5:
            recommendations.append("⚠️ Document has some quality issues - consider cleaning")
        else:
            recommendations.append("❌ Document quality is poor - cleaning strongly recommended")
        
        for issue in issues:
            if issue.type == 'concatenated_words':
                recommendations.append("• Use 'Auto-Clean' to add spaces between concatenated words")
            elif issue.type == 'missing_spaces':
                recommendations.append("• Use 'Auto-Clean' to fix missing spaces")
            elif issue.type == 'repeated_chars':
                recommendations.append("• Use 'Auto-Clean' to remove repeated characters")
            elif issue.type == 'special_chars':
                recommendations.append("• Use 'Auto-Clean' to remove excessive special characters")
        
        if score < 0.5:
            recommendations.append("• Consider re-scanning the document with better OCR")
            recommendations.append("• Or manually review and edit the text")
        
        return list(set(recommendations))  # Remove duplicates


class DocumentCleaner:
    """Cleans and improves document text quality"""
    
    def __init__(self):
        pass
    
    def clean_text(self, text: str, aggressive: bool = False) -> Tuple[str, Dict]:
        """
        Clean text to improve quality
        
        Args:
            text: Input text
            aggressive: If True, apply more aggressive cleaning
            
        Returns:
            Tuple of (cleaned_text, changes_dict)
        """
        if not text:
            return text, {}
        
        original_text = text
        changes = {
            'spaces_added': 0,
            'repeated_chars_removed': 0,
            'special_chars_removed': 0,
            'words_split': 0
        }
        
        # 1. Fix missing spaces between lowercase and uppercase
        # "theQuick" -> "the Quick"
        def add_space(match):
            changes['spaces_added'] += 1
            return match.group(0)[0] + ' ' + match.group(0)[1]
        
        text = re.sub(r'([a-z])([A-Z])', add_space, text)
        
        # 2. Split very long words (likely concatenated)
        if aggressive:
            words = text.split()
            new_words = []
            for word in words:
                if len(word) > 20 and word.islower():
                    # Try to split at common boundaries
                    split_word = re.sub(r'([a-z])([A-Z])', r'\1 \2', word)
                    if split_word != word:
                        changes['words_split'] += 1
                    new_words.append(split_word)
                else:
                    new_words.append(word)
            text = ' '.join(new_words)
        
        # 3. Remove repeated characters (keep max 2)
        # "hellooooo" -> "helloo"
        def remove_repeats(match):
            changes['repeated_chars_removed'] += 1
            return match.group(1) * 2
        
        text = re.sub(r'(.)\1{3,}', remove_repeats, text)
        
        # 4. Remove excessive special characters
        if aggressive:
            # Keep only common punctuation
            before_len = len(text)
            text = re.sub(r'[^\w\s\-.,;:!?()\[\]{}\'\"]+', ' ', text)
            after_len = len(text)
            if before_len != after_len:
                changes['special_chars_removed'] = before_len - after_len
        
        # 5. Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # 6. Fix common OCR errors
        text = self._fix_common_ocr_errors(text)
        
        return text, changes
    
    def _fix_common_ocr_errors(self, text: str) -> str:
        """Fix common OCR misrecognitions"""
        # Common OCR mistakes
        replacements = {
            r'\b0\b': 'O',  # Zero to O
            r'\bl\b': 'I',  # lowercase l to I (in context)
            r'rn': 'm',     # rn often misread as m
            r'\|': 'I',     # pipe to I
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)
        
        return text
    
    def preview_cleaning(self, text: str, max_length: int = 500) -> Dict:
        """
        Preview what cleaning would do without applying it
        
        Returns:
            dict with before/after samples
        """
        cleaned, changes = self.clean_text(text)
        
        # Get sample sections
        sample_length = min(max_length, len(text))
        
        return {
            'before_sample': text[:sample_length],
            'after_sample': cleaned[:sample_length],
            'changes': changes,
            'total_chars_before': len(text),
            'total_chars_after': len(cleaned),
            'improvement': len(cleaned) / len(text) if text else 0
        }


# Convenience functions
def check_document_quality(text: str) -> Dict:
    """Quick quality check"""
    checker = DocumentQualityChecker()
    return checker.analyze_text(text)


def clean_document(text: str, aggressive: bool = False) -> Tuple[str, Dict]:
    """Quick document cleaning"""
    cleaner = DocumentCleaner()
    return cleaner.clean_text(text, aggressive)


def get_quality_emoji(score: float) -> str:
    """Get emoji for quality score"""
    if score >= 0.8:
        return "✅"
    elif score >= 0.5:
        return "⚠️"
    else:
        return "❌"


def get_quality_label(score: float) -> str:
    """Get label for quality score"""
    if score >= 0.8:
        return "Good"
    elif score >= 0.5:
        return "Fair"
    else:
        return "Poor"


if __name__ == "__main__":
    # Test
    test_text = """
    TheQuickBrownFoxJumpsOverTheLazyDog
    thisisaverylongwordwithoutanyspaces
    Hellooooooo World!!!!
    This is normal text.
    """
    
    print("=== Quality Check ===")
    result = check_document_quality(test_text)
    print(f"Quality Score: {result['quality_score']:.2f}")
    print(f"Issues: {len(result['issues'])}")
    for issue in result['issues']:
        print(f"  - {issue.description} ({issue.count} occurrences)")
    
    print("\n=== Cleaning ===")
    cleaned, changes = clean_document(test_text, aggressive=True)
    print(f"Changes: {changes}")
    print(f"Cleaned text:\n{cleaned}")
