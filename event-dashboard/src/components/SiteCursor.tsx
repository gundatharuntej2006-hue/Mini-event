import { useEffect, useRef } from 'react';
import './site-cursor.css';

const interactiveSelector = 'a, button, summary, [role="button"], [role="link"], input[type="button"], input[type="submit"], input[type="reset"], input[type="checkbox"], input[type="radio"], input[type="range"], input[type="color"], input[type="file"]';
const textSelector = 'input:not([type="button"]):not([type="submit"]):not([type="reset"]):not([type="checkbox"]):not([type="radio"]):not([type="range"]):not([type="color"]):not([type="file"]), textarea, select, [contenteditable], [role="textbox"], p, h1, h2, h3, h4, h5, h6, span, small, strong, em, b, li, td, th, label, blockquote, pre, code';

/** A visual pointer with no position tween or React updates during movement. */
export function SiteCursor() {
  const cursorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const cursor = cursorRef.current;
    if (!cursor || typeof window.matchMedia !== 'function' || typeof CSS === 'undefined'
      || !CSS.supports('transform', 'translate3d(0px, 0px, 0px)')) return;

    const root = document.documentElement;
    const finePointer = matchMedia('(hover: hover) and (pointer: fine)');
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
    if (typeof finePointer.addEventListener !== 'function' || typeof reducedMotion.addEventListener !== 'function') return;
    let active = false;
    let textTarget = false;
    let hoverTarget = false;
    let lastTarget: EventTarget | null = null;

    const hide = () => {
      root.classList.remove('site-cursor-active');
      cursor.dataset.hover = 'false';
      cursor.dataset.pressed = 'false';
      cursor.dataset.text = 'false';
      active = false;
      textTarget = false;
      hoverTarget = false;
      lastTarget = null;
    };

    const updateTarget = (target: EventTarget | null) => {
      if (target === lastTarget) return;
      lastTarget = target;
      const element = target instanceof Element ? target : null;
      const interactive = Boolean(element?.closest(interactiveSelector));
      const text = !interactive && Boolean(element?.closest(textSelector));
      if (text !== textTarget) {
        textTarget = text;
        cursor.dataset.text = String(text);
      }
      if (interactive !== hoverTarget) {
        hoverTarget = interactive;
        cursor.dataset.hover = String(interactive);
      }
    };

    const move = (event: PointerEvent) => {
      if (!finePointer.matches || reducedMotion.matches || event.pointerType !== 'mouse') {
        if (active) hide();
        return;
      }
      // Position is updated in the pointer event itself: no spring, queue, or
      // animation frame can make the visual cursor trail the real pointer.
      cursor.style.transform = `translate3d(${event.clientX - 6}px, ${event.clientY - 6}px, 0)`;
      if (!active) {
        active = true;
        root.classList.add('site-cursor-active');
      }
      updateTarget(event.target);
    };

    const over = (event: PointerEvent) => {
      if (active && event.pointerType === 'mouse') updateTarget(event.target);
    };
    const down = (event: PointerEvent) => {
      move(event);
      if (active && !textTarget) cursor.dataset.pressed = 'true';
    };
    const up = () => { cursor.dataset.pressed = 'false'; };
    const visibility = () => { if (document.hidden) hide(); };

    window.addEventListener('pointermove', move, { passive: true });
    window.addEventListener('pointerover', over, { passive: true });
    window.addEventListener('pointerdown', down, { passive: true });
    window.addEventListener('pointerup', up, { passive: true });
    window.addEventListener('pointercancel', up, { passive: true });
    window.addEventListener('blur', hide);
    document.addEventListener('pointerleave', hide);
    document.addEventListener('visibilitychange', visibility);
    finePointer.addEventListener('change', hide);
    reducedMotion.addEventListener('change', hide);
    return () => {
      hide();
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerover', over);
      window.removeEventListener('pointerdown', down);
      window.removeEventListener('pointerup', up);
      window.removeEventListener('pointercancel', up);
      window.removeEventListener('blur', hide);
      document.removeEventListener('pointerleave', hide);
      document.removeEventListener('visibilitychange', visibility);
      finePointer.removeEventListener('change', hide);
      reducedMotion.removeEventListener('change', hide);
    };
  }, []);

  return <div ref={cursorRef} className="site-cursor" aria-hidden="true"><span /></div>;
}
