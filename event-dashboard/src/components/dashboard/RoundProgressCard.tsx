import { Check, ChevronRight, Compass, ShieldAlert, Sparkles, Scale, Layers as CardsIcon } from 'lucide-react';
import { Card, CardHeader, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { RoundProgressionStep } from '../../types';

interface RoundProgressCardProps {
  steps?: RoundProgressionStep[] | null;
}

export function RoundProgressCard({ steps }: RoundProgressCardProps) {
  const getRoundIcon = (roundNumber: number) => {
    switch (roundNumber) {
      case 1:
        return Compass;
      case 2:
        return CardsIcon || Sparkles;
      case 3:
        return ShieldAlert;
      case 4:
        return Scale;
      case 5:
        return Sparkles;
      default:
        return Compass;
    }
  };

  if (!steps || !Array.isArray(steps)) {
    return (
      <Card>
        <CardHeader
          title="Tournament Progression & Elimination Pipeline"
          subtitle="32 Squads competing across 4 progressive elimination rounds into the Grand Finale"
          action={
            <Badge variant="neutral" size="sm">
              Telemetry Offline
            </Badge>
          }
        />
        <CardContent>
          <div className="rounded-2xl border border-dashed border-cyan-500/20 p-6 text-center text-slate-400 bg-[#030712]/60">
            <p className="text-xs font-orbitron font-semibold text-slate-300">
              Tournament progression pipeline telemetry is offline.
            </p>
            <p className="text-[11px] font-mono text-cyan-400/60 mt-1">
              Could not retrieve round stages from event gateway.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (steps.length === 0) {
    return (
      <Card>
        <CardHeader
          title="Tournament Progression & Elimination Pipeline"
          subtitle="32 Squads competing across 4 progressive elimination rounds into the Grand Finale"
          action={
            <Badge variant="neutral" size="sm">
              Empty Pipeline
            </Badge>
          }
        />
        <CardContent>
          <div className="rounded-2xl border border-dashed border-cyan-500/20 p-6 text-center text-slate-400 bg-[#030712]/60">
            <p className="text-xs font-orbitron font-semibold text-slate-300">
              No tournament stages currently configured.
            </p>
            <p className="text-[11px] font-mono text-cyan-400/60 mt-1">
              Tournament schedule has not been populated.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Calculate current active stage for header badge
  const activeStep = steps.find((s) => s.status === 'Live' || s.status === 'In Progress') 
    || steps.find((s) => s.status === 'Scheduled') 
    || steps[steps.length - 1];
  const stageNum = activeStep ? activeStep.roundNumber : 1;

  return (
    <Card>
      <CardHeader
        title="Tournament Progression & Elimination Pipeline"
        subtitle="32 Squads competing across 4 progressive elimination rounds into the Grand Finale"
        action={
          <Badge variant="primary" size="sm">
            Stage {stageNum} of {steps.length} Active
          </Badge>
        }
      />
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 relative">
          {steps.map((step, idx) => {
            const Icon = getRoundIcon(step.roundNumber);
            const isLive = step.status === 'Live' || step.status === 'In Progress';
            const isCompleted = step.status === 'Completed';

            return (
              <div
                key={step.roundNumber}
                className={`relative rounded-2xl p-4 border transition-all duration-300 ${
                  isLive
                    ? 'bg-gradient-to-b from-cyan-950/60 to-[#090d1a] border-cyan-400/60 shadow-[0_0_24px_rgba(6,182,212,0.25)] ring-1 ring-cyan-400/30'
                    : isCompleted
                    ? 'bg-emerald-950/20 border-emerald-500/30 hover:border-emerald-500/50'
                    : 'bg-[#030712]/60 border-slate-800/80 hover:border-cyan-500/30'
                }`}
              >
                {/* Step Header */}
                <div className="flex items-center justify-between gap-1 mb-2.5">
                  <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
                    Stage // 0{step.roundNumber}
                  </span>
                  {isLive && (
                    <span className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded-full border border-cyan-400/50 shadow-[0_0_8px_rgba(6,182,212,0.3)]">
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                      LIVE
                    </span>
                  )}
                  {isCompleted && (
                    <span className="text-emerald-400 flex items-center gap-1 text-[10px] font-mono font-semibold">
                      <Check className="w-3.5 h-3.5" />
                      DONE
                    </span>
                  )}
                </div>

                {/* Round Title & Icon */}
                <div className="flex items-start gap-2.5 mb-3">
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-xs border ${
                      isLive
                        ? 'bg-gradient-to-br from-cyan-500 to-blue-600 text-white border-cyan-300/40 shadow-[0_0_12px_rgba(6,182,212,0.4)]'
                        : isCompleted
                        ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/40'
                        : 'bg-slate-900 text-slate-400 border-slate-800'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-xs font-orbitron font-bold text-slate-100 truncate" title={step.name}>
                      {step.name}
                    </h4>
                    <p className="text-[11px] font-mono text-slate-400 mt-0.5">
                      {step.roundNumber === 5 ? 'Podium Awards' : `Qualify ${step.qualifyingCount}`}
                    </p>
                  </div>
                </div>

                {/* Cutoff Ratio */}
                <div className="pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono">
                  <span className="text-slate-500">Field Size</span>
                  <span className={`font-bold ${isLive ? 'text-cyan-300' : isCompleted ? 'text-emerald-300' : 'text-slate-300'}`}>
                    {step.totalPool} &rarr; {step.qualifyingCount}
                  </span>
                </div>

                {/* Desktop Arrow Connector */}
                {idx < steps.length - 1 && (
                  <div className="hidden md:flex items-center justify-center absolute -right-2.5 top-1/2 -translate-y-1/2 z-10 w-5 h-5 rounded-full bg-[#030712] border border-cyan-500/40 shadow-[0_0_8px_rgba(6,182,212,0.3)]">
                    <ChevronRight className="w-3 h-3 text-cyan-400" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
