import React from 'react';
import { Box } from '@mui/material';
import { 
  Queue as QueueIcon, 
  Speed as SpeedIcon, 
  TrendingUp as TrendingUpIcon, 
  Warning as WarningIcon 
} from '@mui/icons-material';
import MetricCard from '../atoms/MetricCard';

interface SystemMetricsProps {
  queueMessageCount: number;
  totalProcessed: number;
  totalAlerts: number;
}

const SystemMetrics: React.FC<SystemMetricsProps> = ({ 
  queueMessageCount, 
  totalProcessed, 
  totalAlerts 
}) => {
  const metrics = [
    {
      title: 'Queue Status',
      value: queueMessageCount,
      subtitle: 'Messages in Queue',
      icon: QueueIcon,
      gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    },
    {
      title: 'Active Consumers',
      value: 1,
      subtitle: 'Processing Messages',
      icon: SpeedIcon,
      gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
    },
    {
      title: 'Total Processed',
      value: totalProcessed,
      subtitle: 'Records Processed',
      icon: TrendingUpIcon,
      gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
    },
    {
      title: 'Alerts Generated',
      value: totalAlerts,
      subtitle: 'Anomalies Detected',
      icon: WarningIcon,
      gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
    }
  ];

  return (
    <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
      {metrics.map((metric) => (
        <MetricCard
          key={metric.title}
          title={metric.title}
          value={metric.value}
          subtitle={metric.subtitle}
          icon={metric.icon}
          gradient={metric.gradient}
        />
      ))}
    </Box>
  );
};

export default SystemMetrics; 