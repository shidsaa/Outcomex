"""
LSTM-based Anomaly Detector

Uses LSTM neural networks for time series forecasting and anomaly detection.
This detector can learn complex temporal patterns in sensor data.
"""

import logging
import pickle
import os
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from datetime import datetime, timedelta

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, load_model
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    from sklearn.preprocessing import MinMaxScaler
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

from .base import BaseDetector

logger = logging.getLogger(__name__)

class LSTMDetector(BaseDetector):
    """
    LSTM-based anomaly detector using neural networks.
    
    This detector uses LSTM networks to learn temporal patterns in sensor data
    and detect anomalies based on prediction errors. It's particularly good at
    detecting complex temporal anomalies and can learn seasonal patterns.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize LSTM detector.
        
        Args:
            config: Configuration dictionary with parameters:
                - sequence_length: Input sequence length (default: 50)
                - lstm_units: Number of LSTM units (default: 50)
                - dropout_rate: Dropout rate (default: 0.2)
                - learning_rate: Learning rate (default: 0.001)
                - epochs: Training epochs (default: 100)
                - batch_size: Batch size (default: 32)
                - threshold_multiplier: Anomaly threshold multiplier (default: 2.0)
                - min_readings: Minimum readings for training (default: 200)
        """
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow is required for LSTMDetector. "
                            "Install with: pip install tensorflow")
        
        default_config = {
            'sequence_length': 50,
            'lstm_units': 50,
            'dropout_rate': 0.2,
            'learning_rate': 0.001,
            'epochs': 100,
            'batch_size': 32,
            'threshold_multiplier': 2.0,
            'min_readings': 200,
            'validation_split': 0.2,
            'early_stopping_patience': 10
        }
        
        if config:
            default_config.update(config)
            
        super().__init__("LSTMDetector", default_config)
        
        # Per-sensor models and scalers
        self.models = {}
        self.scalers = {}
        self.thresholds = {}
        
    def fit(self, sensor_id: str, readings: List[Dict[str, Any]]) -> bool:
        """
        Train the LSTM detector on historical data.
        
        Args:
            sensor_id: Sensor identifier
            readings: List of reading dictionaries
            
        Returns:
            True if training successful
        """
        try:
            if not self.validate_input(readings):
                return False
                
            if len(readings) < self.config['min_readings']:
                logger.warning(f"{self.name}: Insufficient data for sensor {sensor_id} "
                             f"({len(readings)} < {self.config['min_readings']})")
                return False
                
            # Extract time series data
            timestamps, values = self.extract_time_series(readings)
            
            # Prepare data for LSTM
            X, y = self._prepare_sequences(values)
            
            if len(X) < 10:  # Need enough sequences for training
                logger.warning(f"{self.name}: Insufficient sequences for training")
                return False
            
            # Scale the data
            scaler = MinMaxScaler(feature_range=(0, 1))
            X_scaled = scaler.fit_transform(X.reshape(-1, 1)).reshape(X.shape)
            y_scaled = scaler.transform(y.reshape(-1, 1)).flatten()
            
            # Ensure proper shape for LSTM input
            if len(X_scaled.shape) != 3:
                X_scaled = X_scaled.reshape(X_scaled.shape[0], X_scaled.shape[1], 1)
            
            # Split into training and validation
            split_idx = int(len(X_scaled) * (1 - self.config['validation_split']))
            X_train, X_val = X_scaled[:split_idx], X_scaled[split_idx:]
            y_train, y_val = y_scaled[:split_idx], y_scaled[split_idx:]
            
            # Build and train the model
            model = self._build_model(self.config['sequence_length'])
            
            # Add early stopping
            early_stopping = tf.keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=self.config['early_stopping_patience'],
                restore_best_weights=True
            )
            
            # Train the model
            history = model.fit(
                X_train, y_train,
                epochs=self.config['epochs'],
                batch_size=self.config['batch_size'],
                validation_data=(X_val, y_val),
                callbacks=[early_stopping],
                verbose=0
            )
            
            # Calculate anomaly threshold
            y_pred = model.predict(X_scaled, verbose=0)
            y_pred_original = scaler.inverse_transform(y_pred.reshape(-1, 1)).flatten()
            y_original = scaler.inverse_transform(y_scaled.reshape(-1, 1)).flatten()
            
            errors = np.abs(y_original - y_pred_original)
            threshold = np.mean(errors) + self.config['threshold_multiplier'] * np.std(errors)
            
            # Store model and components
            self.models[sensor_id] = model
            self.scalers[sensor_id] = scaler
            self.thresholds[sensor_id] = threshold
            
            # Initialize rolling window with historical data
            if not hasattr(self, 'rolling_windows'):
                self.rolling_windows = {}
            self.rolling_windows[sensor_id] = values[-self.config['sequence_length']:].tolist()
            
            self.sensor_models[sensor_id] = True
            logger.info(f"{self.name}: Trained on {len(readings)} readings for sensor {sensor_id}")
            return True
            
        except Exception as e:
            logger.error(f"{self.name}: Training failed for sensor {sensor_id}: {e}")
            return False
    
    def predict(self, sensor_id: str, reading: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict anomaly type for a new reading.
        
        Args:
            sensor_id: Sensor identifier
            reading: Reading dictionary with timestamp and value
            
        Returns:
            Prediction results dictionary
        """
        try:
            if sensor_id not in self.sensor_models:
                return self._fallback_prediction(reading, "Model not trained")
                
            # Extract value
            value = float(reading['value'])
            
            # Get model components
            model = self.models[sensor_id]
            scaler = self.scalers[sensor_id]
            threshold = self.thresholds[sensor_id]
            
            # Get recent values for prediction
            recent_values = self._get_recent_values(sensor_id, value)
            
            if len(recent_values) < self.config['sequence_length']:
                return self._fallback_prediction(reading, "Insufficient recent data")
            
            # Prepare sequence for prediction
            sequence = np.array(recent_values[-self.config['sequence_length']:])
            sequence_scaled = scaler.transform(sequence.reshape(-1, 1))
            
            # Get the expected input shape from the model
            expected_shape = model.input_shape
            if expected_shape[1] != self.config['sequence_length']:
                # Adjust sequence length to match model's expected input
                if len(sequence_scaled) > expected_shape[1]:
                    sequence_scaled = sequence_scaled[-expected_shape[1]:]
                else:
                    # Pad with zeros if sequence is too short
                    padding = np.zeros((expected_shape[1] - len(sequence_scaled), 1))
                    sequence_scaled = np.vstack([padding, sequence_scaled])
            
            sequence_reshaped = sequence_scaled.reshape(1, -1, 1)
            
            # Make prediction
            prediction_scaled = model.predict(sequence_reshaped, verbose=0)
            prediction = scaler.inverse_transform(prediction_scaled)[0][0]
            
            # Calculate error
            error = abs(value - prediction)
            error_ratio = error / max(abs(prediction), 1e-6)
            
            # Determine category based on error
            category, confidence, details = self._classify_prediction(
                value, prediction, error, threshold, error_ratio
            )
            
            return {
                'category': category,
                'confidence': confidence,
                'anomaly_score': min(error / threshold, 1.0),
                'details': details
            }
            
        except Exception as e:
            logger.error(f"{self.name}: Prediction failed for sensor {sensor_id}: {e}")
            return self._fallback_prediction(reading, str(e))
    
    def _build_model(self, sequence_length: int) -> tf.keras.Model:
        """Build LSTM model architecture."""
        model = Sequential([
            LSTM(self.config['lstm_units'], 
                 return_sequences=True, 
                 input_shape=(sequence_length, 1)),
            Dropout(self.config['dropout_rate']),
            LSTM(self.config['lstm_units'] // 2, return_sequences=False),
            Dropout(self.config['dropout_rate']),
            Dense(25),
            Dense(1)
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=self.config['learning_rate']),
            loss='mse'
        )
        
        return model
    
    def _prepare_sequences(self, values: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare sequences for LSTM training."""
        X, y = [], []
        
        for i in range(len(values) - self.config['sequence_length']):
            X.append(values[i:i + self.config['sequence_length']])
            y.append(values[i + self.config['sequence_length']])
        
        return np.array(X), np.array(y)
    
    def _get_recent_values(self, sensor_id: str, current_value: float) -> List[float]:
        """Get recent values for prediction."""
        # Initialize rolling window if not exists
        if sensor_id not in self.sensor_models:
            return [current_value] * self.config['sequence_length']
        
        # Get the rolling window from the model data
        if hasattr(self, 'rolling_windows') and sensor_id in self.rolling_windows:
            window = self.rolling_windows[sensor_id]
            window.append(current_value)
            # Keep only the last sequence_length values
            if len(window) > self.config['sequence_length']:
                window = window[-self.config['sequence_length']:]
            self.rolling_windows[sensor_id] = window
            return window
        else:
            # Initialize rolling window
            if not hasattr(self, 'rolling_windows'):
                self.rolling_windows = {}
            self.rolling_windows[sensor_id] = [current_value] * self.config['sequence_length']
            return self.rolling_windows[sensor_id]
    
    def _classify_prediction(self, actual: float, predicted: float, error: float, 
                           threshold: float, error_ratio: float) -> tuple:
        """
        Classify prediction based on error analysis.
        
        Returns:
            Tuple of (category, confidence, details)
        """
        details = {
            'actual': float(actual),
            'predicted': float(predicted),
            'error': float(error),
            'threshold': float(threshold),
            'error_ratio': float(error_ratio)
        }
        
        # Extreme prediction error (alert)
        if error > threshold * 2:
            return 'alert', 0.9, details
        
        # High prediction error (noise)
        if error > threshold:
            return 'noise', 0.7, details
        
        # Moderate prediction error (potential drift)
        if error > threshold * 0.5:
            return 'drift', 0.5, details
        
        # Normal prediction
        return 'normal', 0.8, details
    
    def _fallback_prediction(self, reading: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Fallback prediction when model is not available."""
        return {
            'category': 'normal',
            'confidence': 0.1,
            'anomaly_score': 0.0,
            'details': {
                'reason': reason,
                'fallback': True
            }
        }
    
    def _save_model_impl(self, sensor_id: str, filepath: str) -> bool:
        """Save model to disk."""
        try:
            if sensor_id not in self.models:
                return False
                
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save model
            model_path = f"{filepath}_model.keras"
            self.models[sensor_id].save(model_path)
            
            # Save scaler and threshold
            scaler_path = f"{filepath}_scaler.pkl"
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scalers[sensor_id], f)
            
            threshold_path = f"{filepath}_threshold.pkl"
            with open(threshold_path, 'wb') as f:
                pickle.dump(self.thresholds[sensor_id], f)
                
            logger.info(f"{self.name}: Saved model for sensor {sensor_id} to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to save model: {e}")
            return False
    
    def _load_model_impl(self, sensor_id: str, filepath: str) -> bool:
        """Load model from disk."""
        try:
            # Load model
            model_path = f"{filepath}_model.keras"
            if not os.path.exists(model_path):
                return False
                
            self.models[sensor_id] = load_model(model_path)
            
            # Load scaler
            scaler_path = f"{filepath}_scaler.pkl"
            with open(scaler_path, 'rb') as f:
                self.scalers[sensor_id] = pickle.load(f)
            
            # Load threshold
            threshold_path = f"{filepath}_threshold.pkl"
            with open(threshold_path, 'rb') as f:
                self.thresholds[sensor_id] = pickle.load(f)
                
            logger.info(f"{self.name}: Loaded model for sensor {sensor_id} from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to load model: {e}")
            return False 