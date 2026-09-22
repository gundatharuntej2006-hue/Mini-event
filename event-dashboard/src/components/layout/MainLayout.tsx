import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNavbar } from './TopNavbar';
import { DemoModeBanner } from '../ui/Banner';
import { Cyber3DBackground } from '../ui/Cyber3DBackground';
import { cn } from '../../utils/cn';

export function MainLayout() {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isDesktopCollapsed, setIsDesktopCollapsed] = useState(() => {
    try {
      return localStorage.getItem('event_hq_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const handleToggleSidebar = () => {
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      setIsMobileSidebarOpen((prev) => !prev);
    } else {
      setIsDesktopCollapsed((prev) => {
        const next = !prev;
        try {
          localStorage.setItem('event_hq_sidebar_collapsed', String(next));
        } catch {
          // ignore
        }
        return next;
      });
    }
  };

  return (
    <div className="min-h-screen bg-[#030712] text-slate-100 flex relative overflow-x-hidden selection:bg-cyan-500 selection:text-black font-sans">
      {/* 3D Cyber Animated Background (Persistent Three.js scene behind all routes) */}
      <Cyber3DBackground />

      {/* Top Cyber Laser Ambient Bar */}
      <div className="fixed top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-cyan-500 via-blue-500 to-fuchsia-500 z-50 shadow-[0_0_12px_rgba(34,211,238,0.8)] pointer-events-none" />

      {/* Atmospheric Ambient Glows matching Anvation */}
      <div className="fixed -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-cyan-600/10 blur-3xl pointer-events-none" />
      <div className="fixed top-1/3 -right-40 w-[500px] h-[500px] rounded-full bg-violet-600/10 blur-3xl pointer-events-none" />
      <div className="fixed -bottom-40 left-1/4 w-[600px] h-[600px] rounded-full bg-cyan-500/5 blur-3xl pointer-events-none" />

      {/* Persistent & Responsive Navigation Sidebar */}
      <Sidebar
        isOpen={isMobileSidebarOpen}
        onClose={() => setIsMobileSidebarOpen(false)}
        isCollapsed={isDesktopCollapsed}
        onToggleCollapse={handleToggleSidebar}
      />

      {/* Main Content Viewport */}
      <div
        className={cn(
          'flex-1 flex flex-col min-w-0 relative z-10 transition-all duration-300 ease-in-out',
          isDesktopCollapsed ? 'lg:pl-20' : 'lg:pl-64'
        )}
      >
        <TopNavbar
          onToggleSidebar={handleToggleSidebar}
          isSidebarCollapsed={isDesktopCollapsed}
          isMobileSidebarOpen={isMobileSidebarOpen}
        />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
          <DemoModeBanner />
          <Outlet />
        </main>
      </div>
    </div>
  );
}
