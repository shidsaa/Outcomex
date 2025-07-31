import React, { useEffect, useRef, useState } from 'react';
import { Paper, Typography, Box } from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';

interface SensorData {
  timestamp: string;
  [key: string]: any;
}

interface SensorChartProps {
  title: string;
  data: SensorData[];
  dataKey: string;
  color: string;
  height?: number;
}

const SensorChart: React.FC<SensorChartProps> = ({ 
  title, 
  data, 
  dataKey, 
  color, 
  height = 200 
}) => {
  const chartRef = useRef<any>(null);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [chartKey, setChartKey] = useState(0);

  // Update current time every second for real-time effect
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Force chart re-render when data changes - more aggressive approach
  useEffect(() => {
    console.log(`SensorChart re-rendering for ${dataKey}:`, data.length, 'data points');
    // Force immediate re-render
    setChartKey(Date.now());
  }, [data, dataKey]); // Watch the entire data array

  // Ensure we have data to display
  if (!data || data.length === 0) {
    return (
      <Paper sx={{ p: 2, height }}>
        <Typography variant="subtitle2" gutterBottom align="center">
          {title}
        </Typography>
        <Box sx={{ 
          height: height - 60, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          color: 'text.secondary'
        }}>
          <Typography variant="body2">No data available</Typography>
        </Box>
      </Paper>
    );
  }

  // Use all the filtered data passed from parent component
  const chartData = data;

  // Calculate dynamic Y-axis domain for better visualization
  const values = chartData.map(d => d[dataKey]).filter(v => v !== null && v !== undefined);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = maxValue - minValue;
  
  // For vibration sensor, use fixed range since values are very small
  if (dataKey === 'vibration') {
    const vibrationMin = Math.max(0, minValue - 0.01);
    const vibrationMax = Math.min(0.1, maxValue + 0.01);
    return (
      <Paper sx={{ p: 2, height }}>
        <Typography variant="subtitle2" gutterBottom align="center">
          {title} (Live)
        </Typography>
        <Box sx={{ height: height - 60, border: '1px solid #e0e0e0', position: 'relative' }}>
          {/* Real-time indicator */}
          <Box sx={{ 
            position: 'absolute', 
            top: 5, 
            right: 5, 
            width: 8, 
            height: 8, 
            borderRadius: '50%', 
            backgroundColor: '#4CAF50',
            animation: 'pulse 2s infinite',
            zIndex: 1
          }} />
          <style>
            {`
              @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.5; }
                100% { opacity: 1; }
              }
            `}
          </style>
          
          <ResponsiveContainer width="100%" height="100%">
            <LineChart 
              key={chartKey}
              data={chartData}
              ref={chartRef}
              margin={{ top: 10, right: 10, left: 10, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis 
                dataKey="timestamp" 
                tick={{ fontSize: 8 }}
                interval="preserveStartEnd"
                hide
              />
              <YAxis 
                tick={{ fontSize: 8 }}
                domain={[vibrationMin, vibrationMax]}
                tickFormatter={(value) => value.toFixed(3)}
              />
              <RechartsTooltip 
                labelFormatter={(value) => `Time: ${value}`}
                formatter={(value: any) => [`${value}`, dataKey]}
                contentStyle={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.95)',
                  border: '1px solid #ccc',
                  borderRadius: '4px'
                }}
              />
              <Line 
                type="monotone" 
                dataKey={dataKey} 
                stroke={color} 
                strokeWidth={2} 
                dot={false}
                isAnimationActive={false}
                connectNulls={true}
                activeDot={{ r: 4, fill: color, stroke: '#fff', strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </Paper>
    );
  }
  
  const padding = range * 0.1; // 10% padding

  return (
    <Paper sx={{ p: 2, height }}>
      <Typography variant="subtitle2" gutterBottom align="center">
        {title} (Live)
      </Typography>
      <Box sx={{ height: height - 60, border: '1px solid #e0e0e0', position: 'relative' }}>
        {/* Real-time indicator */}
        <Box sx={{ 
          position: 'absolute', 
          top: 5, 
          right: 5, 
          width: 8, 
          height: 8, 
          borderRadius: '50%', 
          backgroundColor: '#4CAF50',
          animation: 'pulse 2s infinite',
          zIndex: 1
        }} />
        <style>
          {`
            @keyframes pulse {
              0% { opacity: 1; }
              50% { opacity: 0.5; }
              100% { opacity: 1; }
            }
          `}
        </style>
        
                  <ResponsiveContainer width="100%" height="100%">
            <LineChart 
              key={chartKey}
              data={chartData}
              ref={chartRef}
              margin={{ top: 10, right: 10, left: 10, bottom: 10 }}
            >
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="timestamp" 
              tick={{ fontSize: 8 }}
              interval="preserveStartEnd"
              hide
            />
            <YAxis 
              tick={{ fontSize: 8 }}
              domain={[minValue - padding, maxValue + padding]}
              tickFormatter={(value) => value.toFixed(1)}
            />
            <RechartsTooltip 
              labelFormatter={(value) => `Time: ${value}`}
              formatter={(value: any) => [`${value}`, dataKey]}
              contentStyle={{ 
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #ccc',
                borderRadius: '4px'
              }}
            />
            <Line 
              type="monotone" 
              dataKey={dataKey} 
              stroke={color} 
              strokeWidth={2} 
              dot={false}
              isAnimationActive={false}
              connectNulls={true}
              activeDot={{ r: 4, fill: color, stroke: '#fff', strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </Box>
    </Paper>
  );
};

export default SensorChart; 