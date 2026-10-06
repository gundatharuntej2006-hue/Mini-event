import { useState, useEffect, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Compass,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowUpDown,
  Settings,
  ShieldAlert,
  Sparkles,
  RotateCcw,
  Trophy,
  Users,
  Eye,
  Check,
  QrCode,
  Radio,
  Printer,
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
import { SummaryMetric } from '../components/ui/SummaryMetric';
import { eventService } from '../services/eventService';
import { backendApiService } from '../services/backendApiService';
import {
  TeamRound1Record,
  Round1Config,
  UpdateMiniRoundTimingInput,
  GateCheckinRecord,
  RouteAllocationMatrix,
  LocationVolunteerItem,
  EnvelopePreparationItem,
  TeamAuditDetails,
} from '../types';
import { formatDuration } from '../utils/timing';
import { formatTeamNumber } from '../utils/formatters';
import { ScoringEngineResult } from '../utils/round1Scoring';

type SortField = 'rank' | 'teamNumber' | 'name' | 'adjustedTotalSeconds' | 'rawTotalSeconds';
type SortOrder = 'asc' | 'desc';
type OrganizerViewMode = 'leaderboard' | 'allocations' | 'volunteer' | 'envelopes';

const R1_LOCATIONS_META: Record<number, { name: string; target: string; clue: string }> = {
  1: {
    name: 'Campus Border Gate',
    target: 'Metal plate: S=Silicon State, A=50, L=EP, N=1735',
    clue: 'Where campus day ends and the city begins. Vehicles wait nearby.',
  },
  2: {
    name: 'Roasted Bean Trail',
    target: 'Metal plate: S=Silicon State, A=2, L1=K, L2=K, N=6426',
    clue: 'Follow the trail guided by the aroma of roasted beans and caffeine.',
  },
  3: {
    name: "Newton's Domain",
    target: "Newton's Domain of physics and calculations",
    clue: 'Where gravity, light, and electricity calculations happen.',
  },
  4: {
    name: 'Bakery of Logic',
    target: 'Follow the scent of freshly baked logic',
    clue: 'Heat transforms dough and yeast quietly performs chemistry.',
  },
  5: {
    name: 'The Morning Hut',
    target: 'Rustic hut powering campus mornings',
    clue: 'Humble refuge awakening students with boiling brew.',
  },
  6: {
    name: 'Words in Stone',
    target: 'Words carved in stone near skyline designers',
    clue: 'Knowledge carved in stone near designers of skylines.',
  },
  7: {
    name: 'Block Arm & Dimension Room',
    target: 'Block letters after A, R, M. Room dimensions + 0 + dimensions',
    clue: 'Letters after A, R, M. Think of dimensions we inhabit...',
  },
  8: {
    name: 'Discovery Chamber',
    target: 'Room 206 (Number of adult human bones)',
    clue: 'Where experiments explode with excitement or quietly bloom.',
  },
};

const getSetBadgeClass = (setStr?: string) => {
  const s = setStr?.toUpperCase().trim();
  if (s?.includes('A')) return 'bg-cyan-950/80 text-cyan-300 border-cyan-500/40';
  if (s?.includes('B')) return 'bg-purple-950/80 text-purple-300 border-purple-500/40';
  if (s?.includes('C')) return 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40';
  if (s?.includes('D')) return 'bg-amber-950/80 text-amber-300 border-amber-500/40';
  return 'bg-slate-800 text-slate-300 border-slate-700';
};

export function Round1ExpeditionPage() {
  const [data, setData] = useState<{
    records: TeamRound1Record[];
    config: Round1Config;
    engine: ScoringEngineResult;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // View mode
  const [viewMode, setViewMode] = useState<OrganizerViewMode>('leaderboard');

  // Search, filter, sorting, pagination
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterProgress, setFilterProgress] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('rank');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 12;

  // Modals state
  const [selectedRecord, setSelectedRecord] = useState<TeamRound1Record | null>(null);
  const [isManageTimingOpen, setIsManageTimingOpen] = useState(false);
  const [activeMiniRoundTab, setActiveMiniRoundTab] = useState<1 | 2 | 3>(1);
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [isFinalizeConfirmOpen, setIsFinalizeConfirmOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form states for timing edit
  const [timingStartTime, setTimingStartTime] = useState('');
  const [timingEndTime, setTimingEndTime] = useState('');
  const [timingHints, setTimingHints] = useState(0);
  const [timingPhonePenalties, setTimingPhonePenalties] = useState(0);
  const [timingSeparationPenalties, setTimingSeparationPenalties] = useState(0);
  const [timingClueTampering, setTimingClueTampering] = useState(false);
  const [timingIsDisqualified, setTimingIsDisqualified] = useState(false);
  const [timingDisqualificationReason, setTimingDisqualificationReason] = useState('');
  const [timingCheckpoints, setTimingCheckpoints] = useState<string[]>([]);
  const [timingError, setTimingError] = useState<string | null>(null);

  // Config modal form states (Official ODDyssey Protocol values)
  const [configPenaltyMinutes, setConfigPenaltyMinutes] = useState(5);
  const [configCheckpointNames, setConfigCheckpointNames] = useState<string[]>([
    'GATE 42',
    'Map Point J',
    'Lock 48 / Stationary',
  ]);
  const [configHiddenCodeRecovered, setConfigHiddenCodeRecovered] = useState(false);
  const [configHiddenCodeTeamId, setConfigHiddenCodeTeamId] = useState('');
  const [configHiddenCodeNotes, setConfigHiddenCodeNotes] = useState('');

  // Checkins feed state
  const [checkinsFeed, setCheckinsFeed] = useState<GateCheckinRecord[]>([]);
  const [isCheckinsModalOpen, setIsCheckinsModalOpen] = useState(false);
  const [isLoadingCheckins, setIsLoadingCheckins] = useState(false);

  // Allocations Matrix state
  const [allocationsData, setAllocationsData] = useState<RouteAllocationMatrix | null>(null);
  const [isLoadingAllocations, setIsLoadingAllocations] = useState(false);
  const [isRegenerateModalOpen, setIsRegenerateModalOpen] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);

  // Volunteer view state
  const [volunteerCp, setVolunteerCp] = useState<1 | 2 | 3>(1);
  const [volunteerLoc, setVolunteerLoc] = useState<number>(1);
  const [volunteerData, setVolunteerData] = useState<LocationVolunteerItem | null>(null);
  const [isLoadingVolunteer, setIsLoadingVolunteer] = useState(false);

  // Envelope prep sheet state
  const [envelopesData, setEnvelopesData] = useState<EnvelopePreparationItem[]>([]);
  const [isLoadingEnvelopes, setIsLoadingEnvelopes] = useState(false);

  // Team detail / audit modal state
  const [selectedTeamAudit, setSelectedTeamAudit] = useState<TeamAuditDetails | null>(null);
  const [isLoadingTeamAudit, setIsLoadingTeamAudit] = useState(false);
  const [isTeamAuditOpen, setIsTeamAuditOpen] = useState(false);

  // Start round & live timer
  const [isStartingRound, setIsStartingRound] = useState(false);
  const [elapsedDisplay, setElapsedDisplay] = useState('00:00:00');

  const fetchCheckins = async () => {
    setIsLoadingCheckins(true);
    try {
      const res = await backendApiService.getRound1CheckinsFeed();
      if (res.data) {
        setCheckinsFeed(res.data);
      }
    } catch (err) {
      console.error('Failed to load checkins feed:', err);
    } finally {
      setIsLoadingCheckins(false);
    }
  };

  const loadAllocations = async () => {
    setIsLoadingAllocations(true);
    try {
      const res = await backendApiService.getRouteAllocationsMatrix();
      if (res.data) {
        setAllocationsData(res.data);
      }
    } catch (err) {
      console.error('Failed to load allocations:', err);
    } finally {
      setIsLoadingAllocations(false);
    }
  };

  const handleRegenerateAllocations = async () => {
    setIsRegenerating(true);
    try {
      const res = await backendApiService.generateRouteAllocations();
      if (res.data) {
        setAllocationsData(res.data);
        setIsRegenerateModalOpen(false);
        await loadRound1();
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || 'Failed to regenerate allocations');
    } finally {
      setIsRegenerating(false);
    }
  };

  const loadVolunteerData = useCallback(async (cp: number, loc: number) => {
    setIsLoadingVolunteer(true);
    try {
      const res = await backendApiService.getLocationVolunteerView(cp, loc);
      if (res.data) {
        setVolunteerData(res.data);
      }
    } catch (err) {
      console.error('Failed to load volunteer view:', err);
    } finally {
      setIsLoadingVolunteer(false);
    }
  }, []);

  const loadEnvelopesData = async () => {
    setIsLoadingEnvelopes(true);
    try {
      const res = await backendApiService.getEnvelopePreparationSheet();
      if (res.data) {
        setEnvelopesData(res.data);
      }
    } catch (err) {
      console.error('Failed to load envelope sheet:', err);
    } finally {
      setIsLoadingEnvelopes(false);
    }
  };

  const handleOpenTeamAudit = async (teamIdentifier: string) => {
    setIsLoadingTeamAudit(true);
    setIsTeamAuditOpen(true);
    try {
      const res = await backendApiService.getTeamAuditDetails(teamIdentifier);
      if (res.data) {
        setSelectedTeamAudit(res.data);
      }
    } catch (err) {
      console.error('Failed to load team audit:', err);
    } finally {
      setIsLoadingTeamAudit(false);
    }
  };

  // Load round 1 data & subscribe
  const loadRound1 = async () => {
    try {
      const r1Res = await eventService.getRound1Data();
      setData(r1Res);
      fetchCheckins();

      setConfigPenaltyMinutes(Math.round(r1Res.config.penaltyPerHintSeconds / 60));
      setConfigCheckpointNames([...r1Res.config.checkpointNames]);
      setConfigHiddenCodeRecovered(r1Res.config.hiddenCodeRecovered);
      setConfigHiddenCodeTeamId(r1Res.config.hiddenCodeRecoveredByTeamId || '');
      setConfigHiddenCodeNotes(r1Res.config.hiddenCodeNotes || '');

      if (selectedRecord) {
        const updated = r1Res.records.find((r) => r.teamId === selectedRecord.teamId);
        if (updated) setSelectedRecord(updated);
      }
    } catch (err) {
      console.error('Failed to load Round 1 data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Live timer for started round
  useEffect(() => {
    if (!data?.config?.startedAt) {
      setElapsedDisplay('00:00:00');
      return;
    }

    const startMs = new Date(data.config.startedAt).getTime();
    const updateElapsed = () => {
      const nowMs = Date.now();
      const diffSec = Math.max(0, Math.floor((nowMs - startMs) / 1000));
      const hours = Math.floor(diffSec / 3600);
      const minutes = Math.floor((diffSec % 3600) / 60);
      const seconds = diffSec % 60;
      setElapsedDisplay(
        `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
      );
    };

    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);
    return () => clearInterval(interval);
  }, [data?.config?.startedAt]);

  const handleStartRound1 = async () => {
    setIsStartingRound(true);
    try {
      const res = await backendApiService.startRound1();
      if (res.data) {
        await loadRound1();
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.response?.data?.message || err.message || 'Failed to start Round 1';
      alert(msg);
    } finally {
      setIsStartingRound(false);
    }
  };

  // Auto-polling every 6 seconds to keep live data fresh
  useEffect(() => {
    loadRound1();
    loadAllocations();

    const unsubscribe = eventService.subscribe(() => {
      loadRound1();
    });

    const pollInterval = setInterval(() => {
      loadRound1();
      loadAllocations();
    }, 6000);

    return () => {
      unsubscribe();
      clearInterval(pollInterval);
    };
  }, []);

  // Update volunteer view when tab or filters change
  useEffect(() => {
    if (viewMode === 'volunteer') {
      loadVolunteerData(volunteerCp, volunteerLoc);
    }
  }, [viewMode, volunteerCp, volunteerLoc, loadVolunteerData]);

  // Update envelopes view when tab changes
  useEffect(() => {
    if (viewMode === 'envelopes') {
      loadEnvelopesData();
    }
  }, [viewMode]);

  // Filter & Sort for Leaderboard
  const filteredAndSortedRecords = useMemo(() => {
    if (!data) return [];

    return data.records
      .filter((rec) => {
        const query = searchQuery.toLowerCase().trim();
        const matchesSearch =
          !query ||
          rec.teamName.toLowerCase().includes(query) ||
          formatTeamNumber(rec.teamNumber).toLowerCase().includes(query);

        let matchesStatus = true;
        if (filterStatus === 'qualified') {
          matchesStatus =
            rec.qualificationStatus === 'Provisional Qualified' ||
            rec.qualificationStatus === 'Finalized Qualified';
        } else if (filterStatus === 'eliminated') {
          matchesStatus =
            rec.qualificationStatus === 'Provisional Eliminated' ||
            rec.qualificationStatus === 'Finalized Eliminated';
        } else if (filterStatus === 'incomplete') {
          matchesStatus = rec.qualificationStatus === 'Incomplete';
        } else if (filterStatus === 'tied') {
          matchesStatus = !rec.tieRequiresReview;
        }

        let matchesProgress = true;
        if (filterProgress === 'completed') {
          matchesProgress = rec.isComplete;
        } else if (filterProgress === 'inProgress') {
          const anyStarted = rec.miniRounds.some((mr) => mr.status === 'In Progress' || mr.status === 'Completed');
          matchesProgress = anyStarted && !rec.isComplete;
        } else if (filterProgress === 'notStarted') {
          matchesProgress = rec.miniRounds.every((mr) => mr.status === 'Not Started');
        }

        return matchesSearch && matchesStatus && matchesProgress;
      })
      .sort((a, b) => {
        let cmp = 0;
        if (sortField === 'rank') {
          const rA = a.rank ?? 999;
          const rB = b.rank ?? 999;
          cmp = rA - rB;
        } else if (sortField === 'teamNumber') {
          cmp = a.teamNumber - b.teamNumber;
        } else if (sortField === 'name') {
          cmp = a.teamName.localeCompare(b.teamName);
        } else if (sortField === 'adjustedTotalSeconds') {
          const tA = a.adjustedTotalSeconds ?? 999999;
          const tB = b.adjustedTotalSeconds ?? 999999;
          cmp = tA - tB;
        } else if (sortField === 'rawTotalSeconds') {
          const tA = a.rawTotalSeconds ?? 999999;
          const tB = b.rawTotalSeconds ?? 999999;
          cmp = tA - tB;
        }
        return sortOrder === 'asc' ? cmp : -cmp;
      });
  }, [data, searchQuery, filterStatus, filterProgress, sortField, sortOrder]);

  const paginatedRecords = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredAndSortedRecords.slice(start, start + pageSize);
  }, [filteredAndSortedRecords, currentPage, pageSize]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const loadMiniRoundForm = (rec: TeamRound1Record | null, mrNum: 1 | 2 | 3) => {
    if (!rec) return;
    const mr = rec.miniRounds[mrNum - 1];
    setTimingStartTime(mr.startTime || '');
    setTimingEndTime(mr.completionTime || '');
    setTimingHints(mr.hintsUsed || 0);
    setTimingPhonePenalties(mr.phonePenaltiesCount || 0);
    setTimingSeparationPenalties(mr.separationPenaltiesCount || 0);
    setTimingClueTampering(Boolean(mr.clueTamperingDeduction && mr.clueTamperingDeduction > 0));
    setTimingIsDisqualified(mr.isDisqualified || false);
    setTimingDisqualificationReason(mr.disqualificationReason || '');
    setTimingCheckpoints(
      mr.checkpoints && mr.checkpoints.length > 0
        ? mr.checkpoints.map((c) => c.arrivalTime || '')
        : ['', '']
    );
    setTimingError(null);
  };

  const handleOpenManageTiming = (rec: TeamRound1Record, initialTab: 1 | 2 | 3 = 1) => {
    setSelectedRecord(rec);
    setActiveMiniRoundTab(initialTab);
    loadMiniRoundForm(rec, initialTab);
    setIsManageTimingOpen(true);
  };

  const handleTabChange = (tab: 1 | 2 | 3) => {
    setActiveMiniRoundTab(tab);
    loadMiniRoundForm(selectedRecord, tab);
  };

  const handleSaveMiniRoundTiming = async () => {
    if (!selectedRecord) return;
    setTimingError(null);

    if (timingStartTime && timingEndTime) {
      const s = new Date(timingStartTime).getTime();
      const e = new Date(timingEndTime).getTime();
      if (e < s) {
        setTimingError('Completion time cannot be earlier than start time.');
        return;
      }
    }

    if (timingIsDisqualified && !timingDisqualificationReason.trim()) {
      setTimingError('Please provide a reason for disqualification.');
      return;
    }

    setIsSubmitting(true);
    try {
      const input: UpdateMiniRoundTimingInput = {
        miniRoundNumber: activeMiniRoundTab,
        startTime: timingStartTime || null,
        completionTime: timingEndTime || null,
        hintsUsed: Number(timingHints),
        phonePenaltiesCount: Number(timingPhonePenalties),
        separationPenaltiesCount: Number(timingSeparationPenalties),
        clueTamperingDeduction: timingClueTampering ? 20 : 0,
        isDisqualified: timingIsDisqualified,
        disqualificationReason: timingIsDisqualified ? timingDisqualificationReason : null,
        checkpoints: timingCheckpoints.map((at, i) => ({
          checkpointId: `cp-${activeMiniRoundTab}-${i + 1}`,
          name: i === 0 ? 'Entry Clue' : 'Exit Clue',
          arrivalTime: at || null,
        })),
      };

      await eventService.updateRound1MiniRoundTiming(selectedRecord.teamId, input);
      const r1Res = await eventService.getRound1Data();
      setData(r1Res);

      const rec = r1Res.records.find((r) => r.teamId === selectedRecord.teamId);
      if (rec) {
        setSelectedRecord(rec);
        loadMiniRoundForm(rec, activeMiniRoundTab);
      }
      setIsManageTimingOpen(false);
    } catch (err: unknown) {
      setTimingError((err as Error).message || 'Failed to save timing record');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveConfig = async () => {
    setIsSubmitting(true);
    try {
      await eventService.updateRound1Config({
        penaltyPerHintSeconds: configPenaltyMinutes * 60,
        checkpointNames: configCheckpointNames,
        hiddenCodeRecovered: configHiddenCodeRecovered,
        hiddenCodeRecoveredByTeamId: configHiddenCodeTeamId || null,
        hiddenCodeNotes: configHiddenCodeNotes,
      });
      setIsConfigOpen(false);
      await loadRound1();
    } catch (err: unknown) {
      alert((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFinalizeRound1 = async () => {
    setIsSubmitting(true);
    try {
      await eventService.finalizeRound1();
      setIsFinalizeConfirmOpen(false);
      await loadRound1();
    } catch (err: unknown) {
      alert((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetTimings = async () => {
    if (confirm('Reset all Round 1 timings back to initial state? Team rosters and participant records will NOT be erased.')) {
      await eventService.resetRound1Timings();
      await loadRound1();
    }
  };

  const handleSimulateComplete = async () => {
    if (confirm('Simulate complete timing for all 32 squads? This sets valid completion times so you can test full 16-team qualification and finalization.')) {
      await eventService.simulateCompleteFieldRound1();
      await loadRound1();
    }
  };

  const getStatusBadge = (status: TeamRound1Record['qualificationStatus'], tieReview?: boolean) => {
    if (tieReview) {
      return (
        <Badge variant="warning" size="sm" dot>
          Tie Review Needed
        </Badge>
      );
    }
    switch (status) {
      case 'Provisional Qualified':
      case 'Finalized Qualified':
        return (
          <Badge variant="success" size="sm" dot>
            Top 16 (Safe)
          </Badge>
        );
      case 'Provisional Eliminated':
      case 'Finalized Eliminated':
        return (
          <Badge variant="danger" size="sm">
            Elimination
          </Badge>
        );
      case 'Disqualified':
        return (
          <Badge variant="danger" size="sm">
            Disqualified
          </Badge>
        );
      case 'Incomplete':
      default:
        return (
          <Badge variant="neutral" size="sm">
            Incomplete
          </Badge>
        );
    }
  };

  // Summary Metrics calculations
  const stats = useMemo(() => {
    if (!data) return { participating: 0, completed: 0, started: 0, qualified: 0, eliminated: 0, awaiting: 0 };
    const participating = data.records.length;
    const completed = data.records.filter((r) => r.isComplete).length;
    const started = data.records.filter((r) => r.miniRounds.some((mr) => mr.status !== 'Not Started')).length;
    const qualified = data.records.filter(
      (r) => r.qualificationStatus === 'Provisional Qualified' || r.qualificationStatus === 'Finalized Qualified'
    ).length;
    const eliminated = data.records.filter(
      (r) => r.qualificationStatus === 'Provisional Eliminated' || r.qualificationStatus === 'Finalized Eliminated'
    ).length;
    const awaiting = participating - completed;
    return { participating, completed, started, qualified, eliminated, awaiting };
  }, [data]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Round 1: The ODDyssey Protocol"
        subtitle="Official 32-Team Sequential Checkpoint Navigation · 8 Physical Stations · 4 Envelope Sets · Authoritative Server Timing"
        badge={
          data?.config.isFinalized ? (
            <Badge variant="success" size="sm" dot>
              Finalized &amp; Official
            </Badge>
          ) : data?.config.isStarted || data?.config.startedAt ? (
            <Badge variant="success" size="sm" dot>
              LIVE: STARTED AT {new Date(data.config.startedAt!).toISOString().substring(11, 19)} UTC
            </Badge>
          ) : (
            <Badge variant="warning" size="sm" dot>
              NOT STARTED
            </Badge>
          )
        }
        actions={
          <>
            {!data?.config.isFinalized && (
              <Button
                variant={data?.config.isStarted || data?.config.startedAt ? "outline" : "primary"}
                size="sm"
                onClick={handleStartRound1}
                disabled={Boolean(data?.config.isStarted || data?.config.startedAt || isStartingRound)}
                isLoading={isStartingRound}
                leftIcon={<Clock className="w-3.5 h-3.5 text-cyan-400" />}
                title={data?.config.isStarted || data?.config.startedAt ? "Round 1 has already been started." : "Start Round 1 officially"}
              >
                {data?.config.isStarted || data?.config.startedAt ? "ROUND 1 STARTED" : "[ START ROUND 1 ]"}
              </Button>
            )}

            <Link
              to="/round1/scan"
              target="_blank"
              className="text-xs font-mono text-cyan-400 hover:text-cyan-300 px-3 py-1.5 rounded-xl border border-cyan-500/30 bg-cyan-950/40 flex items-center gap-1.5 transition-colors"
            >
              <QrCode className="w-3.5 h-3.5" />
              <span>Participant Portal ↗</span>
            </Link>

            <Link
              to="/protocol/print-qrs"
              target="_blank"
              className="text-xs font-mono text-emerald-400 hover:text-emerald-300 px-3 py-1.5 rounded-xl border border-emerald-500/30 bg-emerald-950/40 flex items-center gap-1.5 transition-colors"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Printable QR Sheet ↗</span>
            </Link>

            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                fetchCheckins();
                setIsCheckinsModalOpen(true);
              }}
              leftIcon={<Radio className="w-3.5 h-3.5 text-cyan-400" />}
            >
              QR Scans ({checkinsFeed.length})
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsConfigOpen(true)}
              leftIcon={<Settings className="w-3.5 h-3.5" />}
            >
              Settings &amp; Rules
            </Button>

            {!data?.config.isFinalized && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSimulateComplete}
                  leftIcon={<Sparkles className="w-3.5 h-3.5 text-purple-600" />}
                  title="Fill all 32 teams with completed times to test qualification"
                >
                  Simulate Field
                </Button>

                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setIsFinalizeConfirmOpen(true)}
                  leftIcon={<Trophy className="w-3.5 h-3.5" />}
                  disabled={!data?.engine.canFinalize}
                >
                  Finalize Top 16
                </Button>
              </>
            )}

            <Button
              variant="ghost"
              size="sm"
              onClick={handleResetTimings}
              leftIcon={<RotateCcw className="w-3.5 h-3.5 text-slate-400" />}
              title="Reset timing records"
            >
              Reset Timings
            </Button>
          </>
        }
      />

      {/* Official Round 1 Timing Status Banner */}
      <div className={`p-4 rounded-2xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 font-mono ${
        data?.config.startedAt || data?.config.isStarted
          ? 'bg-[#041d2d]/90 border-cyan-500/40 text-cyan-200 shadow-[0_0_25px_rgba(6,182,212,0.15)]'
          : 'bg-[#181206]/90 border-amber-500/40 text-amber-200'
      }`}>
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-lg border ${
            data?.config.startedAt || data?.config.isStarted
              ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300'
              : 'bg-amber-500/20 border-amber-400 text-amber-300'
          }`}>
            <Clock className={`w-5 h-5 ${data?.config.startedAt || data?.config.isStarted ? 'animate-pulse text-cyan-300' : 'text-amber-400'}`} />
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
              ROUND 1 — THE ODDYSSEY PROTOCOL
            </div>
            <div className="text-sm font-bold text-white flex items-center gap-2">
              <span>STATUS:</span>
              <span className={data?.config.startedAt || data?.config.isStarted ? 'text-cyan-300' : 'text-amber-400'}>
                {data?.config.startedAt || data?.config.isStarted ? 'LIVE COMPETITION IN PROGRESS' : 'ROUND NOT STARTED — WAITING FOR ORGANIZER SIGNAL'}
              </span>
            </div>
            {data?.config.startedAt && (
              <div className="text-xs text-slate-300 mt-0.5">
                ROUND STARTED:{' '}
                <strong className="text-white">
                  {new Date(data.config.startedAt).toLocaleTimeString()} ({new Date(data.config.startedAt).toISOString().substring(11, 19)} UTC)
                </strong>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">
              GLOBAL ELAPSED
            </div>
            <div className={`text-2xl font-black font-mono tracking-wider ${
              data?.config.startedAt || data?.config.isStarted ? 'text-cyan-300 animate-pulse' : 'text-slate-500'
            }`}>
              {elapsedDisplay}
            </div>
          </div>

          {!data?.config.isFinalized && !data?.config.startedAt && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleStartRound1}
              disabled={isStartingRound}
              isLoading={isStartingRound}
              leftIcon={<Clock className="w-4 h-4" />}
            >
              [ START ROUND 1 ]
            </Button>
          )}
        </div>
      </div>

      {/* Dynamic Overview Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <SummaryMetric
          label="Field Size"
          value={stats.participating}
          subtext="32 Target Roster"
          icon={Users}
          variant="blue"
        />

        <SummaryMetric
          label="In Motion"
          value={stats.started}
          subtext={`${stats.participating - stats.started} Pending Station`}
          icon={Clock}
          variant="amber"
        />

        <SummaryMetric
          label="All 3 Done"
          value={stats.completed}
          subtext={`${Math.round((stats.completed / Math.max(1, stats.participating)) * 100)}% Completed`}
          icon={CheckCircle2}
          variant="emerald"
        />

        <SummaryMetric
          label="Awaiting"
          value={stats.awaiting}
          subtext="In Progress / Incomplete"
          icon={AlertTriangle}
          variant="amber"
        />

        <SummaryMetric
          label="Top 16 Cutoff"
          value={stats.qualified}
          subtext={data?.config.isFinalized ? 'Advanced to Cabo' : 'Eligible to Advance'}
          icon={Trophy}
          variant="purple"
        />

        <SummaryMetric
          label="Elimination"
          value={stats.eliminated}
          subtext="Slowest 16 Teams"
          icon={ShieldAlert}
          variant="rose"
        />
      </div>

      {/* Organizer Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-cyan-500/20 pb-2">
        <button
          type="button"
          onClick={() => setViewMode('leaderboard')}
          className={`px-4 py-2.5 rounded-xl text-xs font-mono font-bold flex items-center gap-2 transition-all ${
            viewMode === 'leaderboard'
              ? 'bg-cyan-500 text-slate-950 shadow-[0_0_15px_rgba(6,182,212,0.4)]'
              : 'bg-slate-900/60 text-slate-300 hover:text-white border border-slate-800'
          }`}
        >
          <Trophy className="w-4 h-4" />
          <span>Live Leaderboard</span>
        </button>

        <button
          type="button"
          onClick={() => setViewMode('allocations')}
          className={`px-4 py-2.5 rounded-xl text-xs font-mono font-bold flex items-center gap-2 transition-all ${
            viewMode === 'allocations'
              ? 'bg-cyan-500 text-slate-950 shadow-[0_0_15px_rgba(6,182,212,0.4)]'
              : 'bg-slate-900/60 text-slate-300 hover:text-white border border-slate-800'
          }`}
        >
          <Compass className="w-4 h-4" />
          <span>Route &amp; Set Allocation Matrix</span>
          {allocationsData?.is_valid && (
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
          )}
        </button>

        <button
          type="button"
          onClick={() => setViewMode('volunteer')}
          className={`px-4 py-2.5 rounded-xl text-xs font-mono font-bold flex items-center gap-2 transition-all ${
            viewMode === 'volunteer'
              ? 'bg-cyan-500 text-slate-950 shadow-[0_0_15px_rgba(6,182,212,0.4)]'
              : 'bg-slate-900/60 text-slate-300 hover:text-white border border-slate-800'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Location Volunteer View</span>
        </button>

        <button
          type="button"
          onClick={() => setViewMode('envelopes')}
          className={`px-4 py-2.5 rounded-xl text-xs font-mono font-bold flex items-center gap-2 transition-all ${
            viewMode === 'envelopes'
              ? 'bg-cyan-500 text-slate-950 shadow-[0_0_15px_rgba(6,182,212,0.4)]'
              : 'bg-slate-900/60 text-slate-300 hover:text-white border border-slate-800'
          }`}
        >
          <Printer className="w-4 h-4" />
          <span>Envelope Preparation Sheet</span>
        </button>
      </div>

      {/* ======================================================== */}
      {/* VIEW 1: LIVE LEADERBOARD                                */}
      {/* ======================================================== */}
      {viewMode === 'leaderboard' && (
        <div className="space-y-4">
          {/* Live Physical QR Checkpoints Telemetry Feed */}
          <Card className="border-cyan-500/30 bg-[#061224]/70 backdrop-blur-md">
            <CardHeader className="py-3 px-4 border-b border-cyan-500/20 flex flex-row items-center justify-between">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-cyan-400 animate-pulse" />
                <h3 className="font-mono font-bold text-xs uppercase text-cyan-200">
                  Live Physical QR Checkpoint Scans
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 border border-cyan-500/30 text-cyan-300">
                  {checkinsFeed.length} Recorded
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => fetchCheckins()}
                  leftIcon={<RotateCcw className={`w-3.5 h-3.5 ${isLoadingCheckins ? 'animate-spin text-cyan-400' : 'text-slate-400'}`} />}
                >
                  Refresh
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    fetchCheckins();
                    setIsCheckinsModalOpen(true);
                  }}
                >
                  View Full Log ({checkinsFeed.length})
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-3">
              {checkinsFeed.length === 0 ? (
                <div className="py-3 text-center text-xs text-slate-400 font-mono">
                  No physical QR checkpoint check-ins recorded yet. When squads reach and scan physical stations, their server-verified timestamps will appear here in real time.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  {checkinsFeed.slice(0, 3).map((chk) => (
                    <div
                      key={chk.id}
                      className={`p-2.5 rounded-xl border text-xs font-mono space-y-1 ${
                        chk.is_duplicate
                          ? 'border-amber-500/30 bg-amber-950/20 text-amber-200'
                          : 'border-cyan-500/30 bg-[#030712]/80 text-cyan-100'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white truncate max-w-[150px]">{chk.team_name}</span>
                        <span className="px-1.5 py-0.2 rounded text-[10px] bg-black/40 border border-current font-semibold">
                          Gate 0{chk.gate_number}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span>{new Date(chk.scanned_at).toLocaleTimeString()} ({new Date(chk.scanned_at).toISOString().substring(11, 19)} UTC)</span>
                        <span className={chk.is_duplicate ? 'text-amber-400' : 'text-emerald-400 font-semibold'}>
                          {chk.status} {chk.attempt_number > 1 ? `(#${chk.attempt_number})` : ''}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Filter and Search Bar */}
          <SearchFilterToolbar
            searchQuery={searchQuery}
            onSearchChange={(val) => {
              setSearchQuery(val);
              setCurrentPage(1);
            }}
            searchPlaceholder="Search squad name or team ID (1014)..."
            filters={[
              {
                id: 'status',
                label: 'Standings',
                value: filterStatus,
                onChange: (val) => {
                  setFilterStatus(val);
                  setCurrentPage(1);
                },
                options: [
                  { label: 'All Standings', value: 'all' },
                  { label: 'Top 16 (Advancing)', value: 'qualified' },
                  { label: 'Ranks 17-32 (Elimination)', value: 'eliminated' },
                  { label: 'Incomplete Only', value: 'incomplete' },
                  { label: 'Tied Teams Only', value: 'tied' },
                ],
              },
              {
                id: 'progress',
                label: 'Progress',
                value: filterProgress,
                onChange: (val) => {
                  setFilterProgress(val);
                  setCurrentPage(1);
                },
                options: [
                  { label: 'All Progress States', value: 'all' },
                  { label: 'All 3 Gates Done', value: 'completed' },
                  { label: 'In Progress', value: 'inProgress' },
                  { label: 'Not Started', value: 'notStarted' },
                ],
              },
            ]}
            activeCount={
              (filterStatus !== 'all' ? 1 : 0) + (filterProgress !== 'all' ? 1 : 0) + (searchQuery ? 1 : 0)
            }
            onClearAll={() => {
              setSearchQuery('');
              setFilterStatus('all');
              setFilterProgress('all');
            }}
          />

          {/* Main Leaderboard Table */}
          <Card>
            <CardHeader
              title="The ODDyssey Protocol — Official Live Standings"
              subtitle={`Showing ${paginatedRecords.length} of ${filteredAndSortedRecords.length} squads · Top 16 qualify for Round 2 (Cabo)`}
              action={
                data?.engine.top16CutoffTime ? (
                  <span className="text-xs font-mono bg-cyan-950/50 text-cyan-300 border border-cyan-500/30 px-2.5 py-1 rounded-xl shadow-[0_0_10px_rgba(6,182,212,0.2)]">
                    16th Cutoff: <strong className="text-white">{formatDuration(data.engine.top16CutoffTime)}</strong>
                  </span>
                ) : null
              }
            />
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-[#030712]/90 border-b border-cyan-500/20 text-[11px] font-mono uppercase tracking-wider font-bold text-cyan-400/80">
                      <th
                        className="py-3.5 px-3 w-14 text-center cursor-pointer hover:text-cyan-300 transition-colors select-none"
                        onClick={() => handleSort('rank')}
                      >
                        <div className="flex items-center justify-center gap-1">
                          <span>Rank</span>
                          <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                        </div>
                      </th>
                      <th className="py-3.5 px-3">Team / Squad</th>
                      <th className="py-3.5 px-2.5 text-center">Checkpoint 1</th>
                      <th className="py-3.5 px-2.5 text-center">Checkpoint 2</th>
                      <th className="py-3.5 px-2.5 text-center">Checkpoint 3</th>
                      <th
                        className="py-3.5 px-3 cursor-pointer hover:text-cyan-300 transition-colors select-none text-right"
                        onClick={() => handleSort('adjustedTotalSeconds')}
                      >
                        <div className="flex items-center justify-end gap-1">
                          <span>Total Time</span>
                          <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                        </div>
                      </th>
                      <th className="py-3.5 px-3 text-center">Status</th>
                      <th className="py-3.5 px-3 text-center">Qualification</th>
                      <th className="py-3.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-cyan-500/10 text-xs text-slate-300">
                    {isLoading ? (
                      Array.from({ length: 8 }).map((_, i) => <TableRowSkeleton key={i} cols={9} />)
                    ) : paginatedRecords.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="py-12">
                          <EmptyState
                            icon={Compass}
                            title="No Squad Timing Found"
                            description="No records match your filter criteria."
                            action={{
                              label: 'Clear Filters',
                              onClick: () => {
                                setSearchQuery('');
                                setFilterStatus('all');
                                setFilterProgress('all');
                              },
                            }}
                          />
                        </td>
                      </tr>
                    ) : (
                      paginatedRecords.map((rec) => {
                        const rankNum = rec.rank ?? null;
                        const isCutoffLine = rankNum === 16;
                        const isBeyondCutoff = rankNum !== null && rankNum > 16;
                        const alloc = allocationsData?.allocations?.find(
                          (a) => a.team_identifier === rec.teamNumber.toString() || a.team_id === rec.teamId
                        );

                        const mr1 = rec.miniRounds[0];
                        const mr2 = rec.miniRounds[1];
                        const mr3 = rec.miniRounds[2];

                        return (
                          <tr
                            key={rec.teamId}
                            className={`hover:bg-cyan-500/[0.05] transition-colors ${
                              isCutoffLine ? 'border-b-2 border-cyan-400 bg-cyan-950/20' : ''
                            } ${isBeyondCutoff ? 'opacity-85' : ''} ${rec.isDisqualified ? 'bg-red-950/20' : ''}`}
                          >
                            {/* Rank */}
                            <td className="py-3 px-3 text-center font-mono font-bold">
                              {rec.isDisqualified ? (
                                <span className="text-rose-400 font-mono font-bold">DQ</span>
                              ) : rankNum ? (
                                <span
                                  className={
                                    rankNum <= 3
                                      ? 'text-amber-300 font-black text-sm'
                                      : rankNum <= 16
                                      ? 'text-emerald-400 font-bold'
                                      : 'text-slate-400'
                                  }
                                >
                                  #{rankNum}
                                </span>
                              ) : (
                                <span className="text-slate-600">—</span>
                              )}
                            </td>

                            {/* Team / Squad */}
                            <td className="py-3 px-3">
                              <div className="font-display font-bold text-white text-xs">{rec.teamName}</div>
                              <div className="text-[11px] font-mono text-cyan-400">
                                {formatTeamNumber(rec.teamNumber)}
                              </div>
                            </td>

                            {/* Checkpoint 1 (Location, Set, Split) */}
                            <td className="py-3 px-2.5 text-center font-mono text-[11px]">
                              <div className="flex flex-col items-center gap-0.5">
                                <div className="flex items-center gap-1">
                                  <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                                    L{alloc?.cp1_location ?? 1}
                                  </span>
                                  <span className={`px-1.5 py-0.2 rounded font-bold border ${getSetBadgeClass(alloc?.cp1_set ?? 'SET A')}`}>
                                    {alloc?.cp1_set ?? 'SET A'}
                                  </span>
                                </div>
                                <span className={mr1?.status === 'Completed' ? 'text-emerald-400 font-semibold' : 'text-slate-500'}>
                                  {mr1?.status === 'Completed' ? formatDuration(mr1.durationSeconds) : mr1?.status}
                                </span>
                              </div>
                            </td>

                            {/* Checkpoint 2 (Location, Set, Split) */}
                            <td className="py-3 px-2.5 text-center font-mono text-[11px]">
                              <div className="flex flex-col items-center gap-0.5">
                                <div className="flex items-center gap-1">
                                  <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                                    L{alloc?.cp2_location ?? 2}
                                  </span>
                                  <span className={`px-1.5 py-0.2 rounded font-bold border ${getSetBadgeClass(alloc?.cp2_set ?? 'SET B')}`}>
                                    {alloc?.cp2_set ?? 'SET B'}
                                  </span>
                                </div>
                                <span className={mr2?.status === 'Completed' ? 'text-emerald-400 font-semibold' : 'text-slate-500'}>
                                  {mr2?.status === 'Completed' ? formatDuration(mr2.durationSeconds) : mr2?.status}
                                </span>
                              </div>
                            </td>

                            {/* Checkpoint 3 (Location, Set, Split) */}
                            <td className="py-3 px-2.5 text-center font-mono text-[11px]">
                              <div className="flex flex-col items-center gap-0.5">
                                <div className="flex items-center gap-1">
                                  <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                                    L{alloc?.cp3_location ?? 3}
                                  </span>
                                  <span className={`px-1.5 py-0.2 rounded font-bold border ${getSetBadgeClass(alloc?.cp3_set ?? 'SET C')}`}>
                                    {alloc?.cp3_set ?? 'SET C'}
                                  </span>
                                </div>
                                <span className={mr3?.status === 'Completed' ? 'text-emerald-400 font-semibold' : 'text-slate-500'}>
                                  {mr3?.status === 'Completed' ? formatDuration(mr3.durationSeconds) : mr3?.status}
                                </span>
                              </div>
                            </td>

                            {/* Total Elapsed Time */}
                            <td className="py-3 px-3 text-right font-mono font-bold">
                              {rec.adjustedTotalSeconds !== null && rec.adjustedTotalSeconds !== undefined ? (
                                <span className="text-white text-xs">{formatDuration(rec.adjustedTotalSeconds)}</span>
                              ) : (
                                <span className="text-slate-500">In Progress</span>
                              )}
                              {rec.totalPenaltySeconds > 0 && (
                                <span className="block text-[10px] text-rose-400 font-normal">
                                  +{Math.round(rec.totalPenaltySeconds / 60)}m pen
                                </span>
                              )}
                            </td>

                            {/* Status */}
                            <td className="py-3 px-3 text-center">
                              {rec.isDisqualified ? (
                                <Badge variant="danger" size="sm">DQ</Badge>
                              ) : rec.isComplete ? (
                                <Badge variant="success" size="sm">Completed</Badge>
                              ) : (
                                <Badge variant="warning" size="sm">In Progress</Badge>
                              )}
                            </td>

                            {/* Qualification */}
                            <td className="py-3 px-3 text-center">
                              {getStatusBadge(rec.qualificationStatus, rec.tieRequiresReview)}
                            </td>

                            {/* Actions */}
                            <td className="py-3 px-3 text-right">
                              <div className="flex items-center justify-end gap-1.5">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleOpenTeamAudit(rec.teamNumber.toString())}
                                  leftIcon={<Eye className="w-3.5 h-3.5 text-cyan-400" />}
                                >
                                  Audit
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleOpenManageTiming(rec, 1)}
                                >
                                  Edit
                                </Button>
                              </div>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              <Pagination
                currentPage={currentPage}
                totalItems={filteredAndSortedRecords.length}
                pageSize={pageSize}
                onPageChange={setCurrentPage}
              />
            </CardContent>
          </Card>
        </div>
      )}

      {/* ======================================================== */}
      {/* VIEW 2: ROUTE & SET ALLOCATION MATRIX                   */}
      {/* ======================================================== */}
      {viewMode === 'allocations' && (
        <div className="space-y-4">
          {/* Validation Status Banner */}
          <div className="p-4 sm:p-5 rounded-3xl bg-slate-900 border border-cyan-500/30 space-y-3">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-2xl flex items-center justify-center ${
                  allocationsData?.is_valid ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-400/40' : 'bg-rose-500/20 text-rose-400 border border-rose-400/40'
                }`}>
                  {allocationsData?.is_valid ? <CheckCircle2 className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wide">
                    {allocationsData?.is_valid ? 'ALLOCATION VALID ✅ ALL 8 CONSTRAINTS SATISFIED' : 'ALLOCATION CONFLICT DETECTED'}
                  </h3>
                  <p className="text-xs text-slate-400 font-mono">
                    Zero-conflict deterministic distribution for 32 teams across 8 physical locations.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsRegenerateModalOpen(true)}
                  leftIcon={<RotateCcw className="w-3.5 h-3.5 text-amber-400" />}
                >
                  Regenerate Matrix
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => window.print()}
                  leftIcon={<Printer className="w-3.5 h-3.5" />}
                >
                  Print Matrix
                </Button>
              </div>
            </div>

            {/* 8 Constraints Status Badges */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800 text-[11px] font-mono">
              <div className="flex items-center gap-1.5 text-emerald-400">
                <Check className="w-3.5 h-3.5 shrink-0" />
                <span>1. 32 Teams (1001-1032)</span>
              </div>
              <div className="flex items-center gap-1.5 text-emerald-400">
                <Check className="w-3.5 h-3.5 shrink-0" />
                <span>2. 8 Locations (No 3/4)</span>
              </div>
              <div className="flex items-center gap-1.5 text-emerald-400">
                <Check className="w-3.5 h-3.5 shrink-0" />
                <span>3. 3 Checkpoints per squad</span>
              </div>
              <div className="flex items-center gap-1.5 text-emerald-400">
                <Check className="w-3.5 h-3.5 shrink-0" />
                <span>4. Max 4 teams per station</span>
              </div>
              <div className="flex items-center gap-1.5 text-emerald-400">
                <Check className="w-3.5 h-3.5 shrink-0" />
                <span>5. 4 Sets (A, B, C, D)</span>
              </div>
              <div className="flex items-center gap-1.5 text-emerald-400">
                <Check className="w-3.5 h-3.5 shrink-0" />
                <span>6. 3 Distinct sets per team</span>
              </div>
              <div className="flex items-center gap-1.5 text-emerald-400">
                <Check className="w-3.5 h-3.5 shrink-0" />
                <span>7. All sets at each station</span>
              </div>
              <div className="flex items-center gap-1.5 text-emerald-400">
                <Check className="w-3.5 h-3.5 shrink-0" />
                <span>8. 8 Physical Station QRs</span>
              </div>
            </div>

            {/* Organizer Note on Set A Gate 2 Q3 */}
            <div className="p-3 rounded-2xl bg-cyan-950/40 border border-cyan-500/30 text-xs font-mono text-cyan-200">
              <strong className="text-cyan-300 uppercase block mb-0.5">Authoritative Organizer Notice:</strong>
              {allocationsData?.summary?.organizer_note ||
                "Set A Gate 2 Q3 accepts both '42' (coordinate logic) and 'ENIGMA' (fragment riddle) to ensure full tournament operational compatibility."}
            </div>
          </div>

          {/* Full 32-Team Schedule Table */}
          <Card>
            <CardHeader
              title="Official 32-Team Allocation & Schedule Table"
              subtitle="Sequential station paths and envelope set assignments for all registered squads."
            />
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs font-mono">
                  <thead>
                    <tr className="bg-[#030712]/90 border-b border-cyan-500/20 text-[11px] uppercase tracking-wider font-bold text-cyan-400/80">
                      <th className="py-3 px-3 w-16 text-center">Team ID</th>
                      <th className="py-3 px-4">Squad Name</th>
                      <th className="py-3 px-3 text-center">R1.1 Station</th>
                      <th className="py-3 px-2 text-center">R1.1 Set</th>
                      <th className="py-3 px-3 text-center">R1.2 Station</th>
                      <th className="py-3 px-2 text-center">R1.2 Set</th>
                      <th className="py-3 px-3 text-center">R1.3 Station</th>
                      <th className="py-3 px-2 text-center">R1.3 Set</th>
                      <th className="py-3 px-3 text-center">Progress</th>
                      <th className="py-3 px-3 text-right">Inspect</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-cyan-500/10 text-slate-300">
                    {isLoadingAllocations ? (
                      Array.from({ length: 8 }).map((_, i) => <TableRowSkeleton key={i} cols={10} />)
                    ) : (
                      allocationsData?.allocations?.map((item) => (
                        <tr key={item.team_identifier} className="hover:bg-cyan-500/[0.05] transition-colors">
                          <td className="py-3 px-3 text-center font-bold text-cyan-300">
                            {item.team_identifier}
                          </td>
                          <td className="py-3 px-4 text-white font-semibold">
                            {item.team_name || `Team ${item.team_identifier}`}
                          </td>

                          {/* R1.1 */}
                          <td className="py-3 px-3 text-center">
                            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700">
                              Loc {item.cp1_location}
                            </span>
                          </td>
                          <td className="py-3 px-2 text-center">
                            <span className={`px-2 py-0.5 rounded font-bold border ${getSetBadgeClass(item.cp1_set)}`}>
                              {item.cp1_set}
                            </span>
                          </td>

                          {/* R1.2 */}
                          <td className="py-3 px-3 text-center">
                            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700">
                              Loc {item.cp2_location}
                            </span>
                          </td>
                          <td className="py-3 px-2 text-center">
                            <span className={`px-2 py-0.5 rounded font-bold border ${getSetBadgeClass(item.cp2_set)}`}>
                              {item.cp2_set}
                            </span>
                          </td>

                          {/* R1.3 */}
                          <td className="py-3 px-3 text-center">
                            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700">
                              Loc {item.cp3_location}
                            </span>
                          </td>
                          <td className="py-3 px-2 text-center">
                            <span className={`px-2 py-0.5 rounded font-bold border ${getSetBadgeClass(item.cp3_set)}`}>
                              {item.cp3_set}
                            </span>
                          </td>

                          {/* Progress */}
                          <td className="py-3 px-3 text-center">
                            {item.cp3_completed ? (
                              <span className="text-emerald-400 font-bold">Done</span>
                            ) : item.cp2_completed ? (
                              <span className="text-cyan-300">CP 3</span>
                            ) : item.cp1_completed ? (
                              <span className="text-cyan-300">CP 2</span>
                            ) : (
                              <span className="text-slate-500">CP 1</span>
                            )}
                          </td>

                          {/* Inspect */}
                          <td className="py-3 px-3 text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleOpenTeamAudit(item.team_identifier)}
                              leftIcon={<Eye className="w-3.5 h-3.5" />}
                            >
                              Audit
                            </Button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ======================================================== */}
      {/* VIEW 3: LOCATION VOLUNTEER VIEW                          */}
      {/* ======================================================== */}
      {viewMode === 'volunteer' && (
        <div className="space-y-4">
          {/* Volunteer Controls */}
          <div className="p-4 sm:p-5 rounded-3xl bg-slate-900 border border-cyan-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              {/* Checkpoint selector */}
              <div>
                <label className="block text-[10px] font-mono text-slate-400 uppercase mb-1">Checkpoint</label>
                <div className="flex bg-slate-950 border border-slate-800 rounded-xl p-1">
                  {([1, 2, 3] as const).map((cp) => (
                    <button
                      key={cp}
                      type="button"
                      onClick={() => setVolunteerCp(cp)}
                      className={`px-3 py-1 rounded-lg text-xs font-mono font-bold transition-all ${
                        volunteerCp === cp
                          ? 'bg-cyan-500 text-slate-950 font-black shadow-sm'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Checkpoint {cp}
                    </button>
                  ))}
                </div>
              </div>

              {/* Location selector */}
              <div>
                <label htmlFor="stationSelect" className="block text-[10px] font-mono text-slate-400 uppercase mb-1">Physical Station</label>
                <select
                  id="stationSelect"
                  value={volunteerLoc}
                  onChange={(e) => setVolunteerLoc(Number(e.target.value))}
                  className="bg-slate-950 border border-slate-800 text-cyan-300 rounded-xl px-3 py-1.5 text-xs font-mono focus:outline-none focus:border-cyan-400"
                >
                  {Object.entries(R1_LOCATIONS_META).map(([locNum, info]) => (
                    <option key={locNum} value={locNum}>
                      Location {locNum} — {info.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <Button
              variant="primary"
              size="sm"
              onClick={() => window.print()}
              leftIcon={<Printer className="w-3.5 h-3.5" />}
            >
              Print Station Sheet
            </Button>
          </div>

          {/* Station Overview & Expected Teams */}
          <Card>
            <CardHeader
              title={`Station Volunteer Sheet · Location ${volunteerLoc} — ${R1_LOCATIONS_META[volunteerLoc]?.name || ''}`}
              subtitle={`Checkpoint ${volunteerCp} Assignments · Hand out the exact Envelope Set assigned to each arriving squad.`}
            />
            <CardContent className="space-y-4">
              {/* Station Clue Card */}
              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 text-xs font-mono space-y-1">
                <div className="text-cyan-400 font-bold uppercase">
                  Station Target: {R1_LOCATIONS_META[volunteerLoc]?.target}
                </div>
                <div className="text-slate-400">
                  Riddle: {R1_LOCATIONS_META[volunteerLoc]?.clue}
                </div>
              </div>

              {/* Expected Teams Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs font-mono">
                  <thead>
                    <tr className="bg-[#030712]/90 border-b border-cyan-500/20 text-[11px] uppercase tracking-wider font-bold text-cyan-400/80">
                      <th className="py-3 px-4 w-24">Team ID</th>
                      <th className="py-3 px-4">Squad Name</th>
                      <th className="py-3 px-4 text-center">Envelope Set To Hand</th>
                      <th className="py-3 px-4 text-center">Station Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-cyan-500/10 text-slate-300">
                    {isLoadingVolunteer ? (
                      Array.from({ length: 4 }).map((_, i) => <TableRowSkeleton key={i} cols={4} />)
                    ) : volunteerData?.expected_teams?.length ? (
                      volunteerData.expected_teams.map((t) => (
                        <tr key={t.team_identifier} className="hover:bg-cyan-500/[0.05] transition-colors">
                          <td className="py-3.5 px-4 font-bold text-cyan-300 text-sm">
                            {t.team_identifier}
                          </td>
                          <td className="py-3.5 px-4 text-white font-semibold">
                            {t.team_name}
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            <span className={`px-3 py-1 rounded-xl text-xs font-black border tracking-wider ${getSetBadgeClass(t.assigned_set)}`}>
                              {t.assigned_set}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            {t.is_completed ? (
                              <span className="px-2.5 py-0.5 rounded-full text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-500/40">
                                Completed
                              </span>
                            ) : (
                              <span className="px-2.5 py-0.5 rounded-full text-[10px] bg-slate-800 text-slate-400">
                                Awaiting Arrival
                              </span>
                            )}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={4} className="py-8 text-center text-slate-500">
                          No squads found for this station and checkpoint.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ======================================================== */}
      {/* VIEW 4: ENVELOPE PREPARATION SHEET                       */}
      {/* ======================================================== */}
      {viewMode === 'envelopes' && (
        <div className="space-y-4">
          <div className="p-4 sm:p-5 rounded-3xl bg-slate-900 border border-cyan-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wide">
                Envelope Packing List (96 Total Envelopes)
              </h3>
              <p className="text-xs text-slate-400 font-mono">
                Prepare 3 labeled envelopes per team (Checkpoint 1, 2, and 3) before tournament kickoff.
              </p>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={() => window.print()}
              leftIcon={<Printer className="w-3.5 h-3.5" />}
            >
              Print Packing Sheet
            </Button>
          </div>

          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs font-mono">
                  <thead>
                    <tr className="bg-[#030712]/90 border-b border-cyan-500/20 text-[11px] uppercase tracking-wider font-bold text-cyan-400/80">
                      <th className="py-3 px-4 w-20 text-center">Team ID</th>
                      <th className="py-3 px-4">Squad Name</th>
                      <th className="py-3 px-3 text-center">CP1 Station &amp; Set</th>
                      <th className="py-3 px-3 text-center">CP2 Station &amp; Set</th>
                      <th className="py-3 px-3 text-center">CP3 Station &amp; Set</th>
                      <th className="py-3 px-3 text-center w-28">Stuffed &amp; Sealed</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-cyan-500/10 text-slate-300">
                    {isLoadingEnvelopes ? (
                      Array.from({ length: 8 }).map((_, i) => <TableRowSkeleton key={i} cols={6} />)
                    ) : envelopesData.length > 0 ? (
                      // Group envelopes by team_identifier
                      Object.values(
                        envelopesData.reduce<Record<string, { team_identifier: string; team_name: string; cp1?: string; cp2?: string; cp3?: string }>>((acc, item) => {
                          if (!acc[item.team_identifier]) {
                            acc[item.team_identifier] = {
                              team_identifier: item.team_identifier,
                              team_name: item.team_name,
                            };
                          }
                          if (item.checkpoint === 1) acc[item.team_identifier].cp1 = `Loc ${item.location} · ${item.question_set}`;
                          if (item.checkpoint === 2) acc[item.team_identifier].cp2 = `Loc ${item.location} · ${item.question_set}`;
                          if (item.checkpoint === 3) acc[item.team_identifier].cp3 = `Loc ${item.location} · ${item.question_set}`;
                          return acc;
                        }, {})
                      ).map((row) => (
                        <tr key={row.team_identifier} className="hover:bg-cyan-500/[0.05] transition-colors">
                          <td className="py-3 px-4 text-center font-bold text-cyan-300">
                            {row.team_identifier}
                          </td>
                          <td className="py-3 px-4 text-white font-semibold">
                            {row.team_name}
                          </td>
                          <td className="py-3 px-3 text-center text-cyan-300 font-bold">
                            {row.cp1 || '—'}
                          </td>
                          <td className="py-3 px-3 text-center text-purple-300 font-bold">
                            {row.cp2 || '—'}
                          </td>
                          <td className="py-3 px-3 text-center text-emerald-300 font-bold">
                            {row.cp3 || '—'}
                          </td>
                          <td className="py-3 px-3 text-center">
                            <input
                              type="checkbox"
                              className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0 cursor-pointer"
                            />
                          </td>
                        </tr>
                      ))
                    ) : (
                      allocationsData?.allocations?.map((alloc) => (
                        <tr key={alloc.team_identifier} className="hover:bg-cyan-500/[0.05] transition-colors">
                          <td className="py-3 px-4 text-center font-bold text-cyan-300">
                            {alloc.team_identifier}
                          </td>
                          <td className="py-3 px-4 text-white font-semibold">
                            {alloc.team_name || `Team ${alloc.team_identifier}`}
                          </td>
                          <td className="py-3 px-3 text-center">
                            <span className="mr-1 text-slate-400">Loc {alloc.cp1_location}</span>
                            <span className={`px-2 py-0.5 rounded font-bold border ${getSetBadgeClass(alloc.cp1_set)}`}>
                              {alloc.cp1_set}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-center">
                            <span className="mr-1 text-slate-400">Loc {alloc.cp2_location}</span>
                            <span className={`px-2 py-0.5 rounded font-bold border ${getSetBadgeClass(alloc.cp2_set)}`}>
                              {alloc.cp2_set}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-center">
                            <span className="mr-1 text-slate-400">Loc {alloc.cp3_location}</span>
                            <span className={`px-2 py-0.5 rounded font-bold border ${getSetBadgeClass(alloc.cp3_set)}`}>
                              {alloc.cp3_set}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-center">
                            <input
                              type="checkbox"
                              className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0 cursor-pointer"
                            />
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ======================================================== */}
      {/* TIMING MANAGEMENT MODAL                                  */}
      {/* ======================================================== */}
      {selectedRecord && (
        <Modal
          isOpen={isManageTimingOpen}
          onClose={() => setIsManageTimingOpen(false)}
          title={
            <div className="flex items-center gap-2">
              <span className="font-mono text-cyan-400">
                {formatTeamNumber(selectedRecord.teamNumber)}
              </span>
              <span>{selectedRecord.teamName}</span>
              <span className="text-xs font-normal text-slate-400">&middot; Mini-Round Timing Console</span>
            </div>
          }
          subtitle={`Current Adjusted Time: ${formatDuration(selectedRecord.adjustedTotalSeconds)} · Rank: ${selectedRecord.rank ? `#${selectedRecord.rank}` : 'Unranked'}`}
          maxWidth="xl"
          footer={
            <div className="flex items-center justify-between w-full">
              <div className="text-[11px] text-slate-500 font-mono">
                {data?.config.isFinalized ? 'Results sealed (Read-only)' : 'Live marshal timing entry'}
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => setIsManageTimingOpen(false)}>
                  Close
                </Button>
                {!data?.config.isFinalized && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleSaveMiniRoundTiming}
                    isLoading={isSubmitting}
                  >
                    Save Mini-Round {activeMiniRoundTab}
                  </Button>
                )}
              </div>
            </div>
          }
        >
          <div className="space-y-4 text-xs font-mono">
            {/* Gate Tabs */}
            <div className="flex border-b border-cyan-500/20">
              {([1, 2, 3] as const).map((num) => {
                const mr = selectedRecord.miniRounds[num - 1];
                const isActive = activeMiniRoundTab === num;
                return (
                  <button
                    key={num}
                    type="button"
                    onClick={() => handleTabChange(num)}
                    className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
                      isActive
                        ? 'border-cyan-400 text-cyan-300 bg-cyan-950/40'
                        : 'border-transparent text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <span>Checkpoint {num}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
                        mr.status === 'Completed'
                          ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/30'
                          : mr.status === 'In Progress'
                          ? 'bg-amber-950/80 text-amber-300 border border-amber-500/30'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {mr.status === 'Completed' ? formatDuration(mr.durationSeconds) : mr.status}
                    </span>
                  </button>
                );
              })}
            </div>

            {timingError && (
              <div className="p-2.5 rounded-xl bg-red-950/50 border border-red-500/40 text-red-200 text-xs">
                {timingError}
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Start Time (ISO/Local)</label>
                <input
                  type="text"
                  value={timingStartTime}
                  onChange={(e) => setTimingStartTime(e.target.value)}
                  placeholder="2026-10-06T10:00:00"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Completion Time (ISO/Local)</label>
                <input
                  type="text"
                  value={timingEndTime}
                  onChange={(e) => setTimingEndTime(e.target.value)}
                  placeholder="2026-10-06T10:15:00"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-white"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Hints Used (+5m each)</label>
                <input
                  type="number"
                  min="0"
                  value={timingHints}
                  onChange={(e) => setTimingHints(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Phone Penalties (+10m)</label>
                <input
                  type="number"
                  min="0"
                  value={timingPhonePenalties}
                  onChange={(e) => setTimingPhonePenalties(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Separation (+5m)</label>
                <input
                  type="number"
                  min="0"
                  value={timingSeparationPenalties}
                  onChange={(e) => setTimingSeparationPenalties(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-white"
                />
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* ======================================================== */}
      {/* TEAM DETAIL / AUDIT MODAL                                */}
      {/* ======================================================== */}
      <Modal
        isOpen={isTeamAuditOpen}
        onClose={() => setIsTeamAuditOpen(false)}
        title={
          <div className="flex items-center gap-2 font-mono">
            <span className="text-cyan-400 font-bold">
              TEAM {selectedTeamAudit?.team_identifier}
            </span>
            <span className="text-white">&middot; {selectedTeamAudit?.team_name}</span>
            <span className="text-xs text-slate-400">Inspection &amp; Audit Log</span>
          </div>
        }
        subtitle={`Current Checkpoint: ${selectedTeamAudit?.current_checkpoint} · Total Time: ${
          selectedTeamAudit?.total_time_seconds ? formatDuration(selectedTeamAudit.total_time_seconds) : 'In Progress'
        }`}
        maxWidth="2xl"
      >
        <div className="space-y-5 text-xs font-mono">
          {isLoadingTeamAudit ? (
            <div className="py-8 text-center text-slate-400">Loading audit data...</div>
          ) : selectedTeamAudit ? (
            <>
              {/* Route Summary */}
              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
                <div className="text-[10px] text-slate-400 uppercase tracking-wider font-bold">
                  Assigned Route &amp; Sets
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <div className="p-2 rounded-xl bg-slate-900 border border-slate-800 space-y-0.5">
                    <div className="text-[10px] text-slate-500">CHECKPOINT 1</div>
                    <div className="font-bold text-white">Loc {selectedTeamAudit.allocations?.cp1?.location} ({selectedTeamAudit.allocations?.cp1?.location_name})</div>
                    <span className={`inline-block px-1.5 py-0.2 rounded font-bold border ${getSetBadgeClass(selectedTeamAudit.allocations?.cp1?.set)}`}>
                      {selectedTeamAudit.allocations?.cp1?.set}
                    </span>
                  </div>

                  <div className="p-2 rounded-xl bg-slate-900 border border-slate-800 space-y-0.5">
                    <div className="text-[10px] text-slate-500">CHECKPOINT 2</div>
                    <div className="font-bold text-white">Loc {selectedTeamAudit.allocations?.cp2?.location} ({selectedTeamAudit.allocations?.cp2?.location_name})</div>
                    <span className={`inline-block px-1.5 py-0.2 rounded font-bold border ${getSetBadgeClass(selectedTeamAudit.allocations?.cp2?.set)}`}>
                      {selectedTeamAudit.allocations?.cp2?.set}
                    </span>
                  </div>

                  <div className="p-2 rounded-xl bg-slate-900 border border-slate-800 space-y-0.5">
                    <div className="text-[10px] text-slate-500">CHECKPOINT 3</div>
                    <div className="font-bold text-white">Loc {selectedTeamAudit.allocations?.cp3?.location} ({selectedTeamAudit.allocations?.cp3?.location_name})</div>
                    <span className={`inline-block px-1.5 py-0.2 rounded font-bold border ${getSetBadgeClass(selectedTeamAudit.allocations?.cp3?.set)}`}>
                      {selectedTeamAudit.allocations?.cp3?.set}
                    </span>
                  </div>
                </div>
              </div>

              {/* Physical Scans Audit Log */}
              <div className="space-y-2">
                <div className="text-[11px] text-slate-300 font-bold uppercase tracking-wider flex items-center justify-between">
                  <span>Physical QR Scans Audit</span>
                  <span className="text-[10px] text-slate-500">{selectedTeamAudit.scans?.length || 0} Events</span>
                </div>
                <div className="max-h-36 overflow-y-auto border border-slate-800 rounded-xl">
                  <table className="w-full text-left text-[11px]">
                    <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="py-1.5 px-3">CP</th>
                        <th className="py-1.5 px-3">Location Scanned</th>
                        <th className="py-1.5 px-3">Result</th>
                        <th className="py-1.5 px-3 text-right">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {selectedTeamAudit.scans?.length ? (
                        selectedTeamAudit.scans.map((s, idx) => (
                          <tr key={idx} className={s.is_valid_location ? '' : 'bg-rose-950/20'}>
                            <td className="py-1.5 px-3">R1.{s.checkpoint_number}</td>
                            <td className="py-1.5 px-3">Location {s.location_number}</td>
                            <td className="py-1.5 px-3">
                              {s.is_valid_location ? (
                                <span className="text-emerald-400">Valid Station</span>
                              ) : (
                                <span className="text-rose-400 font-bold">INVALID LOCATION SCAN</span>
                              )}
                            </td>
                            <td className="py-1.5 px-3 text-right text-slate-400">
                              {new Date(s.scanned_at).toLocaleTimeString()}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={4} className="py-3 text-center text-slate-500">
                            No physical scans recorded yet.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Question Attempts Log */}
              <div className="space-y-2">
                <div className="text-[11px] text-slate-300 font-bold uppercase tracking-wider flex items-center justify-between">
                  <span>Envelope Question Attempts</span>
                  <span className="text-[10px] text-slate-500">{selectedTeamAudit.attempts?.length || 0} Submissions</span>
                </div>
                <div className="max-h-40 overflow-y-auto border border-slate-800 rounded-xl">
                  <table className="w-full text-left text-[11px]">
                    <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="py-1.5 px-3">CP</th>
                        <th className="py-1.5 px-3">Attempt #</th>
                        <th className="py-1.5 px-3">Submitted Answer</th>
                        <th className="py-1.5 px-3">Result</th>
                        <th className="py-1.5 px-3 text-right">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {selectedTeamAudit.attempts?.length ? (
                        selectedTeamAudit.attempts.map((att, idx) => (
                          <tr key={idx} className={att.is_correct ? 'bg-emerald-950/20' : ''}>
                            <td className="py-1.5 px-3">R1.{att.checkpoint_number}</td>
                            <td className="py-1.5 px-3">Attempt {att.attempt_number} of 3</td>
                            <td className="py-1.5 px-3 font-mono font-bold text-white">{att.submitted_answer}</td>
                            <td className="py-1.5 px-3">
                              {att.is_correct ? (
                                <span className="text-emerald-400 font-bold">CORRECT</span>
                              ) : (
                                <span className="text-rose-400">Incorrect</span>
                              )}
                            </td>
                            <td className="py-1.5 px-3 text-right text-slate-400">
                              {new Date(att.created_at).toLocaleTimeString()}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={5} className="py-3 text-center text-slate-500">
                            No question submissions recorded yet.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="py-8 text-center text-slate-500">No audit details found.</div>
          )}
        </div>
      </Modal>

      {/* ======================================================== */}
      {/* REGENERATE CONFIRMATION DIALOG                           */}
      {/* ======================================================== */}
      <ConfirmationDialog
        isOpen={isRegenerateModalOpen}
        onClose={() => setIsRegenerateModalOpen(false)}
        onConfirm={handleRegenerateAllocations}
        title="Regenerate Route Allocations?"
        message="Regenerating allocations will reset any active participant checkpoint sessions and re-generate a fresh mathematical zero-conflict schedule for all 32 squads. Are you sure you want to proceed?"
        confirmLabel="Regenerate Matrix"
        isDestructive={true}
        isLoading={isRegenerating}
      />

      {/* ======================================================== */}
      {/* FINALIZE ROUND 1 CONFIRMATION DIALOG                     */}
      {/* ======================================================== */}
      <ConfirmationDialog
        isOpen={isFinalizeConfirmOpen}
        onClose={() => setIsFinalizeConfirmOpen(false)}
        onConfirm={handleFinalizeRound1}
        title="Finalize Round 1 — The ODDyssey Protocol?"
        message="This action seals Round 1 officially. The Top 16 squads will qualify and advance to Round 2 (Cabo). The public scoreboard will reveal the Top 16 qualified teams."
        confirmLabel="Confirm & Finalize Round 1"
        isDestructive={false}
        isLoading={isSubmitting}
      />

      {/* ======================================================== */}
      {/* SETTINGS MODAL                                           */}
      {/* ======================================================== */}
      <Modal
        isOpen={isConfigOpen}
        onClose={() => setIsConfigOpen(false)}
        title="Round 1 Settings & Parameters"
        subtitle="Operational parameters for The ODDyssey Protocol"
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button variant="outline" size="sm" onClick={() => setIsConfigOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleSaveConfig} isLoading={isSubmitting}>
              Save Settings
            </Button>
          </div>
        }
      >
        <div className="space-y-4 text-xs font-mono">
          <div>
            <label htmlFor="penaltyMinutesInput" className="block text-slate-400 mb-1">Penalty Per Hint (Minutes)</label>
            <input
              id="penaltyMinutesInput"
              type="number"
              value={configPenaltyMinutes}
              onChange={(e) => setConfigPenaltyMinutes(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white"
            />
          </div>
          <div>
            <label className="block text-slate-400 mb-1">Physical Station Names</label>
            <div className="space-y-2">
              {configCheckpointNames.map((name, i) => (
                <input
                  key={i}
                  type="text"
                  value={name}
                  onChange={(e) => {
                    const next = [...configCheckpointNames];
                    next[i] = e.target.value;
                    setConfigCheckpointNames(next);
                  }}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white"
                />
              ))}
            </div>
          </div>
        </div>
      </Modal>

      {/* ======================================================== */}
      {/* CHECKINS MODAL                                           */}
      {/* ======================================================== */}
      <Modal
        isOpen={isCheckinsModalOpen}
        onClose={() => setIsCheckinsModalOpen(false)}
        title="Live Physical QR Checkpoint Scans Feed"
        subtitle={`Recorded Physical Scans (${checkinsFeed.length})`}
        maxWidth="2xl"
      >
        <div className="max-h-96 overflow-y-auto space-y-2">
          {checkinsFeed.map((chk) => (
            <div
              key={chk.id}
              className={`p-3 rounded-xl border text-xs font-mono flex items-center justify-between ${
                chk.is_duplicate ? 'border-amber-500/30 bg-amber-950/20' : 'border-slate-800 bg-slate-950'
              }`}
            >
              <div>
                <span className="font-bold text-white">{chk.team_name}</span>
                <span className="text-slate-400 ml-2">Gate 0{chk.gate_number}</span>
                <div className="text-[10px] text-slate-500">
                  {new Date(chk.scanned_at).toLocaleString()}
                </div>
              </div>
              <span className={chk.is_duplicate ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold'}>
                {chk.status} {chk.attempt_number > 1 ? `(#${chk.attempt_number})` : ''}
              </span>
            </div>
          ))}
        </div>
      </Modal>
    </div>
  );
}
