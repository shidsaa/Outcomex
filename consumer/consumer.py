import os
import json
import logging
import signal
import sys
import time
import threading
from datetime import datetime
from typing import Dict, List
from collections import deque
import pika
import uvicorn
from core.logger import configure_logging
from core.preprocess import Preprocessor
from core.detect import ConsumerDetector
from core.llm_support import LLMReasoner
from core.actions import ActionHandler
from core.database import DatabaseManager
from api_server import create_api_server
from dotenv import load_dotenv


load_dotenv()


configure_logging()
logger = logging.getLogger(__name__)

class SmartSensorConsumer:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.running = False
        
        self.rabbitmq_host = os.environ.get("RABBITMQ_HOST", "rabbitmq-service")
        self.rabbitmq_port = int(os.environ.get("RABBITMQ_PORT", "5672"))
        self.rabbitmq_user = os.environ.get("RABBITMQ_USER", "")
        self.rabbitmq_pass = os.environ.get("RABBITMQ_PASS", "")
        self.queue_name = os.environ.get("QUEUE_NAME", "sensor-data")
        
        self.preprocessor = Preprocessor()
        self.detector = ConsumerDetector()
        self.llm = LLMReasoner() if os.getenv("ENABLE_LLM", "true").lower() == "true" else None
        self.dispatcher = ActionHandler()
        
        self.messages_processed = 0
        self.anomalies_detected = 0
        self.start_time = datetime.now()
        
        self.recent_sensor_data = deque(maxlen=1000)  # Keep last 1000 records
        self.recent_anomalies = deque(maxlen=100)     # Keep last 100 anomalies

        self.db = DatabaseManager()
        
        try:
            from core.ml_client import ml_client
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(ml_client.initialize())
            loop.close()
            logger.info("ML Client initialized successfully")
        except Exception as e:
            logger.warning(f"ML Client not available: {e}")
        
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logger.info("SmartSensor Consumer initialized")
        
    def connect_rabbitmq(self):
        """Connect to RabbitMQ"""
        try:
            logger.info(f"Connecting to RabbitMQ at {self.rabbitmq_host}:{self.rabbitmq_port}")
            credentials = pika.PlainCredentials(self.rabbitmq_user, self.rabbitmq_pass)
            parameters = pika.ConnectionParameters(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare the queue to ensure it exists
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            logger.info(f"Successfully connected to RabbitMQ and declared queue '{self.queue_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def callback(self, ch, method, properties, body):
        """Process incoming messages with enhanced fault tolerance and clear flow"""
        try:
            record = json.loads(body)
            self.messages_processed += 1
            
            logger.debug(f"📥 INGEST: Processing message {self.messages_processed}: {record.get('device_id', 'unknown')}")
            
            cleaned = self.preprocessor.validate_and_normalize(record)
            if not cleaned:
                logger.warning(f"❌ PREPROCESS: Invalid record received: {record}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            logger.debug(f"✅ PREPROCESS: Record normalized for {cleaned['device_id']}")
            
            processed_record = {
                'device_id': cleaned['device_id'],
                'timestamp': cleaned['timestamp'],
                'pm2_5': cleaned.get('pm2_5', 0),
                'pm10': cleaned.get('pm10', 0),
                'dBA': cleaned.get('dBA', 0),
                'vibration': cleaned.get('vibration', 0),
                'processed_at': datetime.now().isoformat()
            }
            self.recent_sensor_data.append(processed_record)
            
            sensor_data_id = self.db.store_sensor_data(processed_record)
            
            # Detect anomalies using detector (ML service + simple rules)
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                anomalies = loop.run_until_complete(self.detector.detect(cleaned))
                loop.close()
                
                logger.debug(f"🔍 DETECT: Found {len(anomalies)} anomalies for {cleaned['device_id']}")
                
            except Exception as e:
                logger.error(f"❌ DETECT: Error in anomaly detection: {e}")
                anomalies = []
            
            llm_decision = None
            actions_taken = []
            
            if anomalies:
                self.anomalies_detected += 1
                
                # LLM reasoning for intelligent decisions
                if self.llm:
                    try:
                        # Convert anomaly objects to strings for LLM
                        anomaly_descriptions = [a.get('reason', str(a)) for a in anomalies]
                        llm_decision = self.llm.reason_about_anomaly(cleaned, ", ".join(anomaly_descriptions))
                        logger.debug(f"🤖 DECISION: LLM reasoning completed")
                    except Exception as e:
                        logger.error(f"❌ DECISION: LLM reasoning failed: {e}")

                try:
                    # Handle async action execution
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    actions_taken = loop.run_until_complete(self.dispatcher.handle_anomalies(anomalies, cleaned))
                    loop.close()
                    logger.debug(f"⚡ DECISION: {len(actions_taken)} actions taken")
                except Exception as e:
                    logger.error(f"❌ DECISION: Action handling failed: {e}")
                
                # Store comprehensive anomaly record
                anomaly_record = {
                    'device_id': cleaned['device_id'],
                    'timestamp': cleaned['timestamp'],
                    'anomalies': anomalies,
                    'actions_taken': actions_taken,
                    'llm_decision': llm_decision,
                    'sensor_data': processed_record,
                    'detected_at': datetime.now().isoformat()
                }
                self.recent_anomalies.append(anomaly_record)
                
                # Store anomalies in database with enhanced metadata
                if sensor_data_id:
                    for anomaly in anomalies:
                        # Extract field and value from anomaly
                        sensor_field = 'unknown'
                        value = 0
                        
                        # Try to determine sensor field from anomaly data
                        if 'pm2_5' in str(anomaly).lower():
                            sensor_field = 'pm2_5'
                            value = cleaned.get('pm2_5', 0)
                        elif 'pm10' in str(anomaly).lower():
                            sensor_field = 'pm10'
                            value = cleaned.get('pm10', 0)
                        elif 'dba' in str(anomaly).lower():
                            sensor_field = 'dBA'
                            value = cleaned.get('dBA', 0)
                        elif 'vibration' in str(anomaly).lower():
                            sensor_field = 'vibration'
                            value = cleaned.get('vibration', 0)
                        
                        self.db.store_anomaly(
                            sensor_data_id=sensor_data_id,
                            device_id=cleaned['device_id'],
                            timestamp=cleaned['timestamp'],
                            anomaly_type=anomaly.get('type', 'detection'),
                            sensor_field=sensor_field,
                            value=value,
                            threshold=anomaly.get('threshold', 0),
                            severity=anomaly.get('severity', 'medium'),
                            llm_decision=llm_decision
                        )
                
                # Enhanced logging with severity levels
                critical_anomalies = [a for a in anomalies if a.get('severity') == 'critical']
                high_anomalies = [a for a in anomalies if a.get('severity') == 'high']
                
                if critical_anomalies:
                    logger.critical(f"🚨 CRITICAL ANOMALIES DETECTED for {cleaned['device_id']}: {len(critical_anomalies)} critical issues")
                elif high_anomalies:
                    logger.warning(f"⚠️ HIGH SEVERITY ANOMALIES for {cleaned['device_id']}: {len(high_anomalies)} high-severity issues")
                else:
                    logger.warning(f"⚠️ ANOMALY DETECTED for {cleaned['device_id']}: {len(anomalies)} issues")
                
                if llm_decision:
                    logger.info(f"🤖 LLM Decision: {llm_decision}")
                
                if actions_taken:
                    logger.info(f"⚡ Actions taken: {actions_taken}")
            else:
                logger.debug(f"✅ OK: {cleaned['device_id']} at {cleaned['timestamp']} - No anomalies detected")

            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.debug(f"✅ ACK: Message processed successfully for {cleaned['device_id']}")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ INGEST: Invalid JSON in message: {e}")
            ch.basic_ack(delivery_tag=method.delivery_tag)  # Acknowledge to avoid infinite retry
        except Exception as e:
            logger.error(f"❌ PROCESSING: Unexpected error: {e}")
            # Don't acknowledge - let RabbitMQ retry
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
        sys.exit(0)
    
    def start_consuming(self):
        if not self.connect_rabbitmq():
            logger.error("Failed to connect to RabbitMQ, exiting")
            return False
        
        # Connect to database
        if not self.db.connect():
            logger.warning("Failed to connect to database, continuing without persistence")
        else:
            logger.info("Database connection established")
        
        # Retry logic for queue setup
        max_retries = 5
        retry_delay = 10  # seconds
        
        for attempt in range(max_retries):
            try:
                # Declare the queue to ensure it exists
                self.channel.queue_declare(queue=self.queue_name, durable=True)
                logger.info(f"Queue '{self.queue_name}' declared successfully")
                
                # Set QoS
                self.channel.basic_qos(prefetch_count=1)
                
                # Start consuming
                self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.callback)
                logger.info(f"Started consuming from queue '{self.queue_name}'")
                
                self.running = True
                logger.info(f"🎯 Consumer started! Waiting for messages on queue '{self.queue_name}'...")
                logger.info(f"Stats: {self.messages_processed} messages processed, {self.anomalies_detected} anomalies detected")
                
                # Start consuming
                self.channel.start_consuming()
                break  # Success, exit retry loop
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Consumer error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    # Reconnect to RabbitMQ
                    if not self.connect_rabbitmq():
                        logger.error("Failed to reconnect to RabbitMQ")
                        return False
                else:
                    logger.error("Max retries reached, giving up")
                    self.stop()
                    return False
        
        return True
    
    def stop(self):
        """Stop the consumer"""
        self.running = False
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        self.db.close()
        logger.info("Consumer stopped")
    
    def get_sensor_data(self, limit: int = 100) -> List[Dict]:
        """Get recent sensor data for API"""
        return list(self.recent_sensor_data)[-limit:]
    
    def get_anomalies(self, limit: int = 50) -> List[Dict]:
        """Get recent anomalies for API"""
        return list(self.recent_anomalies)[-limit:]
    
    def get_stats(self) -> Dict:
        """Get current statistics for API"""
        uptime = datetime.now() - self.start_time
        rate = self.messages_processed / max(uptime.total_seconds(), 1)
        
        return {
            'uptime': str(uptime),
            'messages_processed': self.messages_processed,
            'anomalies_detected': self.anomalies_detected,
            'processing_rate': round(rate, 2),
            'anomaly_rate': round((self.anomalies_detected/max(self.messages_processed, 1)*100), 2),
            'recent_data_count': len(self.recent_sensor_data),
            'recent_anomalies_count': len(self.recent_anomalies)
        }


def main():
    logger.info("Starting SmartSensor Queue Consumer...")
    
    consumer = SmartSensorConsumer()
    api_app = create_api_server(consumer)
    
    # Start API server in a separate thread if available
    api_thread = None
    if api_app:
        logger.info("Creating API server thread...")
        def run_api():
            try:
                logger.info("Starting uvicorn server on port 8001...")
                uvicorn.run(api_app, host="0.0.0.0", port=8001, log_level="info")
            except Exception as e:
                logger.error(f"Failed to start API server: {e}")

        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        logger.info("FastAPI server thread started on port 8001")
    else:
        logger.warning(" API server not available - FastAPI import failed")

    try:
        consumer.start_consuming()
    except Exception as e:
        logger.error(f"Failed to start consumer: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
