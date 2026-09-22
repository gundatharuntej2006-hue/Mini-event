import React from 'react';
import { cn } from '../../utils/cn';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  children: React.ReactNode;
}

export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  children,
  className,
  disabled,
  ...props
}: ButtonProps) {
  const variantStyles: Record<ButtonVariant, string> = {
    primary:
      'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold shadow-[0_0_20px_rgba(6,182,212,0.35)] border border-cyan-400/40 rounded-xl active:scale-[0.98]',
    secondary:
      'bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-slate-700 rounded-xl active:scale-[0.98]',
    outline:
      'bg-transparent hover:bg-cyan-500/10 text-cyan-300 border border-cyan-500/40 hover:border-cyan-400 rounded-xl active:scale-[0.98]',
    ghost:
      'hover:bg-slate-800/60 text-slate-400 hover:text-slate-200 rounded-xl',
    danger:
      'bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white font-bold shadow-[0_0_15px_rgba(244,63,94,0.3)] rounded-xl border border-rose-500/40 active:scale-[0.98]',
  };

  const sizeStyles: Record<ButtonSize, string> = {
    sm: 'text-xs px-3 py-1.5 gap-1.5 font-mono font-medium',
    md: 'text-xs sm:text-sm px-4 py-2 gap-2 font-mono font-semibold',
    lg: 'text-sm sm:text-base px-5 py-2.5 gap-2.5 font-orbitron font-bold',
  };

  return (
    <button
      className={cn(
        'inline-flex items-center justify-center transition-all focus:outline-none focus:ring-2 focus:ring-cyan-400/50 disabled:opacity-50 disabled:pointer-events-none cursor-pointer',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
      ) : (
        leftIcon && <span className="flex-shrink-0">{leftIcon}</span>
      )}
      {children}
      {!isLoading && rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
    </button>
  );
}
