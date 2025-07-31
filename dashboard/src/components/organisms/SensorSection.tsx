import React from 'react';
import { Paper, Box, Divider, Grid, Typography, Chip, Alert } from '@mui/material';
import { Warning, CheckCircle, Error } from '@mui/icons-material';
import SensorHeader from '../molecules/SensorHeader';
import ChartGrid from '../molecules/ChartGrid';
import AlertsSection from '../molecules/AlertsSection';
import ValueGrid from '../molecules/ValueGrid';

interface SensorData {
  device_id: string;
  timestamp: string;
  pm2_5: number;
  pm10: number;
  dBA: number;
  vibration: number;
}

interface AnomalyData {
  device_id: string;
  anomaly: string;
  timestamp: string;
  severity: 'low' | 'medium' | 'high';
}

interface SensorSectionProps {
  sensorId: string;
  sensorData: SensorData[];
  anomalies: AnomalyData[];
}

const SensorSection: React.FC<SensorSectionProps> = ({ 
  sensorId, 
  sensorData, 
  anomalies 
}) => {
  const latestData = sensorData[sensorData.length - 1];
  const recentData = sensorData.slice(-10); // Last 10 readings
  const recentAnomalies = anomalies.slice(-5); // Last 5 anomalies

  // Calculate sensor status
  const getSensorStatus = () => {
    if (!latestData) return { status: 'offline', color: 'error', icon: <Error /> };
    
    const now = new Date();
    const lastReading = new Date(latestData.timestamp + 'Z'); // Ensure UTC parsing
    const timeDiff = now.getTime() - lastReading.getTime();
    
    if (timeDiff < 30000) { // Less than 30 seconds
      return { status: 'online', color: 'success', icon: <CheckCircle /> };
    } else if (timeDiff < 300000) { // Less than 5 minutes
      return { status: 'warning', color: 'warning', icon: <Warning /> };
    } else {
      return { status: 'offline', color: 'error', icon: <Error /> };
    }
  };

  const sensorStatus = getSensorStatus();

  // Calculate statistics
  const getStatistics = () => {
    if (sensorData.length === 0) return null;
    
    const values = {
      pm2_5: sensorData.map(d => d.pm2_5),
      pm10: sensorData.map(d => d.pm10),
      dBA: sensorData.map(d => d.dBA),
      vibration: sensorData.map(d => d.vibration)
    };

    const calculateStats = (arr: number[]) => ({
      min: Math.min(...arr),
      max: Math.max(...arr),
      avg: arr.reduce((a, b) => a + b, 0) / arr.length
    });

    return {
      pm2_5: calculateStats(values.pm2_5),
      pm10: calculateStats(values.pm10),
      dBA: calculateStats(values.dBA),
      vibration: calculateStats(values.vibration)
    };
  };

  const stats = getStatistics();

  return (
    <Paper sx={{ p: 3, mb: 3, border: `2px solid ${sensorStatus.color === 'success' ? '#4caf50' : sensorStatus.color === 'warning' ? '#ff9800' : '#f44336'}` }}>
      {/* Enhanced Header with Status */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <SensorHeader
          sensorId={sensorId}
          readingsCount={sensorData.length}
          alertsCount={anomalies.length}
        />
        <Chip
          icon={sensorStatus.icon}
          label={sensorStatus.status.toUpperCase()}
          color={sensorStatus.color as any}
          variant="outlined"
          sx={{ fontWeight: 'bold' }}
        />
      </Box>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {/* Statistics Summary */}
        {stats && (
          <Box>
            <Typography variant="h6" gutterBottom sx={{ mb: 2, color: 'primary.main' }}>
              Sensor Statistics (Last {sensorData.length} Readings)
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              {Object.entries(stats).map(([sensor, stat]) => (
                <Box key={sensor} sx={{ flex: '1 1 200px', minWidth: '200px' }}>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'grey.50' }}>
                    <Typography variant="subtitle2" color="primary" gutterBottom>
                      {sensor.toUpperCase()}
                    </Typography>
                    <Typography variant="body2">
                      Min: {stat.min.toFixed(2)} | Max: {stat.max.toFixed(2)}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Avg: {stat.avg.toFixed(2)}
                    </Typography>
                  </Paper>
                </Box>
              ))}
            </Box>
          </Box>
        )}

        <Divider sx={{ my: 2, width: '100%' }} />

        {/* Charts Section */}
        <ChartGrid data={sensorData} />

        <Divider sx={{ my: 2, width: '100%' }} />

        {/* Recent Data Section */}
        <Box>
          <Typography variant="h6" gutterBottom sx={{ mb: 2, color: 'primary.main' }}>
            📋 Recent Sensor Readings
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
            {recentData.slice().reverse().map((data, index) => (
              <Box key={index} sx={{ flex: '1 1 300px', minWidth: '300px' }}>
                <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                  <Typography variant="caption" color="textSecondary">
                    {new Date(data.timestamp + 'Z').toLocaleString('en-US', {
                      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    })}
                  </Typography>
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="body2">PM2.5: {data.pm2_5.toFixed(2)}</Typography>
                    <Typography variant="body2">PM10: {data.pm10.toFixed(2)}</Typography>
                    <Typography variant="body2">dBA: {data.dBA.toFixed(2)}</Typography>
                    <Typography variant="body2">Vibration: {data.vibration.toFixed(3)}</Typography>
                  </Box>
                </Paper>
              </Box>
            ))}
          </Box>
        </Box>

        <Divider sx={{ my: 2, width: '100%' }} />

        {/* Recent Anomalies Section */}
        <Box>
          <Typography variant="h6" gutterBottom sx={{ mb: 2, color: 'error.main' }}>
            🚨 Recent Anomalies & Alerts
          </Typography>
          {recentAnomalies.length > 0 ? (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              {recentAnomalies.map((anomaly, index) => (
                <Box key={index} sx={{ flex: '1 1 300px', minWidth: '300px' }}>
                  <Alert severity={anomaly.severity === 'low' ? 'info' : anomaly.severity === 'medium' ? 'warning' : 'error'} sx={{ mb: 1 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      {new Date(anomaly.timestamp + 'Z').toLocaleString('en-US', {
                        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                      })}
                    </Typography>
                    <Typography variant="body2">
                      {anomaly.anomaly}
                    </Typography>
                  </Alert>
                </Box>
              ))}
            </Box>
          ) : (
            <Alert severity="success">
              No recent anomalies detected for this sensor.
            </Alert>
          )}
        </Box>

        <Divider sx={{ my: 2, width: '100%' }} />

        {/* Latest Reading Summary */}
        {latestData && (
          <Box>
            <Typography variant="h6" gutterBottom sx={{ mb: 2, color: 'primary.main' }}>
              📈 Latest Reading
            </Typography>
            <ValueGrid data={latestData} />
          </Box>
        )}
      </Box>
    </Paper>
  );
};

export default SensorSection; 