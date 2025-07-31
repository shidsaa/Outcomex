import React from 'react';
import { Box, Typography } from '@mui/material';
import SensorCard from '../atoms/SensorCard';

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

interface SensorGridProps {
  sensorData: SensorData[];
  anomalies: AnomalyData[];
  onSensorClick?: (deviceId: string) => void;
}

const SensorGrid: React.FC<SensorGridProps> = ({
  sensorData,
  anomalies,
  onSensorClick
}) => {
  // Group sensor data by device_id and get the latest reading for each
  const sensorGroups = sensorData.reduce((groups, data) => {
    const deviceId = data.device_id;
    if (!groups[deviceId] || new Date(data.timestamp + 'Z') > new Date(groups[deviceId].timestamp + 'Z')) {
      groups[deviceId] = data;
    }
    return groups;
  }, {} as Record<string, SensorData>);

  // Count anomalies per device from database
  const anomalyCounts = anomalies.reduce((counts, anomaly) => {
    const deviceId = anomaly.device_id;
    counts[deviceId] = (counts[deviceId] || 0) + 1;
    return counts;
  }, {} as Record<string, number>);

  // Determine sensor status based on database anomalies (not client-side calculations)
  const getSensorStatus = (deviceId: string, data: SensorData): 'normal' | 'warning' | 'critical' | 'offline' => {
    const now = new Date();
    const dataTime = new Date(data.timestamp + 'Z');
    const timeDiff = now.getTime() - dataTime.getTime();
    
    // If no data in last 30 seconds, consider offline
    if (timeDiff > 30000) return 'offline';
    
    // Check if there are recent critical anomalies in database
    const recentCriticalAnomalies = anomalies.filter(anomaly => 
      anomaly.device_id === deviceId && 
      (anomaly.severity === 'high' || anomaly.severity === 'critical') &&
      now.getTime() - new Date(anomaly.timestamp + 'Z').getTime() < 300000 // Last 5 minutes
    );
    
    if (recentCriticalAnomalies.length > 0) return 'critical';
    
    // Check if there are recent warning anomalies in database
    const recentWarningAnomalies = anomalies.filter(anomaly => 
      anomaly.device_id === deviceId && 
      (anomaly.severity === 'medium' || anomaly.severity === 'warning') &&
      now.getTime() - new Date(anomaly.timestamp + 'Z').getTime() < 300000 // Last 5 minutes
    );
    
    if (recentWarningAnomalies.length > 0) return 'warning';
    
    return 'normal';
  };

  // Sort sensor IDs to ensure consistent order: sensor-1, sensor-2, sensor-3
  const sensorIds = Object.keys(sensorGroups).sort((a, b) => {
    // Extract numbers from sensor IDs (e.g., "sensor-1" -> 1, "sensor-2" -> 2)
    const numA = parseInt(a.replace(/\D/g, '')) || 0;
    const numB = parseInt(b.replace(/\D/g, '')) || 0;
    return numA - numB;
  });

  if (sensorIds.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="h6" color="textSecondary">
          No sensor data available
        </Typography>
        <Typography variant="body2" color="textSecondary">
          Waiting for sensor data to be processed...
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 3, fontWeight: 'bold' }}>
        📍 SENSOR LOCATIONS ({sensorIds.length} Active)
      </Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 3 }}>
        {sensorIds.map((deviceId) => {
          const data = sensorGroups[deviceId];
          const status = getSensorStatus(deviceId, data);

          return (
            <Box key={deviceId}>
              <SensorCard
                deviceId={deviceId}
                currentData={{
                  pm2_5: data.pm2_5,
                  pm10: data.pm10,
                  dBA: data.dBA,
                  vibration: data.vibration,
                  timestamp: data.timestamp
                }}
                status={status}
                onClick={() => onSensorClick?.(deviceId)}
              />
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};

export default SensorGrid; 