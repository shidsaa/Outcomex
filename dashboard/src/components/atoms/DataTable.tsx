import React from 'react';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper, 
  Typography, 
  Box,
  Chip,
  Tooltip
} from '@mui/material';
import { 
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon
} from '@mui/icons-material';

interface DataPoint {
  timestamp: string;
  pm2_5: number;
  pm10: number;
  dBA: number;
  vibration: number;
  status?: 'normal' | 'warning' | 'critical';
}

interface DataTableProps {
  data: DataPoint[];
  title: string;
  showStatus?: boolean;
}

const DataTable: React.FC<DataTableProps> = ({ data, title, showStatus = false }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'normal': return <CheckCircleIcon sx={{ color: '#4CAF50', fontSize: 16 }} />;
      case 'warning': return <WarningIcon sx={{ color: '#FF9800', fontSize: 16 }} />;
      case 'critical': return <ErrorIcon sx={{ color: '#F44336', fontSize: 16 }} />;
      default: return <CheckCircleIcon sx={{ color: '#4CAF50', fontSize: 16 }} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'normal': return 'success';
      case 'warning': return 'warning';
      case 'critical': return 'error';
      default: return 'default';
    }
  };

  const getTrendIcon = (current: number, previous: number) => {
    if (!previous) return null;
    const diff = current - previous;
    if (Math.abs(diff) < 0.1) return null;
    return diff > 0 ? 
      <TrendingUpIcon sx={{ color: '#F44336', fontSize: 14 }} /> : 
      <TrendingDownIcon sx={{ color: '#4CAF50', fontSize: 14 }} />;
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp + 'Z').toLocaleTimeString('en-US', {
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
    });
  };

  const getRowStyle = (status?: string) => {
    if (!status) return {};
    switch (status) {
      case 'critical': return { backgroundColor: '#ffebee' };
      case 'warning': return { backgroundColor: '#fff3e0' };
      default: return {};
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
        {title}
      </Typography>
      <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 'bold' }}>Time</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>PM2.5</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>PM10</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>dBA</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Vibration</TableCell>
              {showStatus && <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {data.map((row, index) => (
              <TableRow 
                key={index}
                sx={getRowStyle(row.status)}
                hover
              >
                <TableCell>
                  {formatTime(row.timestamp)}
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {row.pm2_5.toFixed(1)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {row.pm10.toFixed(1)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {row.dBA.toFixed(1)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    {row.vibration.toFixed(3)}
                  </Typography>
                </TableCell>
                {showStatus && row.status && (
                  <TableCell>
                    <Tooltip title={`Status: ${row.status}`}>
                      <Chip
                        icon={getStatusIcon(row.status)}
                        label={row.status}
                        size="small"
                        color={getStatusColor(row.status) as any}
                        variant="outlined"
                      />
                    </Tooltip>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default DataTable; 