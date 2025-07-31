import React, { useState, useEffect } from 'react';
import { Box, Card, CardContent, Typography, Chip, CircularProgress, Tooltip } from '@mui/material';
import { 
  Storage as StorageIcon, 
  Psychology as PsychologyIcon,
  Queue as QueueIcon,
  Dashboard as DashboardIcon,
  Timeline as TimelineIcon,
  Cloud as CloudIcon,
  Settings as SettingsIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Help as HelpIcon
} from '@mui/icons-material';
import axios from 'axios';

interface ServiceHealth {
  name: string;
  status: 'healthy' | 'warning' | 'critical' | 'offline' | 'unknown' | 'running' | 'error';
  icon: React.ReactNode;
  url: string;
  endpoint: string;
  description: string;
}

interface HealthResponse {
  status?: string;
  service?: string;
  timestamp?: string;
  uptime?: number;
  models_trained?: number;
  database_connected?: boolean;
}

const services: ServiceHealth[] = [
  {
    name: 'Consumer',
    status: 'unknown',
    icon: <StorageIcon />,
    url: 'http://localhost:8001',
    endpoint: '/health',
    description: 'Data processing service'
  },
  {
    name: 'ML Service',
    status: 'unknown',
    icon: <PsychologyIcon />,
    url: 'http://localhost:8002',
    endpoint: '/health',
    description: 'AI/ML models service'
  },
  {
    name: 'Log Collector',
    status: 'unknown',
    icon: <TimelineIcon />,
    url: 'http://localhost:9090',
    endpoint: '/api/v1/status/config',
    description: 'Metrics collection'
  }
];

const ServiceHealthGrid: React.FC = () => {
  const [serviceStatuses, setServiceStatuses] = useState<ServiceHealth[]>(services);
  const [loading, setLoading] = useState(true);

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'running':
      case 'success':
        return <CheckCircleIcon color="success" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      case 'critical':
      case 'error':
        return <ErrorIcon color="error" />;
      case 'offline':
      case 'unknown':
        return <HelpIcon color="disabled" />;
      default:
        return <HelpIcon color="disabled" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'running':
      case 'success':
        return 'success';
      case 'warning':
        return 'warning';
      case 'critical':
      case 'error':
        return 'error';
      case 'offline':
      case 'unknown':
        return 'default';
      default:
        return 'default';
    }
  };

  const checkServiceHealth = async (service: ServiceHealth): Promise<ServiceHealth> => {
    try {
      const response = await axios.get(`${service.url}${service.endpoint}`, {
        timeout: 5000,
        headers: {
          'Accept': '*/*',
          'Content-Type': 'application/json'
        }
      });

      let status = 'unknown';
      if (response.status === 200) {
        // For Prometheus, check if config endpoint returns data
        if (service.name === 'Prometheus') {
          status = 'healthy'; // If we get a 200 response, Prometheus is healthy
        }
        // For Consumer and ML Service, use the status from response
        else {
          const data = response.data as HealthResponse;
          status = data.status || 'healthy';
        }
      }

      return {
        ...service,
        status: status as any
      };
    } catch (error) {
      return {
        ...service,
        status: 'offline'
      };
    }
  };

  const checkAllServices = async () => {
    setLoading(true);
    
    try {
      const healthChecks = await Promise.allSettled(
        services.map(service => checkServiceHealth(service))
      );

      const updatedServices = healthChecks.map((result, index) => {
        if (result.status === 'fulfilled') {
          return result.value;
        } else {
          return {
            ...services[index],
            status: 'offline' as const
          };
        }
      });

      setServiceStatuses(updatedServices);
    } catch (error) {
      console.error('Error checking service health:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAllServices();
    const interval = setInterval(checkAllServices, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  return (
    <Box>

      <Box sx={{ 
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: 3,
        width: '100%'
      }}>
        {serviceStatuses.map((service, index) => (
          <Card 
            key={service.name}
            sx={{ 
              width: '100%',
              border: `2px solid ${
                service.status === 'healthy' || service.status === 'running' 
                  ? '#4caf50' 
                  : service.status === 'warning' 
                    ? '#ff9800' 
                    : service.status === 'critical' || service.status === 'error'
                      ? '#f44336'
                      : '#9e9e9e'
              }`,
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: 3,
              }
            }}
          >
            <CardContent sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Box sx={{ mr: 1, display: 'flex', alignItems: 'center' }}>
                  {service.icon}
                </Box>
                <Typography variant="h6" component="div" sx={{ fontWeight: 'bold' }}>
                  {service.name}
                </Typography>
                {loading && index === 0 && (
                  <CircularProgress size={16} sx={{ ml: 1 }} />
                )}
              </Box>
              
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                {getStatusIcon(service.status)}
                <Chip 
                  label={service.status.toUpperCase()} 
                  color={getStatusColor(service.status) as any}
                  size="small"
                  sx={{ ml: 1 }}
                />
              </Box>
              
              <Tooltip title={service.description}>
                <Typography variant="body2" color="textSecondary" sx={{ 
                  fontSize: '0.75rem',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}>
                  {service.description}
                </Typography>
              </Tooltip>
            </CardContent>
          </Card>
        ))}
      </Box>
    </Box>
  );
};

export default ServiceHealthGrid; 