"""
Base Detector Class for ML-based Anomaly Detection

Defines the interface that all detector implementations must follow.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

class BaseDetector(ABC):
    """
    Abstract base class for all anomaly detectors.
    
    All detector implementations must inherit from this class and
    implement the required methods.
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the detector.
        
        Args:
            name: Name of the detector
            config: Configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self.is_trained = False
        self.sensor_models = {}  # Store trained models per sensor
        
    @abstractmethod
    def fit(self, sensor_id: str, readings: List[Dict[str, Any]]) -> bool:
        """
        Train the detector on historical data for a specific sensor.
        
        Args:
            sensor_id: Unique identifier for the sensor
            readings: List of reading dictionaries with 'timestamp', 'value' keys
            
        Returns:
            True if training was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def predict(self, sensor_id: str, reading: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict anomaly type for a new reading.
        
        Args:
            sensor_id: Unique identifier for the sensor
            reading: Dictionary with 'timestamp', 'value' keys
            
        Returns:
            Dictionary with prediction results:
            {
                'category': 'normal' | 'noise' | 'drift' | 'alert',
                'confidence': float (0.0 to 1.0),
                'anomaly_score': float,
                'details': Dict with additional info
            }
        """
        pass
    
    def validate_input(self, readings: List[Dict[str, Any]]) -> bool:
        """
        Validate input data format and values.
        
        Args:
            readings: List of reading dictionaries
            
        Returns:
            True if valid, False otherwise
        """
        if not readings:
            logger.warning(f"{self.name}: Empty readings list")
            return False
            
        for i, reading in enumerate(readings):
            if not isinstance(reading, dict):
                logger.error(f"{self.name}: Reading {i} is not a dictionary")
                return False
                
            if 'timestamp' not in reading or 'value' not in reading:
                logger.error(f"{self.name}: Reading {i} missing required keys")
                return False
                
            try:
                # Validate timestamp
                if isinstance(reading['timestamp'], str):
                    datetime.fromisoformat(reading['timestamp'].replace('Z', '+00:00'))
                elif not isinstance(reading['timestamp'], datetime):
                    logger.error(f"{self.name}: Invalid timestamp type in reading {i}")
                    return False
                    
                # Validate value
                value = float(reading['value'])
                if not np.isfinite(value):
                    logger.error(f"{self.name}: Non-finite value in reading {i}")
                    return False
                    
            except (ValueError, TypeError) as e:
                logger.error(f"{self.name}: Invalid data in reading {i}: {e}")
                return False
                
        return True
    
    def extract_time_series(self, readings: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract time series data from readings.
        
        Args:
            readings: List of reading dictionaries
            
        Returns:
            Tuple of (timestamps, values) as numpy arrays
        """
        timestamps = []
        values = []
        
        for reading in readings:
            # Convert timestamp to datetime if string
            if isinstance(reading['timestamp'], str):
                ts = datetime.fromisoformat(reading['timestamp'].replace('Z', '+00:00'))
            else:
                ts = reading['timestamp']
                
            timestamps.append(ts)
            values.append(float(reading['value']))
            
        return np.array(timestamps), np.array(values)
    
    def save_model(self, sensor_id: str, filepath: str) -> bool:
        """
        Save trained model for a sensor to disk.
        
        Args:
            sensor_id: Sensor identifier
            filepath: Path to save the model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if sensor_id not in self.sensor_models:
                logger.warning(f"{self.name}: No trained model found for sensor {sensor_id}")
                return False
                
            # Implementation specific to each detector
            return self._save_model_impl(sensor_id, filepath)
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to save model for sensor {sensor_id}: {e}")
            return False
    
    def load_model(self, sensor_id: str, filepath: str) -> bool:
        """
        Load trained model for a sensor from disk.
        
        Args:
            sensor_id: Sensor identifier
            filepath: Path to load the model from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Implementation specific to each detector
            success = self._load_model_impl(sensor_id, filepath)
            if success:
                self.sensor_models[sensor_id] = True  # Mark as loaded
                logger.info(f"{self.name}: Loaded model for sensor {sensor_id}")
            return success
            
        except Exception as e:
            logger.error(f"{self.name}: Failed to load model for sensor {sensor_id}: {e}")
            return False
    
    @abstractmethod
    def _save_model_impl(self, sensor_id: str, filepath: str) -> bool:
        """Implementation-specific model saving."""
        pass
    
    @abstractmethod
    def _load_model_impl(self, sensor_id: str, filepath: str) -> bool:
        """Implementation-specific model loading."""
        pass
    
    def get_model_info(self, sensor_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a trained model.
        
        Args:
            sensor_id: Sensor identifier
            
        Returns:
            Dictionary with model information or None if not found
        """
        if sensor_id not in self.sensor_models:
            return None
            
        return {
            'sensor_id': sensor_id,
            'detector_name': self.name,
            'is_trained': True,
            'config': self.config
        } 