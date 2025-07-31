import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from typing import Dict, List

logger = logging.getLogger(__name__)


def create_api_server(consumer):
    """Create and configure the FastAPI application for the consumer API."""
    app = FastAPI(title="SmartSensor Consumer API", version="1.0.0")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, We should specify our React app URL
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "consumer"}
    
    @app.get("/api/sensor-data")
    async def get_sensor_data(limit: int = 100, device_id: str = None, hours: int = None):
        # Try database first, fallback to memory
        if consumer.db.connected:
            data = consumer.db.get_recent_sensor_data(limit, device_id, hours)
        else:
            data = consumer.get_sensor_data(limit)
        
        return {
            "data": data,
            "count": len(data),
            "timestamp": datetime.now().isoformat(),
            "source": "database" if consumer.db.connected else "memory"
        }
    
    @app.get("/api/anomalies")
    async def get_anomalies(limit: int = 50, device_id: str = None):
        # Try database first, fallback to memory
        if consumer.db.connected:
            data = consumer.db.get_recent_anomalies(limit, device_id)
        else:
            data = consumer.get_anomalies(limit)
        
        return {
            "data": data,
            "count": len(data),
            "timestamp": datetime.now().isoformat(),
            "source": "database" if consumer.db.connected else "memory"
        }
    
    @app.get("/api/stats")
    async def get_stats():
        stats = consumer.get_stats()
        return {
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    
    @app.get("/api/metrics")
    async def get_metrics():
        """Compatible with existing API metrics endpoint"""
        stats = consumer.get_stats()
        return {
            "total_records_processed": stats['messages_processed'],
            "total_alerts_generated": stats['anomalies_detected'],
            "last_processing_time": datetime.now().isoformat(),
            "uptime": stats['uptime'],
            "processing_rate": stats['processing_rate'],
            "anomaly_rate": stats['anomaly_rate']
        }

    @app.get("/metrics")
    async def prometheus_metrics():
        """Prometheus-compatible metrics endpoint"""
        stats = consumer.get_stats()
        uptime_seconds = (datetime.now() - consumer.start_time).total_seconds()
        
        metrics = f"""# HELP smartsensor_messages_processed_total Total number of messages processed
# TYPE smartsensor_messages_processed_total counter
smartsensor_messages_processed_total {stats['messages_processed']}

# HELP smartsensor_anomalies_detected_total Total number of anomalies detected
# TYPE smartsensor_anomalies_detected_total counter
smartsensor_anomalies_detected_total {stats['anomalies_detected']}

# HELP smartsensor_uptime_seconds Service uptime in seconds
# TYPE smartsensor_uptime_seconds gauge
smartsensor_uptime_seconds {uptime_seconds}

# HELP smartsensor_processing_rate_messages_per_second Current processing rate
# TYPE smartsensor_processing_rate_messages_per_second gauge
smartsensor_processing_rate_messages_per_second {stats.get('processing_rate', 0)}

# HELP smartsensor_anomaly_rate_percentage Current anomaly detection rate
# TYPE smartsensor_anomaly_rate_percentage gauge
smartsensor_anomaly_rate_percentage {stats.get('anomaly_rate', 0)}

# HELP smartsensor_up Service health status
# TYPE smartsensor_up gauge
smartsensor_up 1
"""
        return PlainTextResponse(content=metrics)
    
    @app.get("/api/system-health")
    async def get_system_health():
        """Get current system health status based on recent anomalies"""
        try:
            # Get recent anomalies from database (last 5 minutes)
            if consumer.db.connected:
                recent_anomalies = consumer.db.get_recent_anomalies(100)
            else:
                recent_anomalies = consumer.get_anomalies(100)
            
            # Get recent sensor data to check if system is online
            if consumer.db.connected:
                recent_data = consumer.db.get_recent_sensor_data(10)
            else:
                recent_data = consumer.get_sensor_data(10)
            
            now = datetime.now()
            
            # Check if system is online (has data in last 60 seconds)
            is_online = False
            if recent_data:
                latest_timestamp = datetime.fromisoformat(recent_data[-1]['timestamp'].replace('Z', '+00:00'))
                is_online = (now - latest_timestamp).total_seconds() < 60
            
            if not is_online:
                return {
                    "status": "offline",
                    "reason": "No recent data",
                    "last_data_timestamp": recent_data[-1]['timestamp'] if recent_data else None,
                    "critical_alerts": 0,
                    "warning_alerts": 0,
                    "total_alerts": 0
                }
            
            # Analyze recent anomalies for health status
            critical_alerts = 0
            warning_alerts = 0
            
            for anomaly in recent_anomalies:
                anomaly_time = datetime.fromisoformat(anomaly['timestamp'].replace('Z', '+00:00'))
                # Only consider anomalies from last 5 minutes
                if (now - anomaly_time).total_seconds() < 300:
                    if anomaly.get('severity') == 'critical':
                        critical_alerts += 1
                    elif anomaly.get('severity') == 'medium':
                        warning_alerts += 1
            
            # Determine health status
            if critical_alerts > 0:
                status = "critical"
                reason = f"{critical_alerts} critical alerts in last 5 minutes"
            elif warning_alerts > 0:
                status = "warning"
                reason = f"{warning_alerts} warning alerts in last 5 minutes"
            else:
                status = "normal"
                reason = "No recent alerts"
            
            # Get stats for data rate
            stats = consumer.get_stats()
            
            return {
                "status": status,
                "reason": reason,
                "last_data_timestamp": recent_data[-1]['timestamp'] if recent_data else None,
                "critical_alerts": critical_alerts,
                "warning_alerts": warning_alerts,
                "total_alerts": critical_alerts + warning_alerts,
                "data_rate_per_minute": round(stats['processing_rate'] * 60, 1) if 'processing_rate' in stats else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                "status": "unknown",
                "reason": f"Error: {str(e)}",
                "critical_alerts": 0,
                "warning_alerts": 0,
                "total_alerts": 0
            }
    
    return app 