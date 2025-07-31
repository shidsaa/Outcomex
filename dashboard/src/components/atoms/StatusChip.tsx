import React from 'react';
import { Chip, ChipProps } from '@mui/material';

interface StatusChipProps extends Omit<ChipProps, 'label'> {
  count: number;
  label: string;
  color?: 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning';
  variant?: 'filled' | 'outlined';
}

const StatusChip: React.FC<StatusChipProps> = ({ 
  count, 
  label, 
  color = 'primary', 
  variant = 'outlined',
  ...props 
}) => {
  return (
    <Chip
      label={`${count} ${label}`}
      color={color}
      variant={variant}
      size="small"
      {...props}
    />
  );
};

export default StatusChip; 