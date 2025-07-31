import json
import logging
import os
import random
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any
import pika

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConfigurableGenerator:
    def __init__(self, config_file: str = "generator-configs.json", config_id: str = None):
        self.config_file = config_file
        self.config_id = config_id
        self.config = self.load_config()
        
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST")
        self.rabbitmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.rabbitmq_user = os.getenv("RABBITMQ_USER")
        self.rabbitmq_pass = os.getenv("RABBITMQ_PASS")
        self.queue_name = os.getenv("QUEUE_NAME", "sensor-data")
        
        if not all([self.rabbitmq_host, self.rabbitmq_user, self.rabbitmq_pass]):
            logger.error("Missing required RabbitMQ environment variables: RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASS")
            sys.exit(1)
        
        self.connection = None
        self.channel = None
        self.reading_counter = 0
        self.running = True
        
        self.sensors = {}
        self.initialize_sensors()
        
        logger.info(f"Initialized generator with config: {self.config['name']}")
        logger.info(f"Device ID: {self.config['device_id']}")
        logger.info(f"Generation interval: {self.config['generation_interval']}s")

    def load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_file, 'r') as f:
                configs = json.load(f)
            
            if self.config_id:
                for config in configs:
                    if config['id'] == self.config_id:
                        return config
                raise ValueError(f"Config with ID '{self.config_id}' not found")
            else:
                return configs[0]
                
        except FileNotFoundError:
            logger.error(f"Config file {self.config_file} not found")
            sys.exit(1)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            sys.exit(1)

    def initialize_sensors(self):
        for sensor_name, sensor_config in self.config['sensors'].items():
            self.sensors[sensor_name] = {
                "config": sensor_config,
                "current_value": sensor_config["current_value"],
                "drift": 0.0,
                "drift_direction": 1,
                "drift_counter": 0,
                "anomaly_counter": 0,
                "alert_counter": 0
            }

    def connect_rabbitmq(self):
        try:
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
            
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            logger.info("Successfully connected to RabbitMQ and declared queue")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False

    def add_normal_fluctuation(self, sensor_name: str) -> float:
        sensor = self.sensors[sensor_name]
        config = sensor["config"]
        base_value = sensor["current_value"]
        
        # Add fluctuation based on config
        fluctuation = random.uniform(-config["fluctuation_range"], config["fluctuation_range"])
        fluctuated_value = base_value * (1 + fluctuation)
        
        # Add noise based on config
        noise = random.uniform(-config["noise_level"], config["noise_level"])
        noisy_value = fluctuated_value * (1 + noise)
        
        return round(noisy_value, 3)

    def generate_anomaly(self, sensor_name: str) -> float:
        sensor = self.sensors[sensor_name]
        config = sensor["config"]
        normal_min, normal_max = config["normal_range"]
        anomaly_config = self.config["anomaly_behavior"]
        
        if random.random() < anomaly_config["spike_chance"]:
            # Spike: use configured multiplier range
            min_mult = anomaly_config["spike_multiplier"][0]
            max_mult = anomaly_config["spike_multiplier"][1]
            anomaly_value = random.uniform(normal_max * min_mult, normal_max * max_mult)
            logger.info(f"Generated spike anomaly for {sensor_name}: {anomaly_value}")
        else:
            # Drop: use configured multiplier range
            min_mult = anomaly_config["drop_multiplier"][0]
            max_mult = anomaly_config["drop_multiplier"][1]
            anomaly_value = random.uniform(normal_min * min_mult, normal_min * max_mult)
            logger.info(f"Generated drop anomaly for {sensor_name}: {anomaly_value}")
        
        return round(anomaly_value, 3)

    def generate_alert(self, sensor_name: str) -> float:
        sensor = self.sensors[sensor_name]
        config = sensor["config"]
        alert_min, alert_max = config["alert_range"]
        
        alert_value = random.uniform(alert_min, alert_max)
        logger.warning(f"Generated alert condition for {sensor_name}: {alert_value}")
        
        return round(alert_value, 3)

    def update_drift(self, sensor_name: str):
        sensor = self.sensors[sensor_name]
        frequencies = self.config["frequencies"]
        drift_config = self.config["drift_behavior"]
        
        # Start new drift based on config
        if sensor["drift_counter"] == 0:
            if random.random() < frequencies["drift_chance"]:
                sensor["drift_direction"] = random.choice([-1, 1])
                sensor["drift_counter"] = random.randint(*frequencies["drift_duration"])
                logger.info(f"Starting new drift for {sensor_name}, direction: {sensor['drift_direction']}")
        
        # Apply drift if active
        if sensor["drift_counter"] > 0:
            # Drift amount from config
            min_drift = drift_config["amount_range"][0]
            max_drift = drift_config["amount_range"][1]
            drift_amount = random.uniform(min_drift, max_drift) * sensor["drift_direction"]
            sensor["drift"] += drift_amount
            sensor["drift_counter"] -= 1
            
            # Reset drift when counter reaches 0
            if sensor["drift_counter"] == 0:
                sensor["drift"] = 0.0
                logger.info(f"Drift completed for {sensor_name}")

    def validate_value(self, sensor_name: str, value: float) -> float:
        validation_config = self.config["value_validation"]
        if sensor_name in validation_config:
            min_val = validation_config[sensor_name]["min"]
            max_val = validation_config[sensor_name]["max"]
            return max(min_val, min(max_val, value))
        return value

    def generate_sensor_value(self, sensor_name: str) -> float:
        sensor = self.sensors[sensor_name]
        config = sensor["config"]
        frequencies = self.config["frequencies"]
        
        # Update drift
        self.update_drift(sensor_name)
        
        # Check for anomaly based on config frequency
        sensor["anomaly_counter"] += 1
        if sensor["anomaly_counter"] >= random.randint(*frequencies["anomaly_every"]):
            sensor["anomaly_counter"] = 0
            anomaly_value = self.generate_anomaly(sensor_name)
            validated_value = self.validate_value(sensor_name, anomaly_value)
            return validated_value
        
        # Check for alert based on config frequency
        sensor["alert_counter"] += 1
        if sensor["alert_counter"] >= random.randint(*frequencies["alert_every"]):
            sensor["alert_counter"] = 0
            alert_value = self.generate_alert(sensor_name)
            validated_value = self.validate_value(sensor_name, alert_value)
            return validated_value
        
        # Normal fluctuation with drift
        normal_value = self.add_normal_fluctuation(sensor_name)
        drifted_value = normal_value + sensor["drift"]
        
        # Validate and constrain value
        validated_value = self.validate_value(sensor_name, drifted_value)
        
        # Update current value for next iteration (use validated value)
        sensor["current_value"] = validated_value
        
        # Reset drift if it caused the value to be clamped to minimum
        validation_config = self.config["value_validation"]
        if sensor_name in validation_config:
            min_val = validation_config[sensor_name]["min"]
            if validated_value == min_val and drifted_value < min_val:
                sensor["drift"] = 0.0  # Reset drift if it caused clamping
        
        return round(validated_value, 3)

    def generate_sensor_data(self) -> Dict[str, Any]:
        data = {
            "timestamp": datetime.now().isoformat(),
            "device_id": self.config["device_id"]
        }
        
        # Generate values for all sensors
        for sensor_name in self.sensors.keys():
            data[sensor_name] = self.generate_sensor_value(sensor_name)
        
        self.reading_counter += 1
        return data

    def publish_message(self, data: Dict[str, Any]):
        try:
            message = json.dumps(data)
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                )
            )
            logger.debug(f"Published: {data}")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")

    def run(self):
        if not self.connect_rabbitmq():
            return False
        
        logger.info(f"Starting generator: {self.config['name']}")
        logger.info(f"Device ID: {self.config['device_id']}")
        logger.info(f"Generation interval: {self.config['generation_interval']}s")
        
        try:
            while self.running:
                data = self.generate_sensor_data()
                self.publish_message(data)
                
                if self.reading_counter % 100 == 0:
                    logger.info(f"Generated {self.reading_counter} readings")
                
                time.sleep(self.config['generation_interval'])
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in generation loop: {e}")
        finally:
            self.cleanup()
        
        return True

    def signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def cleanup(self):
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        logger.info("Generator shutdown complete")

def main():
    # Get config ID from environment variable
    config_id = os.getenv("GENERATOR_CONFIG_ID")
    config_file = os.getenv("GENERATOR_CONFIG_FILE", "generator-configs.json")
    
    # Create generator
    generator = ConfigurableGenerator(config_file, config_id)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, generator.signal_handler)
    signal.signal(signal.SIGTERM, generator.signal_handler)
    
    # Run generator
    success = generator.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 