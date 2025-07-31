import React, { useState, useEffect, useCallback } from 'react';
import { Alert, AlertTitle, Typography, Box, Container, AppBar, Toolbar, IconButton, Tooltip, CircularProgress } from '@mui/material';
import { Refresh as RefreshIcon, Sensors as SensorsIcon, Settings as SettingsIcon } from '@mui/icons-material';
import axios from 'axios';

import SensorGrid from './components/molecules/SensorGrid';
import SensorDetailView from './components/organisms/SensorDetailView';
import ServiceHealthGrid from './components/molecules/ServiceHealthGrid';

interface SensorData {
  device_id: string;
  timestamp: string;
  pm2_5: number;
  pm10: number;
  dBA: number;
  vibration: number;
}

interface AnomalyData {
  id: number;
  device_id: string;
  timestamp: string;
  anomaly_type: string;
  sensor_field: string;
  value: number;
  threshold: number;
  severity: string;
  llm_decision?: string;
  created_at: string;
}

interface QueueStatus {
  messages: number;
  consumers: number;
  message_stats: {
    publish: number;
    deliver: number;
  };
}

interface SystemMetrics {
  total_records_processed: number;
  total_alerts_generated: number;
  last_processing_time: string;
  uptime: string;
}

interface SystemHealth {
  status: 'normal' | 'warning' | 'critical' | 'offline' | 'unknown';
  reason: string;
  last_data_timestamp: string | null;
  critical_alerts: number;
  warning_alerts: number;
  total_alerts: number;
  data_rate_per_minute: number;
}

const App: React.FC = () => {
  const [sensorData, setSensorData] = useState<SensorData[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyData[]>([]);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [error, setError] = useState<string | null>(null);
  const [selectedSensor, setSelectedSensor] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Get API URL from environment variables or use defaults
      const consumerApiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8001';
      
      // Note: RabbitMQ management API calls removed due to CORS issues
      // Queue status is not critical for dashboard functionality

      // Fetch system metrics from consumer API
      try {
        const metricsResponse = await axios.get(`${consumerApiUrl}/api/metrics`);
        setSystemMetrics(metricsResponse.data);
      } catch (apiError) {
        console.log('Consumer API metrics not available:', apiError);
      }

      // Fetch system health status from consumer API
      try {
        const healthResponse = await axios.get(`${consumerApiUrl}/api/system-health`);
        setSystemHealth(healthResponse.data);
      } catch (healthError) {
        console.log('Consumer API health not available:', healthError);
      }

      // Fetch real sensor data from consumer API - get 24 hours of data for time frame filtering
      try {
        const sensorResponse = await axios.get(`${consumerApiUrl}/api/sensor-data?limit=1000&hours=24`); // Get 24 hours of data
        if (sensorResponse.data.data) {
          const realSensorData: SensorData[] = sensorResponse.data.data.map((item: any) => ({
            device_id: item.device_id,
            timestamp: item.timestamp,
            pm2_5: item.pm2_5,
            pm10: item.pm10,
            dBA: item.dBA,
            vibration: item.vibration
          }));
          console.log('Fetched sensor data:', realSensorData.length, 'records, latest timestamp:', realSensorData[0]?.timestamp);
          setSensorData(realSensorData);
        }
      } catch (sensorError) {
        console.log('Sensor data not available:', sensorError);
        setError('Consumer API not available. Please ensure the consumer service is running.');
      }

      // Fetch real anomalies from consumer API
      try {
        const anomaliesResponse = await axios.get(`${consumerApiUrl}/api/anomalies?limit=50`);
        console.log('Raw anomalies response:', anomaliesResponse.data);
        if (anomaliesResponse.data.data) {
          const realAnomalies: AnomalyData[] = anomaliesResponse.data.data.map((item: any) => ({
            id: item.id,
            device_id: item.device_id,
            timestamp: item.timestamp,
            anomaly_type: item.anomaly_type,
            sensor_field: item.sensor_field,
            value: item.value,
            threshold: item.threshold,
            severity: item.severity || 'medium',
            llm_decision: item.llm_decision,
            created_at: item.created_at
          }));
          setAnomalies(realAnomalies);
        }
      } catch (anomaliesError) {
        console.log('Anomalies data not available:', anomaliesError);
        if (!error) {
          setError('Consumer API not available. Please ensure the consumer service is running.');
        }
      }

      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error fetching data:', error);
      setError('Failed to fetch data. Please check if the services are running.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [fetchData]);

  // Use server-side system health status
  const getSystemHealth = () => {
    return systemHealth?.status || 'unknown';
  };

  // Get unique sensor IDs
  const sensorIds = Array.from(new Set(sensorData.map(data => data.device_id)));
  
  // Use server-side data rate and alerts
  const dataRate = systemHealth?.data_rate_per_minute || 0;
  const recentAlerts = systemHealth?.total_alerts || 0;

  return (
    <>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          <AlertTitle>Connection Error</AlertTitle>
          {error}
          <Box sx={{ mt: 1 }}>
            <Typography variant="body2">
              Please ensure the following services are running:
            </Typography>
            <Typography variant="body2">• Consumer service on port 8001</Typography>
            <Typography variant="body2">• RabbitMQ on port 5672</Typography>
            <Typography variant="body2">• Generator service</Typography>
          </Box>
        </Alert>
      )}

      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static" sx={{ background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)' }}>
          <Toolbar>
            <SensorsIcon sx={{ mr: 2, fontSize: 32 }} />
            <Typography variant="h5" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
              SmartSensor Real-Time Dashboard
            </Typography>
            <Tooltip title="Settings">
              <IconButton color="inherit">
                <SettingsIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Refresh Data">
              <IconButton color="inherit" onClick={fetchData} disabled={loading}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Toolbar>
        </AppBar>

        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            
            {/* Service Health Grid */}
            <ServiceHealthGrid />
            
            {/* Sensor Grid */}
            <SensorGrid
              sensorData={sensorData}
              anomalies={anomalies}
              onSensorClick={setSelectedSensor}
            />

            {/* Detailed Sensor View */}
            {selectedSensor && (
              <SensorDetailView
                deviceId={selectedSensor}
                sensorData={sensorData}
                anomalies={anomalies}
                onClose={() => setSelectedSensor(null)}
              />
            )}
          </Box>

          {/* Last Update Footer */}
          <Box sx={{ mt: 4, textAlign: 'center' }}>
            <Typography variant="body2" color="textSecondary">
              Last updated: {lastUpdate.toLocaleString()}
              {loading && <CircularProgress size={16} sx={{ ml: 1 }} />}
            </Typography>
          </Box>
        </Container>
      </Box>
    </>
  );
};

export default App;
