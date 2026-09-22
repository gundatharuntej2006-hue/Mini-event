import { useState, useEffect } from 'react';
import {
  Users,
  UserCheck,
  Compass,
  Trophy,
  RefreshCw,
  RotateCcw,
} from 'lucide-react';
import { SummaryMetric } from '../components/ui/SummaryMetric';
import { RoundProgressCard } from '../components/dashboard/RoundProgressCard';
import { RecentActivityFeed } from '../components/dashboard/RecentActivityFeed';
import { QuickActionsPanel } from '../components/dashboard/QuickActionsPanel';
import { MetricSkeleton } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { ConfirmationDialog } from '../components/ui/ConfirmationDialog';
import { eventService } from '../services/eventService';
import { isLiveMode, onAppModeChange } from '../services/apiConfig';
import { DashboardOverviewData } from '../types';

export function OverviewPage() {
  const [data, setData] = useState<DashboardOverviewData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isResetConfirmOpen, setIsResetConfirmOpen] = useState(false);

  const loadDashboardData = async () => {
    setError(null);
    try {
      const res = await eventService.getDashboardOverview();
      setData(res.data);
    } catch (err: unknown) {
      setError((err as Error).message || 'Failed to load dashboard overview data.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
    const unsubscribe = eventService.subscribe(() => {
      loadDashboardData();
    });
    const unsubMode = onAppModeChange(() => {
      loadDashboardData();
    });
    return () => {
      unsubscribe();
      unsubMode();
    };
  }, []);

  const handleResetDemo = () => {
    setIsResetConfirmOpen(true);
  };

  const executeResetDemo = async () => {
    try {
      eventService.resetToDemoData();
      setIsResetConfirmOpen(false);
      await loadDashboardData();
    } catch (err: unknown) {
      setError((err as Error).message || 'Failed to reset demo data.');
    }
  };

  const checkInRate =
    data?.stats && data.stats.totalParticipants > 0
      ? Math.round((data.stats.checkedInParticipants / data.stats.totalParticipants) * 100)
      : 0;

  return (
    <div className="space-y-6">
      {/* Hero Header matching 3D Cyber Command Center */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-2 min-h-[120px]">
        <div>
          <div className="text-2xl sm:text-3xl lg:text-4xl font-black font-display tracking-tight uppercase leading-tight">
            <span className="text-white">OPERATIONS </span>
            <span className="text-cyan-400 drop-shadow-[0_0_15px_rgba(34,211,238,0.8)]">COMMAND</span>
            <div className="text-white drop-shadow-[0_0_20px_rgba(255,255,255,0.2)]">CENTER</div>
          </div>
          <p className="text-xs sm:text-sm text-slate-300 mt-2 max-w-xl font-sans leading-relaxed">
            Real-time telemetry, squad accreditation, multi-round elimination status, and field operations
          </p>
          <div className="mt-3 flex items-center gap-2.5">
            {isLiveMode() ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-cyan-950/60 border border-cyan-400/50 text-cyan-300 shadow-[0_0_12px_rgba(34,211,238,0.3)]">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                Live API Telemetry Connected
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-amber-950/60 border border-amber-400/50 text-amber-300 shadow-[0_0_12px_rgba(251,191,36,0.3)]">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                Demo Simulation Mode
              </span>
            )}
          </div>
        </div>

        {/* Right side controls */}
        <div className="flex items-center gap-2.5 self-start lg:self-center shrink-0">
          {!isLiveMode() && (
            <button
              onClick={handleResetDemo}
              className="px-3.5 py-2 text-xs font-semibold rounded-xl border border-amber-500/40 bg-amber-950/40 text-amber-300 hover:bg-amber-900/50 transition-all flex items-center gap-2 font-mono backdrop-blur-md shadow-sm"
              title="Reset simulation to default test dataset"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset Demo State</span>
            </button>
          )}
          <button
            onClick={loadDashboardData}
            disabled={isLoading}
            className="px-4 py-2 text-xs font-semibold rounded-xl border border-cyan-400/50 bg-cyan-950/60 text-cyan-300 hover:bg-cyan-900/60 shadow-[0_0_12px_rgba(34,211,238,0.25)] transition-all flex items-center gap-2 font-mono"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh Telemetry</span>
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <ErrorState
          title="Telemetry Connection Issue"
          message={error}
          onRetry={loadDashboardData}
        />
      )}

      {/* Primary KPI Metric Cards Grid */}
      {isLoading || !data || !data.stats ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricSkeleton />
          <MetricSkeleton />
          <MetricSkeleton />
          <MetricSkeleton />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <SummaryMetric
            label="Registered Squads"
            value={data.stats.totalTeams}
            subtext={`${data.stats.completeRosterTeams} of ${data.stats.totalTeams} squads with full 5-member rosters`}
            icon={Users}
            variant="blue"
            trend={{
              value: data.stats.incompleteRosterTeams === 0 ? 'All 5/5 Full' : `${data.stats.incompleteRosterTeams} Incomplete`,
              isPositive: data.stats.incompleteRosterTeams === 0,
            }}
          />

          <SummaryMetric
            label="Accredited Students"
            value={data.stats.totalParticipants}
            subtext={`${data.stats.checkedInParticipants} checked in at security desk`}
            icon={UserCheck}
            variant="emerald"
            trend={{
              value: `${checkInRate}% Checked In`,
              isPositive: checkInRate >= 75,
            }}
          />

          <SummaryMetric
            label="Active Tournament Phase"
            value={data.stats.currentRoundName}
            subtext={`${data.stats.qualifiedTeamsTarget} squads advance to subsequent phase`}
            icon={Compass}
            variant="amber"
          />

          <SummaryMetric
            label="Elimination Pipeline"
            value={`${data.stats.activeTeamsRemaining} Teams`}
            subtext="Currently holding qualifying standing"
            icon={Trophy}
            variant="purple"
          />
        </div>
      )}

      {/* Round Progress Pipeline Card */}
      <RoundProgressCard steps={data?.progression} />

      {/* Bottom Grid: Quick Actions & Live Activity Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <QuickActionsPanel />
        </div>

        <div className="lg:col-span-2">
          <RecentActivityFeed activities={data?.recentActivities} />
        </div>
      </div>

      {/* Demo Reset Confirmation Modal */}
      <ConfirmationDialog
        isOpen={isResetConfirmOpen}
        onClose={() => setIsResetConfirmOpen(false)}
        onConfirm={executeResetDemo}
        title="Reset Demo Simulation State"
        message="Are you sure you want to reset demo data? This will restore the default 32 squads and 160 participants in local browser storage. (Does not affect the real PostgreSQL/SQLite backend)."
        confirmLabel="Reset Demo Data"
        isDestructive={true}
      />
    </div>
  );
}
