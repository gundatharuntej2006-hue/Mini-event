import React from 'react';
import { LucideIcon } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface SummaryMetricProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: LucideIcon;
  badge?: React.ReactNode;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  variant?: 'default' | 'blue' | 'emerald' | 'amber' | 'purple' | 'rose';
  className?: string;
  onClick?: () => void;
}

export const SummaryMetric: React.FC<SummaryMetricProps> = ({
  label,
  value,
  subtext,
  icon: Icon,
  badge,
  trend,
  variant = 'default',
  className,
  onClick,
}) => {
  const iconVariants = {
    default: 'bg-slate-800/60 text-cyan-400 border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.2)]',
    blue: 'bg-blue-600/20 text-blue-400 border-blue-400/40 shadow-[0_0_15px_rgba(59,130,246,0.3)]',
    emerald: 'bg-emerald-500/20 text-emerald-300 border-emerald-400/40 shadow-[0_0_15px_rgba(16,185,129,0.3)]',
    amber: 'bg-amber-500/20 text-amber-300 border-amber-400/40 shadow-[0_0_15px_rgba(245,158,11,0.3)]',
    purple: 'bg-violet-500/20 text-violet-300 border-violet-400/40 shadow-[0_0_15px_rgba(139,92,246,0.3)]',
    rose: 'bg-rose-500/20 text-rose-300 border-rose-400/40 shadow-[0_0_15px_rgba(244,63,94,0.3)]',
  };

  return (
    <div
      onClick={onClick}
      className={cn(
        'relative bg-[#061224]/85 backdrop-blur-xl rounded-2xl border border-cyan-500/35 p-5 shadow-[0_0_25px_rgba(6,182,212,0.12)] transition-all duration-300 overflow-hidden group',
        'before:absolute before:top-0 before:left-0 before:right-0 before:h-[1px] before:bg-gradient-to-r before:from-transparent before:via-cyan-400/40 before:to-transparent',
        'hover:border-cyan-400/60 hover:shadow-[0_0_35px_rgba(6,182,212,0.22)]',
        onClick && 'cursor-pointer hover:-translate-y-0.5',
        className
      )}
    >
      <div className="flex items-center gap-4 relative z-10">
        {Icon && (
          <div
            className={cn(
              'w-14 h-14 rounded-2xl flex items-center justify-center border shrink-0 transition-transform group-hover:scale-105',
              iconVariants[variant]
            )}
          >
            <Icon className="w-7 h-7" />
          </div>
        )}

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className="text-[11px] font-mono tracking-wider font-semibold text-slate-300 uppercase truncate">
              {label}
            </p>
            {trend && (
              <span
                className={cn(
                  'text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border shrink-0',
                  trend.isPositive
                    ? 'text-emerald-300 bg-emerald-950/60 border-emerald-500/40 shadow-[0_0_8px_rgba(16,185,129,0.2)]'
                    : 'text-rose-300 bg-rose-950/60 border-rose-500/40 shadow-[0_0_8px_rgba(244,63,94,0.2)]'
                )}
              >
                {trend.value}
              </span>
            )}
          </div>
          <div className="text-2xl lg:text-3xl font-black font-display text-white mt-0.5 tracking-tight group-hover:text-cyan-200 transition-colors truncate">
            {value}
          </div>
          {subtext && (
            <p className="text-[11px] text-slate-400 mt-0.5 font-sans truncate">
              {subtext}
            </p>
          )}
          {badge && <div className="mt-1">{badge}</div>}
        </div>
      </div>
    </div>
  );
};
