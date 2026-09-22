import { useState } from 'react';
import { UserCheck, FastForward, Megaphone, QrCode, Download, ShieldCheck } from 'lucide-react';
import { Card, CardHeader, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';

export function QuickActionsPanel() {
  const [modalMessage, setModalMessage] = useState<string | null>(null);

  const triggerAction = (name: string, detail: string) => {
    setModalMessage(`[Dispatch Action]: "${name}" activated.\n\n${detail}\n\nFastAPI live orchestration active.`);
  };

  return (
    <>
      <Card>
        <CardHeader
          title="Field Operations Dispatch"
          subtitle="Direct operational dispatch actions for event marshals"
        />
        <CardContent className="space-y-2.5">
          <Button
            variant="outline"
            className="w-full justify-start text-left py-2.5 px-3 bg-[#030712]/60 hover:border-cyan-400 hover:bg-cyan-500/10"
            leftIcon={<UserCheck className="w-4 h-4 text-cyan-400" />}
            onClick={() =>
              triggerAction(
                'Rapid Team Check-In',
                'Fast-scans team QR or USN at desk to mark 5 members present.'
              )
            }
          >
            <div className="text-left">
              <div className="text-xs font-orbitron font-semibold text-slate-100">Rapid Team Check-in</div>
              <div className="text-[11px] font-mono text-slate-400 font-normal">Verify 5 members present</div>
            </div>
          </Button>

          <Button
            variant="outline"
            className="w-full justify-start text-left py-2.5 px-3 bg-[#030712]/60 hover:border-emerald-400 hover:bg-emerald-500/10"
            leftIcon={<QrCode className="w-4 h-4 text-emerald-400" />}
            onClick={() =>
              triggerAction(
                'Verify Clue Token',
                'Accepts secret code submissions from teams in Round 1 & passive hunt.'
              )
            }
          >
            <div className="text-left">
              <div className="text-xs font-orbitron font-semibold text-slate-100">Verify Code Token</div>
              <div className="text-[11px] font-mono text-slate-400 font-normal">Confirm QR or fragment claim</div>
            </div>
          </Button>

          <Button
            variant="outline"
            className="w-full justify-start text-left py-2.5 px-3 bg-[#030712]/60 hover:border-amber-400 hover:bg-amber-500/10"
            leftIcon={<Megaphone className="w-4 h-4 text-amber-400" />}
            onClick={() =>
              triggerAction(
                'Broadcast Announcement',
                'Dispatches urgent broadcast audio/text alert across participant consoles.'
              )
            }
          >
            <div className="text-left">
              <div className="text-xs font-orbitron font-semibold text-slate-100">Broadcast Alert</div>
              <div className="text-[11px] font-mono text-slate-400 font-normal">Send marshal notification</div>
            </div>
          </Button>

          <Button
            variant="outline"
            className="w-full justify-start text-left py-2.5 px-3 bg-[#030712]/60 hover:border-violet-400 hover:bg-violet-500/10"
            leftIcon={<FastForward className="w-4 h-4 text-violet-400" />}
            onClick={() =>
              triggerAction(
                'Advance Elimination Bracket',
                'Evaluates Round 1 Expedition scores and finalizes 24 qualified teams for Round 2 (Cabo).'
              )
            }
          >
            <div className="text-left">
              <div className="text-xs font-orbitron font-semibold text-slate-100">Advance Elimination</div>
              <div className="text-[11px] font-mono text-slate-400 font-normal">Calculate top 24 cutoffs</div>
            </div>
          </Button>

          <Button
            variant="ghost"
            className="w-full justify-start text-left py-2 px-3 text-slate-400 hover:text-cyan-300 border border-slate-800/80 hover:border-cyan-500/30"
            leftIcon={<Download className="w-4 h-4 text-slate-400" />}
            onClick={() =>
              triggerAction(
                'Export Roster CSV',
                'Generates an export of the 32 teams, 160 participants, and current standings.'
              )
            }
          >
            <div className="text-xs font-mono font-medium">Export Roster & Standings</div>
          </Button>
        </CardContent>
      </Card>

      {/* Modal alert for quick action demonstration */}
      {modalMessage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-md">
          <div className="bg-[#090d1a]/95 backdrop-blur-2xl rounded-2xl shadow-[0_16px_60px_rgba(0,0,0,0.9)] max-w-md w-full p-6 border border-cyan-500/30 animate-in fade-in zoom-in-95">
            <div className="flex items-center gap-2.5 text-cyan-400 mb-3">
              <ShieldCheck className="w-5 h-5" />
              <h3 className="font-orbitron font-bold text-sm text-slate-100">Console Dispatch</h3>
            </div>
            <p className="text-xs text-slate-300 whitespace-pre-line leading-relaxed mb-5 bg-[#030712] p-3.5 rounded-xl border border-cyan-500/20 font-mono">
              {modalMessage}
            </p>
            <div className="flex justify-end">
              <Button size="sm" onClick={() => setModalMessage(null)}>
                Acknowledge
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
