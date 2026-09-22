import { Clock, QrCode, UserCheck, Shield, Award, Terminal } from 'lucide-react';
import { Card, CardHeader, CardContent } from '../ui/Card';
import { Badge, BadgeVariant } from '../ui/Badge';
import { ActivityLogItem, ActivityCategory } from '../../types';
import { formatRelativeTime } from '../../utils/formatters';

interface RecentActivityFeedProps {
  activities?: ActivityLogItem[] | null;
}

export function RecentActivityFeed({ activities }: RecentActivityFeedProps) {
  const getCategoryIcon = (cat: ActivityCategory) => {
    switch (cat) {
      case 'clue':
        return QrCode;
      case 'checkin':
        return UserCheck;
      case 'agent':
        return Shield;
      case 'qualification':
        return Award;
      default:
        return Terminal;
    }
  };

  const mapBadgeVariant = (type: ActivityLogItem['badgeType']): BadgeVariant => {
    switch (type) {
      case 'success':
        return 'success';
      case 'warning':
        return 'warning';
      case 'danger':
        return 'danger';
      case 'info':
        return 'primary';
      default:
        return 'neutral';
    }
  };

  if (!activities || !Array.isArray(activities)) {
    return (
      <Card>
        <CardHeader
          title="Live Operations Activity Log"
          subtitle="Recent checkpoint triggers, registration check-ins, and system notices"
          action={
            <Badge variant="neutral" size="sm">
              Telemetry Offline
            </Badge>
          }
        />
        <CardContent>
          <div className="rounded-2xl border border-dashed border-cyan-500/20 p-8 text-center text-slate-400 bg-[#030712]/60">
            <p className="text-xs font-orbitron font-semibold text-slate-300">
              Activity telemetry stream is currently offline.
            </p>
            <p className="text-[11px] font-mono text-cyan-400/60 mt-1">
              Could not retrieve activity logs from server.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (activities.length === 0) {
    return (
      <Card>
        <CardHeader
          title="Live Operations Activity Log"
          subtitle="Recent checkpoint triggers, registration check-ins, and system notices"
          action={
            <Badge variant="neutral" size="sm">
              0 Events
            </Badge>
          }
        />
        <CardContent>
          <div className="rounded-2xl border border-dashed border-cyan-500/20 p-8 text-center text-slate-400 bg-[#030712]/60">
            <p className="text-xs font-orbitron font-semibold text-slate-300">
              No recent activity logged yet.
            </p>
            <p className="text-[11px] font-mono text-cyan-400/60 mt-1">
              Telemetry will automatically update as participant check-ins and scoring events are recorded.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title="Live Operations Activity Log"
        subtitle="Recent checkpoint triggers, registration check-ins, and system notices"
        action={
          <Badge variant="neutral" size="sm">
            {activities.length} {activities.length === 1 ? 'Event' : 'Events'}
          </Badge>
        }
      />
      <CardContent className="p-0">
        <div className="divide-y divide-cyan-500/10">
          {activities.map((item) => {
            const Icon = getCategoryIcon(item.category);
            return (
              <div
                key={item.id}
                className="p-4 flex items-start gap-3.5 hover:bg-cyan-500/[0.05] transition-colors"
              >
                <div className="w-8 h-8 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-cyan-400 flex-shrink-0 mt-0.5 shadow-sm">
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-orbitron font-semibold text-slate-200">
                        {item.title}
                      </span>
                      {item.teamTag && (
                        <span className="text-[10px] font-mono font-bold bg-cyan-950/50 text-cyan-300 px-1.5 py-0.5 rounded border border-cyan-500/30">
                          {item.teamTag}
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] font-mono text-slate-500 flex items-center gap-1 flex-shrink-0">
                      <Clock className="w-3 h-3 text-cyan-500/60" />
                      {formatRelativeTime(item.timestamp)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed font-sans">
                    {item.description}
                  </p>
                </div>
                <div className="flex-shrink-0">
                  <Badge variant={mapBadgeVariant(item.badgeType)} size="sm">
                    {item.category}
                  </Badge>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
