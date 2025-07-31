import React from 'react';
import { Card, CardContent, Typography, Box, Chip, Tooltip } from '@mui/material';
import { Sensors as SensorsIcon, Warning as WarningIcon, Error as ErrorIcon, CheckCircle as CheckCircleIcon } from '@mui/icons-material';

interface SensorCardProps {
  deviceId: string;
  currentData: {
    pm2_5: number;
    pm10: number;
    dBA: number;
    vibration: number;
    timestamp: string;
  };
  status: 'normal' | 'warning' | 'critical' | 'offline';
  onClick?: () => void;
}

const SensorCard: React.FC<SensorCardProps> = ({
  deviceId,
  currentData,
  status,
  onClick
}) => {
  const getStatusColor = () => {
    switch (status) {
      case 'normal': return 'success';
      case 'warning': return 'warning';
      case 'critical': return 'error';
      case 'offline': return 'default';
      default: return 'default';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'normal': return <CheckCircleIcon />;
      case 'warning': return <WarningIcon />;
      case 'critical': return <ErrorIcon />;
      case 'offline': return <SensorsIcon />;
      default: return <SensorsIcon />;
    }
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp + 'Z').toLocaleTimeString('en-US', {
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
    });
  };

  return (
    <Card 
      sx={{ 
        minWidth: 280,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.2s ease-in-out',
        '&:hover': onClick ? {
          transform: 'translateY(-2px)',
          boxShadow: 3
        } : {},
        border: status === 'critical' ? '2px solid #f44336' : 
                status === 'warning' ? '2px solid #ff9800' : '1px solid #e0e0e0'
      }}
      onClick={onClick}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Chip
            icon={getStatusIcon()}
            label={deviceId}
            color={getStatusColor() as any}
            size="small"
            sx={{ fontWeight: 'bold' }}
          />
          <Box sx={{ flexGrow: 1 }} />
          <Typography variant="caption" color="textSecondary">
            {formatTime(currentData.timestamp)}
          </Typography>
        </Box>

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 2, mb: 2 }}>
          <Box>
            <Typography variant="caption" color="textSecondary">PM2.5</Typography>
            <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
              {currentData.pm2_5.toFixed(1)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="textSecondary">PM10</Typography>
            <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
              {currentData.pm10.toFixed(1)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="textSecondary">dBA</Typography>
            <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
              {currentData.dBA.toFixed(1)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="textSecondary">Vibration</Typography>
            <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
              {currentData.vibration.toFixed(3)}
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="caption" color="textSecondary">
            Updated: {formatTime(currentData.timestamp)}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default SensorCard; 