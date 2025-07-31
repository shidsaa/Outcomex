# Synthetic IoT Sensor Data Generator

This generator is designed to simulate a physical device located at a specific site, equipped with environmental sensors such as PM2.5, PM10, dBA, and vibration.

Its behavior is fully configurable through a JSON file.

The `generator-configs.json` file defines the behavior of multiple sensor generators, enabling us to simulate diverse environmental conditions and sensor characteristics. Each configuration entry represents an individual generator, capable of producing realistic sensor data with adjustable patterns, noise levels, anomalies, and alert thresholds.

The `docker-compose` setup references this file to initialize each simulated device with specific parameters such as name, location, and behavior profile.

Each generator publishes its data into q shared queue.

**Sensor Data Format**:
```json
{
  "timestamp": "2025-07-22T14:40:02.322073Z",
  "device_id": "sensor-01",
  "pm2_5": 11.592,
  "pm10": 21.154,
  "dBA": 123.812,
  "vibration": 0.012
}
```




# Configuration Schema Structure

```json
[
  {
    "id": "generator-1",
    "name": "Normal Environment Sensor",
    "description": "Standard environmental monitoring with balanced alert frequency",
    "sensors": { ... },
    "frequencies": { ... },
    "anomaly_behavior": { ... },
    "generation_interval": 5.0,
    "device_id": "sensor-1"
  }
]
```

## Configuration Parameters

### Top-Level Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `id` | string | Unique identifier for the generator configuration | `"generator-1"` |
| `name` | string | Human-readable name for the generator | `"Normal Environment Sensor"` |
| `description` | string | Detailed description of the generator's purpose | `"Standard environmental monitoring..."` |
| `sensors` | object | Configuration for each sensor type | See Sensors section |
| `frequencies` | object | Timing and frequency settings | See Frequencies section |
| `anomaly_behavior` | object | How anomalies are generated | See Anomaly Behavior section |
| `generation_interval` | number | How often data is generated (seconds) | `5.0` |
| `device_id` | string | Unique device identifier for this generator | `"sensor-1"` |

### Sensors Configuration

Each sensor type has its own configuration object:

```json
"sensors": {
  "pm2_5": {
    "normal_range": [10, 25],
    "alert_range": [50, 100],
    "current_value": 17.5,
    "noise_level": 0.02,
    "fluctuation_range": 0.05
  }
}
```

#### Sensor Parameters

| Parameter | Type | Description | Example | Impact |
|-----------|------|-------------|---------|---------|
| `normal_range` | [number, number] | Acceptable operating range [min, max] | `[10, 25]` | Defines baseline values |
| `alert_range` | [number, number] | Threshold range that triggers alerts [min, max] | `[50, 100]` | Defines alert conditions |
| `current_value` | number | Starting value for the sensor | `17.5` | Initial sensor reading |
| `noise_level` | number | Random noise factor (±percentage) | `0.02` | Adds ±2% random variation |
| `fluctuation_range` | number | Normal variation range (±percentage) | `0.05` | Adds ±5% normal fluctuation |

#### Sensor Types

| Sensor | Unit | Normal Range | Alert Range | Purpose |
|--------|------|--------------|-------------|---------|
| `pm2_5` | µg/m³ | 5-45 | 30-150 | Fine particulate matter |
| `pm10` | µg/m³ | 10-80 | 50-250 | Coarse particulate matter |
| `dBA` | dB | 45-85 | 70-110 | Sound level |
| `vibration` | g | 0.005-0.15 | 0.05-0.5 | Mechanical vibration |

### Frequencies Configuration

Controls how often different events occur:

```json
"frequencies": {
  "anomaly_every": [100, 200],
  "alert_every": [300, 600],
  "drift_chance": 0.005,
  "drift_duration": [100, 200]
}
```

#### Frequency Parameters

| Parameter | Type | Description | Example | Impact |
|-----------|------|-------------|---------|---------|
| `anomaly_every` | [number, number] | Anomaly frequency range [min, max] readings | `[100, 200]` | Every 100-200 readings |
| `alert_every` | [number, number] | Alert frequency range [min, max] readings | `[300, 600]` | Every 300-600 readings |
| `drift_chance` | number | Probability of starting a drift (0-1) | `0.005` | 0.5% chance per reading |
| `drift_duration` | [number, number] | How long drift lasts [min, max] readings | `[100, 200]` | 100-200 readings |

### Anomaly Behavior Configuration

Defines how anomalies are generated:

```json
"anomaly_behavior": {
  "spike_multiplier": [1.5, 3.0],
  "drop_multiplier": [0.1, 0.5],
  "spike_chance": 0.5
}
```

#### Anomaly Parameters

| Parameter | Type | Description | Example | Impact |
|-----------|------|-------------|---------|---------|
| `spike_multiplier` | [number, number] | Range for spike anomalies [min, max] | `[1.5, 3.0]` | 1.5x-3x normal max |
| `drop_multiplier` | [number, number] | Range for drop anomalies [min, max] | `[0.1, 0.5]` | 0.1x-0.5x normal min |
| `spike_chance` | number | Probability of spike vs drop (0-1) | `0.5` | 50% chance of spike |

### Drift Behavior Configuration

Controls how sensor values drift over time:

```json
"drift_behavior": {
  "amount_range": [0.001, 0.003],
  "description": "Drift amount as percentage per reading"
}
```

#### Drift Parameters

| Parameter | Type | Description | Example | Impact |
|-----------|------|-------------|---------|---------|
| `amount_range` | [number, number] | Drift amount range [min, max] | `[0.001, 0.003]` | 0.1%-0.3% per reading |
| `description` | string | Human-readable description | `"Drift amount as percentage per reading"` | Documentation |

### Value Validation Configuration

Defines acceptable ranges for each sensor type:

```json
"value_validation": {
  "pm2_5": {"min": 0, "max": 1000},
  "pm10": {"min": 0, "max": 2000},
  "dBA": {"min": 30, "max": 200},
  "vibration": {"min": 0, "max": 10}
}
```

#### Validation Parameters

| Parameter | Type | Description | Example | Impact |
|-----------|------|-------------|---------|---------|
| `min` | number | Minimum allowed value | `0` | Constrains lower bound |
| `max` | number | Maximum allowed value | `1000` | Constrains upper bound |

## Data Generation Logic

### 1. Normal Operation
- **Base Value**: Starts with `current_value`
- **Fluctuation**: Adds random variation within `fluctuation_range`
- **Noise**: Adds random noise within `noise_level`
- **Drift**: Applies long-term trend changes

### 2. Anomaly Generation
- **Frequency**: Every `anomaly_every[0]` to `anomaly_every[1]` readings
- **Type**: 50% chance of spike, 50% chance of drop (configurable)
- **Spike**: `normal_max × random(spike_multiplier[0], spike_multiplier[1])`
- **Drop**: `normal_min × random(drop_multiplier[0], drop_multiplier[1])`

### 3. Alert Generation
- **Frequency**: Every `alert_every[0]` to `alert_every[1]` readings
- **Value**: Random value within `alert_range[0]` to `alert_range[1]`

### 4. Drift Behavior
- **Start**: `drift_chance` probability per reading
- **Duration**: `drift_duration[0]` to `drift_duration[1]` readings
- **Direction**: Random (increasing or decreasing)
- **Amount**: Configurable incremental changes from `drift_behavior.amount_range`

### 5. Value Validation
- **Range Checking**: All values constrained to `value_validation` ranges
- **Automatic Correction**: Values outside ranges are clamped to min/max
- **Per-Sensor**: Each sensor type has its own validation rules

## 🎯 Example Configurations

### Normal Environment Sensor
```json
{
  "id": "generator-1",
  "name": "Normal Environment Sensor",
  "sensors": {
    "vibration": {
      "normal_range": [0.01, 0.05],
      "alert_range": [0.1, 0.3],
      "current_value": 0.03,
      "noise_level": 0.1,
      "fluctuation_range": 0.2
    }
  },
  "frequencies": {
    "anomaly_every": [100, 200],
    "alert_every": [300, 600],
    "drift_chance": 0.005,
    "drift_duration": [100, 200]
  },
  "anomaly_behavior": {
    "spike_multiplier": [1.5, 3.0],
    "drop_multiplier": [0.1, 0.5],
    "spike_chance": 0.5
  },
  "drift_behavior": {
    "amount_range": [0.001, 0.003],
    "description": "Drift amount as percentage per reading"
  },
  "value_validation": {
    "pm2_5": {"min": 0, "max": 1000},
    "pm10": {"min": 0, "max": 2000},
    "dBA": {"min": 30, "max": 200},
    "vibration": {"min": 0, "max": 10}
  },
  "generation_interval": 5.0,
  "device_id": "sensor-1"
}
```

### High Activity Industrial Sensor
```json
{
  "id": "generator-2",
  "name": "High Activity Industrial Sensor",
  "sensors": {
    "vibration": {
      "normal_range": [0.05, 0.15],
      "alert_range": [0.2, 0.5],
      "current_value": 0.1,
      "noise_level": 0.15,
      "fluctuation_range": 0.25
    }
  },
  "frequencies": {
    "anomaly_every": [50, 100],
    "alert_every": [150, 300],
    "drift_chance": 0.01,
    "drift_duration": [80, 150]
  },
  "anomaly_behavior": {
    "spike_multiplier": [2.0, 4.0],
    "drop_multiplier": [0.05, 0.3],
    "spike_chance": 0.7
  },
  "drift_behavior": {
    "amount_range": [0.002, 0.005],
    "description": "Higher drift for industrial environment"
  },
  "value_validation": {
    "pm2_5": {"min": 0, "max": 1000},
    "pm10": {"min": 0, "max": 2000},
    "dBA": {"min": 30, "max": 200},
    "vibration": {"min": 0, "max": 10}
  },
  "generation_interval": 3.0,
  "device_id": "sensor-2"
}
```

## 🔧 Customization Guide

### Creating Different Environments

#### Clean Environment
- **Lower normal ranges**: `[5, 15]` for PM2.5
- **Rare alerts**: `[600, 1000]` for alert frequency
- **Low noise**: `0.01` noise level
- **Slow generation**: `8.0` second interval

#### Industrial Environment
- **Higher normal ranges**: `[25, 45]` for PM2.5
- **Frequent alerts**: `[150, 300]` for alert frequency
- **High noise**: `0.03` noise level
- **Fast generation**: `3.0` second interval

### Adjusting Alert Sensitivity

#### High Sensitivity
```json
"frequencies": {
  "anomaly_every": [50, 100],
  "alert_every": [100, 200],
  "drift_chance": 0.01
}
```

#### Low Sensitivity
```json
"frequencies": {
  "anomaly_every": [300, 500],
  "alert_every": [800, 1200],
  "drift_chance": 0.002
}
```

## Usage

### Environment Variables

The generator requires these environment variables for RabbitMQ connection:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `RABBITMQ_HOST` | RabbitMQ server hostname | Yes | - |
| `RABBITMQ_PORT` | RabbitMQ server port | No | `5672` |
| `RABBITMQ_USER` | RabbitMQ username | Yes | - |
| `RABBITMQ_PASS` | RabbitMQ password | Yes | - |
| `QUEUE_NAME` | Queue name for sensor data | No | `sensor-data` |
| `GENERATOR_CONFIG_ID` | Specific config ID to use | No | Uses first config |
| `GENERATOR_CONFIG_FILE` | Path to config file | No | `generator-configs.json` |

### 1. Edit Configuration
```bash
nano generator-configs.json
```

### 2. Rebuild Generators
```bash
docker-compose build generator-1 [generator-2 generator-3]
```

### 3. Restart Generators
```bash
docker-compose up -d generator-1 [generator-2 generator-3]
```

### 4. Monitor Results
```bash
docker-compose logs -f generator-1
```