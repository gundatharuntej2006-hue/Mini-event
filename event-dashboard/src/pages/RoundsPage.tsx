import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Layers, MapPin, Users, ArrowRight, Compass, ShieldAlert, Sparkles, Scale, ExternalLink } from 'lucide-react';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { PageHeader } from '../components/ui/PageHeader';
import { eventService } from '../services/eventService';
import { RoundInfo } from '../types';

export function RoundsPage() {
  const [rounds, setRounds] = useState<RoundInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    eventService.getRounds().then((res) => {
      setRounds(res.data);
      setIsLoading(false);
    });
  }, []);

  const getRoundIcon = (r: number) => {
    switch (r) {
      case 1:
        return Compass;
      case 2:
        return Layers;
      case 3:
        return ShieldAlert;
      case 4:
        return Scale;
      default:
        return Sparkles;
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tournament Elimination Structure"
        subtitle="Strict multi-tier elimination progression from 32 teams down to the final championship podium"
        badge={
          <Badge variant="primary" size="sm">
            5 Competitive Stages
          </Badge>
        }
      />

      {isLoading ? (
        <div className="space-y-4">
          <div className="h-36 bg-[#090d1a]/80 rounded-xl border border-cyan-500/20 animate-pulse" />
          <div className="h-36 bg-[#090d1a]/80 rounded-xl border border-cyan-500/20 animate-pulse" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {rounds.map((round) => {
            const Icon = getRoundIcon(round.roundNumber);
            const isLive = round.status === 'Live';

            return (
              <Card
                key={round.roundNumber}
                className={`transition-all duration-300 ${
                  isLive
                    ? 'border-cyan-400/80 bg-[#090d1a]/90 shadow-[0_0_25px_rgba(34,211,238,0.2)] ring-1 ring-cyan-500/30'
                    : 'border-cyan-500/20 bg-[#090d1a]/70 hover:border-cyan-500/40 backdrop-blur-md'
                }`}
              >
                <CardHeader
                  title={
                    <div className="flex items-center gap-2.5">
                      <div
                        className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs transition-colors ${
                          isLive
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(34,211,238,0.4)]'
                            : 'bg-[#030712] text-cyan-400/70 border border-cyan-500/20'
                        }`}
                      >
                        <Icon className="w-4 h-4" />
                      </div>
                      <span className="font-bold text-sm text-slate-100 font-display tracking-wide">
                        Round {round.roundNumber}: {round.name}
                      </span>
                      <span className="text-[11px] font-mono bg-[#030712] text-cyan-400 border border-cyan-500/30 px-2 py-0.5 rounded">
                        {round.codename}
                      </span>
                    </div>
                  }
                  action={
                    <div className="flex items-center gap-2">
                      {round.roundNumber === 1 && (
                        <Link to="/round-1">
                          <Button size="sm" variant="primary" rightIcon={<ExternalLink className="w-3 h-3" />}>
                            Open Console
                          </Button>
                        </Link>
                      )}
                      {round.roundNumber === 2 && (
                        <Link to="/round-2">
                          <Button size="sm" variant="primary" rightIcon={<ExternalLink className="w-3 h-3" />}>
                            Open Console
                          </Button>
                        </Link>
                      )}
                      {round.roundNumber === 3 && (
                        <Link to="/round-3">
                          <Button size="sm" variant="primary" rightIcon={<ExternalLink className="w-3 h-3" />}>
                            Open Console
                          </Button>
                        </Link>
                      )}
                      {round.roundNumber === 4 && (
                        <Link to="/round-4">
                          <Button size="sm" variant="primary" rightIcon={<ExternalLink className="w-3 h-3" />}>
                            Open Console
                          </Button>
                        </Link>
                      )}
                      {round.roundNumber === 5 && (
                        <Link to="/finale">
                          <Button size="sm" variant="primary" rightIcon={<ExternalLink className="w-3 h-3" />}>
                            Open Console
                          </Button>
                        </Link>
                      )}
                      {isLive ? (
                        <Badge variant="warning" size="sm" dot>
                          LIVE NOW
                        </Badge>
                      ) : (
                        <Badge variant="neutral" size="sm">
                          {round.status}
                        </Badge>
                      )}
                    </div>
                  }
                />
                <CardContent className="space-y-3">
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {round.description}
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-cyan-500/10 text-xs">
                    <div className="flex items-center gap-2">
                      <Users className="w-4 h-4 text-cyan-400/60" />
                      <div>
                        <span className="text-slate-400 block text-[10px] uppercase font-mono">Field Progression</span>
                        <span className="font-semibold text-slate-200 font-mono">
                          {round.initialTeamsCount} Teams &rarr; Top {round.qualifyingTeamsCount} Qualify
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-cyan-400/60" />
                      <div>
                        <span className="text-slate-400 block text-[10px] uppercase font-mono">Designated Venue</span>
                        <span className="font-medium text-slate-300 truncate block max-w-[200px]" title={round.location}>
                          {round.location}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4 text-cyan-400/60" />
                      <div>
                        <span className="text-slate-400 block text-[10px] uppercase font-mono">Next Elimination Phase</span>
                        <span className="font-medium text-cyan-400 flex items-center gap-1 font-mono hover:text-cyan-300">
                          {round.roundNumber === 5 ? 'Grand Trophy Ceremony' : `Round ${round.roundNumber + 1}`}
                          <ArrowRight className="w-3 h-3" />
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
