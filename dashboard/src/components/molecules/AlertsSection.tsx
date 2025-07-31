import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Grid,
  Tooltip,
  IconButton,
  Collapse,
  Alert,
  AlertTitle
} from '@mui/material';
import {
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Psychology as PsychologyIcon,
  Sensors as SensorsIcon,
  Timeline as TimelineIcon
} from '@mui/icons-material';

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

interface AlertsSectionProps {
  anomalies: AnomalyData[];
  maxDisplay?: number;
}

const AlertsSection: React.FC<AlertsSectionProps> = ({ 
  anomalies, 
  maxDisplay = 10 
}) => {
  const [expandedAlerts, setExpandedAlerts] = React.useState<Set<number>>(new Set());

  const toggleAlertExpansion = (alertId: number) => {
    const newExpanded = new Set(expandedAlerts);
    if (newExpanded.has(alertId)) {
      newExpanded.delete(alertId);
    } else {
      newExpanded.add(alertId);
    }
    setExpandedAlerts(newExpanded);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
      case 'high':
        return 'error';
      case 'medium':
      case 'warning':
        return 'warning';
      case 'low':
      case 'info':
        return 'info';
      default:
        return 'default';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
      case 'high':
        return <ErrorIcon />;
      case 'medium':
      case 'warning':
        return <WarningIcon />;
      case 'low':
      case 'info':
        return <InfoIcon />;
      default:
        return <InfoIcon />;
    }
  };

  const getAnomalyTypeLabel = (type: string) => {
    switch (type) {
      case 'ml_detection':
        return 'ML Detection';
      case 'ml_overall':
        return 'ML Overall';
      case 'threshold':
        return 'Threshold';
      case 'sensor_health':
        return 'Sensor Health';
      default:
        return type.replace('_', ' ').toUpperCase();
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getTimeAgo = (timestamp: string) => {
    const now = new Date();
    const alertTime = new Date(timestamp);
    const diffMs = now.getTime() - alertTime.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `${diffDays}d ago`;
    if (diffHours > 0) return `${diffHours}h ago`;
    if (diffMins > 0) return `${diffMins}m ago`;
    return 'Just now';
  };

  const recentAnomalies = anomalies
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, maxDisplay);

  if (recentAnomalies.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="h6" color="textSecondary">
          No recent alerts
        </Typography>
        <Typography variant="body2" color="textSecondary">
          All systems are operating normally
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 'bold', mr: 2 }}>
          🚨 RECENT ALERTS ({recentAnomalies.length})
        </Typography>
        <Chip 
          label={`${anomalies.length} total`}
          size="small"
          color="primary"
          variant="outlined"
        />
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: 2 }}>
        {recentAnomalies.map((anomaly) => (
          <Card 
            key={anomaly.id}
            sx={{ 
              height: '100%',
              border: `2px solid ${
                anomaly.severity === 'critical' || anomaly.severity === 'high' 
                  ? '#f44336' 
                  : anomaly.severity === 'medium' || anomaly.severity === 'warning'
                  ? '#ff9800'
                  : '#2196f3'
              }`,
              '&:hover': {
                boxShadow: 3,
                transform: 'translateY(-2px)',
                transition: 'all 0.2s ease-in-out'
              }
            }}
          >
            <CardContent>
              {/* Header */}
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Chip
                  icon={getSeverityIcon(anomaly.severity)}
                  label={anomaly.severity.toUpperCase()}
                  color={getSeverityColor(anomaly.severity) as any}
                  size="small"
                  sx={{ fontWeight: 'bold', mr: 1 }}
                />
                <Box sx={{ flexGrow: 1 }} />
                <Tooltip title={formatTimestamp(anomaly.timestamp)}>
                  <Typography variant="caption" color="textSecondary">
                    {getTimeAgo(anomaly.timestamp)}
                  </Typography>
                </Tooltip>
              </Box>

              {/* Device and Type */}
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <SensorsIcon sx={{ mr: 1, fontSize: 16 }} />
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mr: 1 }}>
                  {anomaly.device_id}
                </Typography>
                <Chip
                  label={getAnomalyTypeLabel(anomaly.anomaly_type)}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: '0.7rem' }}
                />
              </Box>

              {/* Sensor Field and Value */}
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <TimelineIcon sx={{ mr: 1, fontSize: 16 }} />
                <Typography variant="body2" sx={{ mr: 1 }}>
                  <strong>{anomaly.sensor_field}</strong>: {anomaly.value.toFixed(3)}
                </Typography>
                {anomaly.threshold > 0 && (
                  <Typography variant="caption" color="textSecondary">
                    (threshold: {anomaly.threshold.toFixed(3)})
                  </Typography>
                )}
              </Box>

              {/* LLM Decision */}
              {anomaly.llm_decision && (
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <PsychologyIcon sx={{ mr: 1, fontSize: 16, color: '#9c27b0' }} />
                    <Typography variant="caption" sx={{ fontWeight: 'bold', color: '#9c27b0' }}>
                      AI Analysis
                    </Typography>
                  </Box>
                  <Typography variant="body2" sx={{ 
                    fontStyle: 'italic',
                    backgroundColor: '#f3e5f5',
                    padding: 1,
                    borderRadius: 1,
                    fontSize: '0.8rem'
                  }}>
                    {anomaly.llm_decision}
                  </Typography>
                </Box>
              )}

              {/* Expandable Details */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="caption" color="textSecondary">
                  ID: {anomaly.id}
                </Typography>
                <IconButton
                  size="small"
                  onClick={() => toggleAlertExpansion(anomaly.id)}
                  sx={{ padding: 0.5 }}
                >
                  {expandedAlerts.has(anomaly.id) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              </Box>

              {/* Expanded Details */}
              <Collapse in={expandedAlerts.has(anomaly.id)}>
                <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid #e0e0e0' }}>
                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                    <Box>
                      <Typography variant="caption" color="textSecondary">Type</Typography>
                      <Typography variant="body2">{anomaly.anomaly_type}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="textSecondary">Field</Typography>
                      <Typography variant="body2">{anomaly.sensor_field}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="textSecondary">Value</Typography>
                      <Typography variant="body2">{anomaly.value.toFixed(6)}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="textSecondary">Threshold</Typography>
                      <Typography variant="body2">{anomaly.threshold.toFixed(6)}</Typography>
                    </Box>
                    <Box sx={{ gridColumn: '1 / -1' }}>
                      <Typography variant="caption" color="textSecondary">Created</Typography>
                      <Typography variant="body2">{formatTimestamp(anomaly.created_at)}</Typography>
                    </Box>
                  </Box>
                </Box>
              </Collapse>
            </CardContent>
          </Card>
        ))}
      </Box>

      {/* Summary Alert */}
      {anomalies.length > maxDisplay && (
        <Alert severity="info" sx={{ mt: 2 }}>
          <AlertTitle>More Alerts Available</AlertTitle>
          Showing {maxDisplay} most recent alerts out of {anomalies.length} total alerts.
        </Alert>
      )}
    </Box>
  );
};

export default AlertsSection; 