/**
 * Timing and duration formatting utilities for Round 1: The Great Expedition
 */

export function formatDuration(seconds?: number | null): string {
  if (seconds === null || seconds === undefined || isNaN(seconds) || seconds < 0) {
    return 'Incomplete';
  }

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return `${hours}h ${String(minutes).padStart(2, '0')}m ${String(secs).padStart(2, '0')}s`;
  }
  return `${minutes}m ${String(secs).padStart(2, '0')}s`;
}

export function formatTimeOnly(isoString?: string | null): string {
  if (!isoString) return '—';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;
    return date.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    });
  } catch {
    return isoString;
  }
}

export function parseLocalTimeToISO(timeStr: string, baseDate = new Date()): string | null {
  if (!timeStr) return null;
  // If already an ISO string
  if (timeStr.includes('T')) {
    const parsed = new Date(timeStr);
    return isNaN(parsed.getTime()) ? null : parsed.toISOString();
  }

  // Expect HH:mm or HH:mm:ss format
  const parts = timeStr.split(':').map((p) => parseInt(p, 10));
  if (parts.some((p) => isNaN(p))) return null;

  const hours = parts[0];
  const minutes = parts[1] || 0;
  const seconds = parts[2] || 0;

  const d = new Date(baseDate);
  d.setHours(hours, minutes, seconds, 0);
  return d.toISOString();
}
