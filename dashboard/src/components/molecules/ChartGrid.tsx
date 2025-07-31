import React from 'react';
import { Grid, Typography, Box } from '@mui/material';
import SensorChart from '../atoms/SensorChart';

interface SensorData {
  timestamp: string;
  pm2_5: number;
  pm10: number;
  dBA: number;
  vibration: number;
}

interface ChartGridProps {
  data: SensorData[];
}

const ChartGrid: React.FC<ChartGridProps> = ({ data }) => {
  const charts = [
    { title: 'PM2.5', dataKey: 'pm2_5', color: '#8884d8' },
    { title: 'PM10', dataKey: 'pm10', color: '#82ca9d' },
    { title: 'dBA', dataKey: 'dBA', color: '#ffc658' },
    { title: 'Vibration', dataKey: 'vibration', color: '#ff7300' }
  ];

  return (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
        📈 Sensor Readings
      </Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
        {charts.map((chart) => (
          <Box key={chart.dataKey} sx={{ flex: '1 1 250px', minWidth: '250px' }}>
            <SensorChart
              title={chart.title}
              data={data}
              dataKey={chart.dataKey}
              color={chart.color}
            />
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default ChartGrid; 