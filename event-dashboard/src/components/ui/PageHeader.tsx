import React from 'react';
import { cn } from '../../utils/cn';

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  breadcrumbs?: Array<{ label: string; href?: string }>;
  actions?: React.ReactNode;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  badge,
  breadcrumbs,
  actions,
  className,
}) => {
  return (
    <div
      className={cn(
        'relative bg-[#061224]/85 backdrop-blur-xl rounded-2xl border border-cyan-500/35 p-5 shadow-[0_0_25px_rgba(6,182,212,0.12)] flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between overflow-hidden',
        'before:absolute before:top-0 before:left-0 before:right-0 before:h-[1px] before:bg-gradient-to-r before:from-transparent before:via-cyan-400/40 before:to-transparent',
        className
      )}
    >
      <div className="space-y-1.5 relative z-10">
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav className="flex items-center gap-1.5 text-xs font-mono text-cyan-400/70 mb-1" aria-label="Breadcrumb">
            {breadcrumbs.map((crumb, idx) => (
              <React.Fragment key={idx}>
                {idx > 0 && <span className="text-slate-600">/</span>}
                {crumb.href ? (
                  <a
                    href={crumb.href}
                    className="hover:text-cyan-300 transition-colors font-medium"
                  >
                    {crumb.label}
                  </a>
                ) : (
                  <span className="text-slate-400 font-medium">{crumb.label}</span>
                )}
              </React.Fragment>
            ))}
          </nav>
        )}
        <div className="flex items-center flex-wrap gap-3">
          <h1 className="font-orbitron font-bold text-lg sm:text-xl lg:text-2xl tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-white to-violet-300">
            {title}
          </h1>
          {badge}
        </div>
        {subtitle && (
          <p className="text-xs text-slate-400 max-w-3xl leading-relaxed font-sans">
            {subtitle}
          </p>
        )}
      </div>

      {actions && (
        <div className="flex items-center flex-wrap gap-2.5 sm:self-center relative z-10">
          {actions}
        </div>
      )}
    </div>
  );
};
