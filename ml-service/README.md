# Machine Learning Service


The Machine Learning Service is a comprehensive anomaly detection system designed for environmental sensor data analysis. This isolated and scalable service implements multiple detection algorithms to identify unusual patterns in sensor readings, providing real-time monitoring capabilities for air quality, noise levels, and vibration data.

The service operates as a multi-algorithm detection system, where different specialized detectors analyze sensor data using various statistical and machine learning approaches. Each detector is optimized for specific data characteristics and can be automatically selected based on data availability and pattern complexity.

### Supported Sensor Types

- **PM2.5**: Fine particulate matter concentration
- **PM10**: Coarse particulate matter concentration  
- **dBA**: Decibel level measurements
- **Vibration**: Structural vibration amplitude

## Key Features

- **Multi-Algorithm Detection**: Implements statistical, time-series, and neural network-based anomaly detection
- **Automatic Model Selection**: Intelligently chooses the most appropriate detection algorithm based on data characteristics
- **Real-Time Processing**: Provides immediate anomaly detection for incoming sensor data
- **Scalable Architecture**: Designed to handle multiple sensors and data streams concurrently
- **Database Integration**: Seamlessly integrates with PostgreSQL for data persistence and model metadata storage
- **RESTful API**: Offers comprehensive API endpoints for detection, training, and status monitoring -> [API Endpoints](localhost:8002/docs)
- **Automated Training**: Implements scheduled model retraining to maintain detection accuracy
- **Configurable Parameters**: Allows fine-tuning of detection sensitivity and model behavior




## **Detection Algorithms**
**Model Selection Logic**:
1. **Z-Score**: Used when we have < 200 readings (simple, fast)
2. **STL**: Used when we have ≥ 100 readings AND seasonal patterns
3. **LSTM**: Used when we have ≥ 200 readings AND complex patterns

### Detector Configurations

```python
DETECTOR_CONFIGS = {
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
        "trend_window": 25,  # Must be > period and odd
        "low_pass_window": 25,  # Must be > period and odd
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
```

### **1. Statistical Detection (Z-Score)**
- Detects outliers using standard deviation
- Threshold: configurable
- Fast and reliable for basic anomaly detection

**How it works**:
- Takes historical data and calculates the average (mean) and spread (standard deviation)
- For new readings, calculates how many "standard deviations" away it is (Z-score)
- If Z-score > 3.0, it's considered an anomaly

**When to use**: When we have little data or need a quick, simple check

**Example**:
```python
# If historical mean = 25, std = 5
# New reading = 40
# Z-score = (40 - 25) / 5 = 3.0 → Anomaly!
```

**Model Files**:
```
sensor-1_dBA_zscore               # Simple statistical data
```

**What each file contains**:
- Historical mean and standard deviation
- Rolling window data
- Configuration settings




### **2. Time-Series Analysis (STL Decomposition)**
- Seasonal-Trend decomposition using LOESS
- Detects trend and seasonal anomalies
- Handles complex time-series patterns

**What it does**: Like a sophisticated time series expert who breaks down data into 3 parts:
1. **Trend**: Long-term direction (going up/down over time)
2. **Seasonal**: Repeating patterns (daily, weekly cycles)
3. **Residual**: Random noise/outliers

**How it works**: Uses STL (Seasonal-Trend decomposition using Loess) algorithm

**When to use**: When you have lots of data and want to understand patterns

**Example Analysis**:
```python
# Input: [25, 26, 28, 30, 32, 35, 38, 40, 42, 45]
# STL Decomposition:
# Trend: [24, 25, 26, 27, 28, 29, 30, 31, 32, 33] (gradual increase)
# Seasonal: [1, 1, 2, 3, 4, 6, 8, 9, 10, 12] (daily pattern)
# Residual: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] (noise)
```

**Model Files**:
```
sensor-1_pm2_5_stl                # STL decomposition data
sensor-1_pm10_stl                 # STL decomposition data
sensor-1_vibration_stl            # STL decomposition data
```

**What each file contains**:
- Historical statistics (mean, std, min, max)
- Trend, seasonal, and residual patterns
- Configuration settings










### **3. Machine Learning (LSTM)**
- Long Short-Term Memory neural networks
- Predicts expected values and flags deviations
- Learns complex temporal patterns

**What it does**: Like an AI teacher that learns patterns by looking at sequences of data.

**How it works**:
- Takes sequences of 50 readings
- Learns to predict the next value
- If prediction is very wrong, it's an anomaly

**When to use**: When you have lots of data and complex patterns

**Model Structure**:
```
Input: [50 readings] → LSTM(50) → Dropout → LSTM(25) → Dropout → Dense(25) → Dense(1) → Output: [prediction]
```

**Model Files**:
```
sensor-1_dBA_lstm_model.keras     # The trained neural network
sensor-1_dBA_lstm_scaler.pkl      # Data scaler (normalizes data)
sensor-1_dBA_lstm_threshold.pkl   # Anomaly threshold
```

**What each file does**:
- **`.keras`**: The actual neural network (like a brain that learned patterns)
- **`_scaler.pkl`**: Converts raw data to 0-1 range for the neural network
- **`_threshold.pkl`**: How much error is considered an anomaly



### **4. LLM Reasoning (Optional)**
- Uses GPT-4 to analyze context and make decisions
- Distinguishes between true alerts and noise
- Provides human-readable explanations



## ML Service Architecture

```
ml-service/
├── main.py              # Main API server
├── training.py          # Training manager
├── database.py          # Database operations
├── config.py            # Configuration
├── models/              # All detectors
│   ├── base.py         # Base class for all detectors
│   ├── zscore_detector.py    # Simple statistical
│   ├── stl_detector.py       # Time series expert
│   ├── lstm_detector.py      # Neural network
│   └── ml_detector.py        # Main orchestrator
└── requirements.txt     # Dependencies
```




## Anomaly Categories

### Detection Categories

1. **normal**: No anomaly detected
2. **noise**: Moderate anomaly (slight deviation)
3. **drift**: Gradual change in pattern
4. **alert**: Severe anomaly (requires attention)

### Confidence Levels

- **0.9+**: Very confident (90%+ sure)
- **0.7-0.9**: Confident (70-90% sure)
- **0.5-0.7**: Moderate confidence (50-70% sure)
- **<0.5**: Low confidence (less than 50% sure)





## How Training Works

### Training Manager (The Administrator)

The TrainingManager is like a administrator who schedules when teachers should learn:

**What it does**:
- Runs every 30 minutes (configurable)
- Checks which sensors have enough data
- Trains models for each sensor

**Training Process**:
1. **Get Data**: Fetch last 24 hours of sensor data
2. **Check Sufficiency**: Need at least 50 readings (configurable)
3. **Train Each Sensor**: pm2_5, pm10, dBA, vibration
4. **Save Metadata**: Store model info in database





### Detection Process

1. **Receive Data**: Get sensor readings (pm2_5, pm10, dBA, vibration)
2. **Analyze Each**: Run each sensor through its trained model
3. **Correlate**: Check relationships between sensors
4. **Save Anomalies**: Store significant anomalies in database
5. **Return Results**: Send back detailed analysis







## Complete System Flow


1. **Data Collection**: Sensors send data to database
2. **Training**: Every 30 minutes, models learn from new data
3. **Detection**: When new data arrives, models analyze it
4. **Storage**: Anomalies are saved to database
5. **Response**: Detailed analysis is returned


```
Sensors → Database → Training Manager → ML Models → API → Dashboard
```


