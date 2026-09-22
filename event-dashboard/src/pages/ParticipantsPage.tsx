import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  UserCheck,
  Plus,
  Edit2,
  Trash2,
  Eye,
  AlertTriangle,
  ArrowUpDown,
  ArrowRightLeft,
  Mail,
  Phone,
  Clock,
  CheckCircle2,
  Users,
  Shield,
  Lock,
  RefreshCw,
} from 'lucide-react';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
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
import { Participant, Team, ParticipantRole, CreateParticipantInput, UpdateParticipantInput, User, ApiError } from '../types';

type SortField = 'name' | 'usn' | 'teamName' | 'checkedIn';
type SortOrder = 'asc' | 'desc';

export function ParticipantsPage() {
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<User | null>(authService.getCurrentUser());
  const [accessError, setAccessError] = useState<{ status?: number; message: string; isForbidden?: boolean } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTeam, setFilterTeam] = useState<string>('all');
  const [filterCheckIn, setFilterCheckIn] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('usn');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 15;

  // Modals state
  const [selectedParticipant, setSelectedParticipant] = useState<Participant | null>(null);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isTransferOpen, setIsTransferOpen] = useState(false);
  const [deleteTargetParticipant, setDeleteTargetParticipant] = useState<Participant | null>(null);

  // Form states
  const [formName, setFormName] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formUsn, setFormUsn] = useState('');
  const [formPhone, setFormPhone] = useState('');
  const [formRole, setFormRole] = useState<ParticipantRole>('Member');
  const [formTeamId, setFormTeamId] = useState<string>('');
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Request sequence tracking & mount guard to prevent stale overwrites and race conditions
  const requestIdRef = useRef(0);
  const isMountedRef = useRef(true);

  // Load data & subscribe to changes
  const loadData = async (showSkeleton = true) => {
    const requestId = ++requestIdRef.current;
    if (showSkeleton) {
      setIsLoading(true);
    }
    setAccessError(null);
    try {
      // 1. Teams are always accessible (PII masked for non-staff)
      const teamsRes = await eventService.getTeams();
      if (requestId !== requestIdRef.current || !isMountedRef.current) return;
      setTeams(teamsRes.data || []);

      // 2. Fetch participants
      const partRes = await eventService.getParticipants();
      if (requestId !== requestIdRef.current || !isMountedRef.current) return;
      setParticipants(partRes.data || []);
      if (selectedParticipant) {
        const updated = (partRes.data || []).find((p) => p.id === selectedParticipant.id);
        if (updated) setSelectedParticipant(updated);
      }
    } catch (err: unknown) {
      if (requestId !== requestIdRef.current || !isMountedRef.current) return;
      console.error('Error loading participants data:', err);
      const apiErr = err as ApiError;
      const isForbidden = apiErr?.status === 403 || apiErr?.status === 401;
      setAccessError({
        status: apiErr?.status,
        message:
          apiErr?.message ||
          (isForbidden
            ? 'Access restricted: student records contain confidential PII.'
            : 'Failed to connect to FastAPI backend.'),
        isForbidden,
      });
      setParticipants([]);
    } finally {
      if (requestId === requestIdRef.current && isMountedRef.current) {
        setIsLoading(false);
      }
    }
  };

  useEffect(() => {
    isMountedRef.current = true;
    loadData(true);

    const unsubEvent = eventService.subscribe(() => {
      loadData(false);
    });

    const prevUserRef = { current: authService.getCurrentUser() };
    const unsubAuth = authService.subscribe((u) => {
      setCurrentUser(u);
      const prev = prevUserRef.current;
      const userChanged = !prev || !u || prev.id !== u.id || prev.role !== u.role;
      prevUserRef.current = u;
      if (userChanged) {
        loadData(false);
      }
    });

    const unsubMode = onAppModeChange(() => {
      loadData(true);
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

  // Filter & Sort
  const filteredAndSortedParticipants = useMemo(() => {
    return participants
      .filter((p) => {
        const query = searchQuery.toLowerCase().trim();
        const matchesSearch =
          !query ||
          p.name.toLowerCase().includes(query) ||
          p.usn.toLowerCase().includes(query) ||
          p.email.toLowerCase().includes(query) ||
          (p.teamName && p.teamName.toLowerCase().includes(query));

        let matchesTeam = true;
        if (filterTeam === 'unassigned') {
          matchesTeam = !p.teamId;
        } else if (filterTeam !== 'all') {
          matchesTeam = p.teamId === filterTeam;
        }

        let matchesCheckIn = true;
        if (filterCheckIn === 'checkedIn') {
          matchesCheckIn = p.checkedIn;
        } else if (filterCheckIn === 'pending') {
          matchesCheckIn = !p.checkedIn;
        }

        return matchesSearch && matchesTeam && matchesCheckIn;
      })
      .sort((a, b) => {
        let comparison = 0;
        if (sortField === 'name') {
          comparison = a.name.localeCompare(b.name);
        } else if (sortField === 'usn') {
          comparison = a.usn.localeCompare(b.usn);
        } else if (sortField === 'teamName') {
          comparison = (a.teamName || '').localeCompare(b.teamName || '');
        } else if (sortField === 'checkedIn') {
          comparison = (a.checkedIn === b.checkedIn) ? 0 : a.checkedIn ? -1 : 1;
        }
        return sortOrder === 'asc' ? comparison : -comparison;
      });
  }, [participants, searchQuery, filterTeam, filterCheckIn, sortField, sortOrder]);

  const paginatedParticipants = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredAndSortedParticipants.slice(start, start + pageSize);
  }, [filteredAndSortedParticipants, currentPage, pageSize]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  // Check-In toggle
  const handleToggleCheckIn = async (participantId: string) => {
    try {
      await eventService.toggleParticipantCheckIn(participantId);
    } catch (err: unknown) {
      alert((err as Error).message);
    }
  };

  // Create Handlers
  const handleOpenCreate = () => {
    setFormName('');
    setFormEmail('');
    setFormUsn('');
    setFormPhone('');
    setFormRole('Member');
    // Default to first team with < 5 members if available
    const availableTeam = teams.find((t) => t.members.length < 5);
    setFormTeamId(availableTeam ? availableTeam.id : '');
    setFormError(null);
    setIsCreateOpen(true);
  };

  const handleCreateParticipant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTeamId) {
      setFormError('Please select a squad. Individual participants cannot be registered without being assigned to an official squad.');
      return;
    }
    setFormError(null);
    setIsSubmitting(true);
    try {
      const input: CreateParticipantInput = {
        name: formName.trim(),
        email: formEmail.trim(),
        usn: formUsn.trim(),
        phone: formPhone.trim() || undefined,
        role: formRole,
        teamId: formTeamId,
        checkedIn: false,
      };
      await eventService.createParticipant(input);
      setIsCreateOpen(false);
      await loadData(false);
    } catch (err: unknown) {
      setFormError((err as Error).message || 'Failed to add student.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Edit Handlers
  const handleOpenEdit = (p: Participant) => {
    setSelectedParticipant(p);
    setFormName(p.name);
    setFormEmail(p.email);
    setFormUsn(p.usn);
    setFormPhone(p.phone || '');
    setFormRole(p.role);
    setFormError(null);
    setIsEditOpen(true);
  };

  const handleUpdateParticipant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedParticipant) return;
    setFormError(null);
    setIsSubmitting(true);
    try {
      const input: UpdateParticipantInput = {
        name: formName,
        email: formEmail,
        usn: formUsn,
        phone: formPhone || undefined,
        role: formRole,
      };
      await eventService.updateParticipant(selectedParticipant.id, input);
      setIsEditOpen(false);
    } catch (err: unknown) {
      setFormError((err as Error).message || 'Failed to update participant.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Transfer / Reassign Handlers
  const handleOpenTransfer = (p: Participant) => {
    setSelectedParticipant(p);
    setFormTeamId(p.teamId || '');
    setFormError(null);
    setIsTransferOpen(true);
  };

  const handleTransferParticipant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedParticipant) return;
    setFormError(null);
    setIsSubmitting(true);
    try {
      await eventService.updateParticipant(selectedParticipant.id, {
        teamId: formTeamId || null,
      });
      setIsTransferOpen(false);
    } catch (err: unknown) {
      setFormError((err as Error).message || 'Transfer failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Handler
  const handleDeleteParticipant = async () => {
    if (!deleteTargetParticipant) return;
    setIsSubmitting(true);
    try {
      await eventService.deleteParticipant(deleteTargetParticipant.id);
      setDeleteTargetParticipant(null);
      if (selectedParticipant?.id === deleteTargetParticipant.id) {
        setIsDetailsOpen(false);
        setSelectedParticipant(null);
      }
    } catch (err: unknown) {
      alert((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <PageHeader
        title="Student Participants Directory"
        subtitle="Individual student accreditation, desk check-in, and squad assignment"
        badge={
          isLiveMode() && accessError?.isForbidden ? (
            <Badge variant="warning" size="sm">
              Restricted · Staff Only
            </Badge>
          ) : (
            <Badge variant="primary" size="sm">
              {participants.length} Students Registered
            </Badge>
          )
        }
        actions={
          (!isLiveMode() || (currentUser && ['ORGANIZER', 'MARSHAL'].includes(currentUser.role))) ? (
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Plus className="w-4 h-4" />}
              onClick={handleOpenCreate}
            >
              Register Student
            </Button>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              disabled
              leftIcon={<Lock className="w-3.5 h-3.5" />}
              title="Student registration requires Organizer or Marshal role"
            >
              Registration Restricted
            </Button>
          )
        }
      />

      {/* Access Error Banner (General server / offline failure) */}
      {accessError && !accessError.isForbidden && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-rose-900 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{accessError.message}</span>
          </div>
          <Button variant="secondary" size="sm" onClick={() => loadData(true)} leftIcon={<RefreshCw className="w-3 h-3" />}>
            Retry
          </Button>
        </div>
      )}

      {/* RBAC Restricted Notice (When in Live Mode and user lacks staff permissions) */}
      {isLiveMode() && accessError?.isForbidden && (
        <div className="bg-amber-50/90 border border-amber-200/90 rounded-xl p-5 text-amber-900 shadow-xs">
          <div className="flex items-start gap-3.5">
            <div className="p-2.5 bg-amber-100/80 rounded-xl text-amber-700 flex-shrink-0 mt-0.5">
              <Shield className="w-5 h-5" />
            </div>
            <div className="flex-1 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-bold text-amber-950">
                  Student Directory Restricted — Role-Based Access Control (RBAC)
                </h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-200/80 text-amber-900 uppercase tracking-wider">
                  Confidential PII
                </span>
              </div>
              <p className="text-xs text-amber-800 leading-relaxed max-w-3xl">
                The individual participant roster contains confidential student personally identifiable information (USN, email, phone number) protected by event data policies.
                Your current role is <span className="font-semibold text-amber-950">{currentUser?.role || 'PUBLIC_PROJECTOR'}</span>.
                Under tournament security policy, full student records can only be viewed and modified by authenticated <strong className="font-semibold text-amber-950">Organizer</strong>, <strong className="font-semibold text-amber-950">Marshal</strong>, or <strong className="font-semibold text-amber-950">Judge</strong> accounts.
              </p>
              <div className="flex flex-wrap items-center gap-2.5 pt-1">
                <Link
                  to="/teams"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-700 hover:bg-amber-800 text-white text-xs font-semibold shadow-xs transition-colors"
                >
                  <Users className="w-3.5 h-3.5" />
                  View Public Teams Roster
                </Link>
                <button
                  onClick={() => {
                    setAppMode('demo');
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-amber-300 text-amber-900 hover:bg-amber-100 text-xs font-medium transition-colors cursor-pointer"
                >
                  Switch to Demo Mode (160 Mock Students)
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Guidance Banner for Combined Registration */}
      <div className="bg-gradient-to-r from-blue-50/80 via-indigo-50/50 to-blue-50/80 border border-blue-200/80 rounded-xl p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-blue-900">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-blue-100/80 rounded-lg text-blue-700 flex-shrink-0">
            <Users className="w-4 h-4" />
          </div>
          <div>
            <span className="font-semibold">Registering an entire squad? </span>
            <span className="text-blue-800">You can now register a team and all 5 squad participants in a single combined workflow.</span>
          </div>
        </div>
        <Link
          to="/teams"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-xs transition-colors flex-shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          Register New Squad
        </Link>
      </div>

      {/* Search and Filters Toolbar */}
      <SearchFilterToolbar
        searchQuery={searchQuery}
        onSearchChange={(val) => {
          setSearchQuery(val);
          setCurrentPage(1);
        }}
        searchPlaceholder="Search by name, USN, email, or squad..."
        filters={[
          {
            id: 'team',
            label: 'Squad',
            value: filterTeam,
            onChange: (val) => {
              setFilterTeam(val);
              setCurrentPage(1);
            },
            options: [
              { label: `All Squads (${teams.length})`, value: 'all' },
              { label: 'Unassigned Only', value: 'unassigned' },
              ...teams.map((t) => ({
                label: `${t.name} (${t.members.length}/5)`,
                value: t.id,
              })),
            ],
          },
          {
            id: 'checkIn',
            label: 'Check-in',
            value: filterCheckIn,
            onChange: (val) => {
              setFilterCheckIn(val);
              setCurrentPage(1);
            },
            options: [
              { label: 'All Statuses', value: 'all' },
              { label: 'Checked In', value: 'checkedIn' },
              { label: 'Pending', value: 'pending' },
            ],
          },
        ]}
        activeCount={
          (filterTeam !== 'all' ? 1 : 0) + (filterCheckIn !== 'all' ? 1 : 0) + (searchQuery ? 1 : 0)
        }
        onClearAll={() => {
          setSearchQuery('');
          setFilterTeam('all');
          setFilterCheckIn('all');
        }}
      />

      {/* Participants Table */}
      <Card>
        <CardHeader
          title="Student Roster"
          subtitle={`Showing ${paginatedParticipants.length} of ${filteredAndSortedParticipants.length} matching students`}
        />
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#030712]/90 border-b border-cyan-500/20 text-[11px] font-mono uppercase tracking-wider font-bold text-cyan-400/80">
                  <th
                    className="py-3.5 px-4 cursor-pointer hover:text-cyan-300 transition-colors select-none"
                    onClick={() => handleSort('usn')}
                  >
                    <div className="flex items-center gap-1">
                      <span>USN</span>
                      <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                    </div>
                  </th>
                  <th
                    className="py-3.5 px-4 cursor-pointer hover:text-cyan-300 transition-colors select-none"
                    onClick={() => handleSort('name')}
                  >
                    <div className="flex items-center gap-1">
                      <span>Student Name</span>
                      <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                    </div>
                  </th>
                  <th className="py-3.5 px-4">Role</th>
                  <th
                    className="py-3.5 px-4 cursor-pointer hover:text-cyan-300 transition-colors select-none"
                    onClick={() => handleSort('teamName')}
                  >
                    <div className="flex items-center gap-1">
                      <span>Assigned Squad</span>
                      <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                    </div>
                  </th>
                  <th
                    className="py-3.5 px-4 cursor-pointer hover:text-cyan-300 transition-colors select-none"
                    onClick={() => handleSort('checkedIn')}
                  >
                    <div className="flex items-center gap-1">
                      <span>Check-In</span>
                      <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                    </div>
                  </th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-cyan-500/10 text-xs text-slate-300">
                {isLoading ? (
                  Array.from({ length: 8 }).map((_, i) => <TableRowSkeleton key={i} cols={6} />)
                ) : isLiveMode() && accessError?.isForbidden ? (
                  <tr>
                    <td colSpan={6} className="py-12">
                      <div className="flex flex-col items-center justify-center text-center p-8">
                        <div className="w-12 h-12 rounded-2xl bg-amber-950/40 flex items-center justify-center text-amber-400 mb-3 border border-amber-500/30">
                          <Lock className="w-6 h-6" />
                        </div>
                        <h3 className="text-sm font-orbitron font-bold text-slate-100">
                          Student Directory Restricted Under RBAC
                        </h3>
                        <p className="text-xs text-slate-400 font-sans max-w-md mt-1">
                          Full student accreditation records (names, USNs, emails, phone numbers) are confidential. Sign in as Organizer, Marshal, or Judge to inspect or manage participants.
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : paginatedParticipants.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12">
                      <EmptyState
                        icon={UserCheck}
                        title="No Participants Found"
                        description="No registered students match your filter or search criteria."
                        action={{
                          label: 'Clear Filters',
                          onClick: () => {
                            setSearchQuery('');
                            setFilterTeam('all');
                            setFilterCheckIn('all');
                          },
                        }}
                      />
                    </td>
                  </tr>
                ) : (
                  paginatedParticipants.map((participant) => (
                    <tr key={participant.id} className="hover:bg-cyan-500/[0.05] transition-colors group">
                      <td className="py-3 px-4 font-mono font-bold text-cyan-300">
                        {participant.usn}
                      </td>
                      <td className="py-3 px-4">
                        <button
                          onClick={() => {
                            setSelectedParticipant(participant);
                            setIsDetailsOpen(true);
                          }}
                          className="font-orbitron font-semibold text-slate-100 hover:text-cyan-300 text-left transition-colors cursor-pointer"
                        >
                          {participant.name}
                        </button>
                        <div className="text-[11px] text-slate-400 font-mono">
                          {participant.email}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {participant.role === 'Leader' ? (
                          <Badge variant="purple" size="sm">
                            Leader
                          </Badge>
                        ) : (
                          <Badge variant="neutral" size="sm">
                            Member
                          </Badge>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {participant.teamId ? (
                          <span className="inline-flex items-center gap-1.5 font-mono font-medium bg-cyan-950/50 text-cyan-300 px-2.5 py-1 rounded-xl border border-cyan-500/30 text-[11px]">
                            <Users className="w-3 h-3 text-cyan-400" />
                            {participant.teamName}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 font-mono text-[11px] text-amber-300 bg-amber-950/40 border border-amber-500/30 px-2.5 py-1 rounded-xl">
                            Unassigned
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {participant.checkedIn ? (
                          <Badge variant="success" size="sm" dot={true}>
                            Checked In
                          </Badge>
                        ) : (
                          <Badge variant="neutral" size="sm">
                            Pending
                          </Badge>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => {
                              setSelectedParticipant(participant);
                              setIsDetailsOpen(true);
                            }}
                            className="p-1.5 rounded-xl text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10 border border-transparent hover:border-cyan-500/20 transition-colors cursor-pointer"
                            title="View student profile"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {isStaff && (
                            <button
                              onClick={() => handleOpenTransfer(participant)}
                              className="p-1.5 rounded-xl text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10 border border-transparent hover:border-cyan-500/20 transition-colors cursor-pointer"
                              title="Transfer squad"
                            >
                              <ArrowRightLeft className="w-4 h-4" />
                            </button>
                          )}
                          {isStaff && (
                            <button
                              onClick={() => handleOpenEdit(participant)}
                              className="p-1.5 rounded-xl text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10 border border-transparent hover:border-cyan-500/20 transition-colors cursor-pointer"
                              title="Edit record"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                          )}
                          {isOrganizer && (
                            <button
                              onClick={() => setDeleteTargetParticipant(participant)}
                              className="p-1.5 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-colors cursor-pointer"
                              title="Delete participant"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <Pagination
            currentPage={currentPage}
            totalItems={filteredAndSortedParticipants.length}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
          />
        </CardContent>
      </Card>

      {/* ========================================== */}
      {/* 1. Add Participant Modal                   */}
      {/* ========================================== */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Register Student Participant"
        subtitle="Add a college student to the tournament directory and assign to a squad"
        maxWidth="md"
        footer={
          <>
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
              onClick={handleCreateParticipant}
              isLoading={isSubmitting}
            >
              Register Student
            </Button>
          </>
        }
      >
        <form onSubmit={handleCreateParticipant} className="space-y-4 text-xs">
          {formError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-600" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Full Name *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Aditi Sharma"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                BMSIT USN *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. 1BY23CS161"
                value={formUsn}
                onChange={(e) => setFormUsn(e.target.value.toUpperCase())}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs font-mono uppercase"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Institutional Email *
              </label>
              <input
                type="email"
                required
                placeholder="student@bmsit.in"
                value={formEmail}
                onChange={(e) => setFormEmail(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Contact Phone
              </label>
              <input
                type="tel"
                placeholder="+91 98765 43210"
                value={formPhone}
                onChange={(e) => setFormPhone(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Squad Role
              </label>
              <select
                value={formRole}
                onChange={(e) => setFormRole(e.target.value as ParticipantRole)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
              >
                <option value="Member">Squad Member</option>
                <option value="Leader">Squad Leader</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Assign to Squad *
              </label>
              <select
                required
                value={formTeamId}
                onChange={(e) => setFormTeamId(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
              >
                <option value="" disabled>-- Select Squad (Required) --</option>
                {teams.map((t) => {
                  const isFull = t.members.length >= 5;
                  return (
                    <option key={t.id} value={t.id} disabled={isFull}>
                      {t.name} ({t.members.length}/5 members) {isFull ? '— SQUAD FULL' : ''}
                    </option>
                  );
                })}
              </select>
              {teams.length === 0 && (
                <p className="text-[11px] text-amber-600 mt-1">
                  No squads registered yet. Please create a squad first via <strong>Teams</strong>.
                </p>
              )}
            </div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-slate-600 text-[11px] space-y-1">
            <p><strong>Assignment Rule:</strong> All participants must belong to an official registered squad. Standalone or unassigned participants are not permitted.</p>
            <p className="text-slate-500">To register an entire 5-person squad with full roster at once, use the <strong>Teams → Register New Squad</strong> workflow.</p>
          </div>
        </form>
      </Modal>

      {/* ========================================== */}
      {/* 2. Edit Participant Modal                  */}
      {/* ========================================== */}
      <Modal
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        title="Edit Participant Info"
        subtitle={`Update attributes for ${selectedParticipant?.name}`}
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
              onClick={handleUpdateParticipant}
              isLoading={isSubmitting}
            >
              Save Changes
            </Button>
          </>
        }
      >
        <form onSubmit={handleUpdateParticipant} className="space-y-4 text-xs">
          {formError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-600" />
              <span>{formError}</span>
            </div>
          )}

          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Full Name *
            </label>
            <input
              type="text"
              required
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                BMSIT USN *
              </label>
              <input
                type="text"
                required
                value={formUsn}
                onChange={(e) => setFormUsn(e.target.value.toUpperCase())}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-mono uppercase focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Squad Role
              </label>
              <select
                value={formRole}
                onChange={(e) => setFormRole(e.target.value as ParticipantRole)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
              >
                <option value="Member">Squad Member</option>
                <option value="Leader">Squad Leader</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Institutional Email *
              </label>
              <input
                type="email"
                required
                value={formEmail}
                onChange={(e) => setFormEmail(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Phone Contact
              </label>
              <input
                type="tel"
                value={formPhone}
                onChange={(e) => setFormPhone(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
              />
            </div>
          </div>
        </form>
      </Modal>

      {/* ========================================== */}
      {/* 3. Assign / Transfer Squad Modal           */}
      {/* ========================================== */}
      <Modal
        isOpen={isTransferOpen}
        onClose={() => setIsTransferOpen(false)}
        title="Transfer / Assign Squad"
        subtitle={`Select target squad for ${selectedParticipant?.name}`}
        maxWidth="md"
        footer={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsTransferOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleTransferParticipant}
              isLoading={isSubmitting}
            >
              Confirm Assignment
            </Button>
          </>
        }
      >
        <form onSubmit={handleTransferParticipant} className="space-y-4 text-xs">
          {formError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-600" />
              <span>{formError}</span>
            </div>
          )}

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <div className="text-[11px] text-slate-500">Current Assignment:</div>
            <div className="font-bold text-slate-800 mt-0.5">
              {selectedParticipant?.teamName ? (
                <span>{selectedParticipant.teamName}</span>
              ) : (
                <span className="text-amber-600 font-normal">Unassigned (Bench)</span>
              )}
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Select Destination Squad
            </label>
            <select
              value={formTeamId}
              onChange={(e) => setFormTeamId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-xs"
            >
              <option value="">Unassign from Squad (Move to Bench)</option>
              {teams.map((t) => {
                const isCurrentTeam = t.id === selectedParticipant?.teamId;
                const isFull = t.members.length >= 5 && !isCurrentTeam;
                return (
                  <option key={t.id} value={t.id} disabled={isFull}>
                    {t.name} ({t.members.length}/5 members){isCurrentTeam ? ' — (Current)' : ''}{isFull ? ' — FULL' : ''}
                  </option>
                );
              })}
            </select>
          </div>

          <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-amber-900 text-[11px] leading-relaxed">
            <strong>Transfer Safeguard:</strong> Reassigning will automatically update both squads&apos; rosters and recalculate check-in completeness.
          </div>
        </form>
      </Modal>

      {/* ========================================== */}
      {/* 4. Participant Details Modal               */}
      {/* ========================================== */}
      {selectedParticipant && (
        <Modal
          isOpen={isDetailsOpen}
          onClose={() => setIsDetailsOpen(false)}
          title={selectedParticipant.name}
          subtitle={`USN: ${selectedParticipant.usn} · ${selectedParticipant.role}`}
          maxWidth="md"
          footer={
            <Button size="sm" variant="outline" onClick={() => setIsDetailsOpen(false)}>
              Close
            </Button>
          }
        >
          <div className="space-y-4 text-xs">
            {/* Check-in Banner */}
            <div
              className={`p-4 rounded-xl border flex items-center justify-between ${
                selectedParticipant.checkedIn
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                  : 'bg-amber-50 border-amber-200 text-amber-900'
              }`}
            >
              <div>
                <div className="font-bold flex items-center gap-1.5">
                  {selectedParticipant.checkedIn ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      Check-In Verified
                    </>
                  ) : (
                    <>
                      <Clock className="w-4 h-4 text-amber-600" />
                      Check-In Pending
                    </>
                  )}
                </div>
                <div className="text-[11px] opacity-80 mt-0.5">
                  {selectedParticipant.checkedIn
                    ? 'Student credential has been verified at the check-in desk.'
                    : 'Student has not yet presented credentials at the tech desk.'}
                </div>
              </div>

              <Button
                variant={selectedParticipant.checkedIn ? 'outline' : 'primary'}
                size="sm"
                onClick={() => handleToggleCheckIn(selectedParticipant.id)}
              >
                {selectedParticipant.checkedIn ? 'Revoke' : 'Check In'}
              </Button>
            </div>

            {/* Profile Data List */}
            <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden bg-white">
              <div className="p-3 flex items-center justify-between">
                <span className="text-slate-500">Assigned Squad</span>
                <span className="font-semibold text-slate-800">
                  {selectedParticipant.teamName || 'Unassigned'}
                </span>
              </div>
              <div className="p-3 flex items-center justify-between">
                <span className="text-slate-500">Squad Role</span>
                <Badge variant={selectedParticipant.role === 'Leader' ? 'purple' : 'neutral'} size="sm">
                  {selectedParticipant.role}
                </Badge>
              </div>
              <div className="p-3 flex items-center justify-between">
                <span className="text-slate-500">Email Address</span>
                <span className="font-mono text-slate-700 flex items-center gap-1">
                  <Mail className="w-3.5 h-3.5 text-slate-400" />
                  {selectedParticipant.email}
                </span>
              </div>
              <div className="p-3 flex items-center justify-between">
                <span className="text-slate-500">Contact Number</span>
                <span className="text-slate-700 flex items-center gap-1">
                  <Phone className="w-3.5 h-3.5 text-slate-400" />
                  {selectedParticipant.phone || 'Not Provided'}
                </span>
              </div>
              <div className="p-3 flex items-center justify-between">
                <span className="text-slate-500">Participant ID</span>
                <span className="font-mono text-slate-400 text-[11px]">
                  {selectedParticipant.id}
                </span>
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* ========================================== */}
      {/* 5. Delete Participant Confirmation         */}
      {/* ========================================== */}
      {deleteTargetParticipant && (
        <ConfirmationDialog
          isOpen={true}
          onClose={() => setDeleteTargetParticipant(null)}
          onConfirm={handleDeleteParticipant}
          title={`Delete Student: ${deleteTargetParticipant.name}`}
          message={
            <p>
              Are you sure you want to permanently remove <strong>{deleteTargetParticipant.name}</strong> ({deleteTargetParticipant.usn}) from the tournament directory?
              {deleteTargetParticipant.teamName && (
                <span className="block mt-1 text-amber-700 font-medium">
                  This student will also be removed from {deleteTargetParticipant.teamName}&apos;s squad roster.
                </span>
              )}
            </p>
          }
          confirmLabel="Delete Student"
          cancelLabel="Cancel"
          isDestructive={true}
          isLoading={isSubmitting}
        />
      )}
    </div>
  );
}
