-- Create sensor_data table
CREATE TABLE IF NOT EXISTS sensor_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    pm2_5 DECIMAL(10,3),
    pm10 DECIMAL(10,3),
    dBA DECIMAL(10,3),
    vibration DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_sensor_data_device_id ON sensor_data(device_id);

-- Create alerts table for anomaly detection results
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    sensor_type VARCHAR(20) NOT NULL,
    value DECIMAL(10,6) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for alerts table
CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_device_id ON alerts(device_id);
CREATE INDEX IF NOT EXISTS idx_alerts_sensor_type ON alerts(sensor_type);

-- Create ml_models table for ML model metadata
CREATE TABLE IF NOT EXISTS ml_models (
    device_id VARCHAR(50) NOT NULL,
    sensor_type VARCHAR(20) NOT NULL,
    model_type VARCHAR(20) NOT NULL,
    trained_at TIMESTAMP NOT NULL,
    accuracy FLOAT,
    config TEXT,
    last_updated TIMESTAMP NOT NULL,
    PRIMARY KEY (device_id, sensor_type)
);

-- Create indexes for ml_models table
CREATE INDEX IF NOT EXISTS idx_ml_models_device_id ON ml_models(device_id);
CREATE INDEX IF NOT EXISTS idx_ml_models_sensor_type ON ml_models(sensor_type);

-- Create anomalies table for ML anomaly detection results
CREATE TABLE IF NOT EXISTS anomalies (
    id SERIAL PRIMARY KEY,
    sensor_data_id INTEGER,
    device_id VARCHAR(50) NOT NULL,
    sensor_field VARCHAR(20) NOT NULL,
    anomaly_type VARCHAR(50) NOT NULL,
    value DECIMAL(10,6) NOT NULL,
    threshold DECIMAL(10,6) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    llm_decision TEXT,
    ml_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for anomalies table
CREATE INDEX IF NOT EXISTS idx_anomalies_device_id ON anomalies(device_id);
CREATE INDEX IF NOT EXISTS idx_anomalies_timestamp ON anomalies(timestamp);
CREATE INDEX IF NOT EXISTS idx_anomalies_sensor_field ON anomalies(sensor_field); 