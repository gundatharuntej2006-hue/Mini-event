import React from 'react';
import { cn } from '../../utils/cn';

export type BadgeVariant = 'primary' | 'success' | 'warning' | 'danger' | 'neutral' | 'purple';
export type BadgeSize = 'sm' | 'md';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  dot?: boolean;
  className?: string;
}

export function Badge({
  children,
  variant = 'neutral',
  size = 'md',
  dot = false,
  className,
  ...props
}: BadgeProps) {
  const variantStyles: Record<BadgeVariant, string> = {
    primary: 'bg-cyan-950/50 text-cyan-300 border-cyan-500/30 shadow-[0_0_10px_rgba(6,182,212,0.2)]',
    success: 'bg-emerald-950/50 text-emerald-300 border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.2)]',
    warning: 'bg-amber-950/50 text-amber-300 border-amber-500/30 shadow-[0_0_10px_rgba(245,158,11,0.2)]',
    danger: 'bg-rose-950/50 text-rose-300 border-rose-500/30 shadow-[0_0_10px_rgba(244,63,94,0.2)]',
    neutral: 'bg-slate-800/80 text-slate-300 border-slate-700',
    purple: 'bg-violet-950/50 text-violet-300 border-violet-500/30 shadow-[0_0_10px_rgba(139,92,246,0.2)]',
  };

  const dotColors: Record<BadgeVariant, string> = {
    primary: 'bg-cyan-400 shadow-[0_0_6px_rgba(6,182,212,0.8)]',
    success: 'bg-emerald-400 shadow-[0_0_6px_rgba(16,185,129,0.8)]',
    warning: 'bg-amber-400 shadow-[0_0_6px_rgba(245,158,11,0.8)]',
    danger: 'bg-rose-400 shadow-[0_0_6px_rgba(244,63,94,0.8)]',
    neutral: 'bg-slate-400',
    purple: 'bg-violet-400 shadow-[0_0_6px_rgba(139,92,246,0.8)]',
  };

  const sizeStyles: Record<BadgeSize, string> = {
    sm: 'text-[11px] px-2 py-0.5 font-mono font-medium',
    md: 'text-xs px-2.5 py-1 font-mono font-medium',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border backdrop-blur-sm',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...props}
    >
      {dot && <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0 animate-pulse', dotColors[variant])} />}
      {children}
    </span>
  );
}
