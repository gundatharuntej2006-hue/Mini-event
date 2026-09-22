import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Users,
  CheckCircle2,
  Clock,
  Plus,
  Edit2,
  Trash2,
  Eye,
  AlertTriangle,
  ArrowUpDown,
  UserCheck,
  UserX,
  Lock,
  RefreshCw,
  Crown,
  User as UserIcon,
  Mail,
  Phone,
  Shield,
} from 'lucide-react';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Badge, BadgeVariant } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { ConfirmationDialog } from '../components/ui/ConfirmationDialog';
import { Pagination } from '../components/ui/Pagination';
import { TableRowSkeleton } from '../components/ui/LoadingSkeleton';
import { EmptyState } from '../components/ui/EmptyState';
import { PageHeader } from '../components/ui/PageHeader';
import { SearchFilterToolbar } from '../components/ui/SearchFilterToolbar';
import { eventService } from '../services/eventService';
import { authService } from '../services/authService';
import { isLiveMode, setAppMode, onAppModeChange } from '../services/apiConfig';
import { Team, Participant, CreateTeamInput, UpdateTeamInput, TeamMemberInput, User, ApiError } from '../types';
import { formatTeamNumber } from '../utils/formatters';

type SortField = 'teamNumber' | 'name' | 'membersCount' | 'checkedInCount';
type SortOrder = 'asc' | 'desc';

type FormMemberState = TeamMemberInput;

const DEFAULT_MEMBERS: FormMemberState[] = [
  { name: '', usn: '', email: '', phone: '', role: 'Leader' },
  { name: '', usn: '', email: '', phone: '', role: 'Member' },
  { name: '', usn: '', email: '', phone: '', role: 'Member' },
  { name: '', usn: '', email: '', phone: '', role: 'Member' },
  { name: '', usn: '', email: '', phone: '', role: 'Member' },
];

export function TeamsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<User | null>(authService.getCurrentUser());
  const [error, setError] = useState<{ message: string } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCheckIn, setFilterCheckIn] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('teamNumber');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 12;

  // Modals state
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [deleteTargetTeam, setDeleteTargetTeam] = useState<Team | null>(null);

  // Form states
  const [formName, setFormName] = useState('');
  const [formTable, setFormTable] = useState('');
  const [formMembers, setFormMembers] = useState<FormMemberState[]>(DEFAULT_MEMBERS);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Request sequence tracking & mount guard to prevent stale overwrites and race conditions
  const requestIdRef = useRef(0);
  const isMountedRef = useRef(true);

  // Load teams and subscribe to pub/sub updates
  const loadTeams = async (showSkeleton = true) => {
    const requestId = ++requestIdRef.current;
    if (showSkeleton) {
      setIsLoading(true);
    }
    setError(null);
    try {
      const res = await eventService.getTeams();
      if (requestId !== requestIdRef.current || !isMountedRef.current) return;
      setTeams(res.data || []);
      // Update selected team if open
      if (selectedTeam) {
        const updated = (res.data || []).find((t) => t.id === selectedTeam.id);
        if (updated) setSelectedTeam(updated);
      }
    } catch (err: unknown) {
      if (requestId !== requestIdRef.current || !isMountedRef.current) return;
      console.error('Error loading teams:', err);
      const apiErr = err as ApiError;
      setError({
        message: apiErr?.message || (err as Error)?.message || 'Failed to connect to FastAPI backend.',
      });
      setTeams([]);
    } finally {
      if (requestId === requestIdRef.current && isMountedRef.current) {
        setIsLoading(false);
      }
    }
  };

  useEffect(() => {
    isMountedRef.current = true;
    // Initial fetch with skeletons
    loadTeams(true);

    // Event updates (e.g. check-in, edits) refresh data seamlessly without flashing skeletons
    const unsubEvent = eventService.subscribe(() => {
      loadTeams(false);
    });

    const prevUserRef = { current: authService.getCurrentUser() };
    const unsubAuth = authService.subscribe((u) => {
      setCurrentUser(u);
      const prev = prevUserRef.current;
      const userChanged = !prev || !u || prev.id !== u.id || prev.role !== u.role;
      prevUserRef.current = u;
      // Only reload if user identity or permissions actually changed, avoiding initial mount duplicate
      if (userChanged) {
        loadTeams(false);
      }
    });

    const unsubMode = onAppModeChange(() => {
      loadTeams(true);
    });

    return () => {
      isMountedRef.current = false;
      unsubEvent();
      unsubAuth();
      unsubMode();
    };
  }, []);

  const isStaff = !isLiveMode() || (currentUser && ['ORGANIZER', 'MARSHAL'].includes(currentUser.role));
  const isOrganizer = !isLiveMode() || (currentUser && currentUser.role === 'ORGANIZER');

  // Compute check-in metrics
  const getTeamCheckInMetrics = (team: Team) => {
    const total = team.members.length;
    const checkedIn = team.members.filter((m) => m.checkedIn).length;
    const isCompleteRoster = total === 5;
    const isFullyCheckedIn = isCompleteRoster && checkedIn === 5;

    let label = 'Unchecked';
    let variant: BadgeVariant = 'neutral';

    if (!isCompleteRoster) {
      label = `Incomplete Roster (${total}/5)`;
      variant = 'warning';
    } else if (isFullyCheckedIn) {
      label = 'Ready · 5/5 Checked In';
      variant = 'success';
    } else if (checkedIn > 0) {
      label = `Partial · ${checkedIn}/5 Checked In`;
      variant = 'primary';
    } else {
      label = '0/5 Checked In';
      variant = 'neutral';
    }

    return { total, checkedIn, isCompleteRoster, isFullyCheckedIn, label, variant };
  };

  // Filter & Sort
  const filteredAndSortedTeams = useMemo(() => {
    return teams
      .filter((team) => {
        const query = searchQuery.toLowerCase().trim();
        const matchesSearch =
          !query ||
          team.name.toLowerCase().includes(query) ||
          formatTeamNumber(team.teamNumber).toLowerCase().includes(query) ||
          team.leaderName.toLowerCase().includes(query);

        const metrics = getTeamCheckInMetrics(team);
        let matchesCheckIn = true;
        if (filterCheckIn === 'ready') {
          matchesCheckIn = metrics.isFullyCheckedIn;
        } else if (filterCheckIn === 'partial') {
          matchesCheckIn = metrics.isCompleteRoster && metrics.checkedIn > 0 && !metrics.isFullyCheckedIn;
        } else if (filterCheckIn === 'incomplete') {
          matchesCheckIn = !metrics.isCompleteRoster;
        } else if (filterCheckIn === 'unchecked') {
          matchesCheckIn = metrics.isCompleteRoster && metrics.checkedIn === 0;
        }

        const matchesStatus = filterStatus === 'all' || team.status === filterStatus;

        return matchesSearch && matchesCheckIn && matchesStatus;
      })
      .sort((a, b) => {
        let comparison = 0;
        if (sortField === 'teamNumber') {
          comparison = a.teamNumber - b.teamNumber;
        } else if (sortField === 'name') {
          comparison = a.name.localeCompare(b.name);
        } else if (sortField === 'membersCount') {
          comparison = a.members.length - b.members.length;
        } else if (sortField === 'checkedInCount') {
          const aCount = a.members.filter((m) => m.checkedIn).length;
          const bCount = b.members.filter((m) => m.checkedIn).length;
          comparison = aCount - bCount;
        }
        return sortOrder === 'asc' ? comparison : -comparison;
      });
  }, [teams, searchQuery, filterCheckIn, filterStatus, sortField, sortOrder]);

  // Paginate
  const paginatedTeams = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredAndSortedTeams.slice(start, start + pageSize);
  }, [filteredAndSortedTeams, currentPage, pageSize]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  // Handlers for Create
  const handleOpenCreate = () => {
    setFormName('');
    setFormTable(`Table ${teams.length + 1}`);
    setFormMembers([
      { name: '', usn: '', email: '', phone: '', role: 'Leader' },
      { name: '', usn: '', email: '', phone: '', role: 'Member' },
      { name: '', usn: '', email: '', phone: '', role: 'Member' },
      { name: '', usn: '', email: '', phone: '', role: 'Member' },
      { name: '', usn: '', email: '', phone: '', role: 'Member' },
    ]);
    setFormError(null);
    setIsCreateOpen(true);
  };

  const handleMemberChange = (index: number, field: keyof FormMemberState, value: string) => {
    setFormMembers((prev) => {
      const copy = [...prev];
      if (field === 'role') {
        if (value === 'Leader') {
          // Exactly one leader: set clicked to Leader, others to Member
          copy.forEach((m, i) => {
            m.role = i === index ? 'Leader' : 'Member';
          });
        } else {
          copy[index].role = 'Member';
        }
      } else if (field === 'usn') {
        copy[index].usn = value.toUpperCase();
      } else {
        copy[index][field] = value;
      }
      return copy;
    });
  };

  const memberValidation = useMemo(() => {
    const usnCounts: Record<string, number> = {};
    const emailCounts: Record<string, number> = {};
    let missingRequired = false;

    formMembers.forEach((m) => {
      if (!m.name.trim() || !m.usn.trim() || !m.email.trim()) {
        missingRequired = true;
      }
      const u = m.usn.trim().toUpperCase();
      if (u) usnCounts[u] = (usnCounts[u] || 0) + 1;
      const e = m.email.trim().toLowerCase();
      if (e) emailCounts[e] = (emailCounts[e] || 0) + 1;
    });

    const duplicateUsns = Object.keys(usnCounts).filter((u) => usnCounts[u] > 1);
    const duplicateEmails = Object.keys(emailCounts).filter((e) => emailCounts[e] > 1);
    const leadersCount = formMembers.filter((m) => m.role === 'Leader').length;

    let errorMsg: string | null = null;
    if (formMembers.length !== 5) {
      errorMsg = 'Squad must have exactly 5 participants.';
    } else if (leadersCount !== 1) {
      errorMsg = 'Squad must have exactly one leader.';
    } else if (duplicateUsns.length > 0) {
      errorMsg = `Duplicate USN in roster: ${duplicateUsns.join(', ')}`;
    } else if (duplicateEmails.length > 0) {
      errorMsg = `Duplicate Email in roster: ${duplicateEmails.join(', ')}`;
    } else if (missingRequired) {
      errorMsg = 'All 5 members must have Full Name, BMSIT USN, and Institutional Email filled.';
    }

    return {
      isValid: !errorMsg && formName.trim().length > 0,
      errorMsg,
      duplicateUsns,
      duplicateEmails,
      leadersCount,
      missingRequired,
    };
  }, [formMembers, formName]);

  const handleCreateTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) {
      setFormError('Squad name is required.');
      return;
    }
    if (memberValidation.errorMsg) {
      setFormError(memberValidation.errorMsg);
      return;
    }

    setFormError(null);
    setIsSubmitting(true);
    try {
      const input: CreateTeamInput = {
        name: formName.trim(),
        assignedTable: formTable.trim() || undefined,
        members: formMembers.map((m) => ({
          name: m.name.trim(),
          usn: m.usn.trim().toUpperCase(),
          email: m.email.trim().toLowerCase(),
          phone: m.phone?.trim() || undefined,
          role: m.role,
        })),
      };
      await eventService.createTeam(input);
      setIsCreateOpen(false);
      await loadTeams(false);
    } catch (err: unknown) {
      setFormError((err as Error).message || 'Failed to register squad.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handlers for Edit
  const handleOpenEdit = (team: Team) => {
    setSelectedTeam(team);
    setFormName(team.name);
    setFormTable(team.assignedTable || '');
    setFormError(null);
    setIsEditOpen(true);
  };

  const handleUpdateTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTeam) return;
    setFormError(null);
    setIsSubmitting(true);
    try {
      const input: UpdateTeamInput = {
        name: formName,
        assignedTable: formTable,
      };
      await eventService.updateTeam(selectedTeam.id, input);
      setIsEditOpen(false);
    } catch (err: unknown) {
      setFormError((err as Error).message || 'Failed to update squad.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handlers for Delete
  const handleDeleteTeam = async () => {
    if (!deleteTargetTeam) return;
    setIsSubmitting(true);
    try {
      await eventService.deleteTeam(deleteTargetTeam.id);
      setDeleteTargetTeam(null);
      if (selectedTeam?.id === deleteTargetTeam.id) {
        setIsDetailsOpen(false);
        setSelectedTeam(null);
      }
    } catch (err: unknown) {
      alert((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Quick check-in toggle from Details Modal
  const handleToggleMemberCheckIn = async (memberId: string) => {
    try {
      await eventService.toggleParticipantCheckIn(memberId);
    } catch (err: unknown) {
      alert((err as Error).message);
    }
  };

  // Remove member from team
  const handleRemoveMemberFromTeam = async (participant: Participant) => {
    if (confirm(`Remove ${participant.name} from ${selectedTeam?.name}? They will become an unassigned participant.`)) {
      try {
        await eventService.updateParticipant(participant.id, { teamId: null });
      } catch (err: unknown) {
        alert((err as Error).message);
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <PageHeader
        title="Tournament Squads Management"
        subtitle="5 members per squad maximum · Target capacity: 32 Squads (160 Students)"
        badge={
          <Badge variant="primary" size="sm">
            {teams.length} Squads Registered
          </Badge>
        }
        actions={
          isStaff ? (
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Plus className="w-4 h-4" />}
              onClick={handleOpenCreate}
            >
              Register New Squad
            </Button>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              disabled
              leftIcon={<Lock className="w-3.5 h-3.5" />}
              title="Squad registration requires Organizer or Marshal role"
            >
              Registration Restricted
            </Button>
          )
        }
      />

      {/* Backend Connection / Error Banner */}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-rose-900 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{error.message}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAppMode('demo')}
              className="px-2.5 py-1 bg-white border border-rose-200 rounded text-rose-700 hover:bg-rose-100 font-medium cursor-pointer"
            >
              Switch to Demo
            </button>
            <Button variant="secondary" size="sm" onClick={() => loadTeams(true)} leftIcon={<RefreshCw className="w-3 h-3" />}>
              Retry
            </Button>
          </div>
        </div>
      )}

      {/* Search and Filters Toolbar */}
      <SearchFilterToolbar
        searchQuery={searchQuery}
        onSearchChange={(val) => {
          setSearchQuery(val);
          setCurrentPage(1);
        }}
        searchPlaceholder="Search squad name, number, or leader..."
        filters={[
          {
            id: 'checkIn',
            label: 'Check-in',
            value: filterCheckIn,
            onChange: (val) => {
              setFilterCheckIn(val);
              setCurrentPage(1);
            },
            options: [
              { label: 'All Check-In Statuses', value: 'all' },
              { label: 'Ready (5/5 Checked In)', value: 'ready' },
              { label: 'Partial Check-In', value: 'partial' },
              { label: 'Incomplete Roster (< 5 Members)', value: 'incomplete' },
              { label: 'Unchecked (0/5)', value: 'unchecked' },
            ],
          },
          {
            id: 'status',
            label: 'Status',
            value: filterStatus,
            onChange: (val) => {
              setFilterStatus(val);
              setCurrentPage(1);
            },
            options: [
              { label: 'All Statuses', value: 'all' },
              { label: 'Checked In', value: 'Checked In' },
              { label: 'Registered', value: 'Registered' },
            ],
          },
        ]}
        activeCount={
          (filterCheckIn !== 'all' ? 1 : 0) + (filterStatus !== 'all' ? 1 : 0) + (searchQuery ? 1 : 0)
        }
        onClearAll={() => {
          setSearchQuery('');
          setFilterCheckIn('all');
          setFilterStatus('all');
        }}
      />

      {/* Main Teams Table */}
      <Card>
        <CardHeader
          title="Registered Squads Roster"
          subtitle={`Showing ${paginatedTeams.length} of ${filteredAndSortedTeams.length} matching squads`}
        />
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#030712]/90 border-b border-cyan-500/20 text-[11px] font-mono uppercase tracking-wider font-bold text-cyan-400/80">
                  <th
                    className="py-3.5 px-4 cursor-pointer hover:text-cyan-300 transition-colors select-none"
                    onClick={() => handleSort('teamNumber')}
                  >
                    <div className="flex items-center gap-1">
                      <span>Tag</span>
                      <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                    </div>
                  </th>
                  <th
                    className="py-3.5 px-4 cursor-pointer hover:text-cyan-300 transition-colors select-none"
                    onClick={() => handleSort('name')}
                  >
                    <div className="flex items-center gap-1">
                      <span>Team Name</span>
                      <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                    </div>
                  </th>
                  <th
                    className="py-3.5 px-4 cursor-pointer hover:text-cyan-300 transition-colors select-none"
                    onClick={() => handleSort('membersCount')}
                  >
                    <div className="flex items-center gap-1">
                      <span>Assigned Members</span>
                      <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                    </div>
                  </th>
                  <th
                    className="py-3.5 px-4 cursor-pointer hover:text-cyan-300 transition-colors select-none"
                    onClick={() => handleSort('checkedInCount')}
                  >
                    <div className="flex items-center gap-1">
                      <span>Check-In Progress</span>
                      <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                    </div>
                  </th>
                  <th className="py-3.5 px-4">Desk Location</th>
                  <th className="py-3.5 px-4">Team Status</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-cyan-500/10 text-xs text-slate-300">
                {isLoading ? (
                  Array.from({ length: 8 }).map((_, i) => <TableRowSkeleton key={i} cols={7} />)
                ) : error ? (
                  <tr>
                    <td colSpan={7} className="py-12">
                      <div className="flex flex-col items-center justify-center text-center p-6 space-y-3">
                        <div className="p-3 bg-rose-950/50 text-rose-400 rounded-2xl border border-rose-500/40">
                          <AlertTriangle className="w-6 h-6" />
                        </div>
                        <div className="max-w-md">
                          <p className="font-orbitron font-bold text-slate-100 text-sm">Failed to Load Squads</p>
                          <p className="text-xs text-slate-400 mt-1 font-mono">{error.message}</p>
                        </div>
                        <div className="flex items-center gap-2 pt-1">
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => loadTeams(true)}
                            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                          >
                            Retry Loading Squads
                          </Button>
                        </div>
                      </div>
                    </td>
                  </tr>
                ) : paginatedTeams.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12">
                      <EmptyState
                        icon={Users}
                        title={teams.length === 0 ? 'No Squads Registered' : 'No Matching Squads'}
                        description={
                          teams.length === 0
                            ? 'No tournament squads have been registered yet.'
                            : 'No registered teams match your filter or search criteria.'
                        }
                        action={
                          teams.length > 0
                            ? {
                                label: 'Clear Filters',
                                onClick: () => {
                                  setSearchQuery('');
                                  setFilterCheckIn('all');
                                  setFilterStatus('all');
                                },
                              }
                            : isStaff
                            ? {
                                label: 'Register First Squad',
                                onClick: handleOpenCreate,
                              }
                            : undefined
                        }
                      />
                    </td>
                  </tr>
                ) : (
                  paginatedTeams.map((team) => {
                    const metrics = getTeamCheckInMetrics(team);
                    return (
                      <tr key={team.id} className="hover:bg-cyan-500/[0.05] transition-colors group">
                        <td className="py-3.5 px-4 font-mono font-bold text-cyan-300">
                          {formatTeamNumber(team.teamNumber)}
                        </td>
                        <td className="py-3.5 px-4">
                          <button
                            onClick={() => {
                              setSelectedTeam(team);
                              setIsDetailsOpen(true);
                            }}
                            className="font-orbitron font-semibold text-slate-100 hover:text-cyan-300 text-left transition-colors cursor-pointer"
                          >
                            {team.name}
                          </button>
                          <div className="text-[11px] text-slate-400 font-mono">
                            Leader: <span className="text-slate-300">{team.leaderName}</span>
                          </div>
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`font-semibold font-mono text-[11px] px-2 py-0.5 rounded-full border ${
                                metrics.isCompleteRoster
                                  ? 'bg-emerald-950/50 text-emerald-300 border-emerald-500/30'
                                  : 'bg-amber-950/50 text-amber-300 border-amber-500/30'
                              }`}
                            >
                              {metrics.total} / 5
                            </span>
                            {!metrics.isCompleteRoster && (
                              <span className="text-[10px] text-amber-400 font-mono">
                                Needs {5 - metrics.total}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="flex flex-col gap-1.5 max-w-[150px]">
                            <Badge variant={metrics.variant} size="sm" dot={metrics.isFullyCheckedIn}>
                              {metrics.label}
                            </Badge>
                            {/* Progress mini bar */}
                            <div className="w-full bg-slate-900 border border-slate-800 h-1.5 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${
                                  metrics.isFullyCheckedIn
                                    ? 'bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.5)]'
                                    : metrics.checkedIn > 0
                                    ? 'bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.5)]'
                                    : 'bg-slate-700'
                                }`}
                                style={{ width: `${(metrics.checkedIn / 5) * 100}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                          {team.assignedTable || '—'}
                        </td>
                        <td className="py-3.5 px-4">
                          {team.status === 'Checked In' ? (
                            <Badge variant="success" size="sm">
                              Checked In
                            </Badge>
                          ) : (
                            <Badge variant="neutral" size="sm">
                              Registered
                            </Badge>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={() => {
                                setSelectedTeam(team);
                                setIsDetailsOpen(true);
                              }}
                              className="p-1.5 rounded-xl text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10 border border-transparent hover:border-cyan-500/20 transition-colors cursor-pointer"
                              title="View squad details"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            {isStaff && (
                              <button
                                onClick={() => handleOpenEdit(team)}
                                className="p-1.5 rounded-xl text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10 border border-transparent hover:border-cyan-500/20 transition-colors cursor-pointer"
                                title="Edit squad"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>
                            )}
                            {isOrganizer && (
                              <button
                                onClick={() => setDeleteTargetTeam(team)}
                                className="p-1.5 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-colors cursor-pointer"
                                title="Delete squad"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {!isLoading && !error && filteredAndSortedTeams.length > 0 && (
            <Pagination
              currentPage={currentPage}
              totalItems={filteredAndSortedTeams.length}
              pageSize={pageSize}
              onPageChange={setCurrentPage}
            />
          )}
        </CardContent>
      </Card>

      {/* ========================================== */}
      {/* 1. Create Team & Roster Combined Modal     */}
      {/* ========================================== */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Register New Squad"
        subtitle="Register an official 5-participant squad slot with complete crew roster"
        maxWidth="3xl"
        footer={
          <div className="flex items-center justify-between w-full">
            <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-cyan-600" />
              <span>Atomic Transaction · 5 Verified Members Required</span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsCreateOpen(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleCreateTeam}
                isLoading={isSubmitting}
                disabled={isSubmitting || !memberValidation.isValid}
                title={memberValidation.errorMsg || 'Register squad and full roster'}
              >
                Register Squad & Roster
              </Button>
            </div>
          </div>
        }
      >
        <form onSubmit={handleCreateTeam} className="space-y-5 text-xs">
          {formError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-600" />
              <span>{formError}</span>
            </div>
          )}

          {/* Section 1: Squad Identity */}
          <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-200/80 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-slate-900 flex items-center gap-2 text-xs uppercase tracking-wider">
                <Users className="w-4 h-4 text-blue-600" />
                Squad Details
              </h4>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 font-mono font-semibold">
                Squad #{teams.length + 1} (T-{String(teams.length + 1).padStart(2, '0')})
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Squad / Team Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Neural Knights"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Assigned Table / Station
                </label>
                <input
                  type="text"
                  placeholder="e.g. Table 1"
                  value={formTable}
                  onChange={(e) => setFormTable(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
                />
              </div>
            </div>
          </div>

          {/* Section 2: 5 Squad Members */}
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2">
              <div className="flex items-center gap-2">
                <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider">
                  Squad Roster (Exactly 5 Members)
                </h4>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-medium ${
                  memberValidation.missingRequired
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-emerald-100 text-emerald-800'
                }`}>
                  {formMembers.filter((m) => m.name.trim() && m.usn.trim() && m.email.trim()).length} / 5 Ready
                </span>
                <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-indigo-100 text-indigo-800 font-medium">
                  {memberValidation.leadersCount} Leader
                </span>
              </div>
            </div>

            {/* Render each of the 5 members */}
            <div className="space-y-3 max-h-[50vh] overflow-y-auto pr-1">
              {formMembers.map((member, idx) => {
                const isLeader = member.role === 'Leader';
                const hasDuplicateUsn = member.usn.trim() && memberValidation.duplicateUsns.includes(member.usn.trim().toUpperCase());
                const hasDuplicateEmail = member.email.trim() && memberValidation.duplicateEmails.includes(member.email.trim().toLowerCase());

                return (
                  <div
                    key={idx}
                    className={`p-3.5 rounded-xl border transition-all ${
                      isLeader
                        ? 'bg-gradient-to-r from-blue-50/50 via-indigo-50/30 to-purple-50/20 border-blue-200 shadow-xs'
                        : 'bg-slate-50/70 border-slate-200'
                    }`}
                  >
                    {/* Member Card Header */}
                    <div className="flex items-center justify-between mb-2.5">
                      <div className="flex items-center gap-2">
                        <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                          isLeader ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-700'
                        }`}>
                          {idx + 1}
                        </span>
                        <span className="font-bold text-slate-800 text-xs">
                          {isLeader ? 'Squad Leader' : `Squad Member ${idx + 1}`}
                        </span>
                        {isLeader && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 uppercase">
                            <Crown className="w-3 h-3 text-amber-500" />
                            Primary Lead
                          </span>
                        )}
                      </div>

                      {/* Role Toggle Pill */}
                      <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5 text-[11px]">
                        <button
                          type="button"
                          onClick={() => handleMemberChange(idx, 'role', 'Leader')}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md font-semibold transition-all cursor-pointer ${
                            isLeader
                              ? 'bg-blue-600 text-white shadow-xs'
                              : 'text-slate-600 hover:text-slate-900'
                          }`}
                        >
                          <Crown className="w-3 h-3" />
                          Leader
                        </button>
                        <button
                          type="button"
                          onClick={() => handleMemberChange(idx, 'role', 'Member')}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md font-semibold transition-all cursor-pointer ${
                            !isLeader
                              ? 'bg-slate-200 text-slate-800'
                              : 'text-slate-600 hover:text-slate-900'
                          }`}
                        >
                          <UserIcon className="w-3 h-3" />
                          Member
                        </button>
                      </div>
                    </div>

                    {/* Member Inputs Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                          Full Name *
                        </label>
                        <input
                          type="text"
                          required
                          placeholder="e.g. Aditi Sharma"
                          value={member.name}
                          onChange={(e) => handleMemberChange(idx, 'name', e.target.value)}
                          className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-xs transition-all"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                          BMSIT USN *
                        </label>
                        <input
                          type="text"
                          required
                          placeholder="e.g. 1BY23CS001"
                          value={member.usn}
                          onChange={(e) => handleMemberChange(idx, 'usn', e.target.value)}
                          className={`w-full px-2.5 py-1.5 bg-white border rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 text-xs font-mono uppercase transition-all ${
                            hasDuplicateUsn
                              ? 'border-rose-400 focus:ring-rose-500/20 focus:border-rose-500 bg-rose-50/30'
                              : 'border-slate-200 focus:ring-blue-500/20 focus:border-blue-500'
                          }`}
                        />
                        {hasDuplicateUsn && (
                          <span className="text-[10px] text-rose-600 font-medium mt-0.5 block">
                            Duplicate USN in form
                          </span>
                        )}
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                          <Mail className="w-3 h-3 text-slate-400 inline mr-1" />
                          Institutional Email *
                        </label>
                        <input
                          type="email"
                          required
                          placeholder="e.g. student@bmsit.in"
                          value={member.email}
                          onChange={(e) => handleMemberChange(idx, 'email', e.target.value)}
                          className={`w-full px-2.5 py-1.5 bg-white border rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 text-xs transition-all ${
                            hasDuplicateEmail
                              ? 'border-rose-400 focus:ring-rose-500/20 focus:border-rose-500 bg-rose-50/30'
                              : 'border-slate-200 focus:ring-blue-500/20 focus:border-blue-500'
                          }`}
                        />
                        {hasDuplicateEmail && (
                          <span className="text-[10px] text-rose-600 font-medium mt-0.5 block">
                            Duplicate email in form
                          </span>
                        )}
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                          <Phone className="w-3 h-3 text-slate-400 inline mr-1" />
                          Contact Phone
                        </label>
                        <input
                          type="tel"
                          placeholder="+91 98765 43210"
                          value={member.phone}
                          onChange={(e) => handleMemberChange(idx, 'phone', e.target.value)}
                          className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-xs transition-all"
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="p-3 bg-blue-50/80 rounded-xl border border-blue-100 text-blue-900 text-[11px] leading-relaxed flex items-start gap-2">
            <Shield className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <strong>Squad & Roster Policy:</strong> Every registered squad must have exactly 5 participants with one designated squad leader. If any member fails validation or duplicate checks, the transaction is safely rolled back without creating partial records.
            </div>
          </div>
        </form>
      </Modal>

      {/* ========================================== */}
      {/* 2. Edit Team Modal                         */}
      {/* ========================================== */}
      <Modal
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        title="Edit Squad Details"
        subtitle={`Update attributes for ${selectedTeam?.name}`}
        maxWidth="md"
        footer={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsEditOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleUpdateTeam}
              isLoading={isSubmitting}
            >
              Save Changes
            </Button>
          </>
        }
      >
        <form onSubmit={handleUpdateTeam} className="space-y-4 text-xs">
          {formError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-600" />
              <span>{formError}</span>
            </div>
          )}

          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Squad Name *
            </label>
            <input
              type="text"
              required
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Assigned Table / Station
            </label>
            <input
              type="text"
              value={formTable}
              onChange={(e) => setFormTable(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
            />
          </div>
        </form>
      </Modal>

      {/* ========================================== */}
      {/* 3. Team Details Drawer / Modal             */}
      {/* ========================================== */}
      {selectedTeam && (
        <Modal
          isOpen={isDetailsOpen}
          onClose={() => setIsDetailsOpen(false)}
          title={
            <div className="flex items-center gap-2.5">
              <span className="font-mono font-bold text-blue-600">
                {formatTeamNumber(selectedTeam.teamNumber)}
              </span>
              <span>{selectedTeam.name}</span>
            </div>
          }
          subtitle={`Assigned Table: ${selectedTeam.assignedTable || 'None'} · Round ${selectedTeam.currentRound}`}
          maxWidth="2xl"
          footer={
            <div className="flex items-center justify-between w-full">
              <div className="text-[11px] text-slate-500">
                Registered: {new Date(selectedTeam.createdAt).toLocaleDateString()}
              </div>
              <Button size="sm" variant="outline" onClick={() => setIsDetailsOpen(false)}>
                Done
              </Button>
            </div>
          }
        >
          <div className="space-y-6 text-xs">
            {/* Check-in Completion Banner */}
            {(() => {
              const metrics = getTeamCheckInMetrics(selectedTeam);
              return (
                <div
                  className={`p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${
                    metrics.isFullyCheckedIn
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                      : metrics.isCompleteRoster
                      ? 'bg-blue-50 border-blue-200 text-blue-900'
                      : 'bg-amber-50 border-amber-200 text-amber-900'
                  }`}
                >
                  <div>
                    <div className="font-bold text-sm flex items-center gap-2">
                      {metrics.isFullyCheckedIn ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                      ) : (
                        <Clock className="w-5 h-5 text-amber-600" />
                      )}
                      <span>{metrics.label}</span>
                    </div>
                    <p className="text-[11px] opacity-80 mt-0.5">
                      {metrics.isFullyCheckedIn
                        ? 'All 5 members are present and verified. Squad is ready to compete in Round 1.'
                        : !metrics.isCompleteRoster
                        ? `Incomplete squad: Only ${metrics.total} of 5 members assigned. Squad cannot compete until full.`
                        : `${metrics.checkedIn} of 5 members checked in at the desk.`}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="font-mono font-bold text-lg">
                      {metrics.checkedIn} / 5
                    </span>
                  </div>
                </div>
              );
            })()}

            {/* Members Roster Table */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-bold text-slate-800 text-xs uppercase tracking-wider">
                  Squad Members ({selectedTeam.members.length} / 5)
                </h4>
                {selectedTeam.members.length < 5 && (
                  <span className="text-[11px] text-amber-600 font-medium">
                    {5 - selectedTeam.members.length} member slot(s) remaining
                  </span>
                )}
              </div>

              {selectedTeam.members.length === 0 ? (
                <div className="p-8 text-center border border-dashed border-slate-200 rounded-xl bg-slate-50 text-slate-500">
                  <UserX className="w-8 h-8 mx-auto mb-2 opacity-40" />
                  <p className="font-semibold text-xs text-slate-700">No Participants Assigned</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Navigate to the Participants page to register students and assign them to this squad.
                  </p>
                </div>
              ) : (
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-50 text-[10px] uppercase font-semibold text-slate-500 border-b border-slate-200">
                        <th className="py-2.5 px-3">Role</th>
                        <th className="py-2.5 px-3">Participant</th>
                        <th className="py-2.5 px-3">USN</th>
                        <th className="py-2.5 px-3">Check-In Status</th>
                        <th className="py-2.5 px-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {selectedTeam.members.map((member) => (
                        <tr key={member.id} className="hover:bg-slate-50/60">
                          <td className="py-2.5 px-3">
                            {member.role === 'Leader' ? (
                              <Badge variant="purple" size="sm">
                                Leader
                              </Badge>
                            ) : (
                              <Badge variant="neutral" size="sm">
                                Member
                              </Badge>
                            )}
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="font-semibold text-slate-800">{member.name}</div>
                            <div className="text-[10px] text-slate-400 font-mono">{member.email}</div>
                          </td>
                          <td className="py-2.5 px-3 font-mono text-slate-600">
                            {member.usn}
                          </td>
                          <td className="py-2.5 px-3">
                            <button
                              onClick={() => handleToggleMemberCheckIn(member.id)}
                              className="cursor-pointer"
                            >
                              {member.checkedIn ? (
                                <Badge variant="success" size="sm" dot>
                                  <UserCheck className="w-3 h-3 inline mr-1" />
                                  Checked In
                                </Badge>
                              ) : (
                                <Badge variant="warning" size="sm">
                                  <Clock className="w-3 h-3 inline mr-1" />
                                  Pending
                                </Badge>
                              )}
                            </button>
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <button
                              onClick={() => handleRemoveMemberFromTeam(member)}
                              className="text-[11px] text-rose-600 hover:text-rose-700 font-medium px-2 py-1 rounded hover:bg-rose-50 transition-colors cursor-pointer"
                              title="Unassign from this squad"
                            >
                              Unassign
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </Modal>
      )}

      {/* ========================================== */}
      {/* 4. Delete Team Safeguard Dialog            */}
      {/* ========================================== */}
      {deleteTargetTeam && (
        <ConfirmationDialog
          isOpen={true}
          onClose={() => setDeleteTargetTeam(null)}
          onConfirm={handleDeleteTeam}
          title={`Delete Squad: ${deleteTargetTeam.name}`}
          message={
            deleteTargetTeam.members.length > 0 ? (
              <p>
                This squad cannot be deleted because it currently has{' '}
                <strong>{deleteTargetTeam.members.length} assigned participant(s)</strong>.
              </p>
            ) : (
              <p>
                Are you sure you want to permanently delete <strong>{deleteTargetTeam.name}</strong> ({formatTeamNumber(deleteTargetTeam.teamNumber)}) from the tournament? This action cannot be undone.
              </p>
            )
          }
          isBlocked={deleteTargetTeam.members.length > 0}
          blockedReason="Data Integrity Safeguard: To prevent silent data loss or orphaned records, please unassign or transfer all participants before deleting this squad."
          confirmLabel="Delete Squad"
          cancelLabel="Close"
          isDestructive={true}
          isLoading={isSubmitting}
        />
      )}
    </div>
  );
}
