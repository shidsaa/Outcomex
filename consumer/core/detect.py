import logging
from typing import Dict, List

try:
    from .ml_client import ml_client
    ML_CLIENT_AVAILABLE = True
except ImportError:
    ML_CLIENT_AVAILABLE = False

logger = logging.getLogger(__name__)

class ConsumerDetector:
    def __init__(self):
        #TODO: We can adjust the thresholds based on the environment or even per device
        self.sensor_thresholds = {
            "pm2_5": {"warning": 45, "critical": 70, "severe": 150},
            "pm10": {"warning": 80, "critical": 150, "severe": 300},
            "dBA": {"warning": 80, "critical": 95, "severe": 120},
            "vibration": {"warning": 0.3, "critical": 0.4, "severe": 0.5}
        }
        self.ml_client = ml_client


    def detect_basic_thresholds(self, record: Dict) -> List[Dict]:
        results = []
        
        for sensor_type, thresholds in self.sensor_thresholds.items():
            if sensor_type not in record:
                continue
        
            value = record[sensor_type]

        if value >= thresholds["severe"]:
                results.append({
                "type": "threshold",
                "severity": "critical",
                "reason": f"{sensor_type} reading {value} exceeds severe threshold {thresholds['severe']}",
                    "threshold": thresholds["severe"],
                    "detector": "consumer_basic"
                })
        elif value >= thresholds["critical"]:
                results.append({
                "type": "threshold",
                "severity": "high",
                "reason": f"{sensor_type} reading {value} exceeds critical threshold {thresholds['critical']}",
                    "threshold": thresholds["critical"],
                    "detector": "consumer_basic"
                })
        elif value >= thresholds["warning"]:
                results.append({
                "type": "threshold",
                "severity": "medium",
                "reason": f"{sensor_type} reading {value} exceeds warning threshold {thresholds['warning']}",
                    "threshold": thresholds["warning"],
                    "detector": "consumer_basic"
                })
        
        return results

    def validate_sensor_data(self, record: Dict) -> List[Dict]:
        results = []
        
        required_fields = ["timestamp", "device_id"]
        for field in required_fields:
            if field not in record:
                results.append({
                    "type": "validation",
                    "severity": "high",
                    "reason": f"Missing required field: {field}",
                    "detector": "consumer_basic"
                })
        
        for sensor_type in ["pm2_5", "pm10", "dBA", "vibration"]:
            if sensor_type in record:
                value = record[sensor_type]
                
                if sensor_type != "vibration" and value is not None and value < 0:
                    results.append({
                        "type": "validation",
                        "severity": "medium",
                        "reason": f"{sensor_type} has negative value: {value}",
                        "detector": "consumer_basic"
                    })
        
        return results

    async def detect_ml_anomalies(self, record: Dict) -> List[Dict]:
        if not self.ml_client:
            return []
        
        ml_anomalies = []
        
        try:
            ml_response = await self.ml_client.detect_anomalies(record)
        
            if ml_response and 'anomalies' in ml_response:
                for anomaly in ml_response['anomalies']:
                    if anomaly['category'] != 'normal':
                        severity_map = {
                            'alert': 'critical',
                            'drift': 'medium',
                            'noise': 'low'
                        }
                        
                        ml_anomalies.append({
                            "type": "ml_detection",
                            "severity": severity_map.get(anomaly['category'], 'medium'),
                            "reason": anomaly['reason'],
                            "confidence": anomaly['confidence'],
                            "anomaly_score": anomaly.get('anomaly_score', 0.0),
                            "sensor_type": anomaly['sensor_type'],
                            "detector": "ml_service",
                            "details": anomaly.get('details', {})
                        })
        
            # Add overall assessment if available
            if ml_response and ml_response.get('overall_assessment') != 'normal':
                ml_anomalies.append({
                    "type": "ml_overall",
                    "severity": "medium",
                    "reason": f"ML service overall assessment: {ml_response['overall_assessment']}",
                    "confidence": ml_response.get('overall_confidence', 0.0),
                    "detector": "ml_service"
                })
                
        except Exception as e:
            logger.error(f"ML detection failed: {e}")
        
        return ml_anomalies

    async def detect(self, record: Dict) -> List[Dict]:
        results = []
        device_id = record.get("device_id", "unknown")
        
        validation_results = self.validate_sensor_data(record)
        results.extend(validation_results)
        
        threshold_results = self.detect_basic_thresholds(record)
        results.extend(threshold_results)
            
        ml_results = await self.detect_ml_anomalies(record)
        results.extend(ml_results)
        
        if results:
            logger.info(f"Detected {len(results)} anomalies for device {device_id}")
            for result in results:
                logger.info(f"  - {result['type']}: {result['reason']} (severity: {result['severity']})")
        
        return results
