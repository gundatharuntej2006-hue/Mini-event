import { useState, useEffect, useMemo } from 'react';
import { QrCode, CheckCircle2, Trophy, KeyRound, RefreshCw, Check, AlertTriangle } from 'lucide-react';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PageHeader } from '../components/ui/PageHeader';
import { SummaryMetric } from '../components/ui/SummaryMetric';
import { SearchFilterToolbar } from '../components/ui/SearchFilterToolbar';
import { backendApiService, CodeHuntStatusData } from '../services/backendApiService';
import { authService } from '../services/authService';
import { Team } from '../types';
import { formatTeamNumber } from '../utils/formatters';

interface TeamCodeHuntRow {
  team: Team;
  status: CodeHuntStatusData | null;
}

export function CodeFragmentsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [statuses, setStatuses] = useState<Record<string, CodeHuntStatusData>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'verified' | 'incomplete'>('all');

  // Action Modal State
  const [isRecordModalOpen, setIsRecordModalOpen] = useState(false);
  const [isVerifyModalOpen, setIsVerifyModalOpen] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [fragmentType, setFragmentType] = useState<'1' | '2'>('1');
  const [fragmentValue, setFragmentValue] = useState('');
  const [verifyCodeValue, setVerifyCodeValue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const currentUser = authService.getCurrentUser();
  const isStaff = currentUser && ['ORGANIZER', 'MARSHAL', 'ADMIN'].includes(currentUser.role);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const teamsRes = await backendApiService.getTeams();
      const teamList = teamsRes.data || [];
      setTeams(teamList);

      const statusMap: Record<string, CodeHuntStatusData> = {};
      await Promise.all(
        teamList.map(async (t) => {
          try {
            const sRes = await backendApiService.getCodeHuntStatus(t.id);
            if (sRes.data) {
              statusMap[t.id] = sRes.data;
            }
          } catch {
            // Unregistered or error
          }
        })
      );
      setStatuses(statusMap);
    } catch (err: any) {
      setError(err.message || 'Failed to load code hunt telemetry from backend.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const teamRows: TeamCodeHuntRow[] = useMemo(() => {
    return teams.map((t) => ({
      team: t,
      status: statuses[t.id] || null,
    }));
  }, [teams, statuses]);

  const filteredRows = useMemo(() => {
    return teamRows.filter(({ team, status }) => {
      const matchesSearch =
        searchQuery === '' ||
        team.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        team.teamNumber.toString().includes(searchQuery);

      const isVerified = status?.final_code_verified ?? false;
      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'verified' && isVerified) ||
        (statusFilter === 'incomplete' && !isVerified);

      return matchesSearch && matchesStatus;
    });
  }, [teamRows, searchQuery, statusFilter]);

  const totalTeams = teams.length;
  const verifiedCount = Object.values(statuses).filter((s) => s.final_code_verified).length;
  const r4EligibleCount = Object.values(statuses).filter((s) => s.r4_eligible).length;

  const handleOpenRecord = (team: Team, type: '1' | '2') => {
    setSelectedTeam(team);
    setFragmentType(type);
    setFragmentValue('');
    setModalError(null);
    setIsRecordModalOpen(true);
  };

  const handleOpenVerify = (team: Team) => {
    setSelectedTeam(team);
    setVerifyCodeValue('');
    setModalError(null);
    setIsVerifyModalOpen(true);
  };

  const submitRecordFragment = async () => {
    if (!selectedTeam || !fragmentValue.trim()) return;
    setIsSubmitting(true);
    setModalError(null);
    try {
      if (fragmentType === '1') {
        await backendApiService.recordFragment1(selectedTeam.id, {
          fragment_value: fragmentValue.trim(),
          overwrite: true,
        });
      } else {
        await backendApiService.recordFragment2(selectedTeam.id, {
          fragment_value: fragmentValue.trim(),
          overwrite: true,
        });
      }
      setIsRecordModalOpen(false);
      await loadData();
    } catch (err: any) {
      setModalError(err.message || 'Failed to record fragment.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const submitVerifyCode = async () => {
    if (!selectedTeam || !verifyCodeValue.trim()) return;
    setIsSubmitting(true);
    setModalError(null);
    try {
      await backendApiService.verifyFinalCode(selectedTeam.id, {
        submitted_final_code: verifyCodeValue.trim(),
      });
      setIsVerifyModalOpen(false);
      await loadData();
    } catch (err: any) {
      setModalError(err.message || 'Verification failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Campus Code Hunt & Final Code Gate"
        subtitle="Cryptographic fragments recovery across Rounds 1 & 2 leading into Round 4 Eligibility"
        badge={
          <Badge variant="primary" size="sm">
            Official Gatekeeper
          </Badge>
        }
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={loadData}
            isLoading={isLoading}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh Telemetry
          </Button>
        }
      />

      {error && (
        <div className="p-4 rounded-xl border border-red-500/40 bg-red-950/40 text-red-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <span>{error}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={loadData}>
            Retry
          </Button>
        </div>
      )}

      {/* KPI Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryMetric
          label="Registered Squads"
          value={totalTeams}
          subtext="Active in tournament track"
          icon={QrCode}
          variant="blue"
        />
        <SummaryMetric
          label="Final Codes Verified"
          value={`${verifiedCount} / ${totalTeams}`}
          subtext="Passed final cryptographic verification"
          icon={CheckCircle2}
          variant="emerald"
        />
        <SummaryMetric
          label="R4 Eligible Squads"
          value={`${r4EligibleCount} / 8`}
          subtext="Cleared Code Hunt gate for Round 4"
          icon={KeyRound}
          variant="purple"
        />
        <SummaryMetric
          label="Pending Clearance"
          value={Math.max(0, totalTeams - verifiedCount)}
          subtext="Awaiting fragment combination"
          icon={Trophy}
          variant="amber"
        />
      </div>

      {/* Search & Filter Toolbar */}
      <SearchFilterToolbar
        searchPlaceholder="Search squad name or number..."
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        filters={[
          {
            id: 'status',
            label: 'Code Gate Status',
            value: statusFilter,
            options: [
              { label: 'All Squads', value: 'all' },
              { label: 'Verified & Cleared', value: 'verified' },
              { label: 'Incomplete', value: 'incomplete' },
            ],
            onChange: (val) => setStatusFilter(val as any),
          },
        ]}
        activeCount={(searchQuery ? 1 : 0) + (statusFilter !== 'all' ? 1 : 0)}
        onClearAll={() => {
          setSearchQuery('');
          setStatusFilter('all');
        }}
      />

      {/* Table Card */}
      <Card className="border-cyan-500/20 bg-[#090d1a]/80 shadow-[0_0_25px_rgba(34,211,238,0.06)] backdrop-blur-md overflow-hidden">
        <CardHeader
          title={<span className="font-display font-bold tracking-wide text-slate-100">Squad Code Gate Matrix</span>}
          subtitle="Real-time status for Fragment 1 (R1), Fragment 2 (R2), and Final Code validation"
          action={
            <Badge variant="neutral" size="sm">
              Showing {filteredRows.length} of {totalTeams} Squads
            </Badge>
          }
        />
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#030712]/95 border-b border-cyan-500/20 text-[10px] uppercase tracking-wider font-mono font-semibold text-cyan-400/90">
                  <th className="py-3 px-4">Squad</th>
                  <th className="py-3 px-4">Fragment 1 (R1)</th>
                  <th className="py-3 px-4">Fragment 2 (R2)</th>
                  <th className="py-3 px-4">Final Code Status</th>
                  <th className="py-3 px-4">R4 Eligibility</th>
                  {isStaff && <th className="py-3 px-4 text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-cyan-500/10">
                {filteredRows.map(({ team, status }) => {
                  const f1Found = status?.fragment_1_status === 'RECOVERED';
                  const f2Found = status?.fragment_2_status === 'RECOVERED';
                  const isVerified = status?.final_code_verified ?? false;

                  return (
                    <tr key={team.id} className="hover:bg-cyan-500/5 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-200">
                          {formatTeamNumber(team.teamNumber)} — {team.name}
                        </div>
                        <div className="text-[10px] font-mono text-slate-400">{team.id}</div>
                      </td>
                      <td className="py-3 px-4">
                        {f1Found ? (
                          <Badge variant="success" size="sm" dot>
                            Recovered
                          </Badge>
                        ) : (
                          <Badge variant="neutral" size="sm">
                            Missing
                          </Badge>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {f2Found ? (
                          <Badge variant="success" size="sm" dot>
                            Recovered
                          </Badge>
                        ) : (
                          <Badge variant="neutral" size="sm">
                            Missing
                          </Badge>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {isVerified ? (
                          <Badge variant="success" size="sm">
                            VERIFIED
                          </Badge>
                        ) : (
                          <Badge variant="warning" size="sm">
                            UNVERIFIED
                          </Badge>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {status?.r4_eligible ? (
                          <span className="inline-flex items-center gap-1 font-mono text-emerald-400 font-bold">
                            <Check className="w-3.5 h-3.5" /> ELIGIBLE
                          </span>
                        ) : (
                          <span className="font-mono text-slate-400 text-[11px]">
                            {status?.gate_reason || 'Gate Locked'}
                          </span>
                        )}
                      </td>
                      {isStaff && (
                        <td className="py-3 px-4 text-right space-x-2">
                          <button
                            onClick={() => handleOpenRecord(team, '1')}
                            className="px-2 py-1 text-[10px] font-mono rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 hover:bg-cyan-900/60"
                          >
                            + Frag 1
                          </button>
                          <button
                            onClick={() => handleOpenRecord(team, '2')}
                            className="px-2 py-1 text-[10px] font-mono rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 hover:bg-cyan-900/60"
                          >
                            + Frag 2
                          </button>
                          <button
                            onClick={() => handleOpenVerify(team)}
                            className="px-2 py-1 text-[10px] font-mono rounded bg-purple-950/60 border border-purple-500/40 text-purple-300 hover:bg-purple-900/60"
                          >
                            Verify Code
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Record Fragment Modal */}
      <Modal
        isOpen={isRecordModalOpen}
        onClose={() => setIsRecordModalOpen(false)}
        title={`Record Fragment ${fragmentType} — ${selectedTeam?.name || ''}`}
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-300">
            Record physical checkpoint fragment discovered by squad{' '}
            <strong className="text-cyan-400 font-mono">{selectedTeam?.name}</strong>.
          </p>
          {modalError && <div className="text-xs text-red-400 font-mono">{modalError}</div>}
          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">Fragment Code Value</label>
            <input
              type="text"
              value={fragmentValue}
              onChange={(e) => setFragmentValue(e.target.value)}
              placeholder="e.g. ALPHA-9924"
              className="w-full px-3 py-2 text-xs bg-[#030712] border border-cyan-500/30 rounded-lg text-slate-100 font-mono focus:border-cyan-400"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" size="sm" onClick={() => setIsRecordModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" isLoading={isSubmitting} onClick={submitRecordFragment}>
              Save Fragment
            </Button>
          </div>
        </div>
      </Modal>

      {/* Verify Code Modal */}
      <Modal
        isOpen={isVerifyModalOpen}
        onClose={() => setIsVerifyModalOpen(false)}
        title={`Verify Final Code — ${selectedTeam?.name || ''}`}
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-300">
            Submit synthesized final code for squad{' '}
            <strong className="text-purple-400 font-mono">{selectedTeam?.name}</strong> to clear the Round 4 gate.
          </p>
          {modalError && <div className="text-xs text-red-400 font-mono">{modalError}</div>}
          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">Synthesized Final Code</label>
            <input
              type="text"
              value={verifyCodeValue}
              onChange={(e) => setVerifyCodeValue(e.target.value)}
              placeholder="e.g. CIPHER-OMEGA"
              className="w-full px-3 py-2 text-xs bg-[#030712] border border-purple-500/30 rounded-lg text-slate-100 font-mono focus:border-purple-400"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" size="sm" onClick={() => setIsVerifyModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" isLoading={isSubmitting} onClick={submitVerifyCode}>
              Verify & Unlock Gate
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
