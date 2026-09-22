import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  currentPage: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  className?: string;
}

export function Pagination({
  currentPage,
  totalItems,
  pageSize,
  onPageChange,
  className = '',
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const startItem = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(totalItems, currentPage * pageSize);

  if (totalPages <= 1 && totalItems <= pageSize) {
    return (
      <div className={`flex items-center justify-between px-4 py-3 bg-[#070b16]/70 border-t border-cyan-500/20 text-xs text-slate-400 font-mono ${className}`}>
        <span>Showing {totalItems} total records</span>
      </div>
    );
  }

  return (
    <div className={`flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 bg-[#070b16]/70 border-t border-cyan-500/20 text-xs text-slate-400 font-mono ${className}`}>
      <div>
        Showing <span className="font-bold text-cyan-300">{startItem}</span> to{' '}
        <span className="font-bold text-cyan-300">{endItem}</span> of{' '}
        <span className="font-bold text-cyan-300">{totalItems}</span> records
      </div>

      <div className="flex items-center gap-1.5">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="p-1.5 rounded-xl border border-cyan-500/20 bg-[#030712]/80 text-slate-300 hover:border-cyan-400 hover:text-cyan-300 disabled:opacity-30 disabled:pointer-events-none transition-colors cursor-pointer"
          aria-label="Previous page"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-1 px-1 font-mono font-medium">
          {Array.from({ length: totalPages }, (_, i) => i + 1)
            .filter((p) => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1)
            .map((page, idx, array) => {
              const showEllipsisBefore = idx > 0 && page - array[idx - 1] > 1;
              return (
                <span key={page} className="flex items-center">
                  {showEllipsisBefore && <span className="px-1 text-slate-600">…</span>}
                  <button
                    onClick={() => onPageChange(page)}
                    className={`min-w-[28px] h-7 px-2 rounded-lg text-xs font-mono font-bold transition-all cursor-pointer ${
                      currentPage === page
                        ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-[0_0_10px_rgba(6,182,212,0.4)] border border-cyan-300/40'
                        : 'text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10'
                    }`}
                  >
                    {page}
                  </button>
                </span>
              );
            })}
        </div>

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="p-1.5 rounded-xl border border-cyan-500/20 bg-[#030712]/80 text-slate-300 hover:border-cyan-400 hover:text-cyan-300 disabled:opacity-30 disabled:pointer-events-none transition-colors cursor-pointer"
          aria-label="Next page"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
