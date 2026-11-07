import { useEffect, useRef } from 'react';
import './cell-cursor.css';

/** A lightweight visual cursor for fine pointers; standard cursor remains for touch and reduced motion. */
export function CellCursor() {
  const cellRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const cell = cellRef.current;
    if (!cell || !matchMedia('(pointer:fine)').matches || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    let frame = 0; let x = innerWidth / 2; let y = innerHeight / 2; let cx = x; let cy = y;
    const move = (event: PointerEvent) => { x = event.clientX; y = event.clientY; cell.style.opacity = '1'; };
    const leave = () => { cell.style.opacity = '0'; };
    const render = () => { cx += (x - cx) * .2; cy += (y - cy) * .2; cell.style.transform = `translate3d(${cx - 16}px,${cy - 16}px,0)`; frame = requestAnimationFrame(render); };
    document.documentElement.classList.add('cell-cursor-enabled'); window.addEventListener('pointermove', move, { passive: true }); document.addEventListener('pointerleave', leave); document.addEventListener('pointerenter', move as EventListener); frame = requestAnimationFrame(render);
    return () => { cancelAnimationFrame(frame); document.documentElement.classList.remove('cell-cursor-enabled'); window.removeEventListener('pointermove', move); document.removeEventListener('pointerleave', leave); document.removeEventListener('pointerenter', move as EventListener); };
  }, []);
  return <div ref={cellRef} className="cell-cursor" aria-hidden="true"><i className="cell-membrane"/><i className="cell-cytoplasm"/><i className="cell-nucleus"/><i className="cell-nucleolus"/><i className="cell-organelle one"/><i className="cell-organelle two"/></div>;
}
