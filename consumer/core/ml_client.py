import logging
import asyncio
from typing import Dict, List, Any, Optional
import aiohttp

logger = logging.getLogger(__name__)

class MLClient:
    
    def __init__(self, ml_service_url: str = "http://ml-service:8002"):
        self.ml_service_url = ml_service_url
        self.client = None
        self.is_available = False
        
    async def initialize(self):
        try:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self.client = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=connector
            )
            
            await self.health_check()
            self.is_available = True
            logger.info(f"ML Service client initialized successfully: {self.ml_service_url}")
            
        except Exception as e:
            logger.warning(f"ML Service not available: {e}")
            self.is_available = False
    
    async def close(self):
        if self.client:
            await self.client.close()
            logger.info("ML Service client closed")
    
    async def health_check(self) -> bool:
        try:
            async with self.client.get(f"{self.ml_service_url}/health") as response:
                response.raise_for_status()
                return True
        except Exception as e:
            logger.debug(f"ML Service health check failed: {e}")
            return False
    
    async def detect_anomalies(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_available:
            return None
            
        try:
            payload = {
                "timestamp": record.get("timestamp"),
                "device_id": record.get("device_id"),
                "pm2_5": record.get("pm2_5"),
                "pm10": record.get("pm10"),
                "dBA": record.get("dBA"),
                "vibration": record.get("vibration")
            }
            
            # Create a new session for this request to avoid event loop issues
            connector = aiohttp.TCPConnector(limit=5, limit_per_host=2)
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                connector=connector
            ) as session:
                async with session.post(
                    f"{self.ml_service_url}/api/ml/detect",
                    json=payload
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    logger.debug(f"ML detection result: {result}")
                    return result
            
        except asyncio.TimeoutError:
            logger.warning("ML Service request timed out")
            return None
        except aiohttp.ClientResponseError as e:
            logger.error(f"ML Service HTTP error: {e.status}")
            return None
        except Exception as e:
            logger.error(f"ML Service request failed: {e}")
            return None
    
    async def get_model_info(self, device_id: str) -> Optional[List[Dict[str, Any]]]:
        if not self.is_available:
            return None
            
        try:
            connector = aiohttp.TCPConnector(limit=5, limit_per_host=2)
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5),
                connector=connector
            ) as session:
                async with session.get(
                    f"{self.ml_service_url}/api/ml/models/{device_id}"
                ) as response:
                    response.raise_for_status()
                    return await response.json()
            
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return None
    
    async def get_service_status(self) -> Optional[Dict[str, Any]]:
        if not self.is_available:
            return None
            
        try:
            connector = aiohttp.TCPConnector(limit=5, limit_per_host=2)
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5),
                connector=connector
            ) as session:
                async with session.get(
                    f"{self.ml_service_url}/api/ml/status"
                ) as response:
                    response.raise_for_status()
                    return await response.json()
            
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return None
    
    async def retrain_model(self, device_id: str, sensor_type: str) -> bool:
        if not self.is_available:
            return False
            
        try:
            connector = aiohttp.TCPConnector(limit=5, limit_per_host=2)
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5),
                connector=connector
            ) as session:
                async with session.post(
                    f"{self.ml_service_url}/api/ml/retrain/{device_id}/{sensor_type}"
                ) as response:
                    response.raise_for_status()
                    logger.info(f"Retraining requested for {device_id} {sensor_type}")
                    return True
            
        except Exception as e:
            logger.error(f"Failed to request retraining: {e}")
            return False

# Global ML client instance
ml_client = MLClient() 