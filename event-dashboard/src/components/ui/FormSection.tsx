import React from 'react';
import { cn } from '../../utils/cn';

export interface FormSectionProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}

export const FormSection: React.FC<FormSectionProps> = ({
  title,
  description,
  children,
  className,
}) => {
  return (
    <div className={cn('space-y-3', className)}>
      <div className="pb-1 border-b border-slate-100">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
          {title}
        </h4>
        {description && (
          <p className="text-[11px] text-slate-400 mt-0.5">{description}</p>
        )}
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
};
