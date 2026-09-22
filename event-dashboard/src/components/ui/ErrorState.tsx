import React from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';
import { cn } from '../../utils/cn';
import { Button } from './Button';

export interface ErrorStateProps {
  title?: string;
  message: string;
  statusCode?: number;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Failed to Load Data',
  message,
  statusCode,
  onRetry,
  className,
}) => {
  return (
    <div
      className={cn(
        'bg-white rounded-xl border border-rose-200 p-8 shadow-sm flex flex-col items-center justify-center text-center',
        className
      )}
    >
      <div className="w-12 h-12 rounded-full bg-rose-50 border border-rose-200/80 flex items-center justify-center text-rose-600 mb-3">
        <AlertTriangle className="w-6 h-6" />
      </div>

      <h3 className="text-sm font-bold text-slate-900">
        {title}
        {statusCode && (
          <span className="ml-2 font-mono text-xs font-semibold px-2 py-0.5 rounded bg-rose-100 text-rose-800">
            HTTP {statusCode}
          </span>
        )}
      </h3>

      <p className="text-xs text-slate-500 max-w-md mt-1 mb-4 leading-relaxed">
        {message}
      </p>

      {onRetry && (
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
        >
          Retry Request
        </Button>
      )}
    </div>
  );
};
