import { LucideIcon } from 'lucide-react';
import { cn } from '../../utils/cn';

interface MetricCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  badge?: {
    text: string;
    variant: 'blue' | 'emerald' | 'amber' | 'purple';
  };
  trend?: {
    text: string;
    isPositive?: boolean;
  };
  className?: string;
}

export function MetricCard({
  label,
  value,
  subtitle,
  icon: Icon,
  badge,
  trend,
  className,
}: MetricCardProps) {
  const badgeStyles = {
    blue: 'bg-cyan-950/50 text-cyan-300 border-cyan-500/30 shadow-[0_0_8px_rgba(6,182,212,0.2)]',
    emerald: 'bg-emerald-950/50 text-emerald-300 border-emerald-500/30 shadow-[0_0_8px_rgba(16,185,129,0.2)]',
    amber: 'bg-amber-950/50 text-amber-300 border-amber-500/30 shadow-[0_0_8px_rgba(245,158,11,0.2)]',
    purple: 'bg-violet-950/50 text-violet-300 border-violet-500/30 shadow-[0_0_8px_rgba(139,92,246,0.2)]',
  };

  const iconBgStyles = {
    blue: 'bg-cyan-950/50 text-cyan-400 border border-cyan-500/30 shadow-[0_0_12px_rgba(6,182,212,0.25)]',
    emerald: 'bg-emerald-950/50 text-emerald-400 border border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.25)]',
    amber: 'bg-amber-950/50 text-amber-400 border border-amber-500/30 shadow-[0_0_12px_rgba(245,158,11,0.25)]',
    purple: 'bg-violet-950/50 text-violet-400 border border-violet-500/30 shadow-[0_0_12px_rgba(139,92,246,0.25)]',
  };

  const currentTheme = badge?.variant || 'blue';

  return (
    <div
      className={cn(
        'relative bg-[#090d1a]/80 backdrop-blur-xl border border-cyan-500/20 rounded-2xl p-5 shadow-[0_8px_32px_rgba(0,0,0,0.4)] transition-all duration-300 hover:border-cyan-400/50 hover:shadow-[0_0_24px_rgba(6,182,212,0.18)] hover:-translate-y-0.5 overflow-hidden group',
        'before:absolute before:top-0 before:left-0 before:right-0 before:h-[1px] before:bg-gradient-to-r before:from-transparent before:via-cyan-400/30 before:to-transparent',
        className
      )}
    >
      <div className="flex items-center justify-between gap-2 relative z-10">
        <span className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider">
          {label}
        </span>
        <div
          className={cn(
            'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-105',
            iconBgStyles[currentTheme]
          )}
        >
          <Icon className="w-5 h-5" />
        </div>
      </div>

      <div className="mt-3 flex items-baseline gap-2 relative z-10">
        <span className="text-2xl lg:text-3xl font-orbitron font-extrabold tracking-tight text-white group-hover:text-cyan-200 transition-colors">
          {value}
        </span>
        {badge && (
          <span
            className={cn(
              'text-[11px] font-mono font-bold px-2 py-0.5 rounded-full border',
              badgeStyles[badge.variant]
            )}
          >
            {badge.text}
          </span>
        )}
      </div>

      {(subtitle || trend) && (
        <div className="mt-3 text-xs text-slate-400 font-mono flex items-center justify-between gap-1 border-t border-slate-800/80 pt-2 relative z-10">
          {subtitle && <span>{subtitle}</span>}
          {trend && (
            <span
              className={cn(
                'font-medium text-[11px]',
                trend.isPositive ? 'text-emerald-400' : 'text-slate-400'
              )}
            >
              {trend.text}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
