import logging
import asyncio
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

class DatabaseManager:    
    def __init__(self):
        self.engine = None
        self.async_engine = None
        self.session_factory = None
        
    async def initialize(self):
        try:
            db_host = os.getenv("DB_HOST", "postgres")
            db_port = int(os.getenv("DB_PORT", "5432"))
            db_name = os.getenv("DB_NAME", "smartsensor")
            db_user = os.getenv("DB_USER", "admin")
            db_password = os.getenv("DB_PASSWORD", "admin123")
            
            database_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            self.async_engine = create_async_engine(database_url, echo=False)
            
            sync_database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            self.engine = create_engine(sync_database_url, echo=False)
            
            async with self.async_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                
            logger.info("Database connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        if self.async_engine:
            await self.async_engine.dispose()
        if self.engine:
            self.engine.dispose()
        logger.info("Database connections closed")
    
    async def get_sensors_with_data(self, min_readings: int = None) -> List[str]:
        if min_readings is None:
            min_readings = int(os.getenv("MIN_TRAINING_DATA", "50"))
            
        try:
            async with self.async_engine.begin() as conn:
                query = """
                SELECT DISTINCT device_id 
                FROM sensor_data 
                GROUP BY device_id 
                HAVING COUNT(*) >= :min_readings
                ORDER BY device_id
                """
                result = await conn.execute(text(query), {"min_readings": min_readings})
                sensors = [row[0] for row in result.fetchall()]
                
            logger.info(f"Found {len(sensors)} sensors with sufficient data")
            return sensors
            
        except Exception as e:
            logger.error(f"Failed to get sensors with data: {e}")
            return []
    
    async def get_sensor_data(self, device_id: str, hours: int = 24, max_readings: int = None) -> List[Dict[str, Any]]:
        if max_readings is None:
            max_readings = int(os.getenv("MAX_TRAINING_DATA", "1000"))
            
        try:
            async with self.async_engine.begin() as conn:
                query = """
                SELECT timestamp, pm2_5, pm10, dBA, vibration
                FROM sensor_data 
                WHERE device_id = :device_id 
                AND timestamp >= NOW() - INTERVAL '24 hours'
                ORDER BY timestamp DESC 
                LIMIT :max_readings
                """
                result = await conn.execute(text(query), {"device_id": device_id, "max_readings": max_readings})
                rows = result.fetchall()
                
                # Convert to list of dictionaries
                data = []
                for row in rows:
                    data.append({
                        'timestamp': row[0].isoformat(),
                        'pm2_5': float(row[1]) if row[1] is not None else 0.0,
                        'pm10': float(row[2]) if row[2] is not None else 0.0,
                        'dBA': float(row[3]) if row[3] is not None else 0.0,
                        'vibration': float(row[4]) if row[4] is not None else 0.0
                    })
                
            logger.info(f"Retrieved {len(data)} readings for sensor {device_id}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get sensor data for {device_id}: {e}")
            return []
    
    async def get_sensor_data_by_type(self, device_id: str, sensor_type: str, hours: int = 24, max_readings: int = None) -> List[Dict[str, Any]]:
        if max_readings is None:
            max_readings = int(os.getenv("MAX_TRAINING_DATA", "1000"))
            
        try:
            async with self.async_engine.begin() as conn:
                query = f"""
                SELECT timestamp, {sensor_type}
                FROM sensor_data 
                WHERE device_id = :device_id 
                AND {sensor_type} IS NOT NULL
                AND timestamp >= NOW() - INTERVAL '24 hours'
                ORDER BY timestamp DESC 
                LIMIT :max_readings
                """
                result = await conn.execute(text(query), {"device_id": device_id, "max_readings": max_readings})
                rows = result.fetchall()
                
                # Convert to list of dictionaries
                data = []
                for row in rows:
                    data.append({
                        'timestamp': row[0].isoformat(),
                        'value': float(row[1])
                    })
                
            logger.info(f"Retrieved {len(data)} {sensor_type} readings for sensor {device_id}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get {sensor_type} data for {device_id}: {e}")
            return []
    
    async def save_ml_anomaly(self, device_id: str, sensor_type: str, anomaly_data: Dict[str, Any]) -> bool:
        try:
            async with self.async_engine.begin() as conn:
                query = """
                INSERT INTO anomalies (
                    device_id, sensor_field, anomaly_type, value, threshold, 
                    severity, timestamp, llm_decision, ml_details
                ) VALUES (:device_id, :sensor_field, :anomaly_type, :value, :threshold, :severity, :timestamp, :llm_decision, :ml_details)
                """
                
                await conn.execute(text(query), {
                    "device_id": device_id,
                    "sensor_field": sensor_type,
                    "anomaly_type": 'ml_detection',
                    "value": anomaly_data.get('value', 0),
                    "threshold": anomaly_data.get('threshold', 0),
                    "severity": anomaly_data.get('severity', 'medium'),
                    "timestamp": datetime.now(),
                    "llm_decision": anomaly_data.get('reason', ''),
                    "ml_details": str(anomaly_data.get('details', {}))
                })
                
            logger.info(f"Saved ML anomaly for {device_id} {sensor_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save ML anomaly: {e}")
            return False
    
    async def get_model_metadata(self, device_id: str, sensor_type: str) -> Optional[Dict[str, Any]]:
        try:
            async with self.async_engine.begin() as conn:
                query = """
                SELECT model_type, trained_at, accuracy, last_updated
                FROM ml_models 
                WHERE device_id = :device_id AND sensor_type = :sensor_type
                ORDER BY trained_at DESC 
                LIMIT 1
                """
                result = await conn.execute(text(query), {"device_id": device_id, "sensor_type": sensor_type})
                row = result.fetchone()
                
                if row:
                    return {
                        'model_type': row[0],
                        'trained_at': row[1].isoformat() if row[1] else None,
                        'accuracy': float(row[2]) if row[2] else None,
                        'last_updated': row[3].isoformat() if row[3] else None
                    }
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to get model metadata: {e}")
            return None
    
    async def save_model_metadata(self, device_id: str, sensor_type: str, metadata: Dict[str, Any]) -> bool:
        try:
            async with self.async_engine.begin() as conn:
                query = """
                INSERT INTO ml_models (
                    device_id, sensor_type, model_type, trained_at, 
                    accuracy, config, last_updated
                ) VALUES (:device_id, :sensor_type, :model_type, :trained_at, :accuracy, :config, :last_updated)
                ON CONFLICT (device_id, sensor_type) 
                DO UPDATE SET 
                    model_type = EXCLUDED.model_type,
                    trained_at = EXCLUDED.trained_at,
                    accuracy = EXCLUDED.accuracy,
                    config = EXCLUDED.config,
                    last_updated = EXCLUDED.last_updated
                """
                
                await conn.execute(text(query), {
                    "device_id": device_id,
                    "sensor_type": sensor_type,
                    "model_type": metadata.get('model_type'),
                    "trained_at": datetime.now(),
                    "accuracy": metadata.get('accuracy'),
                    "config": str(metadata.get('config', {})),
                    "last_updated": datetime.now()
                })
                
            logger.info(f"Saved model metadata for {device_id} {sensor_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save model metadata: {e}")
            return False

db_manager = DatabaseManager()
