import { Lock, EyeOff, KeyRound, UserCheck, Shield } from 'lucide-react';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { PageHeader } from '../components/ui/PageHeader';
import { SummaryMetric } from '../components/ui/SummaryMetric';

export function SecretAgentsPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Secret Agent Programme Management"
        subtitle="Undercover operatives deployment, encrypted dossier handoffs, and tournament-wide sabotage tracking"
        badge={
          <Badge variant="purple" size="sm">
            RESTRICTED CONSOLE
          </Badge>
        }
        actions={
          <Badge variant="danger" size="sm" dot>
            Confidentiality Protocol Active
          </Badge>
        }
      />

      {/* Security Banner */}
      <div className="bg-[#090d1a]/90 text-slate-200 p-5 rounded-xl border border-purple-500/30 flex items-start gap-4 shadow-[0_0_25px_rgba(168,85,247,0.12)] backdrop-blur-md">
        <div className="w-10 h-10 rounded-lg bg-purple-950/70 border border-purple-500/40 flex items-center justify-center text-purple-300 shadow-[0_0_12px_rgba(168,85,247,0.3)] flex-shrink-0">
          <Lock className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-purple-200 font-display tracking-wide flex items-center gap-2">
            Operation Undercover — Compartmentalized Access
          </h3>
          <p className="text-xs text-slate-300 mt-1 leading-relaxed font-sans">
            Per event regulations, individual secret agent identities and sabotage objectives are strictly encrypted. 
            Identities are stored in isolated cryptographic envelopes and will only be revealed during the <strong className="text-purple-300 font-display">Grand Finale Deduction Ceremony</strong>.
          </p>
        </div>
      </div>

      {/* KPI Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SummaryMetric
          label="Agent Allocation"
          value="32 / 32"
          subtext="Exactly 1 secret agent embedded per squad"
          icon={UserCheck}
          variant="purple"
        />
        <SummaryMetric
          label="Transmission Status"
          value="100% Sealed"
          subtext="Initial briefing tokens securely dispatched"
          icon={Shield}
          variant="emerald"
        />
        <SummaryMetric
          label="Finale Unmasking"
          value="Phase 5"
          subtext="Deduction accusations tallied before podium"
          icon={KeyRound}
          variant="blue"
        />
      </div>

      {/* Operations Scaffolding Card */}
      <Card className="border-cyan-500/20 bg-[#090d1a]/80 shadow-[0_0_25px_rgba(34,211,238,0.05)] backdrop-blur-md">
        <CardHeader
          title={<span className="font-display font-bold text-slate-100 tracking-wide">Agent Operations Architecture & Governance</span>}
          subtitle="Cryptographic privacy protections enforced across participant displays"
        />
        <CardContent className="space-y-4">
          <div className="p-4 bg-[#030712]/70 rounded-xl border border-purple-500/20 text-xs text-slate-300 space-y-2.5">
            <div className="flex items-center gap-2 font-semibold text-purple-200 font-display tracking-wider">
              <EyeOff className="w-4 h-4 text-purple-400" />
              Role-Based Access Control Architecture
            </div>
            <p className="leading-relaxed font-sans text-slate-300">
              Agent identities are securely omitted from client state. Role-authenticated access allows the Lead Organizer and Chief Marshal to audit undercover progress without leaking data to projector displays, audience views, or participant screens.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
