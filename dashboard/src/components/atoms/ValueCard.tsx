import React from 'react';
import { Card, CardContent, Typography } from '@mui/material';

interface ValueCardProps {
  value: number | string;
  label: string;
  color: string;
  bgColor: string;
  precision?: number;
}

const ValueCard: React.FC<ValueCardProps> = ({ 
  value, 
  label, 
  color, 
  bgColor, 
  precision = 2 
}) => {
  const displayValue = typeof value === 'number' 
    ? value.toFixed(precision) 
    : value || 'N/A';

  return (
    <Card sx={{ bgcolor: bgColor }}>
      <CardContent sx={{ textAlign: 'center', py: 1 }}>
        <Typography variant="h6" color={color}>
          {displayValue}
        </Typography>
        <Typography variant="caption">{label}</Typography>
      </CardContent>
    </Card>
  );
};

export default ValueCard; 