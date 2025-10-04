"""
Ingestion Validator
==================

Comprehensive validation pipeline for document ingestion.
Validates files, content quality, and metadata before processing.

P0 Critical Fix #2: Data Validation Pipeline
"""

from typing import Dict, Any, Tuple, List, Optional
import hashlib
import re
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Try to import python-magic for MIME type detection
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    logger.warning("python-magic not available. Install with: pip install python-magic-bin")


class IngestionValidator:
    """Validates documents before ingestion"""
    
    # File size limits (in bytes)
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    MIN_FILE_SIZE = 100  # 100 bytes
    
    # Content quality thresholds
    MIN_TEXT_LENGTH = 50
    MAX_SPECIAL_CHAR_RATIO = 0.3
    MIN_WORD_COUNT = 10
    
    # Allowed MIME types
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'text/plain',
        'text/html',
        'text/markdown',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/csv',
        'application/octet-stream'  # Fallback for some PDFs
    }
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        '.pdf', '.txt', '.html', '.htm', '.md', '.markdown', 
        '.docx', '.csv', '.json'
    }
    
    def __init__(self, enable_duplicate_check: bool = True):
        """
        Initialize validator
        
        Args:
            enable_duplicate_check: Enable duplicate detection (uses memory)
        """
        self.enable_duplicate_check = enable_duplicate_check
        self.duplicate_hashes = set() if enable_duplicate_check else None
        self.validation_stats = {
            'total_validated': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }
    
    def validate_file(self, 
                     file_path: Path,
                     file_content: bytes,
                     filename: str = None) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Comprehensive file validation
        
        Args:
            file_path: Path object for the file
            file_content: Raw file content as bytes
            filename: Optional filename override
            
        Returns:
            (is_valid, list_of_errors, validation_metadata)
        """
        errors = []
        metadata = {}
        
        self.validation_stats['total_validated'] += 1
        
        if filename is None:
            filename = file_path.name if isinstance(file_path, Path) else str(file_path)
        
        # 1. File size validation
        file_size = len(file_content)
        metadata['file_size'] = file_size
        
        if file_size > self.MAX_FILE_SIZE:
            errors.append(
                f"File too large: {file_size / 1024 / 1024:.2f}MB "
                f"(max: {self.MAX_FILE_SIZE / 1024 / 1024}MB)"
            )
        
        if file_size < self.MIN_FILE_SIZE:
            errors.append(
                f"File too small: {file_size} bytes "
                f"(min: {self.MIN_FILE_SIZE} bytes)"
            )
        
        # 2. File extension validation
        file_ext = Path(filename).suffix.lower()
        metadata['file_extension'] = file_ext
        
        if file_ext not in self.ALLOWED_EXTENSIONS:
            errors.append(
                f"Unsupported file extension: {file_ext}. "
                f"Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )
        
        # 3. MIME type validation (if magic is available)
        if MAGIC_AVAILABLE:
            try:
                mime = magic.from_buffer(file_content, mime=True)
                metadata['mime_type'] = mime
                
                if mime not in self.ALLOWED_MIME_TYPES:
                    # Don't fail, just warn for MIME type mismatches
                    logger.warning(f"Unexpected MIME type: {mime} for {filename}")
                    metadata['mime_type_warning'] = True
            except Exception as e:
                logger.error(f"Could not determine MIME type: {e}")
                metadata['mime_type'] = 'unknown'
        else:
            metadata['mime_type'] = 'not_checked'
        
        # 4. Duplicate detection
        if self.enable_duplicate_check:
            file_hash = hashlib.sha256(file_content).hexdigest()
            metadata['file_hash'] = file_hash[:16] + '...'
            
            if file_hash in self.duplicate_hashes:
                errors.append(
                    f"Duplicate file detected (hash: {file_hash[:16]}...)"
                )
            else:
                self.duplicate_hashes.add(file_hash)
        
        # 5. Malicious content scanning (basic)
        if self._contains_suspicious_patterns(file_content):
            errors.append("File contains suspicious patterns (potential security risk)")
        
        # 6. Filename validation
        if not self._is_valid_filename(filename):
            errors.append(
                f"Invalid filename: {filename}. "
                "Filename contains invalid characters or is too long."
            )
        
        # Update stats
        if errors:
            self.validation_stats['failed'] += 1
        else:
            self.validation_stats['passed'] += 1
        
        is_valid = len(errors) == 0
        return is_valid, errors, metadata
    
    def validate_text_quality(self, 
                             text: str,
                             filename: str = "unknown") -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate text content quality
        
        Args:
            text: Text content to validate
            filename: Source filename for logging
            
        Returns:
            (is_valid, list_of_warnings, quality_metrics)
        """
        warnings = []
        metrics = {}
        
        # 1. Length check
        text_length = len(text)
        metrics['text_length'] = text_length
        
        if text_length < self.MIN_TEXT_LENGTH:
            warnings.append(
                f"Text too short: {text_length} chars (min: {self.MIN_TEXT_LENGTH})"
            )
        
        # 2. Word count
        words = re.findall(r'\b\w+\b', text)
        word_count = len(words)
        metrics['word_count'] = word_count
        
        if word_count < self.MIN_WORD_COUNT:
            warnings.append(
                f"Too few words: {word_count} (min: {self.MIN_WORD_COUNT})"
            )
        
        # 3. Special character ratio
        special_chars = len(re.findall(r'[^a-zA-Z0-9\s]', text))
        special_char_ratio = special_chars / max(text_length, 1)
        metrics['special_char_ratio'] = round(special_char_ratio, 3)
        
        if special_char_ratio > self.MAX_SPECIAL_CHAR_RATIO:
            warnings.append(
                f"High special character ratio: {special_char_ratio:.2%} "
                f"(max: {self.MAX_SPECIAL_CHAR_RATIO:.2%})"
            )
        
        # 4. Language detection (basic ASCII check)
        ascii_chars = sum(1 for c in text if ord(c) < 128)
        ascii_ratio = ascii_chars / max(text_length, 1)
        metrics['ascii_ratio'] = round(ascii_ratio, 3)
        
        if ascii_ratio < 0.7:
            warnings.append(
                f"Low ASCII ratio: {ascii_ratio:.2%}. "
                "Text may contain non-English characters or encoding issues."
            )
        
        # 5. Readability check (average word length)
        if word_count > 0:
            avg_word_length = sum(len(w) for w in words) / word_count
            metrics['avg_word_length'] = round(avg_word_length, 2)
            
            if avg_word_length > 15:
                warnings.append(
                    f"Unusually long average word length: {avg_word_length:.1f}. "
                    "Content may be corrupted or contain encoded data."
                )
            elif avg_word_length < 2:
                warnings.append(
                    f"Unusually short average word length: {avg_word_length:.1f}. "
                    "Content may be fragmented."
                )
        else:
            metrics['avg_word_length'] = 0
        
        # 6. Line count and structure
        lines = text.split('\n')
        metrics['line_count'] = len(lines)
        metrics['avg_line_length'] = round(text_length / max(len(lines), 1), 2)
        
        # 7. Whitespace ratio
        whitespace_count = sum(1 for c in text if c.isspace())
        whitespace_ratio = whitespace_count / max(text_length, 1)
        metrics['whitespace_ratio'] = round(whitespace_ratio, 3)
        
        if whitespace_ratio > 0.5:
            warnings.append(
                f"High whitespace ratio: {whitespace_ratio:.2%}. "
                "Content may have formatting issues."
            )
        
        # 8. Quality score (0-100)
        quality_score = self._calculate_quality_score(metrics, warnings)
        metrics['quality_score'] = quality_score
        
        # Update stats
        if warnings:
            self.validation_stats['warnings'] += len(warnings)
        
        # Consider valid if quality score > 50
        is_valid = quality_score >= 50
        
        return is_valid, warnings, metrics
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate document metadata
        
        Args:
            metadata: Metadata dictionary to validate
            
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Required fields
        required_fields = ['filename', 'document_type', 'username']
        for field in required_fields:
            if field not in metadata or not metadata[field]:
                errors.append(f"Missing required metadata field: {field}")
        
        # Validate filename
        if 'filename' in metadata:
            filename = metadata['filename']
            if len(filename) > 255:
                errors.append("Filename too long (max: 255 chars)")
            
            if not self._is_valid_filename(filename):
                errors.append("Filename contains invalid characters")
        
        # Validate document_type
        if 'document_type' in metadata:
            valid_types = ['PDF', 'TEXT', 'URL', 'HTML', 'MARKDOWN', 'DOCX', 'CSV']
            if metadata['document_type'].upper() not in valid_types:
                errors.append(
                    f"Invalid document_type: {metadata['document_type']}. "
                    f"Must be one of: {', '.join(valid_types)}"
                )
        
        # Validate username
        if 'username' in metadata:
            username = metadata['username']
            if len(username) < 2 or len(username) > 50:
                errors.append("Username must be between 2 and 50 characters")
        
        return len(errors) == 0, errors
    
    def _contains_suspicious_patterns(self, content: bytes) -> bool:
        """Basic malicious content detection"""
        suspicious_patterns = [
            b'<script>',
            b'javascript:',
            b'eval(',
            b'exec(',
            b'__import__',
            b'<?php',
            b'<%',
            b'${',
        ]
        
        content_lower = content.lower()
        return any(pattern in content_lower for pattern in suspicious_patterns)
    
    def _is_valid_filename(self, filename: str) -> bool:
        """Validate filename for invalid characters"""
        if not filename or len(filename) > 255:
            return False
        
        # Check for invalid characters
        invalid_chars = r'[<>:"|?*\x00-\x1f]'
        if re.search(invalid_chars, filename):
            return False
        
        # Check for reserved names (Windows)
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            return False
        
        return True
    
    def _calculate_quality_score(self, metrics: Dict[str, Any], warnings: List[str]) -> int:
        """
        Calculate overall quality score (0-100)
        
        Args:
            metrics: Quality metrics dictionary
            warnings: List of warnings
            
        Returns:
            Quality score (0-100)
        """
        score = 100
        
        # Deduct points for warnings
        score -= len(warnings) * 10
        
        # Deduct for low word count
        word_count = metrics.get('word_count', 0)
        if word_count < 50:
            score -= 20
        elif word_count < 100:
            score -= 10
        
        # Deduct for high special char ratio
        special_ratio = metrics.get('special_char_ratio', 0)
        if special_ratio > 0.3:
            score -= 15
        
        # Deduct for low ASCII ratio
        ascii_ratio = metrics.get('ascii_ratio', 1.0)
        if ascii_ratio < 0.7:
            score -= 10
        
        # Ensure score is between 0 and 100
        return max(0, min(100, score))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return self.validation_stats.copy()
    
    def reset_stats(self):
        """Reset validation statistics"""
        self.validation_stats = {
            'total_validated': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }
    
    def clear_duplicate_cache(self):
        """Clear duplicate detection cache"""
        if self.duplicate_hashes is not None:
            self.duplicate_hashes.clear()


# Singleton instance
_validator_instance = None

def get_ingestion_validator(enable_duplicate_check: bool = True) -> IngestionValidator:
    """Get singleton validator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = IngestionValidator(enable_duplicate_check)
    return _validator_instance
