import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';

interface SystemOverviewCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: 'primary' | 'success' | 'warning' | 'error' | 'info';
  trend?: 'up' | 'down' | 'stable';
}

const SystemOverviewCard: React.FC<SystemOverviewCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  color,
  trend
}) => {
  const getColorValue = () => {
    switch (color) {
      case 'primary': return '#2196F3';
      case 'success': return '#4CAF50';
      case 'warning': return '#FF9800';
      case 'error': return '#F44336';
      case 'info': return '#00BCD4';
      default: return '#2196F3';
    }
  };

  const getTrendIcon = () => {
    if (!trend) return null;
    return (
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        color: trend === 'up' ? '#4CAF50' : trend === 'down' ? '#F44336' : '#9E9E9E',
        fontSize: '0.75rem'
      }}>
        {trend === 'up' ? '↗' : trend === 'down' ? '↘' : '→'}
      </Box>
    );
  };

  return (
    <Card sx={{ 
      height: '100%',
      background: `linear-gradient(135deg, ${getColorValue()}15 0%, ${getColorValue()}05 100%)`,
      border: `1px solid ${getColorValue()}30`
    }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Box sx={{ 
            color: getColorValue(),
            mr: 1,
            display: 'flex',
            alignItems: 'center'
          }}>
            {icon}
          </Box>
          <Typography variant="h6" component="div" sx={{ fontWeight: 'bold', color: getColorValue() }}>
            {title}
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'baseline', mb: 1 }}>
          <Typography variant="h4" component="div" sx={{ fontWeight: 'bold', mr: 1 }}>
            {value}
          </Typography>
          {getTrendIcon()}
        </Box>

        {subtitle && (
          <Typography variant="body2" color="textSecondary">
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default SystemOverviewCard; 