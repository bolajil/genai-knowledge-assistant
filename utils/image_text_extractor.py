"""
Image Text Extractor - OCR-based text extraction from images
Supports multiple OCR engines with fallback mechanisms
"""

import io
import logging
from typing import Tuple, Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import image processing libraries
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/Pillow not available. Install with: pip install pillow")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("Pytesseract not available. Install with: pip install pytesseract")

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("EasyOCR not available. Install with: pip install easyocr")


class ImageTextExtractor:
    """Extract text from images using OCR"""
    
    def __init__(self, preferred_engine: str = "tesseract"):
        """
        Initialize the image text extractor
        
        Args:
            preferred_engine: 'tesseract' or 'easyocr'
        """
        self.preferred_engine = preferred_engine
        self.easyocr_reader = None
        
        # Check availability
        if not PIL_AVAILABLE:
            raise RuntimeError("PIL/Pillow is required. Install with: pip install pillow")
        
        if preferred_engine == "tesseract" and not TESSERACT_AVAILABLE:
            logger.warning("Tesseract not available, will try EasyOCR")
            self.preferred_engine = "easyocr"
        
        if preferred_engine == "easyocr" and not EASYOCR_AVAILABLE:
            logger.warning("EasyOCR not available, will try Tesseract")
            self.preferred_engine = "tesseract"
    
    def _init_easyocr(self):
        """Lazy initialization of EasyOCR reader"""
        if self.easyocr_reader is None and EASYOCR_AVAILABLE:
            logger.info("Initializing EasyOCR reader...")
            self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
        return self.easyocr_reader
    
    def extract_with_tesseract(self, image: Image.Image) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text using Tesseract OCR
        
        Returns:
            Tuple of (extracted_text, metadata)
        """
        if not TESSERACT_AVAILABLE:
            raise RuntimeError("Tesseract not available")
        
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Extract text with explicit encoding handling
            try:
                text = pytesseract.image_to_string(image, config='--psm 3')
                # Clean up any encoding issues
                text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            except Exception as e:
                logger.warning(f"Tesseract string extraction error: {e}, trying with basic config")
                text = pytesseract.image_to_string(image)
                text = text.encode('ascii', errors='ignore').decode('ascii', errors='ignore')
            
            # Get additional data with error handling
            try:
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                
                # Calculate confidence
                confidences = [int(conf) for conf in data['conf'] if str(conf) != '-1' and str(conf).isdigit()]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                # Count words
                word_count = len([w for w in data['text'] if str(w).strip()])
                blocks = len(set(data['block_num']))
            except Exception as e:
                logger.warning(f"Could not get detailed OCR data: {e}")
                avg_confidence = 0
                word_count = len(text.split())
                blocks = 1
            
            metadata = {
                'method': 'tesseract',
                'confidence': avg_confidence,
                'word_count': word_count,
                'blocks': blocks
            }
            
            return text.strip(), metadata
        
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {e}")
            raise
    
    def extract_with_easyocr(self, image: Image.Image) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text using EasyOCR
        
        Returns:
            Tuple of (extracted_text, metadata)
        """
        if not EASYOCR_AVAILABLE:
            raise RuntimeError("EasyOCR not available")
        
        try:
            reader = self._init_easyocr()
            
            # Convert PIL Image to numpy array
            import numpy as np
            image_array = np.array(image)
            
            # Extract text with encoding handling
            results = reader.readtext(image_array)
            
            # Combine text and calculate average confidence
            text_parts = []
            confidences = []
            
            for (bbox, text, conf) in results:
                # Clean text encoding
                try:
                    clean_text = str(text).encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                    if clean_text.strip():
                        text_parts.append(clean_text)
                        confidences.append(conf)
                except Exception as e:
                    logger.warning(f"Error processing text part: {e}")
                    continue
            
            text = "\n".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            metadata = {
                'method': 'easyocr',
                'confidence': avg_confidence * 100,  # Convert to percentage
                'word_count': len(text.split()),
                'blocks': len(results)
            }
            
            return text.strip(), metadata
        
        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {e}")
            raise
    
    def extract_text_from_image(self, 
                                image_bytes: bytes, 
                                filename: str = "image") -> Tuple[str, str, Dict[str, Any]]:
        """
        Extract text from image bytes
        
        Args:
            image_bytes: Image file bytes
            filename: Original filename for reference
        
        Returns:
            Tuple of (extracted_text, method_used, metadata)
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Get image info
            image_info = {
                'format': image.format,
                'mode': image.mode,
                'size': image.size,
                'width': image.width,
                'height': image.height
            }
            
            logger.info(f"Processing image: {filename} ({image.width}x{image.height}, {image.format})")
            
            # Try preferred engine first
            text = None
            metadata = {}
            method = None
            
            if self.preferred_engine == "tesseract" and TESSERACT_AVAILABLE:
                try:
                    text, metadata = self.extract_with_tesseract(image)
                    method = "tesseract"
                except Exception as e:
                    logger.warning(f"Tesseract failed, trying EasyOCR: {e}")
                    if EASYOCR_AVAILABLE:
                        text, metadata = self.extract_with_easyocr(image)
                        method = "easyocr"
            
            elif self.preferred_engine == "easyocr" and EASYOCR_AVAILABLE:
                try:
                    text, metadata = self.extract_with_easyocr(image)
                    method = "easyocr"
                except Exception as e:
                    logger.warning(f"EasyOCR failed, trying Tesseract: {e}")
                    if TESSERACT_AVAILABLE:
                        text, metadata = self.extract_with_tesseract(image)
                        method = "tesseract"
            
            # If no text extracted
            if not text or not text.strip():
                text = f"[Image: {filename}] - No text detected"
                method = "none"
                metadata = {'method': 'none', 'confidence': 0, 'word_count': 0}
            
            # Add image info to metadata
            metadata.update(image_info)
            metadata['filename'] = filename
            
            return text, method, metadata
        
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return f"[Image: {filename}] - Error: {str(e)}", "error", {'error': str(e)}
    
    def validate_image(self, image_bytes: bytes) -> Tuple[bool, str]:
        """
        Validate if the file is a valid image
        
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.verify()
            return True, f"Valid {image.format} image"
        except Exception as e:
            return False, f"Invalid image: {str(e)}"
    
    def get_image_quality_score(self, image_bytes: bytes) -> float:
        """
        Estimate image quality for OCR (0.0 to 1.0)
        
        Factors:
        - Resolution (higher is better)
        - Contrast
        - Sharpness
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to grayscale for analysis
            if image.mode != 'L':
                gray = image.convert('L')
            else:
                gray = image
            
            import numpy as np
            img_array = np.array(gray)
            
            # Resolution score (0-1)
            min_size = min(image.width, image.height)
            resolution_score = min(min_size / 1000, 1.0)  # 1000px+ is ideal
            
            # Contrast score (0-1)
            contrast = img_array.std() / 128.0  # Normalize by half of 255
            contrast_score = min(contrast, 1.0)
            
            # Sharpness score (using Laplacian variance)
            try:
                from scipy import ndimage
                laplacian = ndimage.laplace(img_array)
                sharpness = laplacian.var()
                sharpness_score = min(sharpness / 1000, 1.0)  # Normalize
            except:
                sharpness_score = 0.5  # Default if scipy not available
            
            # Combined score
            quality_score = (resolution_score * 0.4 + 
                           contrast_score * 0.3 + 
                           sharpness_score * 0.3)
            
            return quality_score
        
        except Exception as e:
            logger.error(f"Error calculating image quality: {e}")
            return 0.5  # Default middle score


def extract_text_from_image_simple(image_bytes: bytes, 
                                   filename: str = "image",
                                   engine: str = "tesseract") -> Tuple[str, str]:
    """
    Simple function to extract text from image
    
    Args:
        image_bytes: Image file bytes
        filename: Original filename
        engine: 'tesseract' or 'easyocr'
    
    Returns:
        Tuple of (extracted_text, method_used)
    """
    extractor = ImageTextExtractor(preferred_engine=engine)
    text, method, metadata = extractor.extract_text_from_image(image_bytes, filename)
    return text, method


# Convenience function for backward compatibility
def extract_text_from_image(image_bytes: bytes, filename: str = "image") -> Tuple[str, str]:
    """Extract text from image using default settings"""
    return extract_text_from_image_simple(image_bytes, filename, engine="tesseract")
