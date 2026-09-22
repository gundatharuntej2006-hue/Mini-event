import React from 'react';
import { Search, X } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface FilterOption {
  label: string;
  value: string;
}

export interface FilterConfig {
  id: string;
  label?: string;
  value: string;
  options: FilterOption[];
  onChange: (value: string) => void;
}

export interface SearchFilterToolbarProps {
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
  searchPlaceholder?: string;
  filters?: FilterConfig[];
  actions?: React.ReactNode;
  activeCount?: number;
  onClearAll?: () => void;
  className?: string;
}

export const SearchFilterToolbar: React.FC<SearchFilterToolbarProps> = ({
  searchQuery,
  onSearchChange,
  searchPlaceholder = 'Search records...',
  filters = [],
  actions,
  activeCount,
  onClearAll,
  className,
}) => {
  return (
    <div
      className={cn(
        'bg-[#061224]/85 backdrop-blur-xl rounded-2xl border border-cyan-500/35 p-3.5 shadow-[0_0_25px_rgba(6,182,212,0.12)] flex flex-col md:flex-row md:items-center justify-between gap-3',
        'before:absolute before:top-0 before:left-0 before:right-0 before:h-[1px] before:bg-gradient-to-r before:from-transparent before:via-cyan-400/30 before:to-transparent relative overflow-hidden',
        className
      )}
    >
      {/* Search Input */}
      <div className="flex-1 flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 min-w-0 relative z-10">
        {onSearchChange && (
          <div className="relative flex-1 min-w-[220px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cyan-400 pointer-events-none" />
            <input
              type="text"
              value={searchQuery || ''}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-full pl-9 pr-8 py-2 text-xs bg-[#030712]/90 border border-cyan-500/30 rounded-xl text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/50 transition-all shadow-inner font-sans"
            />
            {searchQuery && (
              <button
                onClick={() => onSearchChange('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 text-slate-400 hover:text-cyan-300 rounded"
                title="Clear search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}

        {/* Filter Selects */}
        {filters.length > 0 && (
          <div className="flex items-center flex-wrap gap-2">
            {filters.map((filter) => (
              <div key={filter.id} className="flex items-center gap-1.5">
                {filter.label && (
                  <span className="text-[11px] font-mono font-medium text-slate-400 whitespace-nowrap">
                    {filter.label}:
                  </span>
                )}
                <select
                  value={filter.value}
                  onChange={(e) => filter.onChange(e.target.value)}
                  className="text-xs bg-[#030712]/80 border border-cyan-500/20 rounded-xl py-2 px-2.5 text-slate-200 font-mono focus:outline-none focus:border-cyan-400 cursor-pointer"
                >
                  {filter.options.map((opt) => (
                    <option key={opt.value} value={opt.value} className="bg-slate-900 text-slate-200">
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            ))}

            {onClearAll && Boolean(activeCount && activeCount > 0) && (
              <button
                onClick={onClearAll}
                className="text-[11px] font-mono font-semibold text-cyan-400 hover:text-cyan-300 px-2 py-1 rounded-lg hover:bg-cyan-500/10 transition-colors cursor-pointer"
              >
                Reset ({activeCount})
              </button>
            )}
          </div>
        )}
      </div>

      {/* Right Actions Slot */}
      {actions && (
        <div className="flex items-center flex-wrap gap-2 shrink-0">
          {actions}
        </div>
      )}
    </div>
  );
};
