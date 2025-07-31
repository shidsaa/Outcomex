import React from 'react';
import { Paper, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';

interface SensorData {
  device_id: string;
  timestamp: string;
  pm2_5: number;
  pm10: number;
  dBA: number;
  vibration: number;
}

interface SensorDataTableProps {
  data: SensorData[];
}

const SensorDataTable: React.FC<SensorDataTableProps> = ({ data }) => {
  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        All Recent Sensor Data
      </Typography>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Device ID</TableCell>
              <TableCell>Timestamp</TableCell>
              <TableCell>PM2.5</TableCell>
              <TableCell>PM10</TableCell>
              <TableCell>dBA</TableCell>
              <TableCell>Vibration</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.slice(-20).map((row, index) => (
              <TableRow key={index}>
                <TableCell>{row.device_id}</TableCell>
                <TableCell>{new Date(row.timestamp + 'Z').toLocaleString('en-US', {
                timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
              })}</TableCell>
                <TableCell>{row.pm2_5?.toFixed(2) || 'N/A'}</TableCell>
                <TableCell>{row.pm10?.toFixed(2) || 'N/A'}</TableCell>
                <TableCell>{row.dBA?.toFixed(2) || 'N/A'}</TableCell>
                <TableCell>{row.vibration?.toFixed(4) || 'N/A'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};

export default SensorDataTable; 