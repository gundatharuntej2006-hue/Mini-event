import { Link } from 'react-router-dom';
import { Scale, Gavel, FileText, Trophy, ExternalLink } from 'lucide-react';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { PageHeader } from '../components/ui/PageHeader';
import { SummaryMetric } from '../components/ui/SummaryMetric';

export function JudgesPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Faculty & Legal Judges Portal"
        subtitle="Moot court adversarial debating, argument cross-examinations, and official 100-point judging rubric"
        badge={
          <Badge variant="purple" size="sm">
            Round 4 Adjudication
          </Badge>
        }
        actions={
          <Link to="/round-4">
            <Button variant="primary" size="sm" rightIcon={<ExternalLink className="w-3.5 h-3.5" />}>
              Open Round 4 Courtrooms
            </Button>
          </Link>
        }
      />

      {/* KPI Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SummaryMetric
          label="Moot Court Trials"
          value="4 Matchups"
          subtext="Head-to-head bracket arguments evaluated by invited faculty"
          icon={Gavel}
          variant="blue"
        />

        <SummaryMetric
          label="Evaluation Rubric"
          value="4 Criteria"
          subtext="Legal foundation, rebuttal, evidence, and timing (100 pts)"
          icon={FileText}
          variant="purple"
        />

        <SummaryMetric
          label="Finale Cutoff"
          value="Top 3 Teams"
          subtext="Top 3 advancing squads qualify for the Grand Finale podium"
          icon={Trophy}
          variant="amber"
        />
      </div>

      {/* Interactive Hub Card */}
      <Card className="border-cyan-500/20 bg-[#090d1a]/80 shadow-[0_0_25px_rgba(34,211,238,0.06)] backdrop-blur-md">
        <CardHeader
          title={<span className="font-display font-bold tracking-wide text-slate-100">Judges Evaluation Console & Live Docket</span>}
          subtitle="Score submission and trial proceedings are integrated in the Round 4 operations console"
          action={
            <Link to="/round-4">
              <Button variant="outline" size="sm">
                Go to Scoring Portal
              </Button>
            </Link>
          }
        />
        <CardContent className="space-y-4">
          <div className="p-6 text-center border border-cyan-500/30 rounded-xl bg-[#030712]/70 shadow-[0_0_20px_rgba(34,211,238,0.08)] space-y-3">
            <div className="w-12 h-12 mx-auto rounded-xl bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 flex items-center justify-center shadow-[0_0_12px_rgba(34,211,238,0.3)]">
              <Scale className="w-6 h-6" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-100 font-display tracking-wider">Direct Scoring Console Active in Round 4</h4>
              <p className="text-xs text-slate-300 max-w-md mx-auto mt-1 leading-relaxed">
                Faculty judges can access individual courtroom hearings, review team case files, and submit signed scorecards directly through the Round 4 console.
              </p>
            </div>
            <div className="pt-2">
              <Link to="/round-4">
                <Button variant="primary" size="sm">
                  Launch Judicial Scorecard Form &rarr;
                </Button>
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
