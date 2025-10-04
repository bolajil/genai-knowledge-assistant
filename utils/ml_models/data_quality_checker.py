"""
Data Quality Checker using TensorFlow Autoencoder
Detects low-quality, corrupted, or anomalous documents
"""

import os
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# TensorFlow imports with fallback
try:
    import tensorflow as tf
    from tensorflow.keras import layers, models, callbacks
    TF_AVAILABLE = True
except ImportError:
    logger.warning("TensorFlow not available. Install with: pip install tensorflow")
    TF_AVAILABLE = False


class DataQualityChecker:
    """
    Detect data quality issues using autoencoder-based anomaly detection
    
    Detects:
    - Corrupted or garbled text
    - Low-quality OCR output
    - Duplicate or near-duplicate content
    - Outlier documents (very different from corpus)
    - Incomplete or truncated documents
    """
    
    def __init__(self,
                 embedding_dim: int = 384,
                 model_path: Optional[str] = None):
        """
        Initialize data quality checker
        
        Args:
            embedding_dim: Dimension of document embeddings
            model_path: Path to saved model
        """
        if not TF_AVAILABLE:
            raise ImportError("TensorFlow is required for DataQualityChecker")
        
        self.embedding_dim = embedding_dim
        self.model_path = model_path or "data/ml_models/data_quality_checker"
        self.latent_dim = 32  # Compressed representation dimension
        
        self.autoencoder = None
        self.encoder = None
        self.decoder = None
        self.threshold = None  # Anomaly detection threshold
        
        # Try to load existing model
        if Path(self.model_path).exists():
            self.load_model()
        else:
            logger.info("No pre-trained model found. Model will be built on first training.")
    
    def _build_autoencoder(self) -> Tuple[tf.keras.Model, tf.keras.Model, tf.keras.Model]:
        """
        Build autoencoder model
        
        Returns:
            Tuple of (autoencoder, encoder, decoder)
        """
        # Encoder
        encoder_input = layers.Input(shape=(self.embedding_dim,), name='encoder_input')
        x = layers.Dense(256, activation='relu', name='encoder_dense_1')(encoder_input)
        x = layers.BatchNormalization(name='encoder_bn_1')(x)
        x = layers.Dropout(0.2, name='encoder_dropout_1')(x)
        
        x = layers.Dense(128, activation='relu', name='encoder_dense_2')(x)
        x = layers.BatchNormalization(name='encoder_bn_2')(x)
        x = layers.Dropout(0.2, name='encoder_dropout_2')(x)
        
        x = layers.Dense(64, activation='relu', name='encoder_dense_3')(x)
        x = layers.BatchNormalization(name='encoder_bn_3')(x)
        
        # Latent space
        latent = layers.Dense(self.latent_dim, activation='relu', name='latent')(x)
        
        encoder = models.Model(encoder_input, latent, name='encoder')
        
        # Decoder
        decoder_input = layers.Input(shape=(self.latent_dim,), name='decoder_input')
        x = layers.Dense(64, activation='relu', name='decoder_dense_1')(decoder_input)
        x = layers.BatchNormalization(name='decoder_bn_1')(x)
        
        x = layers.Dense(128, activation='relu', name='decoder_dense_2')(x)
        x = layers.BatchNormalization(name='decoder_bn_2')(x)
        x = layers.Dropout(0.2, name='decoder_dropout_1')(x)
        
        x = layers.Dense(256, activation='relu', name='decoder_dense_3')(x)
        x = layers.BatchNormalization(name='decoder_bn_3')(x)
        x = layers.Dropout(0.2, name='decoder_dropout_2')(x)
        
        # Output
        decoder_output = layers.Dense(
            self.embedding_dim,
            activation='sigmoid',
            name='decoder_output'
        )(x)
        
        decoder = models.Model(decoder_input, decoder_output, name='decoder')
        
        # Autoencoder
        autoencoder_input = layers.Input(shape=(self.embedding_dim,), name='autoencoder_input')
        encoded = encoder(autoencoder_input)
        decoded = decoder(encoded)
        autoencoder = models.Model(autoencoder_input, decoded, name='autoencoder')
        
        # Compile
        autoencoder.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return autoencoder, encoder, decoder
    
    def train(self,
              embeddings: np.ndarray,
              validation_split: float = 0.2,
              epochs: int = 50,
              batch_size: int = 32,
              anomaly_percentile: float = 95.0) -> Dict:
        """
        Train the autoencoder on normal document embeddings
        
        Args:
            embeddings: Array of document embeddings (n_docs, embedding_dim)
            validation_split: Fraction for validation
            epochs: Number of training epochs
            batch_size: Batch size
            anomaly_percentile: Percentile for anomaly threshold
            
        Returns:
            Training history
        """
        logger.info(f"Training data quality checker on {len(embeddings)} documents")
        
        # Validate input
        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(f"Expected embedding_dim={self.embedding_dim}, got {embeddings.shape[1]}")
        
        # Normalize embeddings
        embeddings_normalized = self._normalize_embeddings(embeddings)
        
        # Build model
        self.autoencoder, self.encoder, self.decoder = self._build_autoencoder()
        
        # Callbacks
        early_stopping = callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        reduce_lr = callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=0.00001
        )
        
        # Train
        history = self.autoencoder.fit(
            embeddings_normalized,
            embeddings_normalized,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stopping, reduce_lr],
            verbose=1
        )
        
        # Calculate anomaly threshold
        reconstructions = self.autoencoder.predict(embeddings_normalized, verbose=0)
        reconstruction_errors = np.mean(np.square(embeddings_normalized - reconstructions), axis=1)
        self.threshold = np.percentile(reconstruction_errors, anomaly_percentile)
        
        logger.info(f"Training completed. Anomaly threshold: {self.threshold:.6f}")
        
        # Save model
        self.save_model()
        
        return history.history
    
    def check_quality(self, embedding: np.ndarray) -> Dict:
        """
        Check quality of a single document embedding
        
        Args:
            embedding: Document embedding vector
            
        Returns:
            Quality assessment with score and anomaly flag
        """
        if self.autoencoder is None:
            raise ValueError("Model not trained. Train or load a model first.")
        
        # Normalize
        embedding_normalized = self._normalize_embeddings(embedding.reshape(1, -1))
        
        # Reconstruct
        reconstruction = self.autoencoder.predict(embedding_normalized, verbose=0)
        
        # Calculate reconstruction error
        error = np.mean(np.square(embedding_normalized - reconstruction))
        
        # Quality score (inverse of error, normalized)
        quality_score = 1.0 / (1.0 + error)
        
        # Check if anomaly
        is_anomaly = error > self.threshold if self.threshold is not None else False
        
        # Determine quality level
        if quality_score > 0.9:
            quality_level = 'excellent'
        elif quality_score > 0.7:
            quality_level = 'good'
        elif quality_score > 0.5:
            quality_level = 'fair'
        else:
            quality_level = 'poor'
        
        return {
            'quality_score': float(quality_score),
            'reconstruction_error': float(error),
            'is_anomaly': bool(is_anomaly),
            'quality_level': quality_level,
            'threshold': float(self.threshold) if self.threshold is not None else None
        }
    
    def check_batch(self, embeddings: np.ndarray) -> List[Dict]:
        """Check quality of multiple document embeddings"""
        if self.autoencoder is None:
            raise ValueError("Model not trained. Train or load a model first.")
        
        # Normalize
        embeddings_normalized = self._normalize_embeddings(embeddings)
        
        # Reconstruct
        reconstructions = self.autoencoder.predict(embeddings_normalized, verbose=0)
        
        # Calculate errors
        errors = np.mean(np.square(embeddings_normalized - reconstructions), axis=1)
        
        # Process results
        results = []
        for error in errors:
            quality_score = 1.0 / (1.0 + error)
            is_anomaly = error > self.threshold if self.threshold is not None else False
            
            if quality_score > 0.9:
                quality_level = 'excellent'
            elif quality_score > 0.7:
                quality_level = 'good'
            elif quality_score > 0.5:
                quality_level = 'fair'
            else:
                quality_level = 'poor'
            
            results.append({
                'quality_score': float(quality_score),
                'reconstruction_error': float(error),
                'is_anomaly': bool(is_anomaly),
                'quality_level': quality_level
            })
        
        return results
    
    def detect_duplicates(self,
                         embeddings: np.ndarray,
                         similarity_threshold: float = 0.95) -> List[Tuple[int, int, float]]:
        """
        Detect near-duplicate documents using latent representations
        
        Args:
            embeddings: Document embeddings
            similarity_threshold: Cosine similarity threshold for duplicates
            
        Returns:
            List of (doc1_idx, doc2_idx, similarity) tuples
        """
        if self.encoder is None:
            raise ValueError("Model not trained. Train or load a model first.")
        
        # Get latent representations
        embeddings_normalized = self._normalize_embeddings(embeddings)
        latent_reps = self.encoder.predict(embeddings_normalized, verbose=0)
        
        # Calculate pairwise cosine similarities
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(latent_reps)
        
        # Find duplicates
        duplicates = []
        n = len(similarities)
        for i in range(n):
            for j in range(i + 1, n):
                if similarities[i, j] >= similarity_threshold:
                    duplicates.append((i, j, float(similarities[i, j])))
        
        return duplicates
    
    def _normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """Normalize embeddings to [0, 1] range"""
        # Min-max normalization
        min_val = embeddings.min(axis=1, keepdims=True)
        max_val = embeddings.max(axis=1, keepdims=True)
        
        # Avoid division by zero
        range_val = max_val - min_val
        range_val[range_val == 0] = 1
        
        normalized = (embeddings - min_val) / range_val
        return normalized
    
    def get_quality_report(self, embeddings: np.ndarray) -> Dict:
        """
        Generate comprehensive quality report for a corpus
        
        Args:
            embeddings: Document embeddings
            
        Returns:
            Quality report with statistics
        """
        results = self.check_batch(embeddings)
        duplicates = self.detect_duplicates(embeddings)
        
        quality_scores = [r['quality_score'] for r in results]
        anomaly_count = sum(1 for r in results if r['is_anomaly'])
        
        quality_distribution = {
            'excellent': sum(1 for r in results if r['quality_level'] == 'excellent'),
            'good': sum(1 for r in results if r['quality_level'] == 'good'),
            'fair': sum(1 for r in results if r['quality_level'] == 'fair'),
            'poor': sum(1 for r in results if r['quality_level'] == 'poor')
        }
        
        return {
            'total_documents': len(embeddings),
            'average_quality_score': float(np.mean(quality_scores)),
            'median_quality_score': float(np.median(quality_scores)),
            'std_quality_score': float(np.std(quality_scores)),
            'anomaly_count': anomaly_count,
            'anomaly_percentage': float(anomaly_count / len(embeddings) * 100),
            'duplicate_pairs': len(duplicates),
            'quality_distribution': quality_distribution,
            'recommendations': self._generate_recommendations(
                anomaly_count,
                len(duplicates),
                quality_distribution
            )
        }
    
    def _generate_recommendations(self,
                                 anomaly_count: int,
                                 duplicate_count: int,
                                 quality_dist: Dict) -> List[str]:
        """Generate recommendations based on quality analysis"""
        recommendations = []
        
        if anomaly_count > 0:
            recommendations.append(
                f"Found {anomaly_count} anomalous documents. Review for corruption or quality issues."
            )
        
        if duplicate_count > 0:
            recommendations.append(
                f"Found {duplicate_count} near-duplicate pairs. Consider deduplication."
            )
        
        if quality_dist['poor'] > 0:
            recommendations.append(
                f"{quality_dist['poor']} documents have poor quality. Review and potentially re-ingest."
            )
        
        if quality_dist['excellent'] + quality_dist['good'] < quality_dist['fair'] + quality_dist['poor']:
            recommendations.append(
                "Overall corpus quality is below optimal. Consider improving source documents or OCR process."
            )
        
        if not recommendations:
            recommendations.append("Corpus quality is good. No immediate actions required.")
        
        return recommendations
    
    def save_model(self):
        """Save autoencoder model and threshold"""
        if self.autoencoder is None:
            raise ValueError("No model to save")
        
        # Create directory
        Path(self.model_path).mkdir(parents=True, exist_ok=True)
        
        # Save models
        self.autoencoder.save(os.path.join(self.model_path, 'autoencoder.h5'))
        self.encoder.save(os.path.join(self.model_path, 'encoder.h5'))
        self.decoder.save(os.path.join(self.model_path, 'decoder.h5'))
        
        # Save threshold
        import json
        with open(os.path.join(self.model_path, 'config.json'), 'w') as f:
            json.dump({
                'threshold': float(self.threshold) if self.threshold is not None else None,
                'embedding_dim': self.embedding_dim,
                'latent_dim': self.latent_dim
            }, f)
        
        logger.info(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load saved autoencoder model and threshold"""
        try:
            # Load models
            self.autoencoder = tf.keras.models.load_model(
                os.path.join(self.model_path, 'autoencoder.h5')
            )
            self.encoder = tf.keras.models.load_model(
                os.path.join(self.model_path, 'encoder.h5')
            )
            self.decoder = tf.keras.models.load_model(
                os.path.join(self.model_path, 'decoder.h5')
            )
            
            # Load config
            import json
            with open(os.path.join(self.model_path, 'config.json'), 'r') as f:
                config = json.load(f)
                self.threshold = config['threshold']
                self.embedding_dim = config['embedding_dim']
                self.latent_dim = config['latent_dim']
            
            logger.info(f"Model loaded from {self.model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise


# Singleton instance
_checker_instance = None

def get_data_quality_checker(model_path: Optional[str] = None) -> DataQualityChecker:
    """Get or create singleton instance of DataQualityChecker"""
    global _checker_instance
    
    if _checker_instance is None:
        _checker_instance = DataQualityChecker(model_path=model_path)
    
    return _checker_instance
