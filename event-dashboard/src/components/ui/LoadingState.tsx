import React from 'react';
import { cn } from '../../utils/cn';

export interface LoadingSkeletonProps {
  className?: string;
}

export const SkeletonBox: React.FC<LoadingSkeletonProps> = ({ className }) => (
  <div className={cn('bg-slate-800/60 rounded-xl animate-pulse', className)} />
);

export const MetricSkeleton: React.FC = () => (
  <div className="bg-[#090d1a]/80 backdrop-blur-xl rounded-2xl border border-cyan-500/20 p-5 shadow-[0_8px_32px_rgba(0,0,0,0.4)] space-y-3">
    <div className="flex items-center justify-between">
      <SkeletonBox className="h-3.5 w-24" />
      <SkeletonBox className="h-9 w-9 rounded-xl" />
    </div>
    <SkeletonBox className="h-7 w-20" />
    <SkeletonBox className="h-3 w-36" />
  </div>
);

export const TableSkeleton: React.FC<{ rows?: number; columns?: number }> = ({
  rows = 5,
  columns = 5,
}) => (
  <div className="bg-[#090d1a]/80 backdrop-blur-xl rounded-2xl border border-cyan-500/20 shadow-[0_8px_32px_rgba(0,0,0,0.4)] overflow-hidden">
    <div className="p-4 border-b border-cyan-500/20 flex items-center justify-between bg-[#030712]/90">
      <SkeletonBox className="h-5 w-32" />
      <SkeletonBox className="h-8 w-24 rounded-xl" />
    </div>
    <div className="divide-y divide-cyan-500/10">
      {Array.from({ length: rows }).map((_, rIdx) => (
        <div key={rIdx} className="p-4 flex items-center gap-4">
          {Array.from({ length: columns }).map((_, cIdx) => (
            <SkeletonBox
              key={cIdx}
              className={cn(
                'h-4',
                cIdx === 0 ? 'w-16' : cIdx === 1 ? 'w-48' : 'w-24'
              )}
            />
          ))}
        </div>
      ))}
    </div>
  </div>
);

export const LoadingState: React.FC<{ message?: string; className?: string }> = ({
  message = 'Loading data...',
  className,
}) => (
  <div
    className={cn(
      'bg-[#090d1a]/80 backdrop-blur-xl rounded-2xl border border-cyan-500/20 p-12 shadow-[0_8px_32px_rgba(0,0,0,0.4)] flex flex-col items-center justify-center text-center',
      className
    )}
  >
    <div className="w-9 h-9 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mb-3 shadow-[0_0_15px_rgba(6,182,212,0.4)]" />
    <p className="text-xs font-orbitron font-bold text-slate-200">{message}</p>
    <p className="text-[11px] font-mono text-cyan-400/70 mt-1">Accessing telemetry stream...</p>
  </div>
);
