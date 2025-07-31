import logging
import asyncio
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from database import db_manager
from training import training_manager

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "smartsensor")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8002"))
SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")

TRAINING_INTERVAL = int(os.getenv("TRAINING_INTERVAL", "1800"))
MIN_TRAINING_DATA = int(os.getenv("MIN_TRAINING_DATA", "50"))
MAX_TRAINING_DATA = int(os.getenv("MAX_TRAINING_DATA", "1000"))

MODEL_DIR = os.getenv("MODEL_DIR", "/app/models")
DEFAULT_DETECTOR = os.getenv("DEFAULT_DETECTOR", "zscore")
AUTO_SELECT_DETECTOR = os.getenv("AUTO_SELECT_DETECTOR", "true").lower() == "true"
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

DETECTOR_CONFIGS: Dict[str, Dict[str, Any]] = {
    "zscore": {
        "window_size": 50,
        "z_threshold": 3.0,
        "drift_threshold": 0.1,
        "noise_threshold": 0.05,
        "min_readings": 10
    },
    "stl": {
        "period": 24,
        "seasonal_window": 7,
        "trend_window": 21,
        "low_pass_window": 13,
        "residual_threshold": 2.0,
        "trend_threshold": 0.1,
        "min_readings": 100
    },
    "lstm": {
        "sequence_length": 50,
        "lstm_units": 50,
        "dropout_rate": 0.2,
        "learning_rate": 0.001,
        "epochs": 100,
        "batch_size": 32,
        "threshold_multiplier": 2.0,
        "min_readings": 200
    }
}

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Starting ML Service...")
        
        await db_manager.initialize()
        
        await training_manager.initialize(DETECTOR_CONFIGS)
        
        await training_manager.start_training_scheduler()
        
        logger.info("ML Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start ML Service: {e}")
        raise
    
    yield
    
    try:
        logger.info("Shutting down ML Service...")
        
        await training_manager.stop_training_scheduler()
        
        await db_manager.close()
        
        logger.info("ML Service shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

app = FastAPI(
    title="ML Service",
    description="Machine Learning Service for Environmental Sensor Anomaly Detection",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SensorReading(BaseModel):
    timestamp: str = Field(..., description="ISO timestamp")
    device_id: str = Field(..., description="Device identifier")
    pm2_5: Optional[float] = Field(None, description="PM2.5 reading")
    pm10: Optional[float] = Field(None, description="PM10 reading")
    dBA: Optional[float] = Field(None, description="dBA reading")
    vibration: Optional[float] = Field(None, description="Vibration reading")

class AnomalyResult(BaseModel):
    sensor_type: str
    category: str  # normal, noise, drift, alert
    confidence: float
    anomaly_score: float
    reason: str
    details: Dict[str, Any]

class DetectionResponse(BaseModel):
    anomalies: List[AnomalyResult]
    correlations: List[Dict[str, Any]] = []
    overall_assessment: str = "normal"
    overall_confidence: float = 0.0
    processing_time: float = 0.0

class ModelInfo(BaseModel):
    device_id: str
    sensor_type: str
    model_type: str
    trained_at: Optional[str] = None
    accuracy: Optional[float] = None
    readings_count: Optional[int] = None
    last_updated: Optional[str] = None

class ServiceStatus(BaseModel):
    status: str
    uptime: float
    models_trained: int
    last_training: Optional[str] = None
    next_training: Optional[str] = None
    database_connected: bool



@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ml-service"
    }

@app.post("/api/ml/detect", response_model=DetectionResponse)
async def detect_anomalies(reading: SensorReading):
    start_time = datetime.now()
    
    try:
        anomalies = []
        correlations = []
        
        sensor_types = ['pm2_5', 'pm10', 'dBA', 'vibration']
        
        for sensor_type in sensor_types:
            sensor_value = getattr(reading, sensor_type)
            
            if sensor_value is not None:
                sensor_reading = {
                    'timestamp': reading.timestamp,
                    'value': sensor_value
                }
                
                prediction = training_manager.predict(
                    reading.device_id, 
                    sensor_type, 
                    sensor_reading
                )
                
                anomaly = AnomalyResult(
                    sensor_type=sensor_type,
                    category=prediction['category'],
                    confidence=prediction['confidence'],
                    anomaly_score=prediction.get('anomaly_score', 0.0),
                    reason=prediction.get('details', {}).get('reason', f"ML analysis for {sensor_type}"),
                    details=prediction.get('details', {})
                )
                
                anomalies.append(anomaly)
                
                if prediction['category'] != 'normal' and prediction['confidence'] > CONFIDENCE_THRESHOLD:
                    await db_manager.save_ml_anomaly(
                        reading.device_id,
                        sensor_type,
                        {
                            'value': sensor_value,
                            'threshold': prediction.get('details', {}).get('threshold', 0),
                            'severity': prediction['category'],
                            'reason': anomaly.reason,
                            'details': prediction['details']
                        }
                    )
        
        correlations = await analyze_correlations(reading)
        
        overall_assessment, overall_confidence = calculate_overall_assessment(anomalies)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return DetectionResponse(
            anomalies=anomalies,
            correlations=correlations,
            overall_assessment=overall_assessment,
            overall_confidence=overall_confidence,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error in anomaly detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def analyze_correlations(reading: SensorReading) -> List[Dict[str, Any]]:
    correlations = []
    
    try:
        sensor_values = {
            'pm2_5': reading.pm2_5,
            'pm10': reading.pm10,
            'dBA': reading.dBA,
            'vibration': reading.vibration
        }
        
        if sensor_values['pm2_5'] and sensor_values['pm10']:
            if sensor_values['pm2_5'] > 50 and sensor_values['pm10'] > 100:
                correlations.append({
                    'type': 'cross_sensor',
                    'sensors': ['pm2_5', 'pm10'],
                    'correlation_score': 0.85,
                    'description': 'High correlation between PM2.5 and PM10 readings'
                })
        
        if sensor_values['dBA'] and sensor_values['vibration']:
            if sensor_values['dBA'] > 80 and sensor_values['vibration'] > 0.1:
                correlations.append({
                    'type': 'cross_sensor',
                    'sensors': ['dBA', 'vibration'],
                    'correlation_score': 0.75,
                    'description': 'High correlation between noise and vibration levels'
                })
        
    except Exception as e:
        logger.error(f"Error in correlation analysis: {e}")
    
    return correlations

def calculate_overall_assessment(anomalies: List[AnomalyResult]) -> tuple:
    if not anomalies:
        return "normal", 0.0
    
    alert_count = sum(1 for a in anomalies if a.category == 'alert')
    drift_count = sum(1 for a in anomalies if a.category == 'drift')
    noise_count = sum(1 for a in anomalies if a.category == 'noise')
    
    avg_confidence = sum(a.confidence for a in anomalies) / len(anomalies)
    
    if alert_count > 0:
        return "alert", avg_confidence
    elif drift_count > 0:
        return "drift", avg_confidence
    elif noise_count > 0:
        return "noise", avg_confidence
    else:
        return "normal", avg_confidence

@app.get("/api/ml/models/{device_id}", response_model=List[ModelInfo])
async def get_model_info(device_id: str):
    try:
        models = []
        sensor_types = ['pm2_5', 'pm10', 'dBA', 'vibration']
        
        for sensor_type in sensor_types:
            model_info = training_manager.get_model_info(device_id, sensor_type)
            
            metadata = await db_manager.get_model_metadata(device_id, sensor_type)
            
            if model_info or metadata:
                models.append(ModelInfo(
                    device_id=device_id,
                    sensor_type=sensor_type,
                    model_type=metadata.get('model_type') if metadata else 'unknown',
                    trained_at=metadata.get('trained_at') if metadata else None,
                    accuracy=metadata.get('accuracy') if metadata else None,
                    readings_count=metadata.get('readings_count') if metadata else None,
                    last_updated=metadata.get('last_updated') if metadata else None
                ))
        
        return models
        
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ml/retrain/{device_id}/{sensor_type}")
async def retrain_model(device_id: str, sensor_type: str, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(training_manager.retrain_model, device_id, sensor_type)
        
        return {
            "message": f"Retraining initiated for {device_id} {sensor_type}",
            "status": "scheduled"
        }
        
    except Exception as e:
        logger.error(f"Error scheduling retraining: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ml/status", response_model=ServiceStatus)
async def get_service_status():
    try:
        uptime = 3600
        
        models_trained = len(training_manager.ml_detector.sensor_configs) if training_manager.ml_detector else 0
        
        return ServiceStatus(
            status="running",
            uptime=uptime,
            models_trained=models_trained,
            last_training=datetime.now().isoformat(),
            next_training=datetime.now().isoformat(),
            database_connected=True
        )
        
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def prometheus_metrics():
    try:
        models_trained = len(training_manager.ml_detector.sensor_configs) if training_manager.ml_detector else 0
        
        uptime = 3600
        
        metrics = f"""# HELP ml_service_models_trained_total Total number of models trained
# TYPE ml_service_models_trained_total counter
ml_service_models_trained_total {models_trained}

# HELP ml_service_uptime_seconds Service uptime in seconds
# TYPE ml_service_uptime_seconds gauge
ml_service_uptime_seconds {uptime}

# HELP ml_service_up Service health status
# TYPE ml_service_up gauge
ml_service_up 1
"""
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=metrics)
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        error_metrics = f"""# HELP ml_service_up Service health status
# TYPE ml_service_up gauge
ml_service_up 0
"""
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=error_metrics)

@app.post("/api/ml/train/all")
async def train_all_models(background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(training_manager.train_all_models)
        
        return {
            "message": "Training initiated for all models",
            "status": "scheduled"
        }
        
    except Exception as e:
        logger.error(f"Error scheduling training: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=SERVICE_HOST,
        port=SERVICE_PORT,
        reload=True
    ) 