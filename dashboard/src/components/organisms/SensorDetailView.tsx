import React from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Chip, 
  IconButton,
  Collapse,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Card,
  CardContent,
  Tooltip,
  Alert,
  AlertTitle
} from '@mui/material';
import { 
  Close as CloseIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Psychology as PsychologyIcon,
  Sensors as SensorsIcon,
  Timeline as TimelineIcon
} from '@mui/icons-material';
import DataTable from '../atoms/DataTable';
import SensorChart from '../atoms/SensorChart';

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

interface SensorDetailViewProps {
  deviceId: string;
  sensorData: SensorData[];
  anomalies: AnomalyData[];
  onClose: () => void;
}

const SensorDetailView: React.FC<SensorDetailViewProps> = ({
  deviceId,
  sensorData,
  anomalies,
  onClose
}) => {
  const [expanded, setExpanded] = React.useState(true); // Show charts by default
  const [timeFrames, setTimeFrames] = React.useState({
    pm2_5: '15min' as '5min' | '15min' | '1hour' | '6hours' | '24hours',
    pm10: '15min' as '5min' | '15min' | '1hour' | '6hours' | '24hours',
    dBA: '15min' as '5min' | '15min' | '1hour' | '6hours' | '24hours',
    vibration: '15min' as '5min' | '15min' | '1hour' | '6hours' | '24hours'
  });
  const [renderKey, setRenderKey] = React.useState(0);
  
  // Force re-render when time frames change
  React.useEffect(() => {
    console.log('Time frames changed, forcing re-render:', timeFrames);
    setRenderKey(prev => prev + 1);
  }, [timeFrames.pm2_5, timeFrames.pm10, timeFrames.dBA, timeFrames.vibration]);

  // Get data points based on selected time frame for a specific sensor
  const getTimeFrameData = (sensorType: string) => {
    const now = new Date();
    let cutoffTime: Date;
    const timeFrame = timeFrames[sensorType as keyof typeof timeFrames];
    
    switch (timeFrame) {
      case '5min':
        cutoffTime = new Date(now.getTime() - 5 * 60 * 1000);
        break;
      case '15min':
        cutoffTime = new Date(now.getTime() - 15 * 60 * 1000);
        break;
      case '1hour':
        cutoffTime = new Date(now.getTime() - 60 * 60 * 1000);
        break;
      case '6hours':
        cutoffTime = new Date(now.getTime() - 6 * 60 * 60 * 1000);
        break;
      case '24hours':
        cutoffTime = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        break;
      default:
        cutoffTime = new Date(now.getTime() - 15 * 60 * 1000);
    }
    
    const deviceData = sensorData.filter(data => data.device_id === deviceId);
    
    // If no data in the time frame, use all available data for this device
    let timeFilteredData = deviceData.filter(data => new Date(data.timestamp + 'Z') >= cutoffTime);
    
    // If still no data, use the last 10 readings regardless of time
    if (timeFilteredData.length === 0) {
      timeFilteredData = deviceData.slice(-10);
    }
    
    const sortedData = timeFilteredData.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    
    console.log(`${sensorType} filtering:`, {
      timeFrame,
      cutoffTime: cutoffTime.toISOString(),
      totalDeviceData: deviceData.length,
      timeFilteredData: timeFilteredData.length,
      firstTimestamp: timeFilteredData[0]?.timestamp,
      lastTimestamp: timeFilteredData[timeFilteredData.length - 1]?.timestamp
    });
    
    return sortedData;
  };

  // Get data for each sensor type with their individual time frames
  const pm25Data = getTimeFrameData('pm2_5');
  const pm10Data = getTimeFrameData('pm10');
  const dbaData = getTimeFrameData('dBA');
  const vibrationData = getTimeFrameData('vibration');
  
  // Debug logging
  console.log('Time frames:', timeFrames);
  console.log('PM2.5 data points:', pm25Data.length, 'time frame:', timeFrames.pm2_5, 'first:', pm25Data[0]?.timestamp, 'last:', pm25Data[pm25Data.length-1]?.timestamp);
  console.log('PM10 data points:', pm10Data.length, 'time frame:', timeFrames.pm10, 'first:', pm10Data[0]?.timestamp, 'last:', pm10Data[pm10Data.length-1]?.timestamp);
  console.log('dBA data points:', dbaData.length, 'time frame:', timeFrames.dBA, 'first:', dbaData[0]?.timestamp, 'last:', dbaData[dbaData.length-1]?.timestamp);
  console.log('Vibration data points:', vibrationData.length, 'time frame:', timeFrames.vibration, 'first:', vibrationData[0]?.timestamp, 'last:', vibrationData[vibrationData.length-1]?.timestamp);
  
  // Get the actual latest reading from all data for this device (not filtered by time frame)
  const allDeviceData = sensorData.filter(data => data.device_id === deviceId);
  const latestDeviceData = allDeviceData.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  
  // Use pm25Data for time-frame filtered data (for charts and tables)
  const recentData = pm25Data;

  // Force re-render when data changes
  React.useEffect(() => {
    console.log('Data changed, forcing re-render. PM2.5:', pm25Data.length, 'PM10:', pm10Data.length, 'dBA:', dbaData.length, 'Vibration:', vibrationData.length);
    setRenderKey(prev => prev + 1);
  }, [pm25Data.length, pm10Data.length, dbaData.length, vibrationData.length]);

  // Get anomalies for this sensor from database
  const sensorAnomalies = anomalies
    .filter(anomaly => anomaly.device_id === deviceId)
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 10);

  // Determine sensor status based on database anomalies (not client-side calculations)
  const getSensorStatus = (): 'normal' | 'warning' | 'critical' => {
    const now = new Date();
    
    // Check if there are recent critical anomalies in database
    const recentCriticalAnomalies = anomalies.filter(anomaly => 
      anomaly.device_id === deviceId && 
      (anomaly.severity === 'high' || anomaly.severity === 'critical') &&
      now.getTime() - new Date(anomaly.timestamp).getTime() < 300000 // Last 5 minutes
    );
    
    if (recentCriticalAnomalies.length > 0) return 'critical';
    
    // Check if there are recent warning anomalies in database
    const recentWarningAnomalies = anomalies.filter(anomaly => 
      anomaly.device_id === deviceId && 
      (anomaly.severity === 'medium' || anomaly.severity === 'warning') &&
      now.getTime() - new Date(anomaly.timestamp).getTime() < 300000 // Last 5 minutes
    );
    
    if (recentWarningAnomalies.length > 0) return 'warning';
    
    return 'normal';
  };

  // Use recent data without status for the readings table
  const readingsData = recentData;



  const latestData = latestDeviceData[0];
  const status = getSensorStatus();

  const getStatusColor = () => {
    switch (status) {
      case 'normal': return '#4CAF50';
      case 'warning': return '#FF9800';
      case 'critical': return '#F44336';
      default: return '#9E9E9E';
    }
  };

  return (
    <Paper sx={{ p: 3, mb: 3, border: `2px solid ${getStatusColor()}` }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
          {deviceId} - Detailed Analysis
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip
            label={status.toUpperCase()}
            color={status === 'critical' ? 'error' : status === 'warning' ? 'warning' : 'success'}
            size="small"
          />
          <IconButton onClick={() => setExpanded(!expanded)} size="small">
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </Box>



      {/* Real-time data display */}
      {latestData && (
        <Box sx={{ mb: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
            REAL-TIME DATA (Updates every 5s)
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 2 }}>
            <Box>
              <Typography variant="caption" color="textSecondary">PM2.5</Typography>
              <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                {latestData.pm2_5.toFixed(1)} μg/m³
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="textSecondary">PM10</Typography>
              <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                {latestData.pm10.toFixed(1)} μg/m³
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="textSecondary">dBA</Typography>
              <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                {latestData.dBA.toFixed(1)} dB
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="textSecondary">Vibration</Typography>
              <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                {latestData.vibration.toFixed(3)}
              </Typography>
            </Box>
          </Box>
          <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
            Updated: {new Date(latestData.timestamp + 'Z').toLocaleTimeString('en-US', {
              timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
            })} | Next: {new Date(Date.now() + 5000).toLocaleTimeString('en-US', {
              timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
            })}
          </Typography>
        </Box>
      )}

      {/* Last 10 readings table */}
      <Box sx={{ mb: 3 }}>
        <DataTable 
          data={readingsData.slice(-10).reverse()} // Show last 10 in table, latest first
          title={`Last 10 Readings (${recentData.length} total available)`}
          showStatus={false}
        />
      </Box>

      {/* Trend charts */}
      <Collapse in={expanded}>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
            📈 Individual Sensor Trends
          </Typography>
          
          {/* PM2.5 Chart with individual time frame control */}
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
              <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>PM2.5 Time Frame</InputLabel>
                <Select
                  value={timeFrames.pm2_5}
                  label="PM2.5 Time Frame"
                  onChange={(e) => {
                    setTimeFrames(prev => ({ ...prev, pm2_5: e.target.value as any }));
                  }}
                >
                  <MenuItem value="5min">Last 5 minutes</MenuItem>
                  <MenuItem value="15min">Last 15 minutes</MenuItem>
                  <MenuItem value="1hour">Last 1 hour</MenuItem>
                  <MenuItem value="6hours">Last 6 hours</MenuItem>
                  <MenuItem value="24hours">Last 24 hours</MenuItem>
                </Select>
              </FormControl>
              <Typography variant="body2" color="textSecondary">
                {pm25Data.length} data points
              </Typography>
            </Box>
            <Box sx={{ minHeight: 250 }}>
              <SensorChart
                key={`pm2_5-${timeFrames.pm2_5}-${pm25Data.length}-${pm25Data[0]?.timestamp}-${pm25Data[pm25Data.length-1]?.timestamp}-${renderKey}`}
                data={(() => {
                  const chartData = pm25Data.map(data => ({
                    timestamp: new Date(data.timestamp + 'Z').toLocaleTimeString('en-US', { 
                      hour12: false, 
                      hour: '2-digit', 
                      minute: '2-digit', 
                      second: '2-digit',
                      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    }),
                    pm2_5: Number(data.pm2_5) || 0,
                    pm10: Number(data.pm10) || 0,
                    dBA: Number(data.dBA) || 0,
                    vibration: Number(data.vibration) || 0
                  }));
                  console.log('PM2.5 chart data:', chartData.length, 'points, time frame:', timeFrames.pm2_5);
                  return chartData;
                })()}
                dataKey="pm2_5"
                title="PM2.5 Trend"
                color="#2196F3"
                height={250}
              />
            </Box>
          </Box>

          {/* PM10 Chart with individual time frame control */}
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
              <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>PM10 Time Frame</InputLabel>
                <Select
                  value={timeFrames.pm10}
                  label="PM10 Time Frame"
                  onChange={(e) => {
                    setTimeFrames(prev => ({ ...prev, pm10: e.target.value as any }));
                  }}
                >
                  <MenuItem value="5min">Last 5 minutes</MenuItem>
                  <MenuItem value="15min">Last 15 minutes</MenuItem>
                  <MenuItem value="1hour">Last 1 hour</MenuItem>
                  <MenuItem value="6hours">Last 6 hours</MenuItem>
                  <MenuItem value="24hours">Last 24 hours</MenuItem>
                </Select>
              </FormControl>
              <Typography variant="body2" color="textSecondary">
                {pm10Data.length} data points
              </Typography>
            </Box>
            <Box sx={{ minHeight: 250 }}>
              <SensorChart
                key={`pm10-${timeFrames.pm10}-${pm10Data.length}-${pm10Data[0]?.timestamp}-${pm10Data[pm10Data.length-1]?.timestamp}-${renderKey}`}
                data={(() => {
                  const chartData = pm10Data.map(data => ({
                    timestamp: new Date(data.timestamp + 'Z').toLocaleTimeString('en-US', { 
                      hour12: false, 
                      hour: '2-digit', 
                      minute: '2-digit', 
                      second: '2-digit',
                      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    }),
                    pm2_5: Number(data.pm2_5) || 0,
                    pm10: Number(data.pm10) || 0,
                    dBA: Number(data.dBA) || 0,
                    vibration: Number(data.vibration) || 0
                  }));
                  console.log('PM10 chart data:', chartData.length, 'points, time frame:', timeFrames.pm10);
                  return chartData;
                })()}
                dataKey="pm10"
                title="PM10 Trend"
                color="#4CAF50"
                height={250}
              />
            </Box>
          </Box>

          {/* dBA Chart with individual time frame control */}
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
              <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>dBA Time Frame</InputLabel>
                <Select
                  value={timeFrames.dBA}
                  label="dBA Time Frame"
                  onChange={(e) => {
                    setTimeFrames(prev => ({ ...prev, dBA: e.target.value as any }));
                  }}
                >
                  <MenuItem value="5min">Last 5 minutes</MenuItem>
                  <MenuItem value="15min">Last 15 minutes</MenuItem>
                  <MenuItem value="1hour">Last 1 hour</MenuItem>
                  <MenuItem value="6hours">Last 6 hours</MenuItem>
                  <MenuItem value="24hours">Last 24 hours</MenuItem>
                </Select>
              </FormControl>
              <Typography variant="body2" color="textSecondary">
                {dbaData.length} data points
              </Typography>
            </Box>
            <Box sx={{ minHeight: 250 }}>
              <SensorChart
                key={`dBA-${timeFrames.dBA}-${dbaData.length}-${dbaData[0]?.timestamp}-${dbaData[dbaData.length-1]?.timestamp}-${renderKey}`}
                data={(() => {
                  const chartData = dbaData.map(data => ({
                    timestamp: new Date(data.timestamp + 'Z').toLocaleTimeString('en-US', { 
                      hour12: false, 
                      hour: '2-digit', 
                      minute: '2-digit', 
                      second: '2-digit',
                      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    }),
                    pm2_5: Number(data.pm2_5) || 0,
                    pm10: Number(data.pm10) || 0,
                    dBA: Number(data.dBA) || 0,
                    vibration: Number(data.vibration) || 0
                  }));
                  console.log('dBA chart data:', chartData.length, 'points, time frame:', timeFrames.dBA);
                  return chartData;
                })()}
                dataKey="dBA"
                title="dBA Trend"
                color="#FF9800"
                height={250}
              />
            </Box>
          </Box>

          {/* Vibration Chart with individual time frame control */}
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
              <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>Vibration Time Frame</InputLabel>
                <Select
                  value={timeFrames.vibration}
                  label="Vibration Time Frame"
                  onChange={(e) => {
                    setTimeFrames(prev => ({ ...prev, vibration: e.target.value as any }));
                  }}
                >
                  <MenuItem value="5min">Last 5 minutes</MenuItem>
                  <MenuItem value="15min">Last 15 minutes</MenuItem>
                  <MenuItem value="1hour">Last 1 hour</MenuItem>
                  <MenuItem value="6hours">Last 6 hours</MenuItem>
                  <MenuItem value="24hours">Last 24 hours</MenuItem>
                </Select>
              </FormControl>
              <Typography variant="body2" color="textSecondary">
                {vibrationData.length} data points
              </Typography>
            </Box>
            <Box sx={{ minHeight: 250 }}>
              <SensorChart
                key={`vibration-${timeFrames.vibration}-${vibrationData.length}-${vibrationData[0]?.timestamp}-${vibrationData[vibrationData.length-1]?.timestamp}-${renderKey}`}
                data={(() => {
                  const chartData = vibrationData.map(data => ({
                    timestamp: new Date(data.timestamp + 'Z').toLocaleTimeString('en-US', { 
                      hour12: false, 
                      hour: '2-digit', 
                      minute: '2-digit', 
                      second: '2-digit',
                      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                    }),
                    pm2_5: Number(data.pm2_5) || 0,
                    pm10: Number(data.pm10) || 0,
                    dBA: Number(data.dBA) || 0,
                    vibration: Number(data.vibration) || 0
                  }));
                  console.log('Vibration chart data:', chartData.length, 'points, time frame:', timeFrames.vibration);
                  return chartData;
                })()}
                dataKey="vibration"
                title="Vibration Trend"
                color="#F44336"
                height={250}
              />
            </Box>
          </Box>
        </Box>
      </Collapse>

      {/* Enhanced Recent Alerts Section */}
      {sensorAnomalies.length > 0 && (
        <Box>
          <Typography variant="h6" sx={{ mb: 3, fontWeight: 'bold' }}>
            🚨 RECENT ALERTS ({sensorAnomalies.length})
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {sensorAnomalies.slice(0, 10).map((anomaly) => (
              <Card 
                key={anomaly.id}
                sx={{ 
                  border: `2px solid ${
                    anomaly.severity === 'critical' || anomaly.severity === 'high' 
                      ? '#f44336' 
                      : anomaly.severity === 'medium' || anomaly.severity === 'warning'
                      ? '#ff9800'
                      : '#2196f3'
                  }`,
                  '&:hover': {
                    boxShadow: 2,
                    transition: 'all 0.2s ease-in-out'
                  }
                }}
              >
                <CardContent sx={{ py: 1, px: 2 }}>
                  {/* Line 1: Basic Info */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                    {/* Severity Chip */}
                    <Chip
                      icon={anomaly.severity === 'critical' || anomaly.severity === 'high' ? <ErrorIcon /> : 
                            anomaly.severity === 'medium' || anomaly.severity === 'warning' ? <WarningIcon /> : 
                            <InfoIcon />}
                      label={anomaly.severity.toUpperCase()}
                      color={anomaly.severity === 'critical' || anomaly.severity === 'high' ? 'error' : 
                             anomaly.severity === 'medium' || anomaly.severity === 'warning' ? 'warning' : 
                             'info' as any}
                      size="small"
                      sx={{ fontWeight: 'bold', minWidth: 70 }}
                    />

                    {/* Time */}
                    <Typography variant="caption" color="textSecondary" sx={{ minWidth: 120 }}>
                      {new Date(anomaly.timestamp + 'Z').toLocaleString('en-US', {
                        year: 'numeric',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                      })}
                    </Typography>

                    {/* Device */}
                    <Typography variant="body2" sx={{ fontWeight: 'bold', minWidth: 70 }}>
                      {anomaly.device_id}
                    </Typography>

                    {/* Type */}
                    <Chip
                      label={anomaly.anomaly_type === 'ml_detection' ? 'ML Detection' :
                             anomaly.anomaly_type === 'ml_overall' ? 'ML Overall' :
                             anomaly.anomaly_type === 'threshold' ? 'Threshold' :
                             anomaly.anomaly_type === 'sensor_health' ? 'Sensor Health' :
                             anomaly.anomaly_type.replace('_', ' ').toUpperCase()}
                      size="small"
                      variant="outlined"
                      sx={{ fontSize: '0.7rem', minWidth: 80 }}
                    />

                    {/* Sensor Field and Value */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <TimelineIcon sx={{ fontSize: 12 }} />
                      <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                        <strong>{anomaly.sensor_field === 'unknown' ? 'Overall' : 
                               anomaly.sensor_field === 'pm2_5' ? 'PM2.5' :
                               anomaly.sensor_field === 'pm10' ? 'PM10' :
                               anomaly.sensor_field === 'dBA' ? 'dBA' :
                               anomaly.sensor_field === 'vibration' ? 'Vibration' :
                               anomaly.sensor_field}</strong>: {anomaly.value.toFixed(3)}
                      </Typography>
                    </Box>

                    {/* Confidence */}
                    <Chip
                      label={anomaly.severity === 'critical' || anomaly.severity === 'high' ? 'High' :
                             anomaly.severity === 'medium' || anomaly.severity === 'warning' ? 'Medium' :
                             'Low'}
                      size="small"
                      color={anomaly.severity === 'critical' || anomaly.severity === 'high' ? 'error' : 
                             anomaly.severity === 'medium' || anomaly.severity === 'warning' ? 'warning' : 
                             'info' as any}
                      variant="outlined"
                      sx={{ fontSize: '0.6rem', minWidth: 50 }}
                    />

                    {/* Alert ID */}
                    <Typography variant="caption" color="textSecondary" sx={{ minWidth: 40 }}>
                      ID: {anomaly.id}
                    </Typography>
                  </Box>

                  {/* Line 2: LLM Decision (if available) */}
                  {anomaly.llm_decision && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, pl: 1 }}>
                      <PsychologyIcon sx={{ fontSize: 12, color: '#9c27b0' }} />
                      <Typography variant="body2" sx={{ 
                        fontStyle: 'italic',
                        color: '#9c27b0',
                        fontSize: '0.75rem',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        flex: 1
                      }}>
                        {anomaly.llm_decision}
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            ))}
          </Box>
          
          {/* Show more indicator */}
          {sensorAnomalies.length > 10 && (
            <Alert severity="info" sx={{ mt: 2 }}>
              <AlertTitle>More Alerts Available</AlertTitle>
              Showing 10 most recent alerts out of {sensorAnomalies.length} total alerts for this sensor.
            </Alert>
          )}
        </Box>
      )}
    </Paper>
  );
};

export default SensorDetailView; 