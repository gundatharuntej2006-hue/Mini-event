import { ReactNode, useEffect, useRef } from 'react';
import { useGSAP } from '@gsap/react';
import gsap from 'gsap';

export function LiveShell({ children }: { children: ReactNode }) {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    gsap.fromTo('.live-reveal', { autoAlpha: 0, y: 16 }, { autoAlpha: 1, y: 0, duration: .5, stagger: .07, ease: 'power3.out' });
  }, { scope: root });

  useEffect(() => { document.body.classList.add('live-body'); return () => document.body.classList.remove('live-body'); }, []);
  return <div ref={root} className="live-app"><div className="ambient ambient-one" /><div className="ambient ambient-two" />{children}</div>;
}

export const Mark = () => <div className="brand-mark live-reveal"><span className="mark-dot" />ASYMPTOTES <em>BMSIT</em></div>;
