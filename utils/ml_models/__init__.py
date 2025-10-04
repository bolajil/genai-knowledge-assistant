"""
VaultMind ML Models Package
Advanced machine learning models for enhanced document processing and retrieval
"""

# Import simple classifier (always available, no dependencies)
try:
    from .simple_intent_classifier import SimpleIntentClassifier, get_simple_intent_classifier
except Exception as e:
    SimpleIntentClassifier = None
    get_simple_intent_classifier = None

# TensorFlow/PyTorch models (optional, require dependencies)
QueryIntentClassifier = None
DocumentClassifier = None
DataQualityChecker = None

__all__ = [
    'SimpleIntentClassifier',
    'get_simple_intent_classifier',
]
