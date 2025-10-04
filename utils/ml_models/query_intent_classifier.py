"""
Query Intent Classifier using TensorFlow
Classifies user queries into different intent categories for optimized retrieval
"""

import os
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# TensorFlow imports with fallback
try:
    import tensorflow as tf
    from tensorflow.keras import layers, models, callbacks
    from tensorflow.keras.preprocessing.text import Tokenizer
    from tensorflow.keras.preprocessing.sequence import pad_sequences
    TF_AVAILABLE = True
except ImportError:
    logger.warning("TensorFlow not available. Install with: pip install tensorflow")
    TF_AVAILABLE = False

class QueryIntentClassifier:
    """
    Classify query intent using TensorFlow LSTM model
    
    Intent Categories:
    - Factual: Needs precise, specific answer
    - Analytical: Needs reasoning and analysis
    - Procedural: Needs step-by-step instructions
    - Comparative: Needs comparison between items
    - Exploratory: Needs broad context and overview
    """
    
    INTENT_LABELS = [
        'factual',      # "What is X?", "When did Y happen?"
        'analytical',   # "Why does X happen?", "How does Y affect Z?"
        'procedural',   # "How to do X?", "Steps for Y?"
        'comparative',  # "Difference between X and Y?", "Compare A vs B"
        'exploratory'   # "Tell me about X", "Overview of Y"
    ]
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the query intent classifier
        
        Args:
            model_path: Path to saved model (if available)
        """
        if not TF_AVAILABLE:
            raise ImportError("TensorFlow is required for QueryIntentClassifier")
        
        self.model_path = model_path or "data/ml_models/query_intent_classifier"
        self.max_sequence_length = 50
        self.vocab_size = 10000
        self.embedding_dim = 128
        
        self.tokenizer = None
        self.model = None
        
        # Try to load existing model
        if Path(self.model_path).exists():
            self.load_model()
        else:
            logger.info("No pre-trained model found. Model will be built on first training.")
    
    def _build_model(self) -> tf.keras.Model:
        """Build the LSTM-based intent classification model"""
        model = models.Sequential([
            # Embedding layer
            layers.Embedding(
                input_dim=self.vocab_size,
                output_dim=self.embedding_dim,
                input_length=self.max_sequence_length,
                name='embedding'
            ),
            
            # Bidirectional LSTM layers
            layers.Bidirectional(
                layers.LSTM(64, return_sequences=True, dropout=0.2),
                name='bilstm_1'
            ),
            layers.Bidirectional(
                layers.LSTM(32, dropout=0.2),
                name='bilstm_2'
            ),
            
            # Dense layers
            layers.Dense(64, activation='relu', name='dense_1'),
            layers.Dropout(0.5, name='dropout'),
            layers.Dense(32, activation='relu', name='dense_2'),
            
            # Output layer
            layers.Dense(len(self.INTENT_LABELS), activation='softmax', name='output')
        ], name='query_intent_classifier')
        
        # Compile model
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss='categorical_crossentropy',
            metrics=['accuracy', tf.keras.metrics.Precision(), tf.keras.metrics.Recall()]
        )
        
        return model
    
    def _prepare_tokenizer(self, texts: List[str]):
        """Prepare tokenizer from training texts"""
        self.tokenizer = Tokenizer(num_words=self.vocab_size, oov_token='<OOV>')
        self.tokenizer.fit_on_texts(texts)
    
    def _preprocess_text(self, texts: List[str]) -> np.ndarray:
        """Convert texts to padded sequences"""
        if self.tokenizer is None:
            raise ValueError("Tokenizer not initialized. Train the model first.")
        
        sequences = self.tokenizer.texts_to_sequences(texts)
        padded = pad_sequences(
            sequences,
            maxlen=self.max_sequence_length,
            padding='post',
            truncating='post'
        )
        return padded
    
    def train(self,
              queries: List[str],
              labels: List[str],
              validation_split: float = 0.2,
              epochs: int = 20,
              batch_size: int = 32) -> Dict:
        """
        Train the intent classifier
        
        Args:
            queries: List of query texts
            labels: List of intent labels (must be in INTENT_LABELS)
            validation_split: Fraction of data for validation
            epochs: Number of training epochs
            batch_size: Batch size for training
            
        Returns:
            Training history dictionary
        """
        logger.info(f"Training intent classifier on {len(queries)} queries")
        
        # Validate labels
        invalid_labels = set(labels) - set(self.INTENT_LABELS)
        if invalid_labels:
            raise ValueError(f"Invalid labels: {invalid_labels}. Must be in {self.INTENT_LABELS}")
        
        # Prepare tokenizer
        self._prepare_tokenizer(queries)
        
        # Preprocess data
        X = self._preprocess_text(queries)
        
        # Convert labels to one-hot encoding
        label_to_idx = {label: idx for idx, label in enumerate(self.INTENT_LABELS)}
        y_indices = [label_to_idx[label] for label in labels]
        y = tf.keras.utils.to_categorical(y_indices, num_classes=len(self.INTENT_LABELS))
        
        # Build model
        self.model = self._build_model()
        
        # Callbacks
        early_stopping = callbacks.EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True
        )
        
        reduce_lr = callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=3,
            min_lr=0.00001
        )
        
        # Train model
        history = self.model.fit(
            X, y,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stopping, reduce_lr],
            verbose=1
        )
        
        # Save model
        self.save_model()
        
        logger.info("Training completed successfully")
        
        return history.history
    
    def classify_intent(self, query: str) -> Dict[str, any]:
        """
        Classify the intent of a query
        
        Args:
            query: Query text to classify
            
        Returns:
            Dictionary with intent, confidence, and all probabilities
        """
        if self.model is None:
            raise ValueError("Model not trained. Train or load a model first.")
        
        # Preprocess query
        X = self._preprocess_text([query])
        
        # Predict
        predictions = self.model.predict(X, verbose=0)[0]
        
        # Get top intent
        top_idx = np.argmax(predictions)
        top_intent = self.INTENT_LABELS[top_idx]
        confidence = float(predictions[top_idx])
        
        # Get all probabilities
        all_intents = {
            intent: float(prob)
            for intent, prob in zip(self.INTENT_LABELS, predictions)
        }
        
        return {
            'intent': top_intent,
            'confidence': confidence,
            'all_intents': all_intents,
            'query': query
        }
    
    def classify_batch(self, queries: List[str]) -> List[Dict[str, any]]:
        """Classify multiple queries at once"""
        if self.model is None:
            raise ValueError("Model not trained. Train or load a model first.")
        
        # Preprocess queries
        X = self._preprocess_text(queries)
        
        # Predict
        predictions = self.model.predict(X, verbose=0)
        
        results = []
        for query, preds in zip(queries, predictions):
            top_idx = np.argmax(preds)
            results.append({
                'intent': self.INTENT_LABELS[top_idx],
                'confidence': float(preds[top_idx]),
                'all_intents': {
                    intent: float(prob)
                    for intent, prob in zip(self.INTENT_LABELS, preds)
                },
                'query': query
            })
        
        return results
    
    def save_model(self):
        """Save model and tokenizer"""
        if self.model is None:
            raise ValueError("No model to save")
        
        # Create directory
        Path(self.model_path).mkdir(parents=True, exist_ok=True)
        
        # Save model
        self.model.save(os.path.join(self.model_path, 'model.h5'))
        
        # Save tokenizer
        import pickle
        with open(os.path.join(self.model_path, 'tokenizer.pkl'), 'wb') as f:
            pickle.dump(self.tokenizer, f)
        
        logger.info(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load saved model and tokenizer"""
        try:
            # Load model
            self.model = tf.keras.models.load_model(
                os.path.join(self.model_path, 'model.h5')
            )
            
            # Load tokenizer
            import pickle
            with open(os.path.join(self.model_path, 'tokenizer.pkl'), 'rb') as f:
                self.tokenizer = pickle.load(f)
            
            logger.info(f"Model loaded from {self.model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def get_retrieval_strategy(self, intent: str) -> Dict[str, any]:
        """
        Get recommended retrieval strategy based on intent
        
        Args:
            intent: Classified intent
            
        Returns:
            Retrieval strategy configuration
        """
        strategies = {
            'factual': {
                'search_type': 'precise',
                'top_k': 3,
                'use_reranking': True,
                'response_style': 'concise',
                'include_sources': True
            },
            'analytical': {
                'search_type': 'comprehensive',
                'top_k': 7,
                'use_reranking': True,
                'response_style': 'detailed_reasoning',
                'include_sources': True
            },
            'procedural': {
                'search_type': 'structured',
                'top_k': 5,
                'use_reranking': True,
                'response_style': 'step_by_step',
                'include_sources': True
            },
            'comparative': {
                'search_type': 'multi_aspect',
                'top_k': 10,
                'use_reranking': True,
                'response_style': 'comparative_analysis',
                'include_sources': True
            },
            'exploratory': {
                'search_type': 'broad',
                'top_k': 15,
                'use_reranking': False,
                'response_style': 'comprehensive_overview',
                'include_sources': True
            }
        }
        
        return strategies.get(intent, strategies['factual'])


# Singleton instance
_classifier_instance = None

def get_query_intent_classifier(model_path: Optional[str] = None) -> QueryIntentClassifier:
    """Get or create singleton instance of QueryIntentClassifier"""
    global _classifier_instance
    
    if _classifier_instance is None:
        _classifier_instance = QueryIntentClassifier(model_path)
    
    return _classifier_instance
