import React from 'react';
import { Card, CardContent, Box, Typography, SxProps } from '@mui/material';
import { SvgIconComponent } from '@mui/icons-material';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: SvgIconComponent;
  gradient: string;
  sx?: SxProps;
}

const MetricCard: React.FC<MetricCardProps> = ({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  gradient,
  sx 
}) => {
  return (
    <Card sx={{ 
      background: gradient,
      color: 'white',
      flex: '1 1 250px',
      minWidth: '250px',
      ...sx
    }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Icon sx={{ mr: 1 }} />
          <Typography variant="h6">{title}</Typography>
        </Box>
        <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
          {value}
        </Typography>
        <Typography variant="body2">
          {subtitle}
        </Typography>
      </CardContent>
    </Card>
  );
};

export default MetricCard; 