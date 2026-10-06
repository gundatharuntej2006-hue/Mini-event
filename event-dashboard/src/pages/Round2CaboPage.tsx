import React, { useState, useEffect, useMemo } from 'react';
import {
  Layers,
  Trophy,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowUpDown,
  Sparkles,
  ShieldAlert,
  Edit3,
  Users,
  Key,
  Shuffle,
  Lock,
  Printer,
  Download,
  Info,
  Check,
  X,
} from 'lucide-react';
import { eventService } from '../services/eventService';
import {
  backendApiService,
  CaboSummaryData,
  CaboValidationData,
  CaboPlayerDetailData,
  CaboTeamDetailData,
  CaboPrintableSheetData,
} from '../services/backendApiService';
import { isLiveMode } from '../services/apiConfig';
import {
  Round2Data,
  TeamRound2Record,
  CaboTableDetail,
} from '../types/round2';
import { formatTeamNumber } from '../utils/formatters';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { ConfirmationDialog } from '../components/ui/ConfirmationDialog';
import { TableRowSkeleton } from '../components/ui/LoadingSkeleton';
import { MetricCard } from '../components/dashboard/MetricCard';
import { PageHeader } from '../components/ui/PageHeader';
import { SearchFilterToolbar } from '../components/ui/SearchFilterToolbar';
import { Card, CardHeader, CardContent } from '../components/ui/Card';

type TabView = 'leaderboard' | 'seating' | 'game1' | 'game2' | 'game3';
type SortField = 'rank' | 'teamNumber' | 'name' | 'totalPoints' | 'cardTotal' | 'firstPlaces' | 'g1' | 'g2' | 'g3';

export const Round2CaboPage: React.FC = () => {
  // Data State
  const [data, setData] = useState<Round2Data | null>(null);
  const [caboStandings, setCaboStandings] = useState<any[]>([]);
  const [caboTables, setCaboTables] = useState<CaboTableDetail[]>([]);
  const [caboSummary, setCaboSummary] = useState<CaboSummaryData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Active View Tab
  const [activeTab, setActiveTab] = useState<TabView>('leaderboard');
  const [seatingGameNum, setSeatingGameNum] = useState<1 | 2 | 3>(1);

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('rank');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 16; // Exactly 16 squads for Round 2

  // Modals
  const [isFinalizeConfirmOpen, setIsFinalizeConfirmOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // ECHO Verification Modal State
  const [isEchoModalOpen, setIsEchoModalOpen] = useState(false);
  const [echoTeam, setEchoTeam] = useState<TeamRound2Record | null>(null);
  const [echoG1, setEchoG1] = useState(false);
  const [echoG2, setEchoG2] = useState(false);
  const [echoG3, setEchoG3] = useState(false);

  // PRIME Verification Modal State
  const [isPrimeModalOpen, setIsPrimeModalOpen] = useState(false);
  const [primeTeam, setPrimeTeam] = useState<TeamRound2Record | null>(null);
  const [primeSequenceVerified, setPrimeSequenceVerified] = useState(false);

  // Table Score Entry Modal State
  const [isTableScoreModalOpen, setIsTableScoreModalOpen] = useState(false);
  const [scoreTableGameNum, setScoreTableGameNum] = useState<1 | 2 | 3>(1);
  const [scoreTableNum, setScoreTableNum] = useState<number>(1);
  const [tablePlayersScores, setTablePlayersScores] = useState<
    Array<{ participantId: string; participantName: string; teamId: string; teamName: string; placement: number; finalCardHandTotal: number }>
  >([]);
  const [tableScoreError, setTableScoreError] = useState<string | null>(null);

  // Validation & Confirmation State
  const [caboValidation, setCaboValidation] = useState<CaboValidationData | null>(null);
  const [isConfirmTablesModalOpen, setIsConfirmTablesModalOpen] = useState(false);
  const [isRegenerateModalOpen, setIsRegenerateModalOpen] = useState(false);

  // Player Drill-Down Modal State
  const [playerDetail, setPlayerDetail] = useState<CaboPlayerDetailData | null>(null);
  const [isPlayerModalOpen, setIsPlayerModalOpen] = useState(false);

  // Team Drill-Down Modal State
  const [teamDetail, setTeamDetail] = useState<CaboTeamDetailData | null>(null);
  const [isTeamModalOpen, setIsTeamModalOpen] = useState(false);

  // Score Correction Modal State
  const [isCorrectionModalOpen, setIsCorrectionModalOpen] = useState(false);
  const [correctionTarget, setCorrectionTarget] = useState<{
    gameNumber: number;
    tableNumber: number;
    participantId: string;
    participantName: string;
    teamName: string;
    oldPlacement: number;
    newPlacement: number;
    reason: string;
    newCardTotal?: number;
  } | null>(null);

  // Printable Sheets State
  const [printableData, setPrintableData] = useState<CaboPrintableSheetData | null>(null);
  const [isPrintModalOpen, setIsPrintModalOpen] = useState(false);

  // Load Data
  const loadRound2 = async (gameOverride?: 1 | 2 | 3) => {
    try {
      const activeGame = gameOverride ?? seatingGameNum;
      const r2Data = await eventService.getRound2Data();
      setData(r2Data);

      if (isLiveMode()) {
        try {
          const [standingsRes, tablesRes, summaryRes, validationRes] = await Promise.all([
            backendApiService.getCaboStandings(),
            backendApiService.getCaboGameTables(activeGame),
            backendApiService.getCaboSummary(),
            backendApiService.getCaboValidation(),
          ]);
          if (standingsRes.success && standingsRes.data) {
            setCaboStandings(standingsRes.data);
          }
          if (tablesRes.success && tablesRes.data) {
            setCaboTables(tablesRes.data);
          }
          if (summaryRes.success && summaryRes.data) {
            setCaboSummary(summaryRes.data);
          }
          if (validationRes.success && validationRes.data) {
            setCaboValidation(validationRes.data);
          }
        } catch (e) {
          console.error('Failed to fetch live Cabo tables/standings/summary/validation:', e);
        }
      }
    } catch (err) {
      console.error('Failed to load Round 2 data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRound2();
    const unsubscribe = eventService.subscribe(() => {
      loadRound2();
    });
    return unsubscribe;
  }, [seatingGameNum]);

  // Merge backend Cabo standings if available
  const enrichedRecords = useMemo(() => {
    if (!data) return [];
    if (!caboStandings || caboStandings.length === 0) {
      return data.records.slice(0, 16);
    }

    const standingMap = new Map<string, any>();
    caboStandings.forEach((s) => standingMap.set(s.teamId, s));

    return data.records.slice(0, 16).map((rec) => {
      const live = standingMap.get(rec.teamId);
      if (live) {
        return {
          ...rec,
          rank: live.rank,
          totalPoints: live.caboScore,
          game1Points: live.game1Score ?? rec.game1Points,
          game2Points: live.game2Score ?? rec.game2Points,
          game3Points: live.game3Score ?? rec.game3Points,
          combinedCardTotal: live.combinedCardTotal,
          firstPlaceCount: live.firstPlaceCount,
          echoStatus: live.echoStatus,
          echoEVerified: live.echoEVerified,
          echoCVerified: live.echoCVerified,
          echoHoVerified: live.echoHoVerified,
          primeStatus: live.primeStatus,
          primeSequenceVerified: live.primeSequenceVerified,
          isComplete: live.caboScore !== undefined && live.caboScore !== null,
          qualificationStatus: live.isQualified ? 'Provisional Top 8' : 'Provisional Cutoff',
          tieRequiresReview: live.isTiedUnresolved,
          tieReason: live.tieReason,
        } as TeamRound2Record;
      }
      return rec;
    });
  }, [data, caboStandings]);

  // Filter & Sort for Overall Standings
  const filteredAndSortedRecords = useMemo(() => {
    return enrichedRecords
      .filter((rec) => {
        const q = searchQuery.toLowerCase().trim();
        const matchesSearch =
          q === '' ||
          rec.teamName.toLowerCase().includes(q) ||
          formatTeamNumber(rec.teamNumber).toLowerCase().includes(q);

        let matchesStatus = true;
        if (filterStatus === 'top8') {
          matchesStatus = rec.qualificationStatus === 'Provisional Top 8' || rec.qualificationStatus === 'Finalized Qualified' || (rec.rank !== null && rec.rank !== undefined && rec.rank <= 8);
        } else if (filterStatus === 'eliminated') {
          matchesStatus = rec.qualificationStatus === 'Provisional Cutoff' || rec.qualificationStatus === 'Finalized Eliminated' || (rec.rank !== null && rec.rank !== undefined && rec.rank > 8);
        } else if (filterStatus === 'tieReview') {
          matchesStatus = !!rec.tieRequiresReview;
        } else if (filterStatus === 'incomplete') {
          matchesStatus = !rec.isComplete;
        }

        return matchesSearch && matchesStatus;
      })
      .sort((a, b) => {
        let comparison = 0;
        if (sortField === 'rank') {
          const aRank = a.rank ?? 999;
          const bRank = b.rank ?? 999;
          comparison = aRank - bRank;
        } else if (sortField === 'teamNumber') {
          comparison = a.teamNumber - b.teamNumber;
        } else if (sortField === 'name') {
          comparison = a.teamName.localeCompare(b.teamName);
        } else if (sortField === 'totalPoints') {
          const aPts = a.totalPoints ?? -999;
          const bPts = b.totalPoints ?? -999;
          comparison = bPts - aPts;
        } else if (sortField === 'cardTotal') {
          const aC = a.combinedCardTotal ?? 999;
          const bC = b.combinedCardTotal ?? 999;
          comparison = aC - bC; // lower is better
        } else if (sortField === 'firstPlaces') {
          const aF = a.firstPlaceCount ?? 0;
          const bF = b.firstPlaceCount ?? 0;
          comparison = bF - aF; // more is better
        }
        return sortOrder === 'asc' ? comparison : -comparison;
      });
  }, [enrichedRecords, searchQuery, filterStatus, sortField, sortOrder]);

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

  // Open ECHO Verification Modal
  const handleOpenEchoModal = (rec: TeamRound2Record) => {
    setEchoTeam(rec);
    setEchoG1(!!rec.echoEVerified);
    setEchoG2(!!rec.echoCVerified);
    setEchoG3(!!rec.echoHoVerified);
    setIsEchoModalOpen(true);
  };

  const handleSaveEchoVerification = async () => {
    if (!echoTeam) return;
    setIsSubmitting(true);
    try {
      await backendApiService.verifyEcho(echoTeam.teamId, {
        game1E: echoG1,
        game2C: echoG2,
        game3Ho: echoG3,
      });
      setIsEchoModalOpen(false);
      await loadRound2();
    } catch (e: any) {
      alert(e.message || 'Failed to verify ECHO fragment');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Open PRIME Verification Modal
  const handleOpenPrimeModal = (rec: TeamRound2Record) => {
    setPrimeTeam(rec);
    setPrimeSequenceVerified(!!rec.primeSequenceVerified);
    setIsPrimeModalOpen(true);
  };

  const handleSavePrimeVerification = async () => {
    if (!primeTeam) return;
    setIsSubmitting(true);
    try {
      await backendApiService.verifyPrime(primeTeam.teamId, {
        sequence: [2, 3, 5, 7, 11],
        isVerified: primeSequenceVerified,
      });
      setIsPrimeModalOpen(false);
      await loadRound2();
    } catch (e: any) {
      alert(e.message || 'Failed to verify PRIME fragment');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Open Table Score Modal
  const handleOpenTableScoreModal = (table: CaboTableDetail) => {
    setScoreTableGameNum(table.gameNumber as 1 | 2 | 3);
    setScoreTableNum(table.tableNumber);
    setTableScoreError(null);

    const initial = table.players.map((p, idx) => ({
      participantId: p.participantId,
      participantName: p.participantName,
      teamId: p.teamId,
      teamName: p.teamName,
      placement: p.placement ?? idx + 1,
      finalCardHandTotal: p.finalCardHandTotal ?? 10,
    }));
    setTablePlayersScores(initial);
    setIsTableScoreModalOpen(true);
  };

  const handleSaveTableScores = async () => {
    const placements = tablePlayersScores.map((p) => p.placement);
    const unique = new Set(placements);
    if (unique.size !== 5 || !placements.every((p) => p >= 1 && p <= 5)) {
      setTableScoreError('Every seated player must have a unique placement from 1st to 5th (no ties on table).');
      return;
    }

    setIsSubmitting(true);
    try {
      await backendApiService.recordCaboTableScores(scoreTableGameNum, {
        table_number: scoreTableNum,
        scores: tablePlayersScores.map((p) => ({
          gameNumber: scoreTableGameNum,
          participantId: p.participantId,
          teamId: p.teamId,
          placement: p.placement,
          finalCardHandTotal: p.finalCardHandTotal,
        })),
      });
      setIsTableScoreModalOpen(false);
      await loadRound2();
    } catch (e: any) {
      setTableScoreError(e.message || 'Failed to record table scores');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Confirm Tables & Freeze Seating
  const handleConfirmTables = async () => {
    setIsSubmitting(true);
    try {
      await backendApiService.confirmCaboTables();
      setIsConfirmTablesModalOpen(false);
      await loadRound2();
    } catch (e: any) {
      alert(e.message || 'Failed to confirm tables');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Safe table generation / regeneration trigger
  const handleTriggerGenerate = () => {
    if (caboValidation?.isConfirmed) {
      setIsRegenerateModalOpen(true);
    } else {
      handleExecuteGenerate(false);
    }
  };

  const handleExecuteGenerate = async (force: boolean) => {
    setIsSubmitting(true);
    try {
      await backendApiService.generateCaboTables({ force_regenerate: force });
      setIsRegenerateModalOpen(false);
      await loadRound2();
    } catch (e: any) {
      alert(e.message || 'Failed to generate Cabo tables');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Inspect Player Details
  const handleOpenPlayerDetail = async (participantId: string) => {
    try {
      const res = await backendApiService.getCaboPlayerDetail(participantId);
      if (res.success && res.data) {
        setPlayerDetail(res.data);
        setIsPlayerModalOpen(true);
      }
    } catch (e: any) {
      alert(e.message || 'Failed to load player details');
    }
  };

  // Inspect Team Details
  const handleOpenTeamDetail = async (teamId: string) => {
    try {
      const res = await backendApiService.getCaboTeamDetail(teamId);
      if (res.success && res.data) {
        setTeamDetail(res.data);
        setIsTeamModalOpen(true);
      }
    } catch (e: any) {
      alert(e.message || 'Failed to load team details');
    }
  };

  // Open Score Correction Modal
  const handleOpenScoreCorrection = (
    gameNumber: number,
    tableNumber: number,
    p: { participantId: string; participantName: string; teamName: string; placement?: number | null; finalCardHandTotal?: number | null }
  ) => {
    setCorrectionTarget({
      gameNumber,
      tableNumber,
      participantId: p.participantId,
      participantName: p.participantName,
      teamName: p.teamName,
      oldPlacement: p.placement || 1,
      newPlacement: p.placement || 1,
      reason: '',
      newCardTotal: p.finalCardHandTotal ?? undefined,
    });
    setIsCorrectionModalOpen(true);
  };

  const handleSaveScoreCorrection = async () => {
    if (!correctionTarget) return;
    if (!correctionTarget.reason || correctionTarget.reason.trim().length < 3) {
      alert('A valid reason (minimum 3 characters) is mandatory for official organizer score correction.');
      return;
    }

    setIsSubmitting(true);
    try {
      await backendApiService.correctCaboTableScore(
        correctionTarget.gameNumber,
        correctionTarget.tableNumber,
        {
          participantId: correctionTarget.participantId,
          newPlacement: correctionTarget.newPlacement,
          reason: correctionTarget.reason.trim(),
          newCardTotal: correctionTarget.newCardTotal,
        }
      );
      setIsCorrectionModalOpen(false);
      await loadRound2();
    } catch (e: any) {
      alert(e.message || 'Failed to correct score');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Open Printable Table Sheet Modal
  const handleOpenPrintableSheet = async (gameNum: number) => {
    try {
      const res = await backendApiService.getCaboPrintableSheet(gameNum);
      if (res.success && res.data) {
        setPrintableData(res.data);
        setIsPrintModalOpen(true);
      }
    } catch (e: any) {
      alert(e.message || 'Failed to load printable table sheets');
    }
  };

  // Export Data Download
  const handleExportData = async (type: 'assignments' | 'results' | 'standings') => {
    try {
      const blob = await backendApiService.exportCaboData(type);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cabo_${type}_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e: any) {
      alert(e.message || `Failed to export ${type}`);
    }
  };


  // Finalize Round 2
  const handleFinalizeRound2 = async () => {
    setIsSubmitting(true);
    try {
      await backendApiService.finalizeCaboRound();
      setIsFinalizeConfirmOpen(false);
      await loadRound2();
    } catch (err: any) {
      alert(err.message || 'Failed to finalize Round 2');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusBadge = (rec: TeamRound2Record) => {
    const isAdvancing = rec.rank !== null && rec.rank !== undefined && rec.rank <= 8;
    if (data?.config.isFinalized) {
      return isAdvancing ? (
        <Badge variant="success" size="sm" dot>
          Finalized Top 8 (To R3)
        </Badge>
      ) : (
        <Badge variant="danger" size="sm">
          Eliminated
        </Badge>
      );
    }
    if (rec.tieRequiresReview) {
      return (
        <Badge variant="warning" size="sm" dot>
          Cutoff Tie Review
        </Badge>
      );
    }
    if (isAdvancing) {
      return (
        <Badge variant="primary" size="sm" dot>
          Provisional Top 8
        </Badge>
      );
    }
    return (
      <Badge variant="neutral" size="sm">
        Elimination Zone
      </Badge>
    );
  };

  const g1TablesLogged = Math.min(16, Math.max(0, caboSummary?.game1CompletedTables ?? data?.stats.game1CompletionCount ?? 0));
  const g2TablesLogged = Math.min(16, Math.max(0, caboSummary?.game2CompletedTables ?? data?.stats.game2CompletionCount ?? 0));
  const g3TablesLogged = Math.min(16, Math.max(0, caboSummary?.game3CompletedTables ?? data?.stats.game3CompletionCount ?? 0));

  const canFinalize = caboSummary ? caboSummary.canFinalize : (data?.engine.canFinalize ?? false);
  const isFinalized = caboSummary ? caboSummary.isFinalized : (data?.config.isFinalized ?? false);
  const incompleteReasons: string[] = caboSummary?.incompleteReasons || (data?.engine.blockReason ? [data.engine.blockReason] : []);

  const handleSelectGameTab = async (g: 1 | 2 | 3) => {
    setActiveTab(`game${g}` as TabView);
    setSeatingGameNum(g);
    await loadRound2(g);
  };

  const handleSelectSeatingTab = async (g: 1 | 2 | 3) => {
    setSeatingGameNum(g);
    await loadRound2(g);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Round 2: Cabo - The Memory Heist"
        subtitle="16 Qualified Teams from R1 · 16 Tables · 3 Cabo Games · Top 8 advance to Round 3: The Black Market"
        badge={
          isFinalized ? (
            <Badge variant="success" size="sm" dot>
              Finalized &amp; Sealed (Top 8 Advancing)
            </Badge>
          ) : !data?.round1Finalized ? (
            <Badge variant="warning" size="sm" dot>
              R1 Standby (Unfinalized)
            </Badge>
          ) : (
            <Badge variant="primary" size="sm" dot>
              Live Cabo Tournament
            </Badge>
          )
        }
        actions={
          <div className="flex items-center flex-wrap gap-2">
            {caboValidation && !caboValidation.isConfirmed && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsConfirmTablesModalOpen(true)}
                leftIcon={<Lock className="w-3.5 h-3.5 text-slate-900" />}
                className="bg-emerald-400 hover:bg-emerald-300 text-slate-950 font-black shadow-[0_0_15px_rgba(52,211,153,0.3)]"
                disabled={!caboValidation.isValid}
                title={!caboValidation.isValid ? 'All 8 constraints must pass before confirming' : 'Confirm & Freeze Seating Allocation'}
              >
                Confirm Tables
              </Button>
            )}

            {caboValidation?.isConfirmed && (
              <Badge variant="success" size="sm" dot className="border border-emerald-500/40 bg-emerald-950/40 text-emerald-300">
                Tables Confirmed &amp; Frozen
              </Badge>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={handleTriggerGenerate}
              leftIcon={<Shuffle className="w-3.5 h-3.5 text-cyan-400" />}
              disabled={isFinalized}
            >
              {caboValidation?.isConfirmed ? 'Regenerate...' : 'Generate Tables'}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => handleOpenPrintableSheet(seatingGameNum)}
              leftIcon={<Printer className="w-3.5 h-3.5 text-cyan-400" />}
            >
              Print Table Sheets
            </Button>

            <div className="relative group inline-block">
              <Button
                variant="outline"
                size="sm"
                leftIcon={<Download className="w-3.5 h-3.5 text-cyan-400" />}
              >
                Export CSV
              </Button>
              <div className="absolute right-0 mt-1 w-44 bg-[#0a0f1d] border border-cyan-500/30 rounded-xl shadow-xl py-1 z-30 hidden group-hover:block text-xs font-mono">
                <button
                  onClick={() => handleExportData('assignments')}
                  className="w-full text-left px-3 py-1.5 hover:bg-cyan-500/20 text-slate-200"
                >
                  Table Assignments
                </button>
                <button
                  onClick={() => handleExportData('results')}
                  className="w-full text-left px-3 py-1.5 hover:bg-cyan-500/20 text-slate-200"
                >
                  Scorecard Results
                </button>
                <button
                  onClick={() => handleExportData('standings')}
                  className="w-full text-left px-3 py-1.5 hover:bg-cyan-500/20 text-slate-200"
                >
                  Squad Standings
                </button>
              </div>
            </div>

            {!isFinalized && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsFinalizeConfirmOpen(true)}
                leftIcon={<Trophy className="w-3.5 h-3.5" />}
                disabled={!canFinalize}
                title={!canFinalize ? (incompleteReasons[0] || 'Required scores incomplete') : 'Seal Round 2 results and advance Top 8'}
              >
                Finalize Top 8
              </Button>
            )}
          </div>
        }
      />

      {/* Seating Validation Banner (8 Constraints) */}
      {caboValidation && (
        <div className={`p-4 rounded-xl border text-xs shadow-sm ${
          caboValidation.isValid
            ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-200'
            : 'bg-rose-950/20 border-rose-500/30 text-rose-200'
        }`}>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-2 border-b border-white/10">
            <div className="flex items-center gap-2">
              {caboValidation.isValid ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              )}
              <span className="font-orbitron font-bold tracking-wide">
                {caboValidation.isValid
                  ? 'All 8 Seating Constraints Passed — Ready for Confirmation'
                  : 'Seating Allocation Validation Issues Detected'}
              </span>
            </div>
            <div className="font-mono text-[11px] opacity-80">
              16 Teams · 80 Players · 16 Tables · 3 Cabo Games
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-[11px] font-mono">
            {Object.entries(caboValidation.constraints).map(([name, passed]) => (
              <div key={name} className="flex items-center gap-1.5">
                {passed ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                ) : (
                  <X className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                )}
                <span className={passed ? 'text-slate-300' : 'text-rose-300 font-bold'}>
                  {name.replace(/_/g, ' ')}
                </span>
              </div>
            ))}
          </div>

          {caboValidation.errors.length > 0 && (
            <div className="mt-2 pt-2 border-t border-rose-500/20 text-rose-300 text-[11px] space-y-0.5">
              {caboValidation.errors.map((err, i) => (
                <div key={i}>• {err}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Standby Banner if Round 1 is not finalized */}
      {!data?.round1Finalized && (
        <div className="p-4 rounded-xl bg-cyan-950/40 border border-cyan-500/30 text-cyan-200 text-xs flex items-center justify-between gap-3 shadow-md">
          <div className="flex items-center gap-3">
            <Layers className="w-5 h-5 text-cyan-400 shrink-0" />
            <div>
              <div className="font-bold font-orbitron text-cyan-300">
                Waiting for Round 1 qualification
              </div>
              <div className="text-[11px] text-slate-300">
                Round 2 CABO seating and scorecards will automatically lock in the official Top 16 teams once Round 1 is finalized.
              </div>
            </div>
          </div>
          <Badge variant="warning" size="sm">R1 In Progress</Badge>
        </div>
      )}

      {/* Completion Status Alert / Banner */}
      {!isFinalized && !canFinalize && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs flex items-start gap-3 shadow-sm">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1.5 flex-1">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <span className="font-bold font-orbitron tracking-wide text-amber-300">
                Round 2 Incomplete — Scoring &amp; Table Progress
              </span>
              <span className="font-mono text-[11px] text-amber-400 font-bold">
                {caboSummary?.totalCompletedTables ?? 0}/48 Total Tables Logged
              </span>
            </div>
            <div className="text-[11px] text-amber-200/90 font-mono">
              Game 1: <strong>{g1TablesLogged}/16</strong> tables · Game 2: <strong>{g2TablesLogged}/16</strong> tables · Game 3: <strong>{g3TablesLogged}/16</strong> tables
            </div>
            {incompleteReasons.length > 0 && (
              <ul className="list-disc list-inside text-[11px] text-amber-300/80 space-y-0.5 pt-0.5">
                {incompleteReasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* Overview Dynamic Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5">
        <MetricCard
          label="Eligible Teams"
          value="16"
          subtitle="From Round 1"
          icon={Layers}
          badge={{ text: data?.round1Finalized ? 'Sealed' : 'Active', variant: 'emerald' }}
        />

        <MetricCard
          label="Tables"
          value="16"
          subtitle="5 Players / Table"
          icon={Users}
          badge={{ text: '16 Tables', variant: 'blue' }}
        />

        <MetricCard
          label="Game 1 Done"
          value={`${g1TablesLogged}/16`}
          subtitle="Tables Logged"
          icon={Clock}
          badge={{ text: 'Game 1', variant: 'emerald' }}
        />

        <MetricCard
          label="Game 2 Done"
          value={`${g2TablesLogged}/16`}
          subtitle="Tables Logged"
          icon={Clock}
          badge={{ text: 'Game 2', variant: 'emerald' }}
        />

        <MetricCard
          label="Game 3 Done"
          value={`${g3TablesLogged}/16`}
          subtitle="Tables Logged"
          icon={Clock}
          badge={{ text: 'Game 3', variant: 'emerald' }}
        />

        <MetricCard
          label="Max Squad Score"
          value="75"
          subtitle="15 wins * 5 pts"
          icon={Trophy}
          badge={{ text: '75 Pts', variant: 'purple' }}
        />

        <MetricCard
          label="Top 8 Cutoff"
          value="Top 8"
          subtitle="Advance to R3"
          icon={CheckCircle2}
          badge={{ text: 'Cutoff #8', variant: 'purple' }}
        />

        <MetricCard
          label="Elimination"
          value="8"
          subtitle="Ranks 9–16"
          icon={ShieldAlert}
          badge={{ text: 'Eliminated', variant: 'amber' }}
        />
      </div>

      {/* Navigation Tabs for Views */}
      <div className="flex border-b border-cyan-500/20 bg-[#070b16]/70 rounded-t-2xl px-4 pt-2 gap-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab('leaderboard')}
          className={`px-4 py-2.5 text-xs font-orbitron font-bold border-b-2 transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
            activeTab === 'leaderboard'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Trophy className="w-3.5 h-3.5" />
          <span>Overall Standings &amp; Cutoff</span>
        </button>

        <button
          onClick={() => {
            setActiveTab('seating');
            loadRound2(seatingGameNum);
          }}
          className={`px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
            activeTab === 'seating'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>Seating &amp; Tables (16 Tables)</span>
        </button>

        <button
          onClick={() => handleSelectGameTab(1)}
          className={`px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
            activeTab === 'game1'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>Game 1 Console</span>
        </button>

        <button
          onClick={() => handleSelectGameTab(2)}
          className={`px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
            activeTab === 'game2'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>Game 2 Console</span>
        </button>

        <button
          onClick={() => handleSelectGameTab(3)}
          className={`px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
            activeTab === 'game3'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>Game 3 Console</span>
        </button>
      </div>

      {/* SEATING MANAGEMENT VIEW */}
      {activeTab === 'seating' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#0a0f1d] p-4 rounded-xl border border-cyan-500/20">
            <div>
              <h3 className="text-sm font-orbitron font-bold text-slate-100 flex items-center gap-2">
                <Users className="w-4 h-4 text-cyan-400" />
                <span>16 Tables Seating Matrix (80 Players)</span>
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Strict Squad Isolation: Teammates from the same team <strong>NEVER</strong> share a table.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-mono">Game:</span>
              {[1, 2, 3].map((g) => (
                <button
                  key={g}
                  onClick={() => handleSelectSeatingTab(g as 1 | 2 | 3)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all ${
                    seatingGameNum === g
                      ? 'bg-cyan-500 text-slate-950 font-black'
                      : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-cyan-500/20'
                  }`}
                >
                  Game {g}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {caboTables.length === 0 ? (
              <div className="col-span-full py-12 text-center text-slate-400 bg-[#080d1a] border border-cyan-500/10 rounded-2xl">
                No table assignments generated yet. Click &quot;Generate Tables&quot; to initialize 16 squad-isolated tables.
              </div>
            ) : (
              caboTables.map((tbl) => (
                <div
                  key={tbl.tableNumber}
                  className="bg-[#080d1a] border border-cyan-500/20 hover:border-cyan-500/40 rounded-xl p-3.5 space-y-2.5 transition-all shadow-sm"
                >
                  <div className="flex items-center justify-between border-b border-cyan-500/10 pb-2">
                    <span className="font-orbitron font-bold text-cyan-300 text-xs">
                      Table {tbl.tableNumber}
                    </span>
                    {tbl.isCompleted ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        Scored
                      </span>
                    ) : (
                      <button
                        onClick={() => handleOpenTableScoreModal(tbl)}
                        className="text-[11px] font-mono text-cyan-400 hover:underline flex items-center gap-1"
                      >
                        <Edit3 className="w-3 h-3" />
                        Enter Scores
                      </button>
                    )}
                  </div>

                  <div className="space-y-1.5 text-xs">
                    {tbl.players.map((p) => (
                      <div
                        key={p.participantId}
                        className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800 hover:border-cyan-500/30 transition-all"
                      >
                        <div className="truncate mr-2 cursor-pointer" onClick={() => handleOpenPlayerDetail(p.participantId)}>
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] font-mono text-cyan-400/80">
                              S{p.seatPosition}:
                            </span>
                            <span className="font-semibold text-slate-200 hover:text-cyan-300 underline-offset-2 hover:underline">
                              {p.participantName}
                            </span>
                          </div>
                          <div className="text-[10px] text-slate-400 truncate font-mono flex items-center gap-2">
                            <span>{p.teamName}</span>
                            {p.participantUsn && <span className="text-slate-500 font-mono">({p.participantUsn})</span>}
                          </div>
                        </div>

                        <div className="flex items-center gap-1 shrink-0">
                          {p.placement && (
                            <span className="font-mono text-xs font-bold text-amber-300">
                              #{p.placement} ({p.placementPoints}p)
                            </span>
                          )}
                          {tbl.isCompleted && (
                            <button
                              onClick={() => handleOpenScoreCorrection(tbl.gameNumber, tbl.tableNumber, p)}
                              className="p-1 rounded text-slate-500 hover:text-amber-400 hover:bg-amber-500/10"
                              title="Correct Individual Score"
                            >
                              <Edit3 className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* GAME 1 / 2 / 3 CONSOLES */}
      {(activeTab === 'game1' || activeTab === 'game2' || activeTab === 'game3') && (
        <div className="space-y-4">
          <div className="bg-[#0a0f1d] p-4 rounded-xl border border-cyan-500/20 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-orbitron font-bold text-slate-100 flex items-center gap-2">
                <span>Cabo Game {seatingGameNum} Table Results</span>
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Official Cabo Placements: 1st = 5 pts, 2nd = 3 pts, 3rd = 2 pts, 4th = 1 pt, 5th = 0 pts.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {caboTables.map((tbl) => (
              <div
                key={tbl.tableNumber}
                className="bg-[#080d1a] border border-cyan-500/20 rounded-xl p-3.5 space-y-2"
              >
                <div className="flex items-center justify-between border-b border-cyan-500/10 pb-2">
                  <span className="font-orbitron font-bold text-cyan-300 text-xs">Table {tbl.tableNumber}</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleOpenTableScoreModal(tbl)}
                    leftIcon={<Edit3 className="w-3 h-3" />}
                    className="h-6 text-[10px] px-2 py-0 border-cyan-500/30 text-cyan-300"
                  >
                    {tbl.isCompleted ? 'Edit Scores' : 'Record'}
                  </Button>
                </div>
                <div className="space-y-1">
                  {tbl.players.map((p) => (
                    <div key={p.participantId} className="flex items-center justify-between text-xs py-0.5">
                      <span className="text-slate-300 truncate max-w-[140px] font-mono text-[11px]">{p.teamName}</span>
                      <span className="font-mono text-cyan-300 text-xs font-bold">
                        {p.placement ? `#${p.placement} (${p.placementPoints} pts)` : '—'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* OVERALL STANDINGS / SCOREBOARD VIEW */}
      {activeTab === 'leaderboard' && (
        <div className="space-y-4">
          <SearchFilterToolbar
            searchQuery={searchQuery}
            onSearchChange={(val) => {
              setSearchQuery(val);
              setCurrentPage(1);
            }}
            searchPlaceholder="Search squad name or tag..."
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
                  { label: 'All 16 Squads', value: 'all' },
                  { label: 'Top 8 Advancing', value: 'top8' },
                  { label: 'Elimination Zone', value: 'eliminated' },
                  { label: 'Cutoff Tie Review', value: 'tieReview' },
                ],
              },
            ]}
            activeCount={(filterStatus !== 'all' ? 1 : 0) + (searchQuery ? 1 : 0)}
            onClearAll={() => {
              setSearchQuery('');
              setFilterStatus('all');
            }}
          />

          <Card>
            <CardHeader className="flex flex-row items-center justify-between py-3 px-4 border-b border-cyan-500/20 bg-[#070b16]/50">
              <div className="flex items-center gap-2">
                <div className="text-xs font-orbitron font-bold uppercase tracking-wider text-slate-200">
                  Cabo Scoreboard ({filteredAndSortedRecords.length} Squads)
                </div>
                <span className="text-[10px] text-amber-300 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-500/30 font-mono">
                  Max: 75 Pts · 1st=5, 2nd=3, 3rd=2, 4th=1, 5th=0
                </span>
              </div>
              <div className="text-xs text-slate-400 font-mono">
                Cutoff: Top 8 Advance to Round 3
              </div>
            </CardHeader>

            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-cyan-500/20 bg-[#030712]/90 text-[11px] font-mono font-bold text-cyan-400/80 uppercase tracking-wider">
                      <th className="py-3 px-3 text-center w-14 cursor-pointer" onClick={() => handleSort('rank')}>
                        <div className="flex items-center justify-center gap-1">
                          <span>Rank</span>
                          <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                        </div>
                      </th>
                      <th className="py-3 px-4 cursor-pointer" onClick={() => handleSort('name')}>
                        <div className="flex items-center gap-1">
                          <span>Squad</span>
                          <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                        </div>
                      </th>
                      <th className="py-3 px-3 text-center">G1 (/25)</th>
                      <th className="py-3 px-3 text-center">G2 (/25)</th>
                      <th className="py-3 px-3 text-center">G3 (/25)</th>
                      <th className="py-3 px-4 text-right cursor-pointer" onClick={() => handleSort('totalPoints')}>
                        <div className="flex items-center justify-end gap-1">
                          <span>Score (/75)</span>
                          <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                        </div>
                      </th>
                      <th className="py-3 px-3 text-center cursor-pointer" onClick={() => handleSort('firstPlaces')} title="Tie-Breaker 3: More 1st places">
                        1st Places
                      </th>
                      <th className="py-3 px-3 text-center cursor-pointer" onClick={() => handleSort('cardTotal')} title="Tie-Breaker 2: Lower card total">
                        Card Total
                      </th>
                      <th className="py-3 px-3 text-center">ECHO</th>
                      <th className="py-3 px-3 text-center">PRIME</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-cyan-500/10 text-xs text-slate-300">
                    {isLoading ? (
                      Array.from({ length: 8 }).map((_, i) => <TableRowSkeleton key={i} cols={12} />)
                    ) : paginatedRecords.length === 0 ? (
                      <tr>
                        <td colSpan={12} className="py-12 text-center text-slate-400">
                          {!data?.round1Finalized ? (
                            <div className="flex flex-col items-center justify-center gap-2 py-6">
                              <AlertTriangle className="w-8 h-8 text-amber-400" />
                              <span className="font-orbitron font-bold text-sm text-amber-300">
                                Waiting for Round 1 qualification
                              </span>
                              <span className="text-xs text-slate-400 max-w-md">
                                Round 2 (CABO) seating and scoreboards unlock automatically once the official Top 16 squads are finalized in Round 1.
                              </span>
                            </div>
                          ) : (
                            'No squad standings found.'
                          )}
                        </td>
                      </tr>
                    ) : (
                      paginatedRecords.map((rec) => {
                        const rankNum = rec.rank ?? null;
                        const isCutoffLine = rankNum === 8;
                        const isBeyondCutoff = rankNum !== null && rankNum > 8;

                        return (
                          <React.Fragment key={rec.teamId}>
                            <tr
                              className={`hover:bg-cyan-500/[0.05] transition-colors ${
                                isCutoffLine ? 'border-b-2 border-cyan-400 bg-cyan-950/20' : ''
                              } ${isBeyondCutoff ? 'opacity-85' : ''}`}
                            >
                              {/* Rank */}
                              <td className="py-3 px-3 text-center font-mono font-bold">
                                {rec.rank ? (
                                  rec.rank <= 3 ? (
                                    <span className="inline-flex items-center justify-center w-7 h-7 rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-black shadow-[0_0_10px_rgba(245,158,11,0.3)]">
                                      #{rec.rank}
                                    </span>
                                  ) : (
                                    <span className="text-cyan-300 font-mono font-bold">#{rec.rank}</span>
                                  )
                                ) : (
                                  <span className="text-slate-600 font-normal">—</span>
                                )}
                              </td>

                              {/* Squad */}
                              <td className="py-3 px-4">
                                <div className="flex items-center gap-2">
                                  <span className="font-mono text-[11px] font-semibold text-cyan-300 bg-cyan-950/50 px-1.5 py-0.5 rounded-lg border border-cyan-500/30">
                                    {formatTeamNumber(rec.teamNumber)}
                                  </span>
                                  <span className="font-orbitron font-semibold text-slate-100">{rec.teamName}</span>
                                </div>
                              </td>

                              {/* G1 */}
                              <td className="py-3 px-3 text-center font-mono text-slate-300">
                                {rec.game1Points !== null && rec.game1Points !== undefined ? `${rec.game1Points}p` : '—'}
                              </td>

                              {/* G2 */}
                              <td className="py-3 px-3 text-center font-mono text-slate-300">
                                {rec.game2Points !== null && rec.game2Points !== undefined ? `${rec.game2Points}p` : '—'}
                              </td>

                              {/* G3 */}
                              <td className="py-3 px-3 text-center font-mono text-slate-300">
                                {rec.game3Points !== null && rec.game3Points !== undefined ? `${rec.game3Points}p` : '—'}
                              </td>

                              {/* Total Points */}
                              <td className="py-3 px-4 text-right">
                                {rec.totalPoints !== null && rec.totalPoints !== undefined ? (
                                  <span className="font-mono font-extrabold text-sm text-cyan-300">
                                    {rec.totalPoints} pts
                                  </span>
                                ) : (
                                  <span className="text-slate-600 font-mono">—</span>
                                )}
                              </td>

                              {/* 1st Places */}
                              <td className="py-3 px-3 text-center font-mono text-slate-400">
                                {rec.firstPlaceCount ?? 0}
                              </td>

                              {/* Card Total */}
                              <td className="py-3 px-3 text-center font-mono text-slate-400">
                                {rec.combinedCardTotal ?? '—'}
                              </td>

                              {/* ECHO Status */}
                              <td className="py-3 px-3 text-center">
                                <button
                                  onClick={() => handleOpenEchoModal(rec)}
                                  className="cursor-pointer group flex items-center justify-center mx-auto"
                                  title="Click to verify ECHO marked cards"
                                >
                                  {rec.echoStatus === 'RECOVERED' ? (
                                    <span className="px-2 py-0.5 rounded font-mono text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                                      ECHO ✓
                                    </span>
                                  ) : (
                                    <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-slate-800 text-slate-400 group-hover:text-cyan-300 border border-slate-700">
                                      {rec.echoEVerified ? 'E' : '·'}{rec.echoCVerified ? 'C' : '·'}{rec.echoHoVerified ? 'HO' : '··'}
                                    </span>
                                  )}
                                </button>
                              </td>

                              {/* PRIME Status */}
                              <td className="py-3 px-3 text-center">
                                <button
                                  onClick={() => handleOpenPrimeModal(rec)}
                                  className="cursor-pointer group flex items-center justify-center mx-auto"
                                  title="Click to verify PRIME challenge"
                                >
                                  {rec.primeStatus === 'RECOVERED' ? (
                                    <span className="px-2 py-0.5 rounded font-mono text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40">
                                      PRIME ✓
                                    </span>
                                  ) : (
                                    <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-slate-800 text-slate-400 group-hover:text-cyan-300 border border-slate-700">
                                      Pending
                                    </span>
                                  )}
                                </button>
                              </td>

                              {/* Status */}
                              <td className="py-3 px-4">
                                {getStatusBadge(rec)}
                              </td>

                              {/* Actions */}
                              <td className="py-3 px-4 text-right">
                                <div className="flex items-center justify-end gap-1.5">
                                  <button
                                    onClick={() => handleOpenTeamDetail(rec.teamId)}
                                    className="p-1 rounded text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10"
                                    title="View 5-Member Performance Drill-Down"
                                  >
                                    <Info className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    onClick={() => handleOpenEchoModal(rec)}
                                    className="p-1 rounded text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10"
                                    title="Verify ECHO cards"
                                  >
                                    <Key className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    onClick={() => handleOpenPrimeModal(rec)}
                                    className="p-1 rounded text-slate-400 hover:text-purple-300 hover:bg-purple-500/10"
                                    title="Verify PRIME challenge"
                                  >
                                    <Sparkles className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              </td>
                            </tr>

                            {/* Cutoff Marker Row */}
                            {isCutoffLine && (
                              <tr className="bg-cyan-950/40 border-y-2 border-cyan-400/60 shadow-[0_0_12px_rgba(6,182,212,0.2)]">
                                <td colSpan={12} className="py-2.5 px-4 text-center text-xs font-orbitron font-bold text-cyan-300 tracking-wider uppercase">
                                  ⚡ Round 2 Cabo Cutoff Threshold — Top 8 Advance to Round 3: The Black Market
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ECHO Verification Modal */}
      {echoTeam && (
        <Modal
          isOpen={isEchoModalOpen}
          onClose={() => setIsEchoModalOpen(false)}
          title={`Verify ECHO Marked Cards — ${echoTeam.teamName}`}
          subtitle="Mark cards discovered across Cabo Games 1, 2, and 3. Full ECHO awarded only after all 3 verified."
          maxWidth="md"
          footer={
            <div className="flex items-center justify-end gap-2 w-full">
              <Button variant="outline" size="sm" onClick={() => setIsEchoModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" onClick={handleSaveEchoVerification} isLoading={isSubmitting}>
                Save Verification
              </Button>
            </div>
          }
        >
          <div className="space-y-4 text-xs">
            <div className="p-3 bg-cyan-950/40 border border-cyan-500/30 rounded-xl text-slate-300 space-y-1">
              <div className="font-bold text-cyan-300">ODDyssey Official Rule:</div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Only the player who receives the marked card may report it to their team.
                A volunteer verifies each marked card before awarding the fragment centrally.
              </p>
            </div>

            <div className="space-y-2.5">
              <label className="flex items-center gap-3 p-3 rounded-xl bg-slate-900 border border-slate-800 cursor-pointer hover:border-cyan-500/40">
                <input
                  type="checkbox"
                  checked={echoG1}
                  onChange={(e) => setEchoG1(e.target.checked)}
                  className="rounded border-slate-700 text-cyan-500 focus:ring-cyan-500"
                />
                <div>
                  <span className="font-bold text-slate-200">Game 1: Card Marked with &quot;E&quot;</span>
                  <span className="block text-[11px] text-slate-500">Verified by table marshal</span>
                </div>
              </label>

              <label className="flex items-center gap-3 p-3 rounded-xl bg-slate-900 border border-slate-800 cursor-pointer hover:border-cyan-500/40">
                <input
                  type="checkbox"
                  checked={echoG2}
                  onChange={(e) => setEchoG2(e.target.checked)}
                  className="rounded border-slate-700 text-cyan-500 focus:ring-cyan-500"
                />
                <div>
                  <span className="font-bold text-slate-200">Game 2: Card Marked with &quot;C&quot;</span>
                  <span className="block text-[11px] text-slate-500">Verified by table marshal</span>
                </div>
              </label>

              <label className="flex items-center gap-3 p-3 rounded-xl bg-slate-900 border border-slate-800 cursor-pointer hover:border-cyan-500/40">
                <input
                  type="checkbox"
                  checked={echoG3}
                  onChange={(e) => setEchoG3(e.target.checked)}
                  className="rounded border-slate-700 text-cyan-500 focus:ring-cyan-500"
                />
                <div>
                  <span className="font-bold text-slate-200">Game 3: Card Marked with &quot;HO&quot;</span>
                  <span className="block text-[11px] text-slate-500">Verified by table marshal</span>
                </div>
              </label>
            </div>

            {echoG1 && echoG2 && echoG3 ? (
              <div className="p-3 bg-emerald-950/40 border border-emerald-500/30 rounded-xl text-emerald-300 text-xs font-bold text-center">
                ✨ All 3 cards verified! Code Fragment &quot;ECHO&quot; will be officially awarded!
              </div>
            ) : (
              <div className="p-2.5 bg-amber-950/30 border border-amber-500/20 rounded-xl text-amber-300/80 text-[11px] text-center">
                Requires all 3 cards (E + C + HO) to assemble the ECHO fragment.
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* PRIME Verification Modal */}
      {primeTeam && (
        <Modal
          isOpen={isPrimeModalOpen}
          onClose={() => setIsPrimeModalOpen(false)}
          title={`Verify PRIME Number Challenge — ${primeTeam.teamName}`}
          subtitle="Number cards: 1, 2, 3, 4, 5, 7, 9, 11 · Primes: 2=P, 3=R, 5=I, 7=M, 11=E"
          maxWidth="md"
          footer={
            <div className="flex items-center justify-end gap-2 w-full">
              <Button variant="outline" size="sm" onClick={() => setIsPrimeModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" onClick={handleSavePrimeVerification} isLoading={isSubmitting}>
                Award PRIME Fragment
              </Button>
            </div>
          }
        >
          <div className="space-y-4 text-xs">
            <div className="p-3 bg-purple-950/40 border border-purple-500/30 rounded-xl text-slate-300 space-y-1">
              <div className="font-bold text-purple-300">Challenge Instructions:</div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                After Game 3, teams receive number cards [1, 2, 3, 4, 5, 7, 9, 11].
                Teams must identify prime numbers and arrange them smallest to largest:
                <strong> 2=P, 3=R, 5=I, 7=M, 11=E</strong> to spell <strong>PRIME</strong>.
              </p>
            </div>

            <div className="grid grid-cols-5 gap-2 text-center">
              {[
                { num: 2, letter: 'P' },
                { num: 3, letter: 'R' },
                { num: 5, letter: 'I' },
                { num: 7, letter: 'M' },
                { num: 11, letter: 'E' },
              ].map((c) => (
                <div key={c.num} className="p-2.5 rounded-xl bg-slate-900 border border-purple-500/40 font-mono">
                  <div className="text-xs text-purple-400 font-bold">{c.num}</div>
                  <div className="text-lg font-black text-slate-100">{c.letter}</div>
                </div>
              ))}
            </div>

            <label className="flex items-center gap-3 p-3 rounded-xl bg-slate-900 border border-slate-800 cursor-pointer hover:border-purple-500/40">
              <input
                type="checkbox"
                checked={primeSequenceVerified}
                onChange={(e) => setPrimeSequenceVerified(e.target.checked)}
                className="rounded border-slate-700 text-purple-500 focus:ring-purple-500"
              />
              <div>
                <span className="font-bold text-slate-200">Volunteer Verification</span>
                <span className="block text-[11px] text-slate-500">
                  Confirmed: Team successfully arranged prime cards smallest to largest spelling PRIME.
                </span>
              </div>
            </label>
          </div>
        </Modal>
      )}

      {/* Table Score Entry Modal */}
      <Modal
        isOpen={isTableScoreModalOpen}
        onClose={() => setIsTableScoreModalOpen(false)}
        title={`Enter Scores — Table ${scoreTableNum} (Game ${scoreTableGameNum})`}
        subtitle="5 seated players · Assign unique placements 1st through 5th · Points calculated automatically"
        maxWidth="lg"
        footer={
          <div className="flex items-center justify-between w-full">
            <span className="text-[11px] text-slate-500 font-mono">1st=5p, 2nd=3p, 3rd=2p, 4th=1p, 5th=0p</span>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setIsTableScoreModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" onClick={handleSaveTableScores} isLoading={isSubmitting}>
                Save Table Scores
              </Button>
            </div>
          </div>
        }
      >
        <div className="space-y-4 text-xs">
          {tableScoreError && (
            <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{tableScoreError}</span>
            </div>
          )}

          <div className="space-y-2">
            {tablePlayersScores.map((p, idx) => (
              <div
                key={p.participantId}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-xl bg-slate-900 border border-slate-800"
              >
                <div>
                  <div className="font-bold text-slate-200">{p.participantName}</div>
                  <div className="text-[11px] text-slate-400 font-mono">{p.teamName}</div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] text-slate-400 font-mono">Placement:</span>
                    <select
                      value={p.placement}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10);
                        const copy = [...tablePlayersScores];
                        copy[idx].placement = val;
                        setTablePlayersScores(copy);
                        setTableScoreError(null);
                      }}
                      className="px-2.5 py-1 rounded bg-slate-800 border border-slate-700 font-mono font-bold text-cyan-300 text-xs focus:outline-none focus:ring-1 focus:ring-cyan-500"
                    >
                      <option value={1}>1st (5 pts)</option>
                      <option value={2}>2nd (3 pts)</option>
                      <option value={3}>3rd (2 pts)</option>
                      <option value={4}>4th (1 pt)</option>
                      <option value={5}>5th (0 pts)</option>
                    </select>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] text-slate-400 font-mono" title="Combined final card total (tie-breaker)">
                      Cards:
                    </span>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={p.finalCardHandTotal}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10) || 0;
                        const copy = [...tablePlayersScores];
                        copy[idx].finalCardHandTotal = val;
                        setTablePlayersScores(copy);
                      }}
                      className="w-16 px-2 py-1 rounded bg-slate-800 border border-slate-700 font-mono text-center text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Modal>

      {/* Confirm Tables Modal */}
      <ConfirmationDialog
        isOpen={isConfirmTablesModalOpen}
        onClose={() => setIsConfirmTablesModalOpen(false)}
        onConfirm={handleConfirmTables}
        title="Confirm & Freeze Round 2 Table Seating"
        message="Are you sure you want to officially confirm and freeze the Cabo table assignments? All 8 structural constraints have passed. Once confirmed, tables are locked and cannot be regenerated without explicit override confirmation."
        confirmLabel="Confirm & Freeze Tables"
        isDestructive={false}
        isLoading={isSubmitting}
      />

      {/* Safe Regenerate Confirmation Modal */}
      <ConfirmationDialog
        isOpen={isRegenerateModalOpen}
        onClose={() => setIsRegenerateModalOpen(false)}
        onConfirm={() => handleExecuteGenerate(true)}
        title="Override & Regenerate Confirmed Tables"
        message="WARNING: Cabo tables have already been confirmed and frozen. Regenerating will reset all table allocations and clear any existing Cabo scorecards. Are you sure you want to force regeneration?"
        confirmLabel="Force Regenerate Tables"
        isDestructive={true}
        isLoading={isSubmitting}
      />

      {/* Player Drill-Down Modal */}
      {playerDetail && (
        <Modal
          isOpen={isPlayerModalOpen}
          onClose={() => setIsPlayerModalOpen(false)}
          title={`Player Dossier: ${playerDetail.participantName}`}
          subtitle={`Squad: ${playerDetail.teamName} ${playerDetail.participantUsn ? `· USN: ${playerDetail.participantUsn}` : ''}`}
          maxWidth="lg"
          footer={
            <div className="flex items-center justify-between w-full text-xs">
              <span className="font-mono text-cyan-300 font-bold">
                Total Individual Points: {playerDetail.totalPoints} pts · 1st Place Finishes: {playerDetail.firstPlacesCount}
              </span>
              <Button variant="outline" size="sm" onClick={() => setIsPlayerModalOpen(false)}>
                Close
              </Button>
            </div>
          }
        >
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {[1, 2, 3].map((gNum) => {
                const g = playerDetail.games.find((x) => x.gameNumber === gNum);
                return (
                  <div key={gNum} className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-1.5 font-orbitron font-bold text-cyan-300">
                      <span>Game {gNum}</span>
                      {g ? (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                          Table {g.tableNumber} · Seat {g.seatPosition}
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-500 font-mono">Unassigned</span>
                      )}
                    </div>
                    {g ? (
                      <div className="space-y-1 font-mono text-[11px]">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Finish:</span>
                          <span className="font-bold text-amber-300">{g.placement ? `${g.placement}th Place` : 'Not Logged'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Points Awarded:</span>
                          <span className="font-bold text-emerald-300">{g.placementPoints !== null && g.placementPoints !== undefined ? `${g.placementPoints} pts` : '—'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Card Total:</span>
                          <span className="text-slate-200">{g.finalCardHandTotal ?? '—'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Verified:</span>
                          <span className={g.isVerified ? 'text-emerald-400 font-bold' : 'text-slate-500'}>
                            {g.isVerified ? 'YES ✓' : 'NO'}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="py-4 text-center text-slate-500 font-mono">No game record</div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </Modal>
      )}

      {/* Team Drill-Down Modal */}
      {teamDetail && (
        <Modal
          isOpen={isTeamModalOpen}
          onClose={() => setIsTeamModalOpen(false)}
          title={`Squad Performance: ${teamDetail.teamName}`}
          subtitle={`Team #${teamDetail.teamNumber} · 5 Members · 15 Player-Games · Squad Score: ${teamDetail.caboSquadTotal}/75 pts`}
          maxWidth="2xl"
          footer={
            <div className="flex items-center justify-between w-full text-xs">
              <div className="font-mono text-cyan-300 font-bold flex items-center gap-3">
                <span>G1: {teamDetail.game1Total}p</span>
                <span>G2: {teamDetail.game2Total}p</span>
                <span>G3: {teamDetail.game3Total}p</span>
                <span className="text-amber-300 font-black">Total: {teamDetail.caboSquadTotal}/75</span>
              </div>
              <Button variant="outline" size="sm" onClick={() => setIsTeamModalOpen(false)}>
                Close
              </Button>
            </div>
          }
        >
          <div className="space-y-4 text-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs font-mono">
                <thead>
                  <tr className="border-b border-cyan-500/20 bg-slate-900/80 text-[11px] text-cyan-400 uppercase">
                    <th className="py-2.5 px-3">Player</th>
                    <th className="py-2.5 px-3">Role</th>
                    <th className="py-2.5 px-2 text-center">G1 Tbl</th>
                    <th className="py-2.5 px-2 text-center">G1 Place</th>
                    <th className="py-2.5 px-2 text-center">G2 Tbl</th>
                    <th className="py-2.5 px-2 text-center">G2 Place</th>
                    <th className="py-2.5 px-2 text-center">G3 Tbl</th>
                    <th className="py-2.5 px-2 text-center">G3 Place</th>
                    <th className="py-2.5 px-3 text-right">Indiv Pts</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-300">
                  {teamDetail.members.map((m) => (
                    <tr key={m.participantId} className="hover:bg-cyan-500/5">
                      <td className="py-2.5 px-3 font-semibold text-slate-100">
                        <div>{m.participantName}</div>
                        {m.participantUsn && <div className="text-[10px] text-slate-500">{m.participantUsn}</div>}
                      </td>
                      <td className="py-2.5 px-3 text-slate-400 capitalize">{m.role}</td>
                      <td className="py-2.5 px-2 text-center text-slate-400">{m.game1Table ? `T${m.game1Table}` : '—'}</td>
                      <td className="py-2.5 px-2 text-center font-bold text-amber-300">{m.game1Placement ? `${m.game1Placement}th (${m.game1Points}p)` : '—'}</td>
                      <td className="py-2.5 px-2 text-center text-slate-400">{m.game2Table ? `T${m.game2Table}` : '—'}</td>
                      <td className="py-2.5 px-2 text-center font-bold text-amber-300">{m.game2Placement ? `${m.game2Placement}th (${m.game2Points}p)` : '—'}</td>
                      <td className="py-2.5 px-2 text-center text-slate-400">{m.game3Table ? `T${m.game3Table}` : '—'}</td>
                      <td className="py-2.5 px-2 text-center font-bold text-amber-300">{m.game3Placement ? `${m.game3Placement}th (${m.game3Points}p)` : '—'}</td>
                      <td className="py-2.5 px-3 text-right font-black text-cyan-300">{m.totalIndividualPoints} pts</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Modal>
      )}

      {/* Organizer Score Correction Modal */}
      {correctionTarget && (
        <Modal
          isOpen={isCorrectionModalOpen}
          onClose={() => setIsCorrectionModalOpen(false)}
          title={`Organizer Score Correction — Table ${correctionTarget.tableNumber} (Game ${correctionTarget.gameNumber})`}
          subtitle={`Player: ${correctionTarget.participantName} (${correctionTarget.teamName})`}
          maxWidth="md"
          footer={
            <div className="flex items-center justify-end gap-2 w-full">
              <Button variant="outline" size="sm" onClick={() => setIsCorrectionModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" onClick={handleSaveScoreCorrection} isLoading={isSubmitting}>
                Save & Record Audit Trail
              </Button>
            </div>
          }
        >
          <div className="space-y-4 text-xs">
            <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-500/30 text-amber-300 space-y-1">
              <div className="font-bold flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                <span>Audited Administrative Action</span>
              </div>
              <p className="text-[11px] text-amber-200/90 leading-relaxed">
                Modifying this player&apos;s placement will swap placements with the player currently occupying that position at Table {correctionTarget.tableNumber}.
                Points will recalculate automatically and the reason will be logged permanently in audit records.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-400 font-mono text-[11px] mb-1">Current Placement</label>
                <div className="p-2 rounded bg-slate-900 border border-slate-800 font-mono font-bold text-slate-300">
                  {correctionTarget.oldPlacement}th Place
                </div>
              </div>
              <div>
                <label className="block text-slate-400 font-mono text-[11px] mb-1">New Placement</label>
                <select
                  value={correctionTarget.newPlacement}
                  onChange={(e) => setCorrectionTarget({ ...correctionTarget, newPlacement: parseInt(e.target.value, 10) })}
                  className="w-full p-2 rounded bg-slate-800 border border-slate-700 font-mono font-bold text-cyan-300 text-xs focus:ring-1 focus:ring-cyan-500"
                >
                  <option value={1}>1st Place (5 pts)</option>
                  <option value={2}>2nd Place (3 pts)</option>
                  <option value={3}>3rd Place (2 pts)</option>
                  <option value={4}>4th Place (1 pt)</option>
                  <option value={5}>5th Place (0 pts)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-slate-400 font-mono text-[11px] mb-1">
                Mandatory Correction Reason <span className="text-rose-400">*</span>
              </label>
              <textarea
                rows={3}
                value={correctionTarget.reason}
                onChange={(e) => setCorrectionTarget({ ...correctionTarget, reason: e.target.value })}
                placeholder="e.g. Card dispute reviewed by lead marshal; confirmed final hand score..."
                className="w-full p-2.5 rounded bg-slate-900 border border-slate-700 font-mono text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
            </div>
          </div>
        </Modal>
      )}

      {/* Printable Table Sheets Modal */}
      {printableData && (
        <Modal
          isOpen={isPrintModalOpen}
          onClose={() => setIsPrintModalOpen(false)}
          title={`Printable Table Sheets — Cabo Game ${printableData.gameNumber}`}
          subtitle="Official Seating Sheets for Marshals & Table Leads (16 Tables)"
          maxWidth="2xl"
          footer={
            <div className="flex items-center justify-between w-full">
              <Button
                variant="primary"
                size="sm"
                onClick={() => window.print()}
                leftIcon={<Printer className="w-3.5 h-3.5" />}
              >
                Print All 16 Sheets
              </Button>
              <Button variant="outline" size="sm" onClick={() => setIsPrintModalOpen(false)}>
                Close
              </Button>
            </div>
          }
        >
          <div className="space-y-6 text-xs max-h-[70vh] overflow-y-auto pr-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {printableData.tables.map((tbl) => (
                <div key={tbl.tableNumber} className="p-4 rounded-xl border border-slate-700 bg-slate-950 space-y-2.5">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="font-orbitron font-bold text-sm text-cyan-300">
                      Table {tbl.tableNumber} (Game {printableData.gameNumber})
                    </span>
                    <span className="font-mono text-[10px] text-slate-400">5 Seated Players</span>
                  </div>
                  <div className="space-y-1.5 font-mono text-[11px]">
                    {tbl.players.map((p) => (
                      <div key={p.seatPosition} className="flex justify-between items-center p-1.5 rounded bg-slate-900 border border-slate-800">
                        <div className="truncate mr-2">
                          <span className="text-cyan-400 font-bold mr-1">S{p.seatPosition}:</span>
                          <span className="font-semibold text-slate-200">{p.participantName}</span>
                          <span className="text-[10px] text-slate-400 block truncate">{p.teamName}</span>
                        </div>
                        <div className="w-16 h-6 border border-dashed border-slate-700 rounded text-center text-[10px] text-slate-600 flex items-center justify-center">
                          Place: ____
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Modal>
      )}

      {/* Finalize Round 2 Confirmation Modal */}
      <ConfirmationDialog
        isOpen={isFinalizeConfirmOpen}
        onClose={() => setIsFinalizeConfirmOpen(false)}
        onConfirm={handleFinalizeRound2}
        title="Finalize Round 2 Qualification to Round 3: The Black Market"
        message="Are you sure you want to seal official Round 2 results? Exactly the Top 8 squads will advance to Round 3 without re-registration, and 8 squads will be eliminated. All scorecards and fragments will be preserved."
        confirmLabel="Confirm &amp; Advance Top 8"
        isDestructive={false}
        isLoading={isSubmitting}
      />
    </div>
  );
};

