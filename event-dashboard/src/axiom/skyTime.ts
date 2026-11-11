export type SkyPhase = 'morning' | 'afternoon' | 'evening' | 'night';
export type SkyClock = { phase: SkyPhase; minutes: number };

const indiaClock = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Kolkata',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
});

export function getSkyClock(at = new Date()): SkyClock {
  const parts = indiaClock.formatToParts(at);
  const hour = Number(parts.find(part => part.type === 'hour')?.value);
  const minute = Number(parts.find(part => part.type === 'minute')?.value);
  const minutes = hour * 60 + minute;
  const phase: SkyPhase = minutes >= 330 && minutes < 720 ? 'morning'
    : minutes >= 720 && minutes < 990 ? 'afternoon'
      : minutes >= 990 && minutes < 1155 ? 'evening' : 'night';
  return { phase, minutes };
}

export function msUntilNextMinute(now = Date.now()): number {
  return 60_000 - now % 60_000 + 25;
}
