import React from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown, FolderOpen } from 'lucide-react';
import { cn } from '../../utils/cn';
import { TableSkeleton } from './LoadingState';
import { EmptyState } from './EmptyState';

export interface ColumnDef<T> {
  id: string;
  header: React.ReactNode;
  cell: (row: T, index: number) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  className?: string;
  sortable?: boolean;
}

export interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  keyExtractor: (row: T, index: number) => string;
  isLoading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  sortField?: string;
  sortOrder?: 'asc' | 'desc';
  onSort?: (fieldId: string) => void;
  className?: string;
  rowClassName?: (row: T, index: number) => string | undefined;
}

export function DataTable<T>({
  data,
  columns,
  keyExtractor,
  isLoading = false,
  emptyTitle = 'No records found',
  emptyDescription = 'There are no matching items for the selected criteria.',
  sortField,
  sortOrder,
  onSort,
  className,
  rowClassName,
}: DataTableProps<T>) {
  if (isLoading) {
    return <TableSkeleton rows={6} columns={columns.length} />;
  }

  if (data.length === 0) {
    return (
      <div className="bg-[#090d1a]/80 backdrop-blur-xl rounded-2xl border border-cyan-500/20 shadow-[0_8px_32px_rgba(0,0,0,0.4)] p-6">
        <EmptyState icon={FolderOpen} title={emptyTitle} description={emptyDescription} />
      </div>
    );
  }

  return (
    <div
      className={cn(
        'bg-[#090d1a]/80 backdrop-blur-xl rounded-2xl border border-cyan-500/20 shadow-[0_8px_32px_rgba(0,0,0,0.4)] overflow-hidden transition-all',
        className
      )}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-[#030712]/90 border-b border-cyan-500/20 text-[11px] font-mono font-bold uppercase tracking-wider text-cyan-400/80">
              {columns.map((col) => {
                const isSorted = sortField === col.id;
                const alignmentClass =
                  col.align === 'center'
                    ? 'text-center'
                    : col.align === 'right'
                    ? 'text-right'
                    : 'text-left';

                return (
                  <th
                    key={col.id}
                    className={cn('py-3.5 px-4 font-mono select-none', alignmentClass, col.className)}
                  >
                    {col.sortable && onSort ? (
                      <button
                        onClick={() => onSort(col.id)}
                        className={cn(
                          'inline-flex items-center gap-1 hover:text-cyan-300 transition-colors focus:outline-none cursor-pointer',
                          isSorted ? 'text-cyan-300 font-bold' : ''
                        )}
                      >
                        <span>{col.header}</span>
                        {isSorted ? (
                          sortOrder === 'asc' ? (
                            <ArrowUp className="w-3.5 h-3.5 text-cyan-400" />
                          ) : (
                            <ArrowDown className="w-3.5 h-3.5 text-cyan-400" />
                          )
                        ) : (
                          <ArrowUpDown className="w-3.5 h-3.5 text-slate-500 opacity-60" />
                        )}
                      </button>
                    ) : (
                      col.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-cyan-500/10 text-xs text-slate-300 font-sans">
            {data.map((row, idx) => {
              const extraClass = rowClassName ? rowClassName(row, idx) : '';
              return (
                <tr
                  key={keyExtractor(row, idx)}
                  className={cn(
                    'hover:bg-cyan-500/[0.05] transition-colors',
                    extraClass
                  )}
                >
                  {columns.map((col) => {
                    const alignmentClass =
                      col.align === 'center'
                        ? 'text-center'
                        : col.align === 'right'
                        ? 'text-right'
                        : 'text-left';

                    return (
                      <td
                        key={col.id}
                        className={cn('py-3.5 px-4 align-middle', alignmentClass, col.className)}
                      >
                        {col.cell(row, idx)}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
