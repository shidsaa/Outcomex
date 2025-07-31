import React from 'react';
import { Box, Container, AppBar, Toolbar, Typography, IconButton, Tooltip, CircularProgress } from '@mui/material';
import { Refresh as RefreshIcon, Sensors as SensorsIcon } from '@mui/icons-material';
import SystemMetrics from '../organisms/SystemMetrics';
import SensorSection from '../organisms/SensorSection';
import SensorDataTable from '../organisms/SensorDataTable';

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

interface SystemMetricsData {
  total_records_processed: number;
  total_alerts_generated: number;
  last_processing_time: string;
  uptime: string;
}

interface DashboardLayoutProps {
  sensorData: SensorData[];
  anomalies: AnomalyData[];
  systemMetrics: SystemMetricsData | null;
  queueMessageCount: number;
  loading: boolean;
  lastUpdate: Date;
  onRefresh: () => void;
}

const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  sensorData,
  anomalies,
  systemMetrics,
  queueMessageCount,
  loading,
  lastUpdate,
  onRefresh
}) => {
  // Group sensor data by device_id
  const sensorGroups = sensorData.reduce((groups, data) => {
    const deviceId = data.device_id;
    if (!groups[deviceId]) {
      groups[deviceId] = [];
    }
    groups[deviceId].push(data);
    return groups;
  }, {} as Record<string, SensorData[]>);

  // Group anomalies by device_id
  const anomalyGroups = anomalies.reduce((groups, anomaly) => {
    const deviceId = anomaly.device_id;
    if (!groups[deviceId]) {
      groups[deviceId] = [];
    }
    groups[deviceId].push(anomaly);
    return groups;
  }, {} as Record<string, AnomalyData[]>);

  // Get unique sensor IDs
  const sensorIds = Object.keys(sensorGroups);

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static" sx={{ background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)' }}>
        <Toolbar>
          <SensorsIcon sx={{ mr: 2, fontSize: 32 }} />
          <Typography variant="h5" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
            SmartSensor Real-Time Dashboard
          </Typography>
          <Tooltip title="Refresh Data">
            <IconButton color="inherit" onClick={onRefresh} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* System Metrics */}
          <SystemMetrics
            queueMessageCount={queueMessageCount}
            totalProcessed={systemMetrics?.total_records_processed || 0}
            totalAlerts={systemMetrics?.total_alerts_generated || 0}
          />

          {/* Sensor Sections */}
          {sensorIds.map((sensorId) => (
            <SensorSection
              key={sensorId}
              sensorId={sensorId}
              sensorData={sensorGroups[sensorId] || []}
              anomalies={anomalyGroups[sensorId] || []}
            />
          ))}

          {/* Sensor Data Table */}
          <SensorDataTable data={sensorData} />
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
  );
};

export default DashboardLayout; 