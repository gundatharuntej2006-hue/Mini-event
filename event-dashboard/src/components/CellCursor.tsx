import { useEffect, useRef } from 'react';
import './cell-cursor.css';

/** A lightweight visual cursor for fine pointers; standard cursor remains for touch and reduced motion. */
export function CellCursor() {
  const cellRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const cell = cellRef.current;
    if (!cell || !matchMedia('(pointer:fine)').matches || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    let shape = 0;
    const place = (x: number, y: number) => { cell.style.transform = `translate3d(${x - 19}px,${y - 19}px,0)`; };
    const move = (event: PointerEvent) => { place(event.clientX, event.clientY); cell.style.opacity = '1'; };
    const leave = () => { cell.style.opacity = '0'; };
    const click = (event: PointerEvent) => {
      // Keep the morph pinned beneath the press. The visual animation never owns
      // `transform`, which remains exclusively responsible for cursor position.
      place(event.clientX, event.clientY);
      shape = (shape + 1) % 7; cell.dataset.shape = String(shape);
      cell.classList.remove('is-dividing'); void cell.offsetWidth; cell.classList.add('is-dividing');
    };
    document.documentElement.classList.add('cell-cursor-enabled'); window.addEventListener('pointermove', move, { passive: true }); window.addEventListener('pointerdown', click, { passive: true }); document.addEventListener('pointerleave', leave); document.addEventListener('pointerenter', move as EventListener);
    return () => { document.documentElement.classList.remove('cell-cursor-enabled'); window.removeEventListener('pointermove', move); window.removeEventListener('pointerdown', click); document.removeEventListener('pointerleave', leave); document.removeEventListener('pointerenter', move as EventListener); };
  }, []);
  return <div ref={cellRef} className="cell-cursor" data-shape="0" aria-hidden="true"><i className="cell-membrane"/><i className="cell-cytoplasm"/><i className="cell-nucleus"/><i className="cell-nucleolus"/><i className="cell-organelle one"/><i className="cell-organelle two"/></div>;
}
