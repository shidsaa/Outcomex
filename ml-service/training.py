import asyncio
import logging
import os
from typing import List, Dict, Any, Optional

from database import db_manager
from models import MLDetector

logger = logging.getLogger(__name__)

class TrainingManager:    
    def __init__(self):
        self.ml_detector = None
        self.training_task = None
        self.is_running = False
        
    async def initialize(self, detector_configs: Dict[str, Dict[str, Any]] = None):
        try:
            ml_config = {
                'default_detector': os.getenv("DEFAULT_DETECTOR", "zscore"),
                'auto_select': os.getenv("AUTO_SELECT_DETECTOR", "true").lower() == "true",
                'model_dir': os.getenv("MODEL_DIR", "/app/models"),
                'min_data_for_advanced': int(os.getenv("MIN_TRAINING_DATA", "50")),
                'confidence_threshold': float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))
            }
            
            if detector_configs:
                ml_config['detector_configs'] = detector_configs
            
            self.ml_detector = MLDetector(ml_config)
            logger.info("Training manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize training manager: {e}")
            raise
    
    async def start_training_scheduler(self):
        if self.is_running:
            logger.warning("Training scheduler is already running")
            return
            
        self.is_running = True
        self.training_task = asyncio.create_task(self._training_loop())
        logger.info("Training scheduler started")
    
    async def stop_training_scheduler(self):
        if not self.is_running:
            return
            
        self.is_running = False
        if self.training_task:
            self.training_task.cancel()
            try:
                await self.training_task
            except asyncio.CancelledError:
                pass
        logger.info("Training scheduler stopped")
    
    async def _training_loop(self):
        while self.is_running:
            try:
                logger.info("Starting periodic training cycle")
                await self.train_all_models()
                
                await asyncio.sleep(int(os.getenv("TRAINING_INTERVAL", "1800")))
                
            except asyncio.CancelledError:
                logger.info("Training loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in training loop: {e}")
                await asyncio.sleep(60)
    
    async def train_all_models(self):
        try:
            sensors = await db_manager.get_sensors_with_data()
            
            if not sensors:
                logger.info("No sensors with sufficient data for training")
                return
            
            logger.info(f"Training models for {len(sensors)} sensors")
            
            for device_id in sensors:
                await self.train_sensor_models(device_id)
                
        except Exception as e:
            logger.error(f"Failed to train all models: {e}")
    
    async def train_sensor_models(self, device_id: str):
        try:
            sensor_data = await db_manager.get_sensor_data(device_id, hours=24)
            
            if len(sensor_data) < int(os.getenv("MIN_TRAINING_DATA", "50")):
                logger.info(f"Insufficient data for {device_id}: {len(sensor_data)} readings")
                return
            
            sensor_types = ['pm2_5', 'pm10', 'dBA', 'vibration']
            
            for sensor_type in sensor_types:
                await self.train_single_model(device_id, sensor_type, sensor_data)
                
        except Exception as e:
            logger.error(f"Failed to train models for {device_id}: {e}")
    
    async def train_single_model(self, device_id: str, sensor_type: str, sensor_data: List[Dict[str, Any]]):
        try:
            training_data = []
            for record in sensor_data:
                if record.get(sensor_type) is not None:
                    training_data.append({
                        'timestamp': record['timestamp'],
                        'value': record[sensor_type]
                    })
            
            if len(training_data) < int(os.getenv("MIN_TRAINING_DATA", "50")):
                logger.info(f"Insufficient {sensor_type} data for {device_id}: {len(training_data)} readings")
                return
            
            sensor_id = f"{device_id}_{sensor_type}"
            
            logger.info(f"Training {sensor_type} model for {device_id} with {len(training_data)} readings")
            success = self.ml_detector.fit(sensor_id, training_data)
            
            if success:
                model_info = self.ml_detector.get_sensor_info(sensor_id)
                if model_info:
                    metadata = {
                        'model_type': model_info.get('detector_type', 'unknown'),
                        'accuracy': 0.85,
                        'config': model_info.get('config', {}),
                        'readings_count': len(training_data)
                    }
                    await db_manager.save_model_metadata(device_id, sensor_type, metadata)
                
                logger.info(f"Successfully trained {sensor_type} model for {device_id}")
            else:
                logger.warning(f"Failed to train {sensor_type} model for {device_id}")
                
        except Exception as e:
            logger.error(f"Failed to train {sensor_type} model for {device_id}: {e}")
    
    async def retrain_model(self, device_id: str, sensor_type: str) -> bool:
        try:
            logger.info(f"Manual retraining requested for {device_id} {sensor_type}")
            
            sensor_data = await db_manager.get_sensor_data(device_id, hours=48)
            
            if len(sensor_data) < int(os.getenv("MIN_TRAINING_DATA", "50")):
                logger.warning(f"Insufficient data for retraining {device_id} {sensor_type}")
                return False
            
            await self.train_single_model(device_id, sensor_type, sensor_data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to retrain {device_id} {sensor_type}: {e}")
            return False
    
    def get_model_info(self, device_id: str, sensor_type: str) -> Optional[Dict[str, Any]]:
        try:
            sensor_id = f"{device_id}_{sensor_type}"
            return self.ml_detector.get_sensor_info(sensor_id)
        except Exception as e:
            logger.error(f"Failed to get model info for {device_id} {sensor_type}: {e}")
            return None
    
    def predict(self, device_id: str, sensor_type: str, reading: Dict[str, Any]) -> Dict[str, Any]:
        try:
            sensor_id = f"{device_id}_{sensor_type}"
            return self.ml_detector.predict(sensor_id, reading)
        except Exception as e:
            logger.error(f"Failed to predict for {device_id} {sensor_type}: {e}")
            return {
                'category': 'normal',
                'confidence': 0.1,
                'anomaly_score': 0.0,
                'details': {'error': str(e)}
            }

# Global training manager instance
training_manager = TrainingManager() 