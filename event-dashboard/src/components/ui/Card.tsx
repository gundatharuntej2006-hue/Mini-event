import React from 'react';
import { cn } from '../../utils/cn';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
}

export function Card({ children, className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        'relative bg-[#061224]/85 backdrop-blur-xl border border-cyan-500/35 rounded-2xl shadow-[0_0_25px_rgba(6,182,212,0.12)] transition-all overflow-hidden text-slate-200',
        'before:absolute before:top-0 before:left-0 before:right-0 before:h-[1px] before:bg-gradient-to-r before:from-transparent before:via-cyan-400/30 before:to-transparent',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}

export function CardHeader({
  title,
  subtitle,
  action,
  children,
  className,
  ...props
}: CardHeaderProps) {
  if (children) {
    return (
      <div
        className={cn('px-5 py-4 border-b border-cyan-500/25 flex items-center justify-between bg-[#040c1a]/60', className)}
        {...props}
      >
        {children}
      </div>
    );
  }

  return (
    <div
      className={cn('px-5 py-4 border-b border-cyan-500/25 flex items-center justify-between gap-4 bg-[#040c1a]/60', className)}
      {...props}
    >
      <div>
        {title && (
          <h3 className="text-base font-orbitron font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-white to-violet-300 tracking-wide">
            {title}
          </h3>
        )}
        {subtitle && <p className="text-xs text-slate-400 font-sans mt-0.5">{subtitle}</p>}
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  );
}

export function CardContent({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('p-5', className)} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('px-5 py-3 bg-[#040c1a]/70 border-t border-cyan-500/25 text-xs text-slate-400 font-mono', className)}
      {...props}
    >
      {children}
    </div>
  );
}
