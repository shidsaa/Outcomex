"""
Main ML Detector Orchestrator

Coordinates multiple detector backends and provides a unified interface
for anomaly detection across different sensor types.
"""

import logging
import os
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import numpy as np

from .base import BaseDetector
from .zscore_detector import ZScoreDetector
from .stl_detector import STLDetector
from .lstm_detector import LSTMDetector

logger = logging.getLogger(__name__)

class MLDetector:
    """
    Main ML Detector orchestrator that manages multiple detector backends.
    
    This class provides a unified interface for anomaly detection using
    different ML approaches. It can automatically select the best detector
    based on data characteristics and fall back to simpler methods when needed.
    """
    
    # Available detector types
    DETECTOR_TYPES = {
        'zscore': ZScoreDetector,
        'stl': STLDetector,
        'lstm': LSTMDetector
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize ML Detector orchestrator.
        
        Args:
            config: Configuration dictionary with parameters:
                - default_detector: Default detector type (default: 'zscore')
                - auto_select: Auto-select best detector (default: True)
                - model_dir: Directory for saving models (default: './models')
                - min_data_for_advanced: Minimum data for advanced detectors (default: 200)
                - confidence_threshold: Minimum confidence for predictions (default: 0.5)
        """
        default_config = {
            'default_detector': 'zscore',
            'auto_select': True,
            'model_dir': './models',
            'min_data_for_advanced': 200,
            'confidence_threshold': 0.5,
            'enable_ensemble': False,
            'ensemble_weights': {'zscore': 0.3, 'stl': 0.4, 'lstm': 0.3}
        }
        
        if config:
            default_config.update(config)
            
        self.config = default_config
        self.detectors = {}
        self.sensor_configs = {}  # Per-sensor detector configurations
        self.ensemble_mode = self.config['enable_ensemble']
        
        # Initialize default detector
        self._initialize_detector(self.config['default_detector'])
        
        # Create model directory
        os.makedirs(self.config['model_dir'], exist_ok=True)
        
        logger.info(f"MLDetector initialized with config: {self.config}")
    
    def _initialize_detector(self, detector_type: str) -> bool:
        """Initialize a detector of the specified type."""
        try:
            if detector_type not in self.DETECTOR_TYPES:
                logger.error(f"Unknown detector type: {detector_type}")
                return False
                
            detector_class = self.DETECTOR_TYPES[detector_type]
            self.detectors[detector_type] = detector_class()
            logger.info(f"Initialized {detector_type} detector")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {detector_type} detector: {e}")
            return False
    
    def fit(self, sensor_id: str, readings: List[Dict[str, Any]], 
            detector_type: Optional[str] = None) -> bool:
        """
        Train detectors on historical data for a sensor.
        
        Args:
            sensor_id: Sensor identifier
            readings: List of reading dictionaries
            detector_type: Specific detector type to use (optional)
            
        Returns:
            True if training successful
        """
        try:
            if not readings:
                logger.warning(f"No readings provided for sensor {sensor_id}")
                return False
            
            # Auto-select detector if not specified
            if detector_type is None and self.config['auto_select']:
                detector_type = self._select_best_detector(sensor_id, readings)
            elif detector_type is None:
                detector_type = self.config['default_detector']
            
            # Initialize detector if not already done
            if detector_type not in self.detectors:
                if not self._initialize_detector(detector_type):
                    return False
            
            # Train the detector
            detector = self.detectors[detector_type]
            success = detector.fit(sensor_id, readings)
            
            if success:
                self.sensor_configs[sensor_id] = {
                    'detector_type': detector_type,
                    'trained_at': datetime.now().isoformat(),
                    'readings_count': len(readings)
                }
                
                # Save model
                model_path = os.path.join(self.config['model_dir'], f"{sensor_id}_{detector_type}")
                detector.save_model(sensor_id, model_path)
                
                logger.info(f"Trained {detector_type} detector for sensor {sensor_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Training failed for sensor {sensor_id}: {e}")
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
            # Check if we have a trained detector for this sensor
            if sensor_id not in self.sensor_configs:
                return self._fallback_prediction(reading, "No trained model")
            
            detector_type = self.sensor_configs[sensor_id]['detector_type']
            
            if detector_type not in self.detectors:
                # Try to load the model
                model_path = os.path.join(self.config['model_dir'], f"{sensor_id}_{detector_type}")
                if not self._load_detector_model(detector_type, sensor_id, model_path):
                    return self._fallback_prediction(reading, "Failed to load model")
            
            detector = self.detectors[detector_type]
            prediction = detector.predict(sensor_id, reading)
            
            # Apply confidence threshold
            if prediction['confidence'] < self.config['confidence_threshold']:
                prediction['category'] = 'normal'
                prediction['confidence'] = 0.1
            
            return prediction
            
        except Exception as e:
            logger.error(f"Prediction failed for sensor {sensor_id}: {e}")
            return self._fallback_prediction(reading, str(e))
    
    def predict_ensemble(self, sensor_id: str, reading: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make ensemble prediction using multiple detectors.
        
        Args:
            sensor_id: Sensor identifier
            reading: Reading dictionary
            
        Returns:
            Ensemble prediction results
        """
        if not self.ensemble_mode:
            return self.predict(sensor_id, reading)
        
        predictions = {}
        weights = self.config['ensemble_weights']
        
        # Get predictions from all available detectors
        for detector_type, detector in self.detectors.items():
            if detector_type in weights and sensor_id in detector.sensor_models:
                try:
                    pred = detector.predict(sensor_id, reading)
                    predictions[detector_type] = pred
                except Exception as e:
                    logger.warning(f"Ensemble prediction failed for {detector_type}: {e}")
        
        if not predictions:
            return self._fallback_prediction(reading, "No ensemble predictions available")
        
        # Combine predictions using weighted voting
        return self._combine_predictions(predictions, weights)
    
    def _select_best_detector(self, sensor_id: str, readings: List[Dict[str, Any]]) -> str:
        """
        Auto-select the best detector based on data characteristics.
        
        Args:
            sensor_id: Sensor identifier
            readings: Historical readings
            
        Returns:
            Selected detector type
        """
        if len(readings) < self.config['min_data_for_advanced']:
            return 'zscore'  # Fallback to simple detector
        
        # Extract time series data
        timestamps, values = self._extract_time_series(readings)
        
        # Analyze data characteristics
        data_stats = self._analyze_data_characteristics(values)
        
        # Select detector based on characteristics
        if data_stats['has_seasonality'] and len(values) >= 100:
            return 'stl'
        elif data_stats['complex_patterns'] and len(values) >= 200:
            return 'lstm'
        else:
            return 'zscore'
    
    def _analyze_data_characteristics(self, values: np.ndarray) -> Dict[str, Any]:
        """Analyze data characteristics to select appropriate detector."""
        stats = {
            'has_seasonality': False,
            'complex_patterns': False,
            'variance': np.var(values),
            'mean': np.mean(values)
        }
        
        # Simple seasonality detection (check for periodic patterns)
        if len(values) >= 50:
            # Calculate autocorrelation
            autocorr = np.correlate(values - np.mean(values), 
                                  values - np.mean(values), mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # Check for significant autocorrelation at different lags
            for lag in [5, 10, 20]:
                if lag < len(autocorr) and autocorr[lag] > 0.3 * autocorr[0]:
                    stats['has_seasonality'] = True
                    break
        
        # Complexity detection (high variance and non-linear patterns)
        if stats['variance'] > 0.1 * stats['mean']**2:
            stats['complex_patterns'] = True
        
        return stats
    
    def _extract_time_series(self, readings: List[Dict[str, Any]]) -> tuple:
        """Extract time series data from readings."""
        timestamps = []
        values = []
        
        for reading in readings:
            if isinstance(reading['timestamp'], str):
                ts = datetime.fromisoformat(reading['timestamp'].replace('Z', '+00:00'))
            else:
                ts = reading['timestamp']
                
            timestamps.append(ts)
            values.append(float(reading['value']))
            
        return np.array(timestamps), np.array(values)
    
    def _combine_predictions(self, predictions: Dict[str, Dict[str, Any]], 
                           weights: Dict[str, float]) -> Dict[str, Any]:
        """Combine multiple predictions using weighted voting."""
        # Category voting
        categories = {}
        total_confidence = 0
        total_anomaly_score = 0
        total_weight = 0
        
        for detector_type, pred in predictions.items():
            weight = weights.get(detector_type, 0.1)
            category = pred['category']
            
            if category not in categories:
                categories[category] = 0
            categories[category] += weight
            
            total_confidence += pred['confidence'] * weight
            total_anomaly_score += pred.get('anomaly_score', 0) * weight
            total_weight += weight
        
        # Select category with highest weight
        best_category = max(categories.items(), key=lambda x: x[1])[0]
        
        # Calculate weighted averages
        avg_confidence = total_confidence / total_weight if total_weight > 0 else 0
        avg_anomaly_score = total_anomaly_score / total_weight if total_weight > 0 else 0
        
        return {
            'category': best_category,
            'confidence': avg_confidence,
            'anomaly_score': avg_anomaly_score,
            'details': {
                'ensemble': True,
                'predictions': predictions,
                'weights': weights
            }
        }
    
    def _load_detector_model(self, detector_type: str, sensor_id: str, model_path: str) -> bool:
        """Load a trained model for a detector."""
        try:
            if detector_type not in self.detectors:
                if not self._initialize_detector(detector_type):
                    return False
            
            detector = self.detectors[detector_type]
            return detector.load_model(sensor_id, model_path)
            
        except Exception as e:
            logger.error(f"Failed to load model for {detector_type}: {e}")
            return False
    
    def _fallback_prediction(self, reading: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Fallback prediction when no model is available."""
        return {
            'category': 'normal',
            'confidence': 0.1,
            'anomaly_score': 0.0,
            'details': {
                'reason': reason,
                'fallback': True
            }
        }
    
    def get_sensor_info(self, sensor_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a trained sensor."""
        if sensor_id not in self.sensor_configs:
            return None
        
        config = self.sensor_configs[sensor_id]
        detector_type = config['detector_type']
        
        info = {
            'sensor_id': sensor_id,
            'detector_type': detector_type,
            'trained_at': config['trained_at'],
            'readings_count': config['readings_count']
        }
        
        # Add detector-specific info if available
        if detector_type in self.detectors:
            detector_info = self.detectors[detector_type].get_model_info(sensor_id)
            if detector_info:
                info['detector_info'] = detector_info
        
        return info
    
    def list_trained_sensors(self) -> List[str]:
        """List all sensors with trained models."""
        return list(self.sensor_configs.keys())
    
    def remove_sensor(self, sensor_id: str) -> bool:
        """Remove a trained sensor model."""
        try:
            if sensor_id not in self.sensor_configs:
                return False
            
            detector_type = self.sensor_configs[sensor_id]['detector_type']
            
            # Remove from detector
            if detector_type in self.detectors:
                if sensor_id in self.detectors[detector_type].sensor_models:
                    del self.detectors[detector_type].sensor_models[sensor_id]
            
            # Remove from config
            del self.sensor_configs[sensor_id]
            
            # Remove model files
            model_path = os.path.join(self.config['model_dir'], f"{sensor_id}_{detector_type}")
            for ext in ['', '_model.h5', '_scaler.pkl', '_threshold.pkl']:
                try:
                    os.remove(f"{model_path}{ext}")
                except FileNotFoundError:
                    pass
            
            logger.info(f"Removed model for sensor {sensor_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove sensor {sensor_id}: {e}")
            return False 