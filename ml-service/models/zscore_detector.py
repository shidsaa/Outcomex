"""
Z-Score Based Anomaly Detector

Simple statistical fallback detector using Z-score analysis for outlier detection.
"""

import logging
import pickle
import os
from typing import Dict, List, Optional, Any
import numpy as np
from scipy import stats
from datetime import datetime, timedelta

from .base import BaseDetector

logger = logging.getLogger(__name__)

class ZScoreDetector(BaseDetector):
    """
    Z-Score based anomaly detector using statistical analysis.
    
    This detector uses rolling statistics to identify outliers and drifts
    in time series data. It's a lightweight fallback option that doesn't
    require heavy ML dependencies.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Z-Score detector.
        
        Args:
            config: Configuration dictionary with parameters:
                - window_size: Rolling window size (default: 50)
                - z_threshold: Z-score threshold for outliers (default: 3.0)
                - drift_threshold: Threshold for drift detection (default: 0.1)
                - noise_threshold: Threshold for noise detection (default: 0.05)
        """
        default_config = {
            'window_size': 50,
            'z_threshold': 3.0,
            'drift_threshold': 0.1,
            'noise_threshold': 0.05,
            'min_readings': 10
        }
        
        if config:
            default_config.update(config)
            
        super().__init__("ZScoreDetector", default_config)
        
        # Per-sensor statistics
        self.sensor_stats = {}
        
    def fit(self, sensor_id: str, readings: List[Dict[str, Any]]) -> bool:
        """
        Train the detector on historical data.
        
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
            
            # Calculate initial statistics
            mean_val = np.mean(values)
            std_val = np.std(values)
            
            # Store statistics for this sensor
            self.sensor_stats[sensor_id] = {
                'mean': mean_val,
                'std': std_val,
                'min': np.min(values),
                'max': np.max(values),
                'last_values': values[-self.config['window_size']:].tolist(),
                'last_timestamps': timestamps[-self.config['window_size']:].tolist(),
                'total_readings': len(values)
            }
            
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
            timestamp = reading['timestamp']
            
            # Get sensor statistics
            stats = self.sensor_stats[sensor_id]
            
            # Calculate Z-score
            z_score = abs((value - stats['mean']) / stats['std']) if stats['std'] > 0 else 0
            
            # Update rolling statistics
            self._update_stats(sensor_id, value, timestamp)
            
            # Determine category based on analysis
            category, confidence, details = self._classify_reading(
                sensor_id, value, z_score, stats
            )
            
            return {
                'category': category,
                'confidence': confidence,
                'anomaly_score': min(z_score / self.config['z_threshold'], 1.0),
                'details': details
            }
            
        except Exception as e:
            logger.error(f"{self.name}: Prediction failed for sensor {sensor_id}: {e}")
            return self._fallback_prediction(reading, str(e))
    
    def _update_stats(self, sensor_id: str, value: float, timestamp: Any):
        """Update rolling statistics for a sensor."""
        stats = self.sensor_stats[sensor_id]
        
        # Add new value to rolling window
        stats['last_values'].append(value)
        stats['last_timestamps'].append(timestamp)
        
        # Remove oldest value if window is full
        if len(stats['last_values']) > self.config['window_size']:
            stats['last_values'].pop(0)
            stats['last_timestamps'].pop(0)
        
        # Recalculate statistics
        values = np.array(stats['last_values'])
        stats['mean'] = np.mean(values)
        stats['std'] = np.std(values)
        stats['total_readings'] += 1
    
    def _classify_reading(self, sensor_id: str, value: float, z_score: float, 
                         stats: Dict[str, Any]) -> tuple:
        """
        Classify a reading into anomaly categories.
        
        Returns:
            Tuple of (category, confidence, details)
        """
        details = {
            'z_score': z_score,
            'mean': stats['mean'],
            'std': stats['std'],
            'value': value
        }
        
        # Check for extreme outliers (alerts)
        if z_score > self.config['z_threshold'] * 2:
            return 'alert', 0.9, details
        
        # Check for moderate outliers (noise)
        if z_score > self.config['z_threshold']:
            return 'noise', 0.7, details
        
        # Check for drift using rolling mean
        if len(stats['last_values']) >= 10:
            recent_mean = np.mean(stats['last_values'][-10:])
            historical_mean = stats['mean']
            drift_ratio = abs(recent_mean - historical_mean) / max(abs(historical_mean), 1e-6)
            
            if drift_ratio > self.config['drift_threshold']:
                details['drift_ratio'] = drift_ratio
                return 'drift', 0.6, details
        
        # Check for noise using variance
        if len(stats['last_values']) >= 5:
            recent_std = np.std(stats['last_values'][-5:])
            if recent_std > stats['std'] * (1 + self.config['noise_threshold']):
                details['noise_std'] = recent_std
                return 'noise', 0.5, details
        
        # Normal reading
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
            if sensor_id not in self.sensor_stats:
                return False
                
            model_data = {
                'sensor_stats': {sensor_id: self.sensor_stats[sensor_id]},
                'config': self.config
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
                
            logger.info(f"{self.name}: Saved model for sensor {sensor_id} to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to save model: {e}")
            return False
    
    def _load_model_impl(self, sensor_id: str, filepath: str) -> bool:
        """Load model from disk."""
        try:
            if not os.path.exists(filepath):
                return False
                
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            # Load sensor statistics
            if 'sensor_stats' in model_data and sensor_id in model_data['sensor_stats']:
                self.sensor_stats[sensor_id] = model_data['sensor_stats'][sensor_id]
            
            # Update config if provided
            if 'config' in model_data:
                self.config.update(model_data['config'])
                
            logger.info(f"{self.name}: Loaded model for sensor {sensor_id} from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to load model: {e}")
            return False 