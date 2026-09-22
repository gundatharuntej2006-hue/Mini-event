import React from 'react';
import { cn } from '../../utils/cn';

export type StatusType =
  | 'qualified'
  | 'eliminated'
  | 'in_progress'
  | 'completed'
  | 'incomplete'
  | 'checked_in'
  | 'pending'
  | 'restricted'
  | 'neutral'
  | 'info';

export interface StatusBadgeProps {
  status: StatusType | string;
  label?: string;
  dot?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  dot = true,
  size = 'md',
  className,
}) => {
  const normalized = status.toLowerCase().replace(/[\s-]+/g, '_');

  let variantStyles = 'bg-slate-100 text-slate-700 border-slate-200/80';
  let dotColor = 'bg-slate-400';
  let defaultText = label || status;

  if (
    normalized.includes('qualif') ||
    normalized === 'checked_in' ||
    normalized === 'ready' ||
    normalized === 'completed' ||
    normalized === 'success' ||
    normalized === 'active'
  ) {
    variantStyles = 'bg-emerald-50 text-emerald-700 border-emerald-200/80';
    dotColor = 'bg-emerald-500';
  } else if (
    normalized.includes('eliminat') ||
    normalized === 'failed' ||
    normalized === 'danger' ||
    normalized === 'error'
  ) {
    variantStyles = 'bg-rose-50 text-rose-700 border-rose-200/80';
    dotColor = 'bg-rose-500';
  } else if (
    normalized.includes('progress') ||
    normalized.includes('pending') ||
    normalized.includes('partial') ||
    normalized === 'warning' ||
    normalized === 'review'
  ) {
    variantStyles = 'bg-amber-50 text-amber-800 border-amber-200/80';
    dotColor = 'bg-amber-500';
  } else if (
    normalized.includes('restrict') ||
    normalized.includes('secret') ||
    normalized.includes('judge') ||
    normalized === 'confidential'
  ) {
    variantStyles = 'bg-purple-50 text-purple-700 border-purple-200/80';
    dotColor = 'bg-purple-500';
  } else if (
    normalized.includes('lead') ||
    normalized.includes('organizer') ||
    normalized === 'info' ||
    normalized === 'live'
  ) {
    variantStyles = 'bg-blue-50 text-blue-700 border-blue-200/80';
    dotColor = 'bg-blue-500';
  }

  const sizeStyles = {
    sm: 'text-[10px] px-2 py-0.5 font-medium',
    md: 'text-xs px-2.5 py-1 font-medium',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-sans',
        variantStyles,
        sizeStyles[size],
        className
      )}
    >
      {dot && (
        <span
          className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', dotColor)}
        />
      )}
      <span>{defaultText}</span>
    </span>
  );
};
