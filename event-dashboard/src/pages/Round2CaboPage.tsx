import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Layers,
  Trophy,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowUpDown,
  Settings,
  Sparkles,
  RotateCcw,
  ExternalLink,
  ShieldAlert,
  Edit3,
  Trash2,
} from 'lucide-react';
import { eventService } from '../services/eventService';
import {
  Round2Data,
  TeamRound2Record,
  CaboScoringDirection,
  CaboTiePolicy,
} from '../types/round2';
import { formatTeamNumber } from '../utils/formatters';
import { createDefaultPointTable, isPointTableValid } from '../utils/round2Scoring';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { ConfirmationDialog } from '../components/ui/ConfirmationDialog';
import { TableRowSkeleton } from '../components/ui/LoadingSkeleton';
import { EmptyState } from '../components/ui/EmptyState';
import { MetricCard } from '../components/dashboard/MetricCard';
import { PageHeader } from '../components/ui/PageHeader';
import { SearchFilterToolbar } from '../components/ui/SearchFilterToolbar';
import { Card, CardHeader, CardContent } from '../components/ui/Card';

type TabView = 'leaderboard' | 'game1' | 'game2' | 'game3';
type SortField = 'rank' | 'teamNumber' | 'name' | 'totalPoints' | 'g1' | 'g2' | 'g3';

export const Round2CaboPage: React.FC = () => {
  const navigate = useNavigate();

  // Data State
  const [data, setData] = useState<Round2Data | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Active View Tab
  const [activeTab, setActiveTab] = useState<TabView>('leaderboard');

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterCompletion, setFilterCompletion] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('rank');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 12; // 12 or 24 fits 24 squads cleanly

  // Modals
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [isEditTeamModalOpen, setIsEditTeamModalOpen] = useState(false);
  const [selectedTeamRecord, setSelectedTeamRecord] = useState<TeamRound2Record | null>(null);
  const [isFinalizeConfirmOpen, setIsFinalizeConfirmOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Edit Team Placements Form
  const [editG1Placement, setEditG1Placement] = useState<string>('');
  const [editG2Placement, setEditG2Placement] = useState<string>('');
  const [editG3Placement, setEditG3Placement] = useState<string>('');
  const [editFormError, setEditFormError] = useState<string | null>(null);

  // Single Game Console Placement Form
  const [gameSelectedTeamId, setGameSelectedTeamId] = useState<string>('');
  const [gamePlacementInput, setGamePlacementInput] = useState<string>('');
  const [gameNotesInput, setGameNotesInput] = useState<string>('');
  const [gameFormError, setGameFormError] = useState<string | null>(null);

  // Config Drawer Form States
  const [configDirection, setConfigDirection] = useState<CaboScoringDirection>('higher_is_better');
  const [configTiePolicy, setConfigTiePolicy] = useState<CaboTiePolicy>('strict_unique');
  const [configPointTable, setConfigPointTable] = useState<Record<number, number>>(createDefaultPointTable());
  const [configError, setConfigError] = useState<string | null>(null);

  // Load Data
  const loadRound2 = async () => {
    try {
      const r2Data = await eventService.getRound2Data();
      setData(r2Data);

      setConfigDirection(r2Data.config.scoringDirection);
      setConfigTiePolicy(r2Data.config.tiePolicy);
      setConfigPointTable({ ...r2Data.config.pointTable });

      if (selectedTeamRecord) {
        const updated = r2Data.records.find((r) => r.teamId === selectedTeamRecord.teamId);
        if (updated) setSelectedTeamRecord(updated);
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
  }, []);

  // Filter & Sort for Overall Standings
  const filteredAndSortedRecords = useMemo(() => {
    if (!data) return [];
    return data.records
      .filter((rec) => {
        const q = searchQuery.toLowerCase().trim();
        const matchesSearch =
          q === '' ||
          rec.teamName.toLowerCase().includes(q) ||
          formatTeamNumber(rec.teamNumber).toLowerCase().includes(q);

        let matchesStatus = true;
        if (filterStatus === 'top12') {
          matchesStatus = rec.qualificationStatus === 'Provisional Top 12' || rec.qualificationStatus === 'Finalized Qualified';
        } else if (filterStatus === 'eliminated') {
          matchesStatus = rec.qualificationStatus === 'Provisional Cutoff' || rec.qualificationStatus === 'Finalized Eliminated';
        } else if (filterStatus === 'tieReview') {
          matchesStatus = rec.qualificationStatus === 'Tie Review Needed';
        } else if (filterStatus === 'incomplete') {
          matchesStatus = rec.qualificationStatus === 'Incomplete';
        }

        let matchesCompletion = true;
        if (filterCompletion === 'complete') {
          matchesCompletion = rec.isComplete;
        } else if (filterCompletion === 'missing') {
          matchesCompletion = !rec.isComplete;
        } else if (filterCompletion === 'missingG1') {
          matchesCompletion = rec.game1Placement === null || rec.game1Placement === undefined;
        } else if (filterCompletion === 'missingG2') {
          matchesCompletion = rec.game2Placement === null || rec.game2Placement === undefined;
        } else if (filterCompletion === 'missingG3') {
          matchesCompletion = rec.game3Placement === null || rec.game3Placement === undefined;
        }

        return matchesSearch && matchesStatus && matchesCompletion;
      })
      .sort((a, b) => {
        let comparison = 0;
        if (sortField === 'rank') {
          const aRank = a.rank ?? null;
          const bRank = b.rank ?? null;
          if (aRank === null && bRank === null) comparison = a.teamNumber - b.teamNumber;
          else if (aRank === null) comparison = 1;
          else if (bRank === null) comparison = -1;
          else comparison = aRank - bRank;
        } else if (sortField === 'teamNumber') {
          comparison = a.teamNumber - b.teamNumber;
        } else if (sortField === 'name') {
          comparison = a.teamName.localeCompare(b.teamName);
        } else if (sortField === 'totalPoints') {
          const aPts = a.totalPoints ?? null;
          const bPts = b.totalPoints ?? null;
          if (aPts === null && bPts === null) comparison = 0;
          else if (aPts === null) comparison = 1;
          else if (bPts === null) comparison = -1;
          else {
            comparison = data.config.scoringDirection === 'higher_is_better' ? bPts - aPts : aPts - bPts;
          }
        } else if (sortField === 'g1') {
          const aP = a.game1Placement ?? 999;
          const bP = b.game1Placement ?? 999;
          comparison = aP - bP;
        } else if (sortField === 'g2') {
          const aP = a.game2Placement ?? 999;
          const bP = b.game2Placement ?? 999;
          comparison = aP - bP;
        } else if (sortField === 'g3') {
          const aP = a.game3Placement ?? 999;
          const bP = b.game3Placement ?? 999;
          comparison = aP - bP;
        }
        return sortOrder === 'asc' ? comparison : -comparison;
      });
  }, [data, searchQuery, filterStatus, filterCompletion, sortField, sortOrder]);

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

  // Open Edit Team Placements Modal
  const handleOpenEditTeam = (rec: TeamRound2Record) => {
    setSelectedTeamRecord(rec);
    setEditG1Placement(rec.game1Placement ? rec.game1Placement.toString() : '');
    setEditG2Placement(rec.game2Placement ? rec.game2Placement.toString() : '');
    setEditG3Placement(rec.game3Placement ? rec.game3Placement.toString() : '');
    setEditFormError(null);
    setIsEditTeamModalOpen(true);
  };

  // Save Team Placements
  const handleSaveTeamPlacements = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTeamRecord || !data) return;
    setEditFormError(null);
    setIsSubmitting(true);

    try {
      // Validate inputs if provided
      const parseVal = (str: string, gameNum: 1 | 2 | 3) => {
        if (!str.trim()) return null;
        const num = parseInt(str, 10);
        if (isNaN(num) || num < 1 || num > 24) {
          throw new Error(`Game ${gameNum} placement must be a whole number between 1 and 24.`);
        }
        return num;
      };

      const p1 = parseVal(editG1Placement, 1);
      const p2 = parseVal(editG2Placement, 2);
      const p3 = parseVal(editG3Placement, 3);

      // Save or clear Game 1
      if (p1 !== null) {
        await eventService.recordCaboGamePlacement(1, selectedTeamRecord.teamId, p1);
      } else if (selectedTeamRecord.game1Placement !== null && selectedTeamRecord.game1Placement !== undefined) {
        await eventService.clearCaboGamePlacement(1, selectedTeamRecord.teamId);
      }

      // Save or clear Game 2
      if (p2 !== null) {
        await eventService.recordCaboGamePlacement(2, selectedTeamRecord.teamId, p2);
      } else if (selectedTeamRecord.game2Placement !== null && selectedTeamRecord.game2Placement !== undefined) {
        await eventService.clearCaboGamePlacement(2, selectedTeamRecord.teamId);
      }

      // Save or clear Game 3
      if (p3 !== null) {
        await eventService.recordCaboGamePlacement(3, selectedTeamRecord.teamId, p3);
      } else if (selectedTeamRecord.game3Placement !== null && selectedTeamRecord.game3Placement !== undefined) {
        await eventService.clearCaboGamePlacement(3, selectedTeamRecord.teamId);
      }

      setIsEditTeamModalOpen(false);
    } catch (err: unknown) {
      setEditFormError((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Single Game Console Placement Submission
  const handleRecordGamePlacement = async (gameNum: 1 | 2 | 3) => {
    if (!gameSelectedTeamId) {
      setGameFormError('Please select a participating squad.');
      return;
    }
    const p = parseInt(gamePlacementInput, 10);
    if (isNaN(p) || p < 1 || p > 24) {
      setGameFormError('Placement must be a valid positive number between 1 and 24.');
      return;
    }

    setGameFormError(null);
    setIsSubmitting(true);
    try {
      await eventService.recordCaboGamePlacement(gameNum, gameSelectedTeamId, p, gameNotesInput);
      setGamePlacementInput('');
      setGameNotesInput('');
      setGameSelectedTeamId('');
    } catch (err: unknown) {
      setGameFormError((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClearPlacement = async (gameNum: 1 | 2 | 3, teamId: string) => {
    if (confirm('Clear placement record for this squad in this game?')) {
      try {
        await eventService.clearCaboGamePlacement(gameNum, teamId);
      } catch (err: unknown) {
        alert((err as Error).message);
      }
    }
  };

  // Save Scoring Config
  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setConfigError(null);

    if (!isPointTableValid(configPointTable)) {
      setConfigError('All 24 placement values must have non-negative point numbers.');
      return;
    }

    setIsSubmitting(true);
    try {
      await eventService.updateCaboConfig({
        scoringDirection: configDirection,
        tiePolicy: configTiePolicy,
        pointTable: configPointTable,
      });
      setIsConfigOpen(false);
    } catch (err: unknown) {
      setConfigError((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetPointTableDefaults = () => {
    if (confirm('Reset point table back to linear demo defaults (24 to 1 points)?')) {
      setConfigPointTable(createDefaultPointTable());
    }
  };

  // Finalize Round 2
  const handleFinalizeRound2 = async () => {
    setIsSubmitting(true);
    try {
      await eventService.finalizeRound2();
      setIsFinalizeConfirmOpen(false);
    } catch (err: unknown) {
      alert((err as Error).message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Reset Placements
  const handleResetPlacements = async () => {
    if (confirm('Reset all Cabo game placements? Team rosters and configuration will NOT be lost.')) {
      await eventService.resetRound2Placements();
    }
  };

  // Simulate Complete Field
  const handleSimulateField = async () => {
    if (confirm('Simulate complete placements for all 24 squads across all 3 games? This allows testing 12-team qualification.')) {
      await eventService.simulateCompleteRound2Games();
    }
  };

  const getStatusBadge = (status: TeamRound2Record['qualificationStatus']) => {
    switch (status) {
      case 'Finalized Qualified':
        return (
          <Badge variant="success" size="sm" dot>
            Finalized Top 12 (To R3)
          </Badge>
        );
      case 'Finalized Eliminated':
        return (
          <Badge variant="danger" size="sm">
            Eliminated
          </Badge>
        );
      case 'Provisional Top 12':
        return (
          <Badge variant="primary" size="sm" dot>
            Provisional Top 12
          </Badge>
        );
      case 'Provisional Cutoff':
        return (
          <Badge variant="danger" size="sm">
            Elimination Zone
          </Badge>
        );
      case 'Tie Review Needed':
        return (
          <Badge variant="warning" size="sm" dot>
            Tie Review Needed
          </Badge>
        );
      case 'Round 1 Pending':
        return (
          <Badge variant="neutral" size="sm">
            R1 Pending
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

  // Render Single Game Console View
  const renderGameConsole = (gameNum: 1 | 2 | 3) => {
    if (!data) return null;
    const game = data.games[gameNum - 1];
    const eligibleTeams = eventService.getEligibleRound2Teams();

    // Map participating teams with their placement in this game
    const teamEntries = eligibleTeams.map((team) => {
      const p = game.placements[team.id];
      return {
        team,
        placement: p?.placement ?? null,
        points: p?.points ?? null,
        recordedAt: p?.recordedAt ?? null,
        notes: p?.notes ?? null,
      };
    });

    const recordedEntries = teamEntries.filter((e) => e.placement !== null).sort((a, b) => a.placement! - b.placement!);
    const unrecordedEntries = teamEntries.filter((e) => e.placement === null);

    return (
      <div className="space-y-6">
        {/* Game Console Header Bar */}
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-card flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                GAME 0{gameNum}
              </span>
              <h3 className="text-sm font-bold text-slate-800">{game.name} Placement Console</h3>
              {game.isCompleted ? (
                <Badge variant="success" size="sm" dot>
                  Complete (24/24)
                </Badge>
              ) : (
                <Badge variant="warning" size="sm" dot>
                  {Object.keys(game.placements).length} / 24 Logged
                </Badge>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Record official placements (1st to 24th) for participating squads. Points are derived automatically from the configured point table.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">
              Policy: <strong>{data.config.tiePolicy === 'strict_unique' ? 'Strict (No Duplicates)' : 'Shared Permitted'}</strong>
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsConfigOpen(true)}
              leftIcon={<Settings className="w-3.5 h-3.5" />}
            >
              Configure Points Table
            </Button>
          </div>
        </div>

        {/* Record Placement Quick-Action Card */}
        {!data.config.isFinalized && (
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-card">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Edit3 className="w-4 h-4 text-blue-600" />
              <span>Record Placement for Game {gameNum}</span>
            </h4>

            {gameFormError && (
              <div className="mb-3 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <span>{gameFormError}</span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
              <div className="sm:col-span-5">
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                  Select Squad:
                </label>
                <select
                  value={gameSelectedTeamId}
                  onChange={(e) => {
                    setGameSelectedTeamId(e.target.value);
                    setGameFormError(null);
                  }}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                >
                  <option value="">Choose Participating Squad...</option>
                  {eligibleTeams.map((t) => {
                    const hasPlacement = game.placements[t.id] !== undefined;
                    return (
                      <option key={t.id} value={t.id}>
                        {formatTeamNumber(t.teamNumber)} — {t.name} {hasPlacement ? `(Current: #${game.placements[t.id].placement})` : '— [Pending]'}
                      </option>
                    );
                  })}
                </select>
              </div>

              <div className="sm:col-span-3">
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                  Placement (1–24):
                </label>
                <input
                  type="number"
                  min="1"
                  max="24"
                  placeholder="e.g. 1"
                  value={gamePlacementInput}
                  onChange={(e) => {
                    setGamePlacementInput(e.target.value);
                    setGameFormError(null);
                  }}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg font-mono text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                />
              </div>

              <div className="sm:col-span-2">
                <div className="text-[11px] text-slate-500 mb-1 font-semibold">
                  Point Value:
                </div>
                <div className="px-3 py-2 bg-slate-100 border border-slate-200 rounded-lg font-mono text-xs text-slate-700">
                  {gamePlacementInput && parseInt(gamePlacementInput, 10) >= 1 && parseInt(gamePlacementInput, 10) <= 24
                    ? `${data.config.pointTable[parseInt(gamePlacementInput, 10)] ?? 0} pts`
                    : '—'}
                </div>
              </div>

              <div className="sm:col-span-2">
                <Button
                  variant="primary"
                  size="sm"
                  className="w-full justify-center"
                  onClick={() => handleRecordGamePlacement(gameNum)}
                  isLoading={isSubmitting}
                >
                  Save Result
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Game Standings & Missing Teams Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recorded Standings (2 Columns) */}
          <div className="lg:col-span-2 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Recorded Standings ({recordedEntries.length})
              </h4>
              <span className="text-xs text-slate-400 font-mono">Game {gameNum} Leaderboard</span>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 shadow-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                      <th className="py-2.5 px-3 text-center w-16">Placement</th>
                      <th className="py-2.5 px-4">Squad</th>
                      <th className="py-2.5 px-3 text-right">Points Earned</th>
                      {!data.config.isFinalized && <th className="py-2.5 px-3 text-right">Action</th>}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs">
                    {recordedEntries.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="py-8 text-center text-slate-400">
                          No placements recorded yet for Game {gameNum}.
                        </td>
                      </tr>
                    ) : (
                      recordedEntries.map((e) => (
                        <tr key={e.team.id} className="hover:bg-slate-50/80 transition-colors">
                          <td className="py-2.5 px-3 text-center font-mono font-bold">
                            {e.placement! <= 3 ? (
                              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-100 text-amber-800 text-xs font-black">
                                #{e.placement}
                              </span>
                            ) : (
                              <span className="text-slate-700">#{e.placement}</span>
                            )}
                          </td>
                          <td className="py-2.5 px-4">
                            <span className="font-mono text-[11px] text-blue-600 mr-2">
                              {formatTeamNumber(e.team.teamNumber)}
                            </span>
                            <span className="font-semibold text-slate-800">{e.team.name}</span>
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-700">
                            +{e.points} pts
                          </td>
                          {!data.config.isFinalized && (
                            <td className="py-2.5 px-3 text-right">
                              <button
                                onClick={() => handleClearPlacement(gameNum, e.team.id)}
                                className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors"
                                title="Clear placement"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </td>
                          )}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Missing Results Panel (1 Column) */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Missing Results ({unrecordedEntries.length})
              </h4>
              <span className="text-[11px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                Pending Log
              </span>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 shadow-card p-4 space-y-2">
              {unrecordedEntries.length === 0 ? (
                <div className="py-6 text-center text-emerald-600 text-xs flex flex-col items-center gap-1">
                  <CheckCircle2 className="w-6 h-6" />
                  <span className="font-bold">All 24 Squads Recorded!</span>
                  <span className="text-slate-400 text-[11px]">Game {gameNum} has complete verified results.</span>
                </div>
              ) : (
                <div className="space-y-1.5 max-h-[400px] overflow-y-auto pr-1">
                  <p className="text-[11px] text-slate-500 mb-2">
                    These participating squads do not have a placement logged for Game {gameNum} yet:
                  </p>
                  {unrecordedEntries.map((e) => (
                    <div
                      key={e.team.id}
                      className="p-2 bg-slate-50 hover:bg-blue-50/50 rounded-lg border border-slate-200/80 flex items-center justify-between text-xs transition-colors"
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span className="font-mono text-slate-400 text-[11px]">
                          {formatTeamNumber(e.team.teamNumber)}
                        </span>
                        <span className="font-medium text-slate-700 truncate">{e.team.name}</span>
                      </div>
                      {!data.config.isFinalized && (
                        <button
                          onClick={() => {
                            setGameSelectedTeamId(e.team.id);
                            setGamePlacementInput('');
                            setGameFormError(null);
                          }}
                          className="text-[11px] text-blue-600 hover:underline shrink-0 ml-2"
                        >
                          Select &rarr;
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Round 2: Cabo Operations Console"
        subtitle="24 Qualified Teams from R1 · 3 Cabo Games · Top 12 advance to Round 3: The Black Market"
        badge={
          data?.config.isFinalized ? (
            <Badge variant="success" size="sm" dot>
              Finalized &amp; Sealed
            </Badge>
          ) : !data?.round1Finalized ? (
            <Badge variant="warning" size="sm" dot>
              R1 Standby (Unfinalized)
            </Badge>
          ) : (
            <Badge variant="primary" size="sm" dot>
              Live Cabo Games
            </Badge>
          )
        }
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsConfigOpen(true)}
              leftIcon={<Settings className="w-3.5 h-3.5" />}
            >
              Scoring &amp; Rules
            </Button>

            {!data?.config.isFinalized && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSimulateField}
                  leftIcon={<Sparkles className="w-3.5 h-3.5 text-purple-600" />}
                  title="Fill all 24 squads with valid placements across Games 1, 2, and 3"
                >
                  Simulate Games
                </Button>

                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setIsFinalizeConfirmOpen(true)}
                  leftIcon={<Trophy className="w-3.5 h-3.5" />}
                  disabled={!data?.engine.canFinalize}
                >
                  Finalize Top 12
                </Button>
              </>
            )}

            <Button
              variant="ghost"
              size="sm"
              onClick={handleResetPlacements}
              leftIcon={<RotateCcw className="w-3.5 h-3.5 text-slate-400" />}
              title="Reset game placements"
            >
              Reset Placements
            </Button>
          </>
        }
      />

      {/* Warning if Round 1 is NOT finalized */}
      {!data?.round1Finalized && (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start justify-between gap-3 shadow-sm">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-amber-950">Round 1 (The Great Expedition) Is Not Yet Finalized!</span>
              <p className="mt-0.5 leading-relaxed text-amber-800">
                Official Round 2 qualification to Round 3 is <strong>strictly blocked</strong> until Round 1 results are officially sealed.
                The 24 squads shown below are currently derived from provisional Round 1 standings.
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/round-1')}
            leftIcon={<ExternalLink className="w-3.5 h-3.5 text-amber-800" />}
            className="shrink-0 border-amber-300 hover:bg-amber-100 text-amber-900"
          >
            Go to Round 1 Console
          </Button>
        </div>
      )}

      {/* Discrepancy warning if Round 1 does not provide exactly 24 teams */}
      {data?.round1Finalized && data?.round1QualifiedTeamsCount !== 24 && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Team Count Discrepancy Detected:</span>
            <p className="mt-0.5 leading-relaxed">
              Finalized Round 1 results yielded {data?.round1QualifiedTeamsCount} teams instead of exactly 24.
              Official tournament rules prohibit inventing substitute teams. Organizer manual review required.
            </p>
          </div>
        </div>
      )}

      {/* Cutoff & Tie Warning Banner */}
      {data?.engine.tiesAffectingCutoff ? (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold">Cutoff Tie Detected — Finalization Blocked:</span>
            <p className="mt-0.5 leading-relaxed">
              Two or more teams share identical points across the <strong>12th-place qualification cutoff boundary</strong>.
              In accordance with tournament guidelines, no arbitrary tie-breaker is invented. Manual organizer/marshal review is required.
            </p>
          </div>
        </div>
      ) : null}

      {/* Overview Dynamic Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5">
        <MetricCard
          label="Eligible Teams"
          value={`${data?.stats.round1EligibleTeamsCount ?? 24}`}
          subtitle="From Round 1"
          icon={Layers}
          badge={{ text: data?.round1Finalized ? 'Sealed' : 'Provisional', variant: data?.round1Finalized ? 'emerald' : 'amber' }}
        />

        <MetricCard
          label="Participating"
          value={`${data?.stats.participatingCount ?? 24}`}
          subtitle="24 Target Field"
          icon={Layers}
          badge={{ text: '24 Squads', variant: 'blue' }}
        />

        <MetricCard
          label="Game 1 Done"
          value={`${data?.stats.game1CompletionCount ?? 0}/24`}
          subtitle={`${Math.round(((data?.stats.game1CompletionCount ?? 0) / 24) * 100)}% Placed`}
          icon={Clock}
          badge={{ text: 'Game 1', variant: (data?.stats.game1CompletionCount ?? 0) === 24 ? 'emerald' : 'amber' }}
        />

        <MetricCard
          label="Game 2 Done"
          value={`${data?.stats.game2CompletionCount ?? 0}/24`}
          subtitle={`${Math.round(((data?.stats.game2CompletionCount ?? 0) / 24) * 100)}% Placed`}
          icon={Clock}
          badge={{ text: 'Game 2', variant: (data?.stats.game2CompletionCount ?? 0) === 24 ? 'emerald' : 'amber' }}
        />

        <MetricCard
          label="Game 3 Done"
          value={`${data?.stats.game3CompletionCount ?? 0}/24`}
          subtitle={`${Math.round(((data?.stats.game3CompletionCount ?? 0) / 24) * 100)}% Placed`}
          icon={Clock}
          badge={{ text: 'Game 3', variant: (data?.stats.game3CompletionCount ?? 0) === 24 ? 'emerald' : 'amber' }}
        />

        <MetricCard
          label="All 3 Complete"
          value={`${data?.stats.completeTeamsCount ?? 0}/24`}
          subtitle="Valid 3-Game Total"
          icon={CheckCircle2}
          badge={{ text: 'Field', variant: (data?.stats.completeTeamsCount ?? 0) === 24 ? 'emerald' : 'amber' }}
        />

        <MetricCard
          label="Top 12 Cutoff"
          value={`${data?.stats.provisionalTop12Count ?? 0}`}
          subtitle="Advance to R3"
          icon={Trophy}
          badge={{ text: 'Cutoff #12', variant: 'purple' }}
        />

        <MetricCard
          label="Elimination"
          value={`${data?.stats.provisionalEliminatedCount ?? 0}`}
          subtitle="Ranks 13–24"
          icon={ShieldAlert}
          badge={{ text: 'Eliminated', variant: 'amber' }}
        />
      </div>

      {/* Navigation Tabs for Views */}
      <div className="flex border-b border-cyan-500/20 bg-[#070b16]/70 rounded-t-2xl px-4 pt-2 gap-2">
        <button
          onClick={() => setActiveTab('leaderboard')}
          className={`px-4 py-2.5 text-xs font-orbitron font-bold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === 'leaderboard'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Trophy className="w-3.5 h-3.5" />
          <span>Overall Standings & Cutoff</span>
        </button>

        <button
          onClick={() => setActiveTab('game1')}
          className={`px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === 'game1'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>Game 1 Console</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 text-cyan-300 font-mono border border-cyan-500/30">
            {data?.stats.game1CompletionCount ?? 0}/24
          </span>
        </button>

        <button
          onClick={() => setActiveTab('game2')}
          className={`px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === 'game2'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>Game 2 Console</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 text-cyan-300 font-mono border border-cyan-500/30">
            {data?.stats.game2CompletionCount ?? 0}/24
          </span>
        </button>

        <button
          onClick={() => setActiveTab('game3')}
          className={`px-4 py-2.5 text-xs font-mono font-bold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === 'game3'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>Game 3 Console</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 text-cyan-300 font-mono border border-cyan-500/30">
            {data?.stats.game3CompletionCount ?? 0}/24
          </span>
        </button>
      </div>

      {/* Render Active View */}
      {activeTab === 'game1' && renderGameConsole(1)}
      {activeTab === 'game2' && renderGameConsole(2)}
      {activeTab === 'game3' && renderGameConsole(3)}

      {activeTab === 'leaderboard' && (
        <div className="space-y-4">
          {/* Finalization Block Standby Alert */}
          {!data?.config.isFinalized && !data?.engine.canFinalize && data?.engine.blockReason && (
            <div className="p-3 bg-[#090d1a]/80 border border-cyan-500/20 rounded-2xl text-xs text-slate-300 flex items-center justify-between font-mono">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400 shrink-0" />
                <span>
                  <strong className="text-cyan-300">Qualification Standby:</strong> {data.engine.blockReason}
                </span>
              </div>
              <span className="text-[11px] text-slate-400 font-mono shrink-0 ml-2">
                Provisional Mode
              </span>
            </div>
          )}

          {/* Filter and Search Bar */}
          <SearchFilterToolbar
            searchQuery={searchQuery}
            onSearchChange={(val) => {
              setSearchQuery(val);
              setCurrentPage(1);
            }}
            searchPlaceholder="Search squad name or tag (T-01)..."
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
                  { label: 'Top 12 Advancing', value: 'top12' },
                  { label: 'Elimination Zone', value: 'eliminated' },
                  { label: 'Tie Review Needed', value: 'tieReview' },
                  { label: 'Incomplete', value: 'incomplete' },
                ],
              },
              {
                id: 'completion',
                label: 'Games',
                value: filterCompletion,
                onChange: (val) => {
                  setFilterCompletion(val);
                  setCurrentPage(1);
                },
                options: [
                  { label: 'All Progress', value: 'all' },
                  { label: 'All 3 Games Complete', value: 'complete' },
                  { label: 'Missing Games', value: 'missing' },
                  { label: 'Missing Game 1', value: 'missingG1' },
                  { label: 'Missing Game 2', value: 'missingG2' },
                  { label: 'Missing Game 3', value: 'missingG3' },
                ],
              },
            ]}
            activeCount={
              (filterStatus !== 'all' ? 1 : 0) + (filterCompletion !== 'all' ? 1 : 0) + (searchQuery ? 1 : 0)
            }
            onClearAll={() => {
              setSearchQuery('');
              setFilterStatus('all');
              setFilterCompletion('all');
            }}
          />

          {/* Leaderboard Table Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between py-3 px-4 border-b border-cyan-500/20 bg-[#070b16]/50">
              <div className="flex items-center gap-2">
                <div className="text-xs font-orbitron font-bold uppercase tracking-wider text-slate-200">
                  Round 2 Cabo Standings ({filteredAndSortedRecords.length} Squads)
                </div>
                <span className="text-[10px] text-amber-300 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-500/30 font-mono">
                  Scoring: {data?.config.scoringDirection === 'higher_is_better' ? 'Higher Points Win' : 'Lower Points Win'}
                </span>
              </div>
              <div className="text-xs text-slate-400 font-mono">
                Cutoff Boundary: Top 12 Advance
              </div>
            </CardHeader>

            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-cyan-500/20 bg-[#030712]/90 text-[11px] font-mono font-bold text-cyan-400/80 uppercase tracking-wider">
                      <th
                        className="py-3 px-3 text-center w-14 cursor-pointer hover:text-cyan-300 transition-colors select-none"
                        onClick={() => handleSort('rank')}
                      >
                        <div className="flex items-center justify-center gap-1">
                          <span>Rank</span>
                          <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                        </div>
                      </th>
                      <th
                        className="py-3 px-4 cursor-pointer hover:text-cyan-300 transition-colors select-none"
                        onClick={() => handleSort('name')}
                      >
                        <div className="flex items-center gap-1">
                          <span>Squad</span>
                          <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                        </div>
                      </th>
                      <th
                        className="py-3 px-3 text-center cursor-pointer hover:text-cyan-300 transition-colors select-none"
                        onClick={() => handleSort('g1')}
                      >
                        <div className="flex items-center justify-center gap-1">
                          <span>Game 1</span>
                          <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                        </div>
                      </th>
                      <th
                        className="py-3 px-3 text-center cursor-pointer hover:text-cyan-300 transition-colors select-none"
                        onClick={() => handleSort('g2')}
                      >
                        <div className="flex items-center justify-center gap-1">
                          <span>Game 2</span>
                          <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                        </div>
                      </th>
                      <th
                        className="py-3 px-3 text-center cursor-pointer hover:text-cyan-300 transition-colors select-none"
                        onClick={() => handleSort('g3')}
                      >
                        <div className="flex items-center justify-center gap-1">
                          <span>Game 3</span>
                          <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                        </div>
                      </th>
                      <th
                        className="py-3 px-4 text-right cursor-pointer hover:text-cyan-300 transition-colors select-none"
                        onClick={() => handleSort('totalPoints')}
                      >
                        <div className="flex items-center justify-end gap-1">
                          <span>Total Points</span>
                          <ArrowUpDown className="w-3 h-3 text-cyan-400/60" />
                        </div>
                      </th>
                      <th className="py-3 px-4">Qualification</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-cyan-500/10 text-xs text-slate-300">
                    {isLoading ? (
                      Array.from({ length: 8 }).map((_, i) => <TableRowSkeleton key={i} cols={8} />)
                    ) : paginatedRecords.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="py-12">
                          <EmptyState
                            icon={Layers}
                            title="No Squad Standings Found"
                            description="No records match your search or filter criteria."
                            action={{
                              label: 'Clear Filters',
                              onClick: () => {
                                setSearchQuery('');
                                setFilterStatus('all');
                                setFilterCompletion('all');
                              },
                            }}
                          />
                        </td>
                      </tr>
                    ) : (
                      paginatedRecords.map((rec) => {
                        const rankNum = rec.rank ?? null;
                        const isCutoffLine = rankNum === 12;
                        const isBeyondCutoff = rankNum !== null && rankNum > 12;

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

                              {/* Squad Name & Tag */}
                              <td className="py-3 px-4">
                                <div className="flex items-center gap-2">
                                  <span className="font-mono text-[11px] font-semibold text-cyan-300 bg-cyan-950/50 px-1.5 py-0.5 rounded-lg border border-cyan-500/30">
                                    {formatTeamNumber(rec.teamNumber)}
                                  </span>
                                  <span className="font-orbitron font-semibold text-slate-100">{rec.teamName}</span>
                                </div>
                                {rec.tieRequiresReview && (
                                  <span className="inline-flex items-center gap-1 text-[10px] text-amber-300 mt-1 font-mono">
                                    <AlertTriangle className="w-3 h-3 text-amber-400" />
                                    <span>Cutoff Tie Review Required</span>
                                  </span>
                                )}
                              </td>

                              {/* Game 1 */}
                              <td className="py-3 px-3 text-center">
                                {rec.game1Placement ? (
                                  <span className="font-mono text-xs font-semibold text-slate-200">
                                    #{rec.game1Placement} <span className="text-[11px] text-cyan-400/70">({rec.game1Points} pts)</span>
                                  </span>
                                ) : (
                                  <span className="text-slate-600 font-mono">—</span>
                                )}
                              </td>

                              {/* Game 2 */}
                              <td className="py-3 px-3 text-center">
                                {rec.game2Placement ? (
                                  <span className="font-mono text-xs font-semibold text-slate-200">
                                    #{rec.game2Placement} <span className="text-[11px] text-cyan-400/70">({rec.game2Points} pts)</span>
                                  </span>
                                ) : (
                                  <span className="text-slate-600 font-mono">—</span>
                                )}
                              </td>

                              {/* Game 3 */}
                              <td className="py-3 px-3 text-center">
                                {rec.game3Placement ? (
                                  <span className="font-mono text-xs font-semibold text-slate-200">
                                    #{rec.game3Placement} <span className="text-[11px] text-cyan-400/70">({rec.game3Points} pts)</span>
                                  </span>
                                ) : (
                                  <span className="text-slate-600 font-mono">—</span>
                                )}
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

                              {/* Qualification Badge */}
                              <td className="py-3 px-4">
                                {getStatusBadge(rec.qualificationStatus)}
                              </td>

                              {/* Actions */}
                              <td className="py-3 px-4 text-right">
                                {!data?.config.isFinalized && (
                                  <button
                                    onClick={() => handleOpenEditTeam(rec)}
                                    className="p-1.5 rounded-xl text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10 transition-colors"
                                    title="Edit squad placements"
                                  >
                                    <Edit3 className="w-4 h-4" />
                                  </button>
                                )}
                              </td>
                            </tr>

                            {/* Cutoff Marker Row */}
                            {isCutoffLine && (
                              <tr className="bg-cyan-950/40 border-y-2 border-cyan-400/60 shadow-[0_0_12px_rgba(6,182,212,0.2)]">
                                <td colSpan={8} className="py-2.5 px-4 text-center text-xs font-orbitron font-bold text-cyan-300 tracking-wider uppercase">
                                  ⚡ Round 2 Cabo Cutoff Threshold — Top 12 Advance to Round 3: The Black Market
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

              {/* Pagination */}
              {filteredAndSortedRecords.length > pageSize && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-xs text-slate-500">
                  <div>
                    Showing {(currentPage - 1) * pageSize + 1} to{' '}
                    {Math.min(currentPage * pageSize, filteredAndSortedRecords.length)} of{' '}
                    {filteredAndSortedRecords.length} participating squads
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                      disabled={currentPage === 1}
                    >
                      Previous
                    </Button>
                    <span className="px-2 font-mono">
                      Page {currentPage} of {Math.ceil(filteredAndSortedRecords.length / pageSize)}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setCurrentPage(
                          Math.min(Math.ceil(filteredAndSortedRecords.length / pageSize), currentPage + 1)
                        )
                      }
                      disabled={currentPage === Math.ceil(filteredAndSortedRecords.length / pageSize)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ========================================== */}
      {/* 1. Edit Squad Placements Modal              */}
      {/* ========================================== */}
      {selectedTeamRecord && (
        <Modal
          isOpen={isEditTeamModalOpen}
          onClose={() => setIsEditTeamModalOpen(false)}
          title={
            <div className="flex items-center gap-2">
              <span className="font-mono text-blue-600">
                {formatTeamNumber(selectedTeamRecord.teamNumber)}
              </span>
              <span>{selectedTeamRecord.teamName}</span>
              <span className="text-xs font-normal text-slate-400">&middot; Cabo Placements</span>
            </div>
          }
          subtitle={`Current Total: ${selectedTeamRecord.totalPoints !== null && selectedTeamRecord.totalPoints !== undefined ? `${selectedTeamRecord.totalPoints} pts` : 'Incomplete'} · Rank: ${selectedTeamRecord.rank ? `#${selectedTeamRecord.rank}` : 'Unranked'}`}
          maxWidth="md"
          footer={
            <div className="flex items-center justify-between w-full">
              <span className="text-[11px] text-slate-400 font-mono">Placements 1 to 24</span>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => setIsEditTeamModalOpen(false)}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" onClick={handleSaveTeamPlacements} isLoading={isSubmitting}>
                  Save Placements
                </Button>
              </div>
            </div>
          }
        >
          <form onSubmit={handleSaveTeamPlacements} className="space-y-4 text-xs">
            {editFormError && (
              <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <span>{editFormError}</span>
              </div>
            )}

            <div className="space-y-3">
              {/* Game 1 */}
              <div className="flex items-center justify-between gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div>
                  <div className="font-bold text-slate-800">Cabo Game 1</div>
                  <div className="text-[11px] text-slate-500">
                    Points:{' '}
                    {editG1Placement && parseInt(editG1Placement, 10) >= 1 && parseInt(editG1Placement, 10) <= 24
                      ? `+${data?.config.pointTable[parseInt(editG1Placement, 10)] ?? 0} pts`
                      : '—'}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400 font-mono">Rank #</span>
                  <input
                    type="number"
                    min="1"
                    max="24"
                    placeholder="1–24"
                    value={editG1Placement}
                    onChange={(e) => setEditG1Placement(e.target.value)}
                    className="w-20 px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg font-mono text-center text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>
              </div>

              {/* Game 2 */}
              <div className="flex items-center justify-between gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div>
                  <div className="font-bold text-slate-800">Cabo Game 2</div>
                  <div className="text-[11px] text-slate-500">
                    Points:{' '}
                    {editG2Placement && parseInt(editG2Placement, 10) >= 1 && parseInt(editG2Placement, 10) <= 24
                      ? `+${data?.config.pointTable[parseInt(editG2Placement, 10)] ?? 0} pts`
                      : '—'}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400 font-mono">Rank #</span>
                  <input
                    type="number"
                    min="1"
                    max="24"
                    placeholder="1–24"
                    value={editG2Placement}
                    onChange={(e) => setEditG2Placement(e.target.value)}
                    className="w-20 px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg font-mono text-center text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>
              </div>

              {/* Game 3 */}
              <div className="flex items-center justify-between gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div>
                  <div className="font-bold text-slate-800">Cabo Game 3</div>
                  <div className="text-[11px] text-slate-500">
                    Points:{' '}
                    {editG3Placement && parseInt(editG3Placement, 10) >= 1 && parseInt(editG3Placement, 10) <= 24
                      ? `+${data?.config.pointTable[parseInt(editG3Placement, 10)] ?? 0} pts`
                      : '—'}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400 font-mono">Rank #</span>
                  <input
                    type="number"
                    min="1"
                    max="24"
                    placeholder="1–24"
                    value={editG3Placement}
                    onChange={(e) => setEditG3Placement(e.target.value)}
                    className="w-20 px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg font-mono text-center text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>
              </div>
            </div>

            <p className="text-[11px] text-slate-400 italic">
              * Note: Teams must complete all 3 games to receive a valid total score. Leaving a field blank leaves that game unrecorded (never counted as 0).
            </p>
          </form>
        </Modal>
      )}

      {/* ========================================== */}
      {/* 2. Round 2 Settings & Point Table Modal     */}
      {/* ========================================== */}
      <Modal
        isOpen={isConfigOpen}
        onClose={() => setIsConfigOpen(false)}
        title="Round 2 Scoring Parameters &amp; Point Table"
        subtitle="Manage scoring direction, tie policy, and placement point values"
        maxWidth="2xl"
        footer={
          <div className="flex items-center justify-between w-full">
            <Button variant="ghost" size="sm" onClick={handleResetPointTableDefaults}>
              Reset Demo Defaults
            </Button>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setIsConfigOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" onClick={handleSaveConfig} isLoading={isSubmitting}>
                Save Configuration
              </Button>
            </div>
          </div>
        }
      >
        <form onSubmit={handleSaveConfig} className="space-y-5 text-xs">
          {/* Unconfirmed Tournament Rules Notice */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl space-y-1.5">
            <div className="flex items-center gap-1.5 font-bold text-amber-900 text-xs">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>Organizer Notice: Unconfirmed Tournament Rules</span>
            </div>
            <p className="text-[11px] text-amber-800 leading-relaxed">
              1. <strong>Placement Points</strong>: The point values below are currently set to a <strong>demo default linear table (24 to 1 points)</strong>. This is <em>not</em> an official rule. Configure the official point values as decided by the organizing committee.<br />
              2. <strong>Scoring Direction</strong>: Higher points win is set as a demo default. If your Cabo tournament rules specify lower cumulative score wins, toggle the option below.
            </p>
          </div>

          {configError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{configError}</span>
            </div>
          )}

          {/* Scoring Direction & Tie Policy */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Scoring Direction
              </label>
              <select
                value={configDirection}
                onChange={(e) => setConfigDirection(e.target.value as CaboScoringDirection)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="higher_is_better">Higher Points Win (Desc) — Demo Default</option>
                <option value="lower_is_better">Lower Points Win (Asc)</option>
              </select>
              <span className="text-[10px] text-slate-400 mt-1 block">
                Controls leaderboard ordering and Top 12 determination.
              </span>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Placement Tie Policy
              </label>
              <select
                value={configTiePolicy}
                onChange={(e) => setConfigTiePolicy(e.target.value as CaboTiePolicy)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="strict_unique">Strict: Disallow Duplicate Placements</option>
                <option value="allow_shared">Permit Shared Placements in Same Game</option>
              </select>
              <span className="text-[10px] text-slate-400 mt-1 block">
                Controls whether multiple squads can hold the same placement in a game.
              </span>
            </div>
          </div>

          {/* 24-Placement Point Table */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block font-semibold text-slate-700">
                Configurable Placement-Point Table (1st to 24th)
              </label>
              <span className="text-[10px] text-amber-700 font-medium">
                Unconfirmed Demo Defaults
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2 max-h-64 overflow-y-auto p-1 bg-slate-50 border border-slate-200 rounded-xl">
              {Array.from({ length: 24 }, (_, i) => i + 1).map((pos) => (
                <div key={pos} className="p-2 bg-white rounded-lg border border-slate-200 flex items-center justify-between gap-1">
                  <span className="font-mono text-slate-500 text-xs font-semibold w-8">
                    #{pos}:
                  </span>
                  <input
                    type="number"
                    min="0"
                    max="1000"
                    value={configPointTable[pos] ?? 0}
                    onChange={(e) => {
                      const val = Math.max(0, parseInt(e.target.value, 10) || 0);
                      setConfigPointTable({ ...configPointTable, [pos]: val });
                    }}
                    className="w-16 px-2 py-1 bg-slate-50 border border-slate-200 rounded text-center font-mono text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>
              ))}
            </div>
            <span className="text-[10px] text-slate-400 mt-1 block">
              Changing point values dynamically recalculates all team totals and standings upon saving.
            </span>
          </div>
        </form>
      </Modal>

      {/* ========================================== */}
      {/* 3. Finalize Round 2 Confirmation Modal     */}
      {/* ========================================== */}
      <ConfirmationDialog
        isOpen={isFinalizeConfirmOpen}
        onClose={() => setIsFinalizeConfirmOpen(false)}
        onConfirm={handleFinalizeRound2}
        title="Finalize Round 2 Qualification to Round 3: The Black Market"
        message="Are you sure you want to seal official Round 2 results? The top 12 squads will advance to Round 3, and 12 squads will be officially eliminated. All records will be preserved."
        confirmLabel="Confirm & Seal Top 12"
        isDestructive={false}
        isLoading={isSubmitting}
      />
    </div>
  );
};
