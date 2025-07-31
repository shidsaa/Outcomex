import React from 'react';
import { Box, Typography } from '@mui/material';
import { Sensors as SensorsIcon } from '@mui/icons-material';
import StatusChip from '../atoms/StatusChip';

interface SensorHeaderProps {
  sensorId: string;
  readingsCount: number;
  alertsCount: number;
}

const SensorHeader: React.FC<SensorHeaderProps> = ({ 
  sensorId, 
  readingsCount, 
  alertsCount 
}) => {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
      <SensorsIcon sx={{ mr: 2, fontSize: 28, color: '#2196F3' }} />
      <Typography variant="h5" sx={{ fontWeight: 'bold', flexGrow: 1 }}>
        {sensorId}
      </Typography>
      <StatusChip 
        count={readingsCount}
        label="readings"
        color="primary"
        variant="outlined"
        sx={{ mr: 1 }}
      />
      <StatusChip 
        count={alertsCount}
        label="alerts"
        color="error"
        variant="outlined"
      />
    </Box>
  );
};

export default SensorHeader; 