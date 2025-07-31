"""
STL (Seasonal-Trend-Loess) Decomposition Based Anomaly Detector

Uses STL decomposition to separate trend, seasonal, and residual components
for more sophisticated anomaly detection.
"""

import logging
import pickle
import os
from typing import Dict, List, Optional, Any
import numpy as np
from datetime import datetime, timedelta

try:
    from statsmodels.tsa.seasonal import STL
except ImportError:
    STL = None

from .base import BaseDetector

logger = logging.getLogger(__name__)

class STLDetector(BaseDetector):
    """
    STL decomposition based anomaly detector.
    
    This detector uses Seasonal-Trend decomposition to separate time series
    into trend, seasonal, and residual components for sophisticated anomaly
    detection. It's particularly good at detecting drifts and seasonal patterns.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize STL detector.
        
        Args:
            config: Configuration dictionary with parameters:
                - period: Seasonal period (default: 24 for hourly data)
                - seasonal_window: Seasonal smoothing window (default: 7)
                - trend_window: Trend smoothing window (default: 21)
                - low_pass_window: Low-pass filter window (default: 13)
                - residual_threshold: Threshold for residual anomalies (default: 2.0)
                - trend_threshold: Threshold for trend changes (default: 0.1)
                - min_readings: Minimum readings for training (default: 100)
        """
        if STL is None:
            raise ImportError("statsmodels is required for STLDetector. "
                            "Install with: pip install statsmodels")
        
        default_config = {
            'period': 24,  # Assuming hourly data
            'seasonal_window': 7,
            'trend_window': 25,  # Must be > period and odd
            'low_pass_window': 25,  # Must be > period and odd
            'residual_threshold': 2.0,
            'trend_threshold': 0.1,
            'min_readings': 100,
            'seasonal_periods': 2  # Minimum seasonal periods for training
        }
        
        if config:
            default_config.update(config)
            
        super().__init__("STLDetector", default_config)
        
        # Per-sensor models and statistics
        self.sensor_models = {}
        self.sensor_stats = {}
        
    def fit(self, sensor_id: str, readings: List[Dict[str, Any]]) -> bool:
        """
        Train the STL detector on historical data.
        
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
            
            # Ensure we have enough data for seasonal decomposition
            min_required = self.config['period'] * self.config['seasonal_periods']
            if len(values) < min_required:
                logger.warning(f"{self.name}: Insufficient data for seasonal decomposition "
                             f"({len(values)} < {min_required})")
                return False
            
            # Perform STL decomposition
            stl_result = self._perform_stl_decomposition(values)
            
            if stl_result is None:
                return False
            
            # Calculate statistics for each component
            trend_stats = self._calculate_component_stats(stl_result.trend)
            seasonal_stats = self._calculate_component_stats(stl_result.seasonal)
            residual_stats = self._calculate_component_stats(stl_result.resid)
            
            # Store model and statistics
            self.sensor_models[sensor_id] = {
                'stl_result': stl_result,
                'last_values': values[-self.config['period']:].tolist(),
                'last_timestamps': timestamps[-self.config['period']:].tolist(),
                'total_readings': len(values)
            }
            
            self.sensor_stats[sensor_id] = {
                'trend': trend_stats,
                'seasonal': seasonal_stats,
                'residual': residual_stats,
                'overall_mean': np.mean(values),
                'overall_std': np.std(values)
            }
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
            
            # Get sensor data
            model_data = self.sensor_models[sensor_id]
            stats = self.sensor_stats[sensor_id]
            
            # Update rolling window
            self._update_window(sensor_id, value, timestamp)
            
            # Perform analysis on updated data
            category, confidence, details = self._analyze_components(
                sensor_id, value, model_data, stats
            )
            
            return {
                'category': category,
                'confidence': confidence,
                'anomaly_score': details.get('anomaly_score', 0.0),
                'details': details
            }
            
        except Exception as e:
            logger.error(f"{self.name}: Prediction failed for sensor {sensor_id}: {e}")
            return self._fallback_prediction(reading, str(e))
    
    def _perform_stl_decomposition(self, values: np.ndarray):
        """Perform STL decomposition on time series data."""
        try:
            stl = STL(
                values,
                period=self.config['period'],
                seasonal=self.config['seasonal_window'],
                trend=self.config['trend_window'],
                low_pass=self.config['low_pass_window']
            )
            return stl.fit()
        except Exception as e:
            logger.error(f"{self.name}: STL decomposition failed: {e}")
            return None
    
    def _calculate_component_stats(self, component: np.ndarray) -> Dict[str, float]:
        """Calculate statistics for a component."""
        return {
            'mean': np.mean(component),
            'std': np.std(component),
            'min': np.min(component),
            'max': np.max(component),
            'range': np.max(component) - np.min(component)
        }
    
    def _update_window(self, sensor_id: str, value: float, timestamp: Any):
        """Update the rolling window with new data."""
        model_data = self.sensor_models[sensor_id]
        
        # Add new value
        model_data['last_values'].append(value)
        model_data['last_timestamps'].append(timestamp)
        
        # Remove oldest value if window is too large
        if len(model_data['last_values']) > self.config['period'] * 2:
            model_data['last_values'].pop(0)
            model_data['last_timestamps'].pop(0)
        
        model_data['total_readings'] += 1
    
    def _analyze_components(self, sensor_id: str, value: float, 
                          model_data: Dict[str, Any], stats: Dict[str, Any]) -> tuple:
        """
        Analyze STL components to determine anomaly type.
        
        Returns:
            Tuple of (category, confidence, details)
        """
        details = {
            'value': float(value),
            'overall_mean': float(stats['overall_mean']),
            'overall_std': float(stats['overall_std'])
        }
        
        # Get recent values for analysis
        recent_values = np.array(model_data['last_values'])
        
        # Check if we have enough data for analysis
        if len(recent_values) < self.config['period']:
            return 'normal', 0.5, details
        
        # Perform STL decomposition on recent data
        recent_stl = self._perform_stl_decomposition(recent_values)
        if recent_stl is None:
            return 'normal', 0.3, details
        
        # Analyze residual component for noise/outliers
        residual = recent_stl.resid[-1]  # Latest residual
        residual_stats = stats['residual']
        residual_z_score = abs((residual - residual_stats['mean']) / 
                              max(residual_stats['std'], 1e-6))
        
        details['residual'] = float(residual)
        details['residual_z_score'] = float(residual_z_score)
        
        # Check for extreme residuals (alerts)
        if residual_z_score > self.config['residual_threshold'] * 2:
            details['anomaly_score'] = min(residual_z_score / (self.config['residual_threshold'] * 2), 1.0)
            return 'alert', 0.9, details
        
        # Check for moderate residuals (noise)
        if residual_z_score > self.config['residual_threshold']:
            details['anomaly_score'] = min(residual_z_score / self.config['residual_threshold'], 1.0)
            return 'noise', 0.7, details
        
        # Analyze trend component for drift
        trend = recent_stl.trend
        if len(trend) >= 10:
            recent_trend = trend[-10:]
            trend_slope = np.polyfit(range(len(recent_trend)), recent_trend, 1)[0]
            trend_change = abs(trend_slope) / max(abs(np.mean(trend)), 1e-6)
            
            details['trend_slope'] = float(trend_slope)
            details['trend_change'] = float(trend_change)
            
            if trend_change > self.config['trend_threshold']:
                details['anomaly_score'] = min(trend_change / self.config['trend_threshold'], 1.0)
                return 'drift', 0.6, details
        
        # Check for seasonal anomalies
        seasonal = recent_stl.seasonal
        if len(seasonal) >= self.config['period']:
            current_seasonal = seasonal[-1]
            seasonal_stats = stats['seasonal']
            seasonal_z_score = abs((current_seasonal - seasonal_stats['mean']) / 
                                  max(seasonal_stats['std'], 1e-6))
            
            details['seasonal'] = float(current_seasonal)
            details['seasonal_z_score'] = float(seasonal_z_score)
            
            if seasonal_z_score > self.config['residual_threshold']:
                details['anomaly_score'] = min(seasonal_z_score / self.config['residual_threshold'], 1.0)
                return 'noise', 0.5, details
        
        # Normal reading
        details['anomaly_score'] = 0.0
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
            if sensor_id not in self.sensor_models:
                return False
                
            # STL results can't be pickled directly, so we save the data
            model_data = {
                'sensor_stats': {sensor_id: self.sensor_stats[sensor_id]},
                'config': self.config,
                'last_values': self.sensor_models[sensor_id]['last_values'],
                'last_timestamps': self.sensor_models[sensor_id]['last_timestamps'],
                'total_readings': self.sensor_models[sensor_id]['total_readings']
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
            
            # Reconstruct model data
            if 'last_values' in model_data:
                self.sensor_models[sensor_id] = {
                    'last_values': model_data['last_values'],
                    'last_timestamps': model_data['last_timestamps'],
                    'total_readings': model_data['total_readings']
                }
            
            # Update config if provided
            if 'config' in model_data:
                self.config.update(model_data['config'])
                
            logger.info(f"{self.name}: Loaded model for sensor {sensor_id} from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to load model: {e}")
            return False 