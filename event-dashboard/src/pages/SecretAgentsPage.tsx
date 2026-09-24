import { useState, useEffect, useMemo } from 'react';
import { Lock, EyeOff, KeyRound, UserCheck, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PageHeader } from '../components/ui/PageHeader';
import { SummaryMetric } from '../components/ui/SummaryMetric';
import { SearchFilterToolbar } from '../components/ui/SearchFilterToolbar';
import { backendApiService, SecretAgentDossierData, SecretAgentTaskData } from '../services/backendApiService';
import { authService } from '../services/authService';
import { Team } from '../types';
import { formatTeamNumber } from '../utils/formatters';

export function SecretAgentsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [dossiers, setDossiers] = useState<Record<string, SecretAgentDossierData>>({});
  const [tasks, setTasks] = useState<Record<string, SecretAgentTaskData[]>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);

  // Modals
  const [isCreateTaskModalOpen, setIsCreateTaskModalOpen] = useState(false);
  const [isInspectTasksModalOpen, setIsInspectTasksModalOpen] = useState(false);
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDesc, setTaskDesc] = useState('');
  const [taskRound, setTaskRound] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const currentUser = authService.getCurrentUser();
  const isStaff = currentUser && ['ORGANIZER', 'MARSHAL', 'ADMIN'].includes(currentUser.role);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const teamsRes = await backendApiService.getTeams();
      const teamList = teamsRes.data || [];
      setTeams(teamList);

      if (isStaff) {
        const dossierMap: Record<string, SecretAgentDossierData> = {};
        const taskMap: Record<string, SecretAgentTaskData[]> = {};

        await Promise.all(
          teamList.map(async (t) => {
            try {
              const dRes = await backendApiService.getSecretAgentDossier(t.id);
              if (dRes.data) {
                dossierMap[t.id] = dRes.data;
              }
            } catch {
              // No dossier or forbidden
            }

            try {
              const tRes = await backendApiService.getSecretAgentTasks(t.id);
              if (tRes.data) {
                taskMap[t.id] = tRes.data;
              }
            } catch {
              // No tasks or forbidden
            }
          })
        );
        setDossiers(dossierMap);
        setTasks(taskMap);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load secret agent telemetry.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const totalAssigned = Object.keys(dossiers).length;
  const allTasksList = Object.values(tasks).flat();
  const verifiedTasksCount = allTasksList.filter((t) => t.status === 'VERIFIED').length;
  const pendingTasksCount = allTasksList.filter((t) => t.status === 'SUBMITTED' || t.status === 'ASSIGNED').length;

  const filteredTeams = useMemo(() => {
    return teams.filter((t) => {
      return (
        searchQuery === '' ||
        t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.teamNumber.toString().includes(searchQuery)
      );
    });
  }, [teams, searchQuery]);

  const handleVerifyTask = async (taskId: string) => {
    try {
      await backendApiService.verifySecretAgentTask(taskId, {
        verification_notes: 'Verified by Chief Marshal via console',
      });
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Verification failed');
    }
  };

  const handleRejectTask = async (taskId: string) => {
    const reason = prompt('Enter rejection reason:');
    if (!reason) return;
    try {
      await backendApiService.rejectSecretAgentTask(taskId, { reason });
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Rejection failed');
    }
  };

  const handleCreateTask = async () => {
    if (!selectedTeam || !taskTitle.trim()) return;
    setIsSubmitting(true);
    setActionError(null);
    try {
      await backendApiService.createSecretAgentTask(selectedTeam.id, {
        title: taskTitle.trim(),
        description: taskDesc.trim(),
        target_round: taskRound,
      });
      setIsCreateTaskModalOpen(false);
      setTaskTitle('');
      setTaskDesc('');
      await loadData();
    } catch (err: any) {
      setActionError(err.message || 'Failed to create task');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Secret Agent Programme Management"
        subtitle="Undercover operatives deployment, encrypted dossier handoffs, and sabotage task verification"
        badge={
          <Badge variant="purple" size="sm">
            {isStaff ? 'ORGANIZER CONSOLE' : 'RESTRICTED CONSOLE'}
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2">
            <Badge variant="danger" size="sm" dot>
              Confidentiality Protocol Active
            </Badge>
            <Button
              variant="secondary"
              size="sm"
              onClick={loadData}
              isLoading={isLoading}
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Refresh
            </Button>
          </div>
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

      {error && (
        <div className="p-4 rounded-xl border border-red-500/40 bg-red-950/40 text-red-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SummaryMetric
          label="Agent Allocation"
          value={`${isStaff ? totalAssigned : teams.length} / ${teams.length || 32}`}
          subtext="Exactly 1 secret agent embedded per squad"
          icon={UserCheck}
          variant="purple"
        />
        <SummaryMetric
          label="Verified Sabotage Tasks"
          value={isStaff ? `${verifiedTasksCount} Verified` : 'CONFIDENTIAL'}
          subtext={isStaff ? `${pendingTasksCount} pending review (+50 pts awarded)` : '+50 pts awarded upon server verification'}
          icon={CheckCircle2}
          variant="emerald"
        />
        <SummaryMetric
          label="Finale Deduction Gate"
          value="Grand Finale"
          subtext="+30 correct / -20 incorrect unmasking"
          icon={KeyRound}
          variant="blue"
        />
      </div>

      {/* Organizer Secret Agent Task Ledger */}
      {isStaff && (
        <div className="space-y-4">
          <SearchFilterToolbar
            searchPlaceholder="Search squads..."
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
          />

          <Card className="border-purple-500/20 bg-[#090d1a]/80 shadow-[0_0_25px_rgba(168,85,247,0.06)] backdrop-blur-md overflow-hidden">
            <CardHeader
              title={<span className="font-display font-bold tracking-wide text-purple-200">Organizer Operatives Dossier Matrix</span>}
              subtitle="Confidential operative codenames, mission statuses, and verification ledger"
              action={
                <Badge variant="purple" size="sm">
                  {teams.length} Squads Monitored
                </Badge>
              }
            />
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-[#030712]/95 border-b border-purple-500/20 text-[10px] uppercase tracking-wider font-mono font-semibold text-purple-400/90">
                      <th className="py-3 px-4">Squad</th>
                      <th className="py-3 px-4">Codename</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Active Tasks</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-purple-500/10">
                    {filteredTeams.map((team) => {
                      const dossier = dossiers[team.id];
                      const teamTasks = tasks[team.id] || [];
                      const verified = teamTasks.filter((t) => t.status === 'VERIFIED').length;

                      return (
                        <tr key={team.id} className="hover:bg-purple-500/5 transition-colors">
                          <td className="py-3 px-4">
                            <div className="font-semibold text-slate-200">
                              {formatTeamNumber(team.teamNumber)} — {team.name}
                            </div>
                            <div className="text-[10px] font-mono text-slate-400">{team.id}</div>
                          </td>
                          <td className="py-3 px-4 font-mono text-purple-300 font-bold">
                            {dossier?.codename || 'Agent Unassigned'}
                          </td>
                          <td className="py-3 px-4">
                            <Badge variant={dossier ? 'success' : 'neutral'} size="sm">
                              {dossier?.status || 'INACTIVE'}
                            </Badge>
                          </td>
                          <td className="py-3 px-4 font-mono text-slate-300">
                            {verified} / {teamTasks.length} verified
                          </td>
                          <td className="py-3 px-4 text-right space-x-2">
                            <button
                              onClick={() => {
                                setSelectedTeam(team);
                                setIsInspectTasksModalOpen(true);
                              }}
                              className="px-2 py-1 text-[10px] font-mono rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 hover:bg-cyan-900/60"
                            >
                              Inspect Tasks ({teamTasks.length})
                            </button>
                            <button
                              onClick={() => {
                                setSelectedTeam(team);
                                setIsCreateTaskModalOpen(true);
                              }}
                              className="px-2 py-1 text-[10px] font-mono rounded bg-purple-950/60 border border-purple-500/40 text-purple-300 hover:bg-purple-900/60"
                            >
                              + Add Task
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Non-staff info card */}
      {!isStaff && (
        <Card className="border-purple-500/20 bg-[#090d1a]/80 shadow-[0_0_25px_rgba(168,85,247,0.05)] backdrop-blur-md">
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
      )}

      {/* Inspect / Verify Tasks Modal */}
      <Modal
        isOpen={isInspectTasksModalOpen}
        onClose={() => setIsInspectTasksModalOpen(false)}
        title={`Undercover Tasks Ledger — ${selectedTeam?.name || ''}`}
      >
        <div className="space-y-4 max-h-[70vh] overflow-y-auto">
          {selectedTeam && (tasks[selectedTeam.id] || []).length === 0 ? (
            <p className="text-xs text-slate-400 font-mono text-center py-4">
              No tasks assigned yet for this squad's operative.
            </p>
          ) : (
            selectedTeam &&
            (tasks[selectedTeam.id] || []).map((t) => (
              <div key={t.id} className="p-3 bg-[#030712] border border-purple-500/20 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-purple-200">{t.title}</span>
                  <Badge
                    variant={t.status === 'VERIFIED' ? 'success' : t.status === 'REJECTED' ? 'danger' : 'warning'}
                    size="sm"
                  >
                    {t.status}
                  </Badge>
                </div>
                <p className="text-xs text-slate-300">{t.description}</p>
                <div className="text-[10px] font-mono text-slate-400">
                  Target Round: {t.target_round} | Reward: +{t.points_awarded || 50} pts
                </div>
                {t.evidence && (
                  <div className="p-2 bg-purple-950/30 rounded border border-purple-500/20 text-[11px] font-mono text-purple-300">
                    Evidence: {t.evidence}
                  </div>
                )}
                {t.status !== 'VERIFIED' && (
                  <div className="flex justify-end gap-2 pt-1">
                    <button
                      onClick={() => handleRejectTask(t.id)}
                      className="px-2 py-1 text-[10px] font-mono rounded bg-red-950/60 border border-red-500/40 text-red-300 hover:bg-red-900/60"
                    >
                      Reject
                    </button>
                    <button
                      onClick={() => handleVerifyTask(t.id)}
                      className="px-2 py-1 text-[10px] font-mono rounded bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-900/60"
                    >
                      Verify (+50 pts)
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
          <div className="flex justify-end pt-2">
            <Button variant="ghost" size="sm" onClick={() => setIsInspectTasksModalOpen(false)}>
              Close
            </Button>
          </div>
        </div>
      </Modal>

      {/* Create Task Modal */}
      <Modal
        isOpen={isCreateTaskModalOpen}
        onClose={() => setIsCreateTaskModalOpen(false)}
        title={`Assign Mission Task — ${selectedTeam?.name || ''}`}
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-300">
            Dispatch an undercover mission task to the secret agent embedded in squad{' '}
            <strong className="text-purple-300 font-mono">{selectedTeam?.name}</strong>.
          </p>
          {actionError && <div className="text-xs text-red-400 font-mono">{actionError}</div>}
          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">Task Title</label>
            <input
              type="text"
              value={taskTitle}
              onChange={(e) => setTaskTitle(e.target.value)}
              placeholder="e.g. Gather Intel on Courtroom Strategy"
              className="w-full px-3 py-2 text-xs bg-[#030712] border border-purple-500/30 rounded-lg text-slate-100 font-mono focus:border-purple-400"
            />
          </div>
          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">Target Tournament Round</label>
            <select
              value={taskRound}
              onChange={(e) => setTaskRound(Number(e.target.value))}
              className="w-full px-3 py-2 text-xs bg-[#030712] border border-purple-500/30 rounded-lg text-slate-100 font-mono focus:border-purple-400"
            >
              <option value={1}>Round 1: The Great Expedition</option>
              <option value={2}>Round 2: Cabo Tournament</option>
              <option value={3}>Round 3: The Black Market</option>
              <option value={4}>Round 4: The Legal Battle</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">Task Description / Criteria</label>
            <textarea
              value={taskDesc}
              onChange={(e) => setTaskDesc(e.target.value)}
              rows={3}
              placeholder="Provide covert verification criteria..."
              className="w-full px-3 py-2 text-xs bg-[#030712] border border-purple-500/30 rounded-lg text-slate-100 font-mono focus:border-purple-400"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" size="sm" onClick={() => setIsCreateTaskModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" isLoading={isSubmitting} onClick={handleCreateTask}>
              Dispatch Task
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
