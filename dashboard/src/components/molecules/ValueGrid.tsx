import React from 'react';
import { Box, Typography, Grid } from '@mui/material';
import ValueCard from '../atoms/ValueCard';

interface SensorData {
  pm2_5: number;
  pm10: number;
  dBA: number;
  vibration: number;
  timestamp: string;
}

interface ValueGridProps {
  data: SensorData;
}

const ValueGrid: React.FC<ValueGridProps> = ({ data }) => {
  const values = [
    { key: 'pm2_5', label: 'PM2.5', color: 'primary.main', bgColor: '#e3f2fd', precision: 2 },
    { key: 'pm10', label: 'PM10', color: 'success.main', bgColor: '#e8f5e8', precision: 2 },
    { key: 'dBA', label: 'dBA', color: 'warning.main', bgColor: '#fff3e0', precision: 2 },
    { key: 'vibration', label: 'Vibration', color: 'error.main', bgColor: '#fce4ec', precision: 4 }
  ];

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Latest Reading
      </Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
        {values.map((value) => (
          <Box key={value.key} sx={{ flex: '1 1 200px', minWidth: '200px' }}>
            <ValueCard
              value={data[value.key as keyof SensorData] as number}
              label={value.label}
              color={value.color}
              bgColor={value.bgColor}
              precision={value.precision}
            />
          </Box>
        ))}
      </Box>
      <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
        Last updated: {new Date(data.timestamp + 'Z').toLocaleString('en-US', {
          timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
        })}
      </Typography>
    </Box>
  );
};

export default ValueGrid; 