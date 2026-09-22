import { LucideIcon } from 'lucide-react';
import { cn } from '../../utils/cn';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-8 text-center bg-[#090d1a]/80 backdrop-blur-xl border border-dashed border-cyan-500/30 rounded-2xl',
        className
      )}
    >
      <div className="w-12 h-12 rounded-2xl bg-cyan-950/40 border border-cyan-500/30 flex items-center justify-center text-cyan-300 mb-3 shadow-[0_0_15px_rgba(6,182,212,0.2)]">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-orbitron font-bold text-slate-100">{title}</h3>
      <p className="text-xs text-slate-400 font-sans max-w-sm mt-1 mb-4">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="text-xs font-mono font-semibold text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 px-4 py-2 rounded-xl transition-all cursor-pointer shadow-[0_0_12px_rgba(6,182,212,0.3)]"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
