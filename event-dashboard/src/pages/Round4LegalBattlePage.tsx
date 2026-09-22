import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  Scale,
  Gavel,
  Trophy,
  AlertTriangle,
  CheckCircle2,
  Search,
  ArrowUpDown,
  Settings,
  Sparkles,
  RotateCcw,
  ExternalLink,
  ShieldAlert,
  Clock,
  UserCheck,
  FileText,
  Lock,
  Unlock,
  Info,
  Shield,
  Sliders,
  ChevronDown,
  ChevronUp,
  Award,
} from 'lucide-react';
import { eventService } from '../services/eventService';
import {
  Round4Data,
  TeamPair,
  Round4StageId,
  StageStatus,
  LegalSide,
  JudgeScoreRecord,
  AgentGuessingOutcome,
  RubricCategoryConfig,
} from '../types/round4';
import { formatTeamNumber } from '../utils/formatters';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { ConfirmationDialog } from '../components/ui/ConfirmationDialog';
import { EmptyState } from '../components/ui/EmptyState';
import { PageHeader } from '../components/ui/PageHeader';
import { SummaryMetric } from '../components/ui/SummaryMetric';
import { Card, CardHeader, CardContent } from '../components/ui/Card';

type TabView = 'leaderboard' | 'courtrooms' | 'judging' | 'agent_portal';
type SortField = 'rank' | 'teamNumber' | 'name' | 'panelScore' | 'finalScore' | 'bmContribution';

export const Round4LegalBattlePage: React.FC = () => {
  // Data State
  const [data, setData] = useState<Round4Data | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Navigation / Tabs
  const [activeTab, setActiveTab] = useState<TabView>('leaderboard');

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('rank');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Modals & Drawers
  const [isRulesModalOpen, setIsRulesModalOpen] = useState(false);
  const [isScorecardModalOpen, setIsScorecardModalOpen] = useState(false);
  const [isEditPairModalOpen, setIsEditPairModalOpen] = useState(false);
  const [isQuestionModalOpen, setIsQuestionModalOpen] = useState(false);
  const [isTimingModalOpen, setIsTimingModalOpen] = useState(false);
  const [isAgentModalOpen, setIsAgentModalOpen] = useState(false);
  const [isConfirmPairingsOpen, setIsConfirmPairingsOpen] = useState(false);
  const [isUnlockPairingsOpen, setIsUnlockPairingsOpen] = useState(false);
  const [isFinalizeModalOpen, setIsFinalizeModalOpen] = useState(false);
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [showChecklist, setShowChecklist] = useState(false);

  // Target Selections for Modals
  const [selectedPair, setSelectedPair] = useState<TeamPair | null>(null);
  const [selectedTeamId, setSelectedTeamId] = useState<string>('');
  const [selectedJudgeId, setSelectedJudgeId] = useState<string>('judge-1');

  // Form States
  // Rules Config Form
  const [formAdvancingCount, setFormAdvancingCount] = useState<number>(3);
  const [formJudgeAggregation, setFormJudgeAggregation] = useState<'average' | 'sum' | 'single_judge'>('average');
  const [formFormulaConfirmed, setFormFormulaConfirmed] = useState<boolean>(false);
  const [formRubricConfirmed, setFormRubricConfirmed] = useState<boolean>(false);
  const [formPanelWeight, setFormPanelWeight] = useState<number>(1.0);
  const [formAgentWeight, setFormAgentWeight] = useState<number>(1.0);
  const [formBmWeightPercent, setFormBmWeightPercent] = useState<number>(10);
  const [formRubricCategories, setFormRubricCategories] = useState<RubricCategoryConfig[]>([]);

  // Scorecard Form
  const [scorecardMarks, setScorecardMarks] = useState<Record<string, number>>({});
  const [scorecardComments, setScorecardComments] = useState<string>('');
  const [scorecardJudgeName, setScorecardJudgeName] = useState<string>('Faculty Judge 1 [TBD]');

  // Question Form
  const [questionPairId, setQuestionPairId] = useState<string>('');
  const [questionTeamId, setQuestionTeamId] = useState<string>('');
  const [questionText, setQuestionText] = useState<string>('');
  const [questionStage, setQuestionStage] = useState<Round4StageId>('prep_1');
  const [questionNotes, setQuestionNotes] = useState<string>('');

  // Edit Pair Form
  const [editPairCaseName, setEditPairCaseName] = useState<string>('');
  const [editPairCaseDetails, setEditPairCaseDetails] = useState<string>('');
  const [editPairSideA, setEditPairSideA] = useState<LegalSide>('Prosecution / Plaintiff');
  const [editPairSideB, setEditPairSideB] = useState<LegalSide>('Defense / Respondent');
  const [editPairFileA, setEditPairFileA] = useState<boolean>(false);
  const [editPairOppFileA, setEditPairOppFileA] = useState<boolean>(false);
  const [editPairFileB, setEditPairFileB] = useState<boolean>(false);
  const [editPairOppFileB, setEditPairOppFileB] = useState<boolean>(false);

  // Stage Timing Form
  const [timingPairId, setTimingPairId] = useState<string>('');
  const [timingStageId, setTimingStageId] = useState<Round4StageId>('prep_1');
  const [timingStatus, setTimingStatus] = useState<StageStatus>('not_started');
  const [timingDurationMinutes, setTimingDurationMinutes] = useState<string>('');
  const [timingNotes, setTimingNotes] = useState<string>('');

  // Agent Guessing Form
  const [agentTeamId, setAgentTeamId] = useState<string>('');
  const [agentOutcome, setAgentOutcome] = useState<AgentGuessingOutcome>('pending');
  const [agentPoints, setAgentPoints] = useState<string>('');
  const [agentIsVerified, setAgentIsVerified] = useState<boolean>(false);
  const [agentNotes, setAgentNotes] = useState<string>('');

  // Feedback Messages
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showToast = (text: string, type: 'success' | 'error' | 'info' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Load Round 4 Data
  const loadData = async () => {
    try {
      setIsLoading(true);
      const res = await eventService.getRound4Data();
      setData(res);

      // Pre-fill rules modal
      setFormAdvancingCount(res.config.advancingTeamsCount ?? 3);
      setFormJudgeAggregation(res.config.judgeAggregation);
      setFormFormulaConfirmed(res.config.finalScoreFormula.isFormulaConfirmed);
      setFormRubricConfirmed(res.config.isRubricConfirmed);
      setFormPanelWeight(res.config.finalScoreFormula.panelScoreWeight);
      setFormAgentWeight(res.config.finalScoreFormula.agentGuessingWeight);
      setFormBmWeightPercent(res.config.finalScoreFormula.blackMarketWeightPercent);
      setFormRubricCategories(JSON.parse(JSON.stringify(res.config.rubricCategories)));
    } catch (err: any) {
      console.error('Failed to load Round 4 data:', err);
      showToast(err.message || 'Failed to load Round 4 data', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const unsub = eventService.subscribe(() => {
      loadData();
    });
    return () => unsub();
  }, []);

  // Filtered & Sorted Standings
  const filteredRecords = useMemo(() => {
    if (!data) return [];
    return data.records.filter((rec) => {
      const matchesSearch =
        rec.teamName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rec.teamNumber.toString().includes(searchQuery) ||
        (rec.caseName && rec.caseName.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesStatus =
        filterStatus === 'all' ||
        (filterStatus === 'qualified' && rec.reviewStatus.includes('Qualified')) ||
        (filterStatus === 'review' && rec.reviewStatus.includes('Review')) ||
        (filterStatus === 'incomplete' && (rec.reviewStatus.includes('Awaiting') || rec.reviewStatus.includes('Stage')));

      return matchesSearch && matchesStatus;
    }).sort((a, b) => {
      let valA: any = a.rank ?? 999;
      let valB: any = b.rank ?? 999;

      if (sortField === 'teamNumber') {
        valA = a.teamNumber;
        valB = b.teamNumber;
      } else if (sortField === 'name') {
        valA = a.teamName.toLowerCase();
        valB = b.teamName.toLowerCase();
      } else if (sortField === 'panelScore') {
        valA = a.panelScore ?? -1;
        valB = b.panelScore ?? -1;
      } else if (sortField === 'finalScore') {
        valA = a.finalScoreBreakdown.finalScore ?? -1;
        valB = b.finalScoreBreakdown.finalScore ?? -1;
      } else if (sortField === 'bmContribution') {
        valA = a.finalScoreBreakdown.blackMarketContribution;
        valB = b.finalScoreBreakdown.blackMarketContribution;
      }

      if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
      if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
  }, [data, searchQuery, filterStatus, sortField, sortOrder]);

  // Handlers
  const handleRandomizePairings = async () => {
    try {
      await eventService.randomizeAndFormPairings();
      showToast('Random pairings formed successfully. Organizers must review and confirm.', 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to randomize pairings', 'error');
    }
  };

  const handleConfirmPairings = async () => {
    try {
      await eventService.confirmPairings('Technical Head / Event Lead');
      setIsConfirmPairingsOpen(false);
      showToast('Courtroom matchups and case assignments confirmed and locked.', 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to confirm pairings', 'error');
    }
  };

  const handleUnlockPairings = async () => {
    try {
      await eventService.resetPairings();
      setIsUnlockPairingsOpen(false);
      showToast('Pairings unlocked. Matchups can now be modified or re-randomized.', 'info');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to unlock pairings', 'error');
    }
  };

  const handleSaveRulesConfig = async () => {
    if (!data) return;
    try {
      await eventService.updateRound4Config({
        advancingTeamsCount: formAdvancingCount,
        judgeAggregation: formJudgeAggregation,
        isRubricConfirmed: formRubricConfirmed,
        rubricCategories: formRubricCategories,
        finalScoreFormula: {
          ...data.config.finalScoreFormula,
          panelScoreWeight: formPanelWeight,
          agentGuessingWeight: formAgentWeight,
          blackMarketWeightPercent: formBmWeightPercent,
          isFormulaConfirmed: formFormulaConfirmed,
          confirmedAt: formFormulaConfirmed ? new Date().toISOString() : null,
          confirmedBy: formFormulaConfirmed ? 'Event Lead' : null,
        },
      });
      setIsRulesModalOpen(false);
      showToast('Round 4 rules and rubric parameters successfully saved.', 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to update rules configuration', 'error');
    }
  };

  const handleSaveScorecard = async () => {
    if (!selectedTeamId || !selectedJudgeId) return;
    try {
      await eventService.recordJudgeScore({
        teamId: selectedTeamId,
        judgeId: selectedJudgeId,
        judgeName: scorecardJudgeName,
        scores: scorecardMarks,
        comments: scorecardComments,
      });
      setIsScorecardModalOpen(false);
      showToast(`Scorecard recorded for judge "${scorecardJudgeName}".`, 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to record judge scorecard', 'error');
    }
  };

  const handleSaveQuestion = async () => {
    if (!questionPairId || !questionTeamId || !questionText.trim()) return;
    try {
      await eventService.recordResourcePersonQuestion({
        pairId: questionPairId,
        teamId: questionTeamId,
        questionText: questionText.trim(),
        stage: questionStage,
        notes: questionNotes.trim() || undefined,
      });
      setIsQuestionModalOpen(false);
      setQuestionText('');
      setQuestionNotes('');
      showToast('Inquiry logged with the faculty resource person.', 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to log resource query', 'error');
    }
  };

  const handleSavePairDetails = async () => {
    if (!selectedPair) return;
    try {
      await eventService.updatePairDetails(selectedPair.pairId, {
        caseName: editPairCaseName,
        caseDetails: editPairCaseDetails,
        teamAAssignment: {
          ...selectedPair.teamAAssignment,
          side: editPairSideA,
          hasReceivedCaseFile: editPairFileA,
          caseFileReceivedAt: editPairFileA ? selectedPair.teamAAssignment.caseFileReceivedAt || new Date().toISOString() : null,
          hasReceivedOpposingFile: editPairOppFileA,
          opposingFileReceivedAt: editPairOppFileA ? selectedPair.teamAAssignment.opposingFileReceivedAt || new Date().toISOString() : null,
        },
        teamBAssignment: {
          ...selectedPair.teamBAssignment,
          side: editPairSideB,
          hasReceivedCaseFile: editPairFileB,
          caseFileReceivedAt: editPairFileB ? selectedPair.teamBAssignment.caseFileReceivedAt || new Date().toISOString() : null,
          hasReceivedOpposingFile: editPairOppFileB,
          opposingFileReceivedAt: editPairOppFileB ? selectedPair.teamBAssignment.opposingFileReceivedAt || new Date().toISOString() : null,
        },
      });
      setIsEditPairModalOpen(false);
      showToast(`Courtroom docket for Pair #${selectedPair.pairNumber} updated.`, 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to update matchup details', 'error');
    }
  };

  const handleSaveTiming = async () => {
    if (!timingPairId || !timingStageId) return;
    try {
      const durSec = timingDurationMinutes ? Math.round(parseFloat(timingDurationMinutes) * 60) : null;
      await eventService.updateStageTiming(timingPairId, timingStageId, {
        status: timingStatus,
        actualDurationSeconds: durSec,
        notes: timingNotes,
        endedAt: timingStatus === 'completed' ? new Date().toISOString() : null,
      });
      setIsTimingModalOpen(false);
      showToast('Stage timing and courtroom trial logs updated.', 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to update stage timing', 'error');
    }
  };

  const handleSaveAgentGuess = async () => {
    if (!agentTeamId) return;
    try {
      const points = agentPoints.trim() ? parseFloat(agentPoints) : null;
      await eventService.recordAgentGuessing({
        teamId: agentTeamId,
        outcome: agentOutcome,
        pointsAwarded: points,
        isVerified: agentIsVerified,
        organizerRef: 'Marshal Signed Off',
        notes: agentNotes,
      });
      setIsAgentModalOpen(false);
      showToast('Secret agent accusation record saved.', 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to save agent accusation', 'error');
    }
  };

  const handleFinalize = async () => {
    try {
      const res = await eventService.finalizeRound4();
      setIsFinalizeModalOpen(false);
      showToast(`Round 4 successfully finalized! Top ${res.advancingTeamsCount} squads qualify for Grand Finale.`, 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Finalization blocked', 'error');
    }
  };

  const handleResetData = async () => {
    try {
      await eventService.resetRound4Data();
      setIsResetModalOpen(false);
      showToast('Round 4 court hearings and scorecards reset.', 'info');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to reset data', 'error');
    }
  };

  const handleSimulate = async () => {
    try {
      await eventService.simulateRound4Field();
      showToast('Simulated complete oral arguments, scorecards, and verified guesses for 8 finalist squads.', 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Simulation failed', 'error');
    }
  };

  // Open Scorecard Modal for a squad
  const openScorecardModal = (teamId: string, judgeId: string = 'judge-1') => {
    if (!data) return;
    setSelectedTeamId(teamId);
    setSelectedJudgeId(judgeId);

    const existingScorecard = data.judgeScores[teamId]?.find((js: JudgeScoreRecord) => js.judgeId === judgeId);
    if (existingScorecard) {
      setScorecardMarks({ ...existingScorecard.scores });
      setScorecardComments(existingScorecard.comments || '');
      setScorecardJudgeName(existingScorecard.judgeName);
    } else {
      // Default suggested scores
      const initialMarks: Record<string, number> = {};
      data.config.rubricCategories.forEach((cat) => {
        initialMarks[cat.id] = Math.round(cat.maxMarks * 0.75); // Demo default 75%
      });
      setScorecardMarks(initialMarks);
      setScorecardComments('');
      const judgeObj = data.config.judgesList.find((j) => j.id === judgeId);
      setScorecardJudgeName(judgeObj?.name || `Faculty Judge (${judgeId})`);
    }
    setIsScorecardModalOpen(true);
  };

  // Open Edit Pair Modal
  const openEditPairModal = (pair: TeamPair) => {
    setSelectedPair(pair);
    setEditPairCaseName(pair.caseName || '');
    setEditPairCaseDetails(pair.caseDetails || '');
    setEditPairSideA(pair.teamAAssignment.side);
    setEditPairSideB(pair.teamBAssignment.side);
    setEditPairFileA(pair.teamAAssignment.hasReceivedCaseFile);
    setEditPairOppFileA(pair.teamAAssignment.hasReceivedOpposingFile);
    setEditPairFileB(pair.teamBAssignment.hasReceivedCaseFile);
    setEditPairOppFileB(pair.teamBAssignment.hasReceivedOpposingFile);
    setIsEditPairModalOpen(true);
  };

  // Open Timing Modal
  const openTimingModal = (pairId: string, stageId: Round4StageId) => {
    if (!data) return;
    const pair = data.pairs.find((p) => p.pairId === pairId);
    if (!pair) return;
    const stage = pair.stages[stageId];
    setTimingPairId(pairId);
    setTimingStageId(stageId);
    setTimingStatus(stage.status);
    setTimingDurationMinutes(stage.actualDurationSeconds ? (stage.actualDurationSeconds / 60).toString() : '');
    setTimingNotes(stage.notes || '');
    setIsTimingModalOpen(true);
  };

  // Open Question Modal
  const openQuestionModal = (pairId: string, teamId: string) => {
    setQuestionPairId(pairId);
    setQuestionTeamId(teamId);
    setQuestionText('');
    setQuestionStage('prep_1');
    setQuestionNotes('');
    setIsQuestionModalOpen(true);
  };

  // Open Agent Guessing Modal
  const openAgentModal = (teamId: string) => {
    if (!data) return;
    setAgentTeamId(teamId);
    const existing = data.records.find((r) => r.teamId === teamId)?.agentGuessingRecord;
    if (existing) {
      setAgentOutcome(existing.outcome);
      setAgentPoints(existing.pointsAwarded !== null ? existing.pointsAwarded.toString() : '');
      setAgentIsVerified(existing.isVerified);
      setAgentNotes(existing.notes || '');
    } else {
      setAgentOutcome('pending');
      setAgentPoints('');
      setAgentIsVerified(false);
      setAgentNotes('');
    }
    setIsAgentModalOpen(true);
  };

  if (isLoading && !data) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <Scale className="w-10 h-10 text-primary-500 animate-pulse" />
          <p className="text-sm text-neutral-400 font-medium">Loading Round 4: The Legal Battle Console...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-6">
        <EmptyState
          title="Round 4 Data Unavailable"
          description="Could not load court records and courtroom configuration."
          icon={Scale}
        />
      </div>
    );
  }

  const { config, stats, engine, round3Finalized, pairs } = data;

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg shadow-xl text-sm font-medium flex items-center gap-2 border transition-all ${
            toastMessage.type === 'success'
              ? 'bg-emerald-900/90 text-emerald-100 border-emerald-700'
              : toastMessage.type === 'error'
              ? 'bg-rose-900/90 text-rose-100 border-rose-700'
              : 'bg-primary-900/90 text-primary-100 border-primary-700'
          }`}
        >
          {toastMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          ) : toastMessage.type === 'error' ? (
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          ) : (
            <Info className="w-4 h-4 text-primary-400" />
          )}
          {toastMessage.text}
        </div>
      )}

      {/* Page Header */}
      <PageHeader
        title="Round 4: The Legal Battle"
        subtitle="8 finalist squads randomly paired into 4 fictional legal matchups. Case preparation, oral hearings, faculty judging rubric, and secret agent submissions."
        badge={
          <Badge
            variant={
              config.isFinalized
                ? 'success'
                : !round3Finalized
                ? 'neutral'
                : !config.pairingsConfirmed
                ? 'warning'
                : engine.canFinalize
                ? 'purple'
                : 'primary'
            }
          >
            {config.isFinalized
              ? 'Finalized & Sealed'
              : !round3Finalized
              ? 'Awaiting Round 3 Finalization'
              : !config.pairingsConfirmed
              ? 'Pairings Pending Confirmation'
              : engine.canFinalize
              ? 'Ready for Finalization'
              : 'In Progress'}
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            {!config.isFinalized && !config.pairingsConfirmed && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleRandomizePairings}
              >
                <ArrowUpDown className="w-3.5 h-3.5 mr-1.5 text-primary-500" />
                Randomize Pairings
              </Button>
            )}

            {!config.isFinalized && !config.pairingsConfirmed && pairs.length === 4 && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsConfirmPairingsOpen(true)}
              >
                <Lock className="w-3.5 h-3.5 mr-1.5" />
                Confirm Pairings
              </Button>
            )}

            {!config.isFinalized && config.pairingsConfirmed && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsUnlockPairingsOpen(true)}
                className="text-slate-600 hover:text-amber-600"
              >
                <Unlock className="w-3.5 h-3.5 mr-1.5" />
                Unlock Pairings
              </Button>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsRulesModalOpen(true)}
            >
              <Settings className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
              Rules & Rubric
            </Button>

            {!config.isFinalized && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSimulate}
                >
                  <Sparkles className="w-3.5 h-3.5 mr-1.5 text-primary-500" />
                  Simulate Field
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsResetModalOpen(true)}
                  className="text-slate-500 hover:text-rose-600"
                >
                  <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                  Reset
                </Button>
              </>
            )}

            {!config.isFinalized && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsFinalizeModalOpen(true)}
                disabled={!engine.canFinalize}
              >
                <Award className="w-3.5 h-3.5 mr-1.5" />
                Finalize Round 4
              </Button>
            )}
          </div>
        }
      />

      {/* Dependency Warning Banner: Round 3 Not Finalized */}
      {!round3Finalized && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-amber-900">
                Prerequisite Incomplete: Round 3 (The Black Market) is Not Finalized
              </p>
              <p className="text-xs text-amber-700">
                The 8 participating finalist squads shown below are provisional based on current Black Market ledgers. Finalize Round 3 to seal official qualification.
              </p>
            </div>
          </div>
          <Link to="/round-3">
            <Button variant="outline" size="sm" className="border-amber-300 text-amber-800 hover:bg-amber-100">
              Go to Round 3 <ExternalLink className="w-3.5 h-3.5 ml-1.5" />
            </Button>
          </Link>
        </div>
      )}

      {/* Warning Banner: Pairings Not Confirmed */}
      {!config.isFinalized && !config.pairingsConfirmed && (
        <div className="bg-amber-50/80 border border-amber-200 rounded-xl p-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-amber-900">
                Matchup Pairings Require Organizer Review & Confirmation
              </p>
              <p className="text-xs text-amber-700">
                Official tournament rules require organizers to confirm the 4 head-to-head pairs before oral hearings begin. Confirmed pairings will be locked against accidental re-shuffling.
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsConfirmPairingsOpen(true)}
            className="border-amber-300 text-amber-800 hover:bg-amber-100 shrink-0"
          >
            <Lock className="w-3.5 h-3.5 mr-1.5" /> Review & Confirm
          </Button>
        </div>
      )}

      {/* Suggested Formula Notice Banner */}
      {!config.finalScoreFormula.isFormulaConfirmed && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Info className="w-5 h-5 text-blue-600 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-blue-900">
                Scoring Formula: Suggested — Pending Organizer Confirmation
              </p>
              <p className="text-xs text-blue-700">
                Formula components: 100% Panel Score + 100% Secret Agent Guessing + 10% Black Market Remaining Points. Review and confirm in Rules & Rubric.
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsRulesModalOpen(true)}
            className="border-blue-300 text-blue-800 hover:bg-blue-100 shrink-0"
          >
            Review Formula
          </Button>
        </div>
      )}

      {/* 6-Metric KPI Bar */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <SummaryMetric
          label="Finalist Squads"
          value={`${stats.eligibleTeamsCount} / 8`}
          subtext={stats.eligibleTeamsCount === 8 ? 'Complete roster' : 'Roster incomplete'}
          icon={Trophy}
          variant="blue"
        />
        <SummaryMetric
          label="Matchup Pairs"
          value={`${stats.pairsConfiguredCount} / 4`}
          subtext={stats.pairingsConfirmed ? 'Locked & Confirmed' : 'Unconfirmed'}
          icon={Scale}
          variant={stats.pairingsConfirmed ? 'emerald' : 'amber'}
        />
        <SummaryMetric
          label="Cases Assigned"
          value={`${stats.casesAssignedCount} / 4`}
          subtext="Counsel designated"
          icon={FileText}
          variant="default"
        />
        <SummaryMetric
          label="Hearings Done"
          value={`${stats.hearing2CompletedCount} / 4`}
          subtext={`Exch: ${stats.fileExchangeCompletedCount}/4`}
          icon={Gavel}
          variant="purple"
        />
        <SummaryMetric
          label="Scorecards"
          value={`${stats.judgingCompletedCount} / 8`}
          subtext="100-mark rubric"
          icon={Award}
          variant="blue"
        />
        <SummaryMetric
          label="Agent Guesses"
          value={`${stats.agentGuessesVerifiedCount} / 8`}
          subtext="Portal verified"
          icon={ShieldAlert}
          variant="rose"
        />
      </div>

      {/* Finalization Checklist Drawer */}
      <Card className="border-cyan-500/20 overflow-hidden">
        <button
          onClick={() => setShowChecklist(!showChecklist)}
          className="w-full p-4 flex items-center justify-between text-left hover:bg-cyan-500/5 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-cyan-400" />
            <div>
              <span className="text-sm font-semibold text-slate-100 font-display tracking-wider">Pre-Finalization Safeguards & Diagnostics</span>
              <span className="text-xs text-slate-400 ml-2 font-mono">
                ({engine.checklist.filter((c) => c.passed).length}/{engine.checklist.length} Passed)
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {engine.canFinalize ? (
              <Badge variant="success">All Requirements Satisfied</Badge>
            ) : (
              <Badge variant="danger">
                {engine.checklist.filter((c) => !c.passed && c.severity === 'blocker').length} Blocker(s)
              </Badge>
            )}
            {showChecklist ? <ChevronUp className="w-4 h-4 text-cyan-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
          </div>
        </button>

        {showChecklist && (
          <div className="p-4 pt-0 border-t border-cyan-500/20 grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
            {engine.checklist.map((item) => (
              <div
                key={item.id}
                className={`p-3 rounded-lg border text-xs flex items-start gap-2.5 ${
                  item.passed
                    ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
                    : item.severity === 'blocker'
                    ? 'bg-rose-950/40 border-rose-500/40 text-rose-300'
                    : 'bg-amber-950/40 border-amber-500/40 text-amber-300'
                }`}
              >
                {item.passed ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                )}
                <div>
                  <p className="font-semibold">{item.label}</p>
                  {item.details && <p className="text-slate-400 mt-0.5">{item.details}</p>}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-cyan-500/20">
        <button
          onClick={() => setActiveTab('leaderboard')}
          className={`px-4 py-2.5 text-xs font-bold border-b-2 flex items-center gap-2 transition-all rounded-t-lg ${
            activeTab === 'leaderboard'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/40 shadow-[0_0_15px_rgba(34,211,238,0.15)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Trophy className="w-3.5 h-3.5" />
          Leaderboard & Final Standings
        </button>
        <button
          onClick={() => setActiveTab('courtrooms')}
          className={`px-4 py-2.5 text-xs font-bold border-b-2 flex items-center gap-2 transition-all rounded-t-lg ${
            activeTab === 'courtrooms'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/40 shadow-[0_0_15px_rgba(34,211,238,0.15)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Gavel className="w-3.5 h-3.5" />
          Matchups & Courtroom Sessions ({pairs.length})
        </button>
        <button
          onClick={() => setActiveTab('judging')}
          className={`px-4 py-2.5 text-xs font-bold border-b-2 flex items-center gap-2 transition-all rounded-t-lg ${
            activeTab === 'judging'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/40 shadow-[0_0_15px_rgba(34,211,238,0.15)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          Faculty Judging Scorecards
        </button>
        <button
          onClick={() => setActiveTab('agent_portal')}
          className={`px-4 py-2.5 text-xs font-bold border-b-2 flex items-center gap-2 transition-all rounded-t-lg ${
            activeTab === 'agent_portal'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/40 shadow-[0_0_15px_rgba(34,211,238,0.15)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          Secret Agent Accusation Portal (Restricted)
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: LEADERBOARD & FINAL STANDINGS */}
      {/* ========================================================================= */}
      {activeTab === 'leaderboard' && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-navy-900/40 p-3.5 rounded-xl border border-neutral-800">
            <div className="relative flex-1 max-w-sm">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search squad number, name, or case..."
                className="w-full pl-9 pr-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white placeholder-neutral-500 focus:outline-none focus:border-primary-500"
              />
            </div>

            <div className="flex items-center gap-3">
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="bg-neutral-900 border border-neutral-700 rounded-lg text-xs px-3 py-1.5 text-neutral-200 focus:outline-none focus:border-primary-500"
              >
                <option value="all">All Statuses</option>
                <option value="qualified">Qualified / Advancing</option>
                <option value="review">Review Needed</option>
                <option value="incomplete">Incomplete Hearings</option>
              </select>

              <select
                value={sortField}
                onChange={(e) => setSortField(e.target.value as SortField)}
                className="bg-neutral-900 border border-neutral-700 rounded-lg text-xs px-3 py-1.5 text-neutral-200 focus:outline-none focus:border-primary-500"
              >
                <option value="rank">Sort by Rank</option>
                <option value="finalScore">Sort by Final Score</option>
                <option value="panelScore">Sort by Panel Score</option>
                <option value="bmContribution">Sort by Black Market Pts</option>
                <option value="teamNumber">Sort by Team #</option>
                <option value="name">Sort by Team Name</option>
              </select>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                className="p-1.5 text-neutral-400 hover:text-white"
              >
                <ArrowUpDown className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Standings Table */}
          <div className="bg-navy-900/40 border border-neutral-800 rounded-xl overflow-hidden shadow-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-neutral-300">
                <thead className="bg-neutral-900/90 text-xs uppercase font-semibold text-neutral-400 border-b border-neutral-800">
                  <tr>
                    <th className="py-3 px-4 w-16 text-center">Rank</th>
                    <th className="py-3 px-4">Squad Details</th>
                    <th className="py-3 px-4">Courtroom Matchup & Side</th>
                    <th className="py-3 px-4 text-center">Stages (5)</th>
                    <th className="py-3 px-4 text-right">Faculty Panel</th>
                    <th className="py-3 px-4 text-right">Agent Guess</th>
                    <th className="py-3 px-4 text-right">BM (10%)</th>
                    <th className="py-3 px-4 text-right font-bold">Final Score</th>
                    <th className="py-3 px-4 text-center">Review Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/60">
                  {filteredRecords.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-12 text-center text-neutral-500">
                        No squads matched your filter criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredRecords.map((rec) => {
                      const isPodium = rec.rank !== null && rec.rank !== undefined && rec.rank <= (config.advancingTeamsCount || 3);
                      const isCutoffBorder = rec.rank === (config.advancingTeamsCount || 3);

                      return (
                        <React.Fragment key={rec.teamId}>
                          <tr
                            className={`hover:bg-neutral-800/30 transition-colors ${
                              isPodium && config.isFinalized
                                ? 'bg-emerald-950/15'
                                : rec.tieRequiresReview
                                ? 'bg-rose-950/20'
                                : ''
                            }`}
                          >
                            {/* Rank Column */}
                            <td className="py-3 px-4 text-center font-bold">
                              {rec.rank !== null && rec.rank !== undefined ? (
                                <span
                                  className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs ${
                                    rec.rank === 1
                                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                                      : rec.rank === 2
                                      ? 'bg-slate-300/20 text-slate-200 border border-slate-400/40'
                                      : rec.rank === 3
                                      ? 'bg-amber-700/20 text-amber-400 border border-amber-700/40'
                                      : 'text-neutral-400'
                                  }`}
                                >
                                  #{rec.rank}
                                </span>
                              ) : (
                                <span className="text-neutral-500 text-xs">—</span>
                              )}
                            </td>

                            {/* Squad Details */}
                            <td className="py-3 px-4">
                              <div className="font-semibold text-white">{rec.teamName}</div>
                              <div className="text-xs text-neutral-400 flex items-center gap-2">
                                <span className="font-mono text-primary-400">{formatTeamNumber(rec.teamNumber)}</span>
                                {rec.tieRequiresReview && (
                                  <span className="text-[11px] text-rose-400 flex items-center gap-1 font-medium">
                                    <AlertTriangle className="w-3 h-3" /> Cutoff Tie Review
                                  </span>
                                )}
                              </div>
                            </td>

                            {/* Matchup & Side */}
                            <td className="py-3 px-4">
                              <div className="text-xs font-medium text-neutral-200">
                                {rec.pairNumber ? `Pair #${rec.pairNumber}` : 'Unassigned'}
                                {rec.opponentTeamName ? ` vs ${rec.opponentTeamName}` : ''}
                              </div>
                              <div className="text-[11px] text-neutral-400 flex items-center gap-1.5 mt-0.5">
                                <Badge
                                  variant={rec.side.includes('Prosecution') ? 'primary' : 'neutral'}
                                  size="sm"
                                >
                                  {rec.side}
                                </Badge>
                                <span className="truncate max-w-[140px]" title={rec.caseName || 'TBD'}>
                                  {rec.caseName || 'Case Pending'}
                                </span>
                              </div>
                            </td>

                            {/* Stages Completed */}
                            <td className="py-3 px-4 text-center">
                              <span
                                className={`inline-flex items-center justify-center px-2 py-0.5 rounded text-xs font-mono font-medium ${
                                  rec.stagesCompletedCount === 5
                                    ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800'
                                    : 'bg-neutral-800 text-neutral-400'
                                }`}
                              >
                                {rec.stagesCompletedCount}/5
                              </span>
                            </td>

                            {/* Panel Score */}
                            <td className="py-3 px-4 text-right font-mono">
                              {rec.panelScore !== null ? (
                                <span className="text-white font-medium">{rec.panelScore}</span>
                              ) : (
                                <span className="text-neutral-500 text-xs">Missing</span>
                              )}
                              <div className="text-[10px] text-neutral-500">
                                {rec.judgeScores.length} scorecards
                              </div>
                            </td>

                            {/* Agent Guessing Points */}
                            <td className="py-3 px-4 text-right font-mono">
                              {rec.finalScoreBreakdown.agentGuessingPoints !== null ? (
                                <span
                                  className={
                                    rec.finalScoreBreakdown.agentGuessingPoints > 0
                                      ? 'text-emerald-400 font-medium'
                                      : 'text-neutral-400'
                                  }
                                >
                                  +{rec.finalScoreBreakdown.agentGuessingPoints}
                                </span>
                              ) : (
                                <span className="text-neutral-500 text-xs">Pending</span>
                              )}
                            </td>

                            {/* Black Market Remaining Points Contribution */}
                            <td className="py-3 px-4 text-right font-mono">
                              <span className="text-primary-300">
                                +{rec.finalScoreBreakdown.blackMarketContribution}
                              </span>
                              <div className="text-[10px] text-neutral-500">
                                bal: {rec.blackMarketBalance}
                              </div>
                            </td>

                            {/* Final Score */}
                            <td className="py-3 px-4 text-right font-mono font-bold text-base">
                              {rec.finalScoreBreakdown.finalScore !== null ? (
                                <span className="text-emerald-400">{rec.finalScoreBreakdown.finalScore}</span>
                              ) : (
                                <span className="text-neutral-500 text-xs font-normal">Pending Formula</span>
                              )}
                            </td>

                            {/* Status */}
                            <td className="py-3 px-4 text-center">
                              <Badge
                                variant={
                                  rec.reviewStatus === 'Finalized Qualified'
                                    ? 'success'
                                    : rec.reviewStatus === 'Finalized Eliminated'
                                    ? 'neutral'
                                    : rec.reviewStatus === 'Tie Review Needed'
                                    ? 'danger'
                                    : rec.reviewStatus === 'Ready for Review'
                                    ? 'purple'
                                    : 'warning'
                                }
                              >
                                {rec.reviewStatus}
                              </Badge>
                            </td>
                          </tr>

                          {/* Cutoff Demarcation Line */}
                          {isCutoffBorder && (
                            <tr className="border-b-2 border-dashed border-amber-500/60 bg-amber-950/10">
                              <td colSpan={9} className="py-1 px-4 text-center">
                                <span className="text-[11px] font-semibold text-amber-300 uppercase tracking-widest flex items-center justify-center gap-1.5">
                                  <Award className="w-3.5 h-3.5 text-amber-400" />
                                  Grand Finale Podium Advancement Cutoff (Top {config.advancingTeamsCount || 3})
                                </span>
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
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: MATCHUPS & COURTROOM SESSIONS */}
      {/* ========================================================================= */}
      {activeTab === 'courtrooms' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-neutral-400">
              4 head-to-head courtroom trials. Teams advance through 5 stages: Prep 1, Hearing 1, Opposing-File Exchange, Prep 2, and Hearing 2.
            </p>
            {!config.isFinalized && !config.pairingsConfirmed && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsConfirmPairingsOpen(true)}
                className="bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                <Lock className="w-4 h-4 mr-1.5" /> Confirm All Pairings
              </Button>
            )}
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {pairs.map((pair) => {
              const teamA = data.records.find((r) => r.teamId === pair.teamAId);
              const teamB = data.records.find((r) => r.teamId === pair.teamBId);
              const rp = data.resourcePersons[pair.pairId];

              return (
                <Card
                  key={pair.pairId}
                  className="bg-navy-900/50 border-neutral-800 rounded-2xl overflow-hidden shadow-xl"
                >
                  <CardHeader className="bg-neutral-900/80 border-b border-neutral-800/80 p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <span className="w-7 h-7 rounded-lg bg-primary-950/80 border border-primary-800 text-primary-300 font-bold text-xs flex items-center justify-center">
                          #{pair.pairNumber}
                        </span>
                        <div>
                          <h3 className="text-base font-bold text-white flex items-center gap-2">
                            {pair.caseName || `Fictional Case #${pair.pairNumber}`}
                          </h3>
                          <span className="text-xs text-neutral-400 font-mono">
                            {pair.caseId || 'CASE-TBD'}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <Badge variant={pair.isConfirmed ? 'success' : 'warning'}>
                          {pair.isConfirmed ? 'Pairing Confirmed' : 'Unconfirmed'}
                        </Badge>
                        {!config.isFinalized && (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => openEditPairModal(pair)}
                            className="text-xs py-1 px-2 border-neutral-700"
                          >
                            Edit Case
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent className="p-5 space-y-6">
                    {/* Versus Matchup Card */}
                    <div className="grid grid-cols-2 gap-4 bg-neutral-900/50 p-4 rounded-xl border border-neutral-800">
                      {/* Team A */}
                      <div className="space-y-2 border-r border-neutral-800 pr-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-primary-400">
                            {pair.teamAAssignment.side}
                          </span>
                          <span className="text-[11px] font-mono text-neutral-500">
                            {teamA ? formatTeamNumber(teamA.teamNumber) : ''}
                          </span>
                        </div>
                        <h4 className="text-sm font-bold text-white truncate">
                          {teamA ? teamA.teamName : 'Unassigned'}
                        </h4>
                        <div className="space-y-1 text-xs">
                          <div className="flex items-center justify-between text-neutral-400">
                            <span>Case File:</span>
                            <span className={pair.teamAAssignment.hasReceivedCaseFile ? 'text-emerald-400 font-medium' : 'text-neutral-500'}>
                              {pair.teamAAssignment.hasReceivedCaseFile ? 'Received' : 'Pending'}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-neutral-400">
                            <span>Opposing File:</span>
                            <span className={pair.teamAAssignment.hasReceivedOpposingFile ? 'text-emerald-400 font-medium' : 'text-neutral-500'}>
                              {pair.teamAAssignment.hasReceivedOpposingFile ? 'Received' : 'Pending'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Team B */}
                      <div className="space-y-2 pl-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-amber-400">
                            {pair.teamBAssignment.side}
                          </span>
                          <span className="text-[11px] font-mono text-neutral-500">
                            {teamB ? formatTeamNumber(teamB.teamNumber) : ''}
                          </span>
                        </div>
                        <h4 className="text-sm font-bold text-white truncate">
                          {teamB ? teamB.teamName : 'Unassigned'}
                        </h4>
                        <div className="space-y-1 text-xs">
                          <div className="flex items-center justify-between text-neutral-400">
                            <span>Case File:</span>
                            <span className={pair.teamBAssignment.hasReceivedCaseFile ? 'text-emerald-400 font-medium' : 'text-neutral-500'}>
                              {pair.teamBAssignment.hasReceivedCaseFile ? 'Received' : 'Pending'}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-neutral-400">
                            <span>Opposing File:</span>
                            <span className={pair.teamBAssignment.hasReceivedOpposingFile ? 'text-emerald-400 font-medium' : 'text-neutral-500'}>
                              {pair.teamBAssignment.hasReceivedOpposingFile ? 'Received' : 'Pending'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 5-Stage Timeline Progression */}
                    <div className="space-y-2">
                      <h5 className="text-xs font-bold uppercase tracking-wider text-neutral-400">
                        Courtroom Stage Progression
                      </h5>
                      <div className="space-y-2">
                        {Object.values(pair.stages).map((stage) => {
                          const isDone = stage.status === 'completed';
                          const isInProgress = stage.status === 'in_progress';

                          return (
                            <div
                              key={stage.stageId}
                              className={`p-3 rounded-lg border text-xs flex items-center justify-between transition-all ${
                                isDone
                                  ? 'bg-emerald-950/20 border-emerald-900/60 text-emerald-200'
                                  : isInProgress
                                  ? 'bg-primary-950/40 border-primary-800 text-primary-200'
                                  : 'bg-neutral-900/60 border-neutral-800 text-neutral-400'
                              }`}
                            >
                              <div className="flex items-center gap-2.5">
                                {isDone ? (
                                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                                ) : isInProgress ? (
                                  <Clock className="w-4 h-4 text-primary-400 animate-spin shrink-0" />
                                ) : (
                                  <div className="w-4 h-4 rounded-full border border-neutral-600 shrink-0" />
                                )}
                                <div>
                                  <span className="font-semibold text-white">{stage.name}</span>
                                  <span className="text-[11px] text-neutral-400 ml-2">
                                    {stage.suggestedDurationMinutes
                                      ? `(Config: ${stage.suggestedDurationMinutes}m)`
                                      : '(Handoff exchange)'}
                                  </span>
                                  {stage.actualDurationSeconds && (
                                    <span className="text-[11px] text-neutral-300 ml-2 font-mono">
                                      Actual: {Math.round(stage.actualDurationSeconds / 60)} min
                                    </span>
                                  )}
                                </div>
                              </div>

                              <div className="flex items-center gap-2">
                                <Badge
                                  variant={isDone ? 'success' : isInProgress ? 'primary' : 'neutral'}
                                  size="sm"
                                >
                                  {stage.status.replace('_', ' ')}
                                </Badge>
                                {!config.isFinalized && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => openTimingModal(pair.pairId, stage.stageId)}
                                    className="text-[11px] p-1 text-neutral-400 hover:text-white"
                                  >
                                    Log
                                  </Button>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Faculty Resource Person & Question Log */}
                    <div className="space-y-3 pt-2 border-t border-neutral-800">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <UserCheck className="w-4 h-4 text-primary-400" />
                          <span className="text-xs font-bold text-white">
                            {rp?.nameOrIdentifier || 'Faculty Resource Person'}
                          </span>
                        </div>
                        {!config.isFinalized && pair.teamAId && pair.teamBId && (
                          <div className="flex items-center gap-1.5">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => openQuestionModal(pair.pairId, pair.teamAId!)}
                              className="text-[11px] py-1 px-2 border-neutral-700"
                            >
                              + Question (Team A)
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => openQuestionModal(pair.pairId, pair.teamBId!)}
                              className="text-[11px] py-1 px-2 border-neutral-700"
                            >
                              + Question (Team B)
                            </Button>
                          </div>
                        )}
                      </div>

                      {/* Question Log */}
                      <div className="bg-neutral-900/60 rounded-xl p-3 border border-neutral-800 max-h-32 overflow-y-auto space-y-2 text-xs">
                        {(!rp || rp.questions.length === 0) ? (
                          <p className="text-neutral-500 italic text-center py-2">
                            No questions logged with the resource person yet.
                          </p>
                        ) : (
                          rp.questions.map((q) => {
                            const qTeam = data.records.find((r) => r.teamId === q.teamId);
                            return (
                              <div key={q.id} className="p-2 rounded bg-neutral-800/40 border border-neutral-700/60">
                                <div className="flex items-center justify-between text-[11px] text-neutral-400 mb-1">
                                  <span className="font-semibold text-primary-300">
                                    {qTeam ? qTeam.teamName : 'Squad'}
                                  </span>
                                  <span className="font-mono text-neutral-500">{q.stage}</span>
                                </div>
                                <p className="text-neutral-200 font-medium">"{q.questionText}"</p>
                                {q.notes && <p className="text-[11px] text-neutral-400 mt-1">Note: {q.notes}</p>}
                              </div>
                            );
                          })
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: FACULTY JUDGING SCORECARDS */}
      {/* ========================================================================= */}
      {activeTab === 'judging' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-navy-900/40 p-4 rounded-xl border border-neutral-800">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-primary-400" />
                100-Mark Faculty Judging Rubric & Panel Scores
              </h3>
              <p className="text-xs text-neutral-400 mt-0.5">
                Each squad is scored across 6 categories. Aggregation method:{' '}
                <span className="font-semibold text-primary-300 capitalize">{config.judgeAggregation}</span>.
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsRulesModalOpen(true)}
              className="border-neutral-700 text-xs"
            >
              <Sliders className="w-3.5 h-3.5 mr-1.5 text-neutral-400" />
              Edit Rubric Dimensions
            </Button>
          </div>

          {/* Rubric Category Reference Bar */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {config.rubricCategories.map((cat) => (
              <div key={cat.id} className="bg-neutral-900/60 p-3 rounded-lg border border-neutral-800">
                <p className="text-xs text-neutral-400 font-medium truncate" title={cat.name}>
                  {cat.name}
                </p>
                <div className="mt-1 flex items-baseline justify-between">
                  <span className="text-base font-bold text-white">{cat.maxMarks}</span>
                  <span className="text-[10px] text-amber-400 font-medium">Suggested</span>
                </div>
              </div>
            ))}
          </div>

          {/* Scorecards Grid per Finalist Squad */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {data.records.map((rec) => {
              const teamScores = data.judgeScores[rec.teamId] || [];

              return (
                <Card key={rec.teamId} className="bg-navy-900/50 border-neutral-800 p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-primary-400 font-bold">
                          {formatTeamNumber(rec.teamNumber)}
                        </span>
                        <h4 className="text-sm font-bold text-white">{rec.teamName}</h4>
                      </div>
                      <p className="text-xs text-neutral-400 mt-0.5">
                        {rec.side} | {rec.caseName || 'Case TBD'}
                      </p>
                    </div>

                    <div className="text-right">
                      <div className="text-lg font-bold font-mono text-white">
                        {rec.panelScore !== null ? `${rec.panelScore} / 100` : 'Pending'}
                      </div>
                      <Badge variant={rec.isJudgePanelComplete ? 'success' : 'warning'} size="sm">
                        {rec.isJudgePanelComplete ? 'Panel Complete' : 'Awaiting Scores'}
                      </Badge>
                    </div>
                  </div>

                  {/* Submitted Scorecards List */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs font-semibold text-neutral-400 border-b border-neutral-800 pb-1">
                      <span>Faculty Judge</span>
                      <span>Total Marks</span>
                      <span>Action</span>
                    </div>

                    {teamScores.length === 0 ? (
                      <p className="text-neutral-500 italic text-xs py-2 text-center">
                        No faculty scorecards entered for this squad yet.
                      </p>
                    ) : (
                      teamScores.map((js: JudgeScoreRecord) => (
                        <div
                          key={js.id}
                          className="flex items-center justify-between text-xs p-2 rounded bg-neutral-900/50 border border-neutral-800"
                        >
                          <div className="font-medium text-white">{js.judgeName}</div>
                          <div className="font-mono text-emerald-400 font-bold">
                            {js.totalScore} / 100
                          </div>
                          {!config.isFinalized && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openScorecardModal(rec.teamId, js.judgeId)}
                              className="text-[11px] p-1 text-primary-400 hover:text-white"
                            >
                              Edit
                            </Button>
                          )}
                        </div>
                      ))
                    )}
                  </div>

                  {!config.isFinalized && (
                    <div className="flex items-center gap-2 pt-2 border-t border-neutral-800">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => openScorecardModal(rec.teamId, 'judge-1')}
                        className="text-xs flex-1 border-neutral-700"
                      >
                        + Judge 1 Scorecard
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => openScorecardModal(rec.teamId, 'judge-2')}
                        className="text-xs flex-1 border-neutral-700"
                      >
                        + Judge 2 Scorecard
                      </Button>
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: SECRET AGENT ACCUSATION PORTAL (RESTRICTED) */}
      {/* ========================================================================= */}
      {activeTab === 'agent_portal' && (
        <div className="space-y-6">
          <div className="bg-amber-950/20 border border-amber-800/60 rounded-xl p-4 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <ShieldAlert className="w-6 h-6 text-amber-400 shrink-0" />
              <div>
                <h3 className="text-sm font-bold text-amber-200">
                  Restricted Organizer Console: Secret Agent Accusations & Guessing
                </h3>
                <p className="text-xs text-amber-300/80">
                  Strictly protect confidential answers and agent identities. Points entered here contribute directly to each squad's final score according to the configured weighting.
                </p>
              </div>
            </div>
            <Badge variant="purple">Restricted Access</Badge>
          </div>

          <div className="bg-navy-900/40 border border-neutral-800 rounded-xl overflow-hidden shadow-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-neutral-300">
                <thead className="bg-neutral-900/90 text-xs uppercase font-semibold text-neutral-400 border-b border-neutral-800">
                  <tr>
                    <th className="py-3 px-4">Squad Details</th>
                    <th className="py-3 px-4 text-center">Accusation Outcome</th>
                    <th className="py-3 px-4 text-right">Points Awarded</th>
                    <th className="py-3 px-4 text-center">Verification Status</th>
                    <th className="py-3 px-4">Organizer Notes</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/60">
                  {data.records.map((rec) => {
                    const guess = rec.agentGuessingRecord;

                    return (
                      <tr key={rec.teamId} className="hover:bg-neutral-800/30 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-semibold text-white">{rec.teamName}</div>
                          <div className="text-xs font-mono text-primary-400">
                            {formatTeamNumber(rec.teamNumber)}
                          </div>
                        </td>

                        <td className="py-3 px-4 text-center">
                          <Badge
                            variant={
                              guess?.outcome === 'correct'
                                ? 'success'
                                : guess?.outcome === 'incorrect'
                                ? 'danger'
                                : 'neutral'
                            }
                          >
                            {guess?.outcome ? guess.outcome.toUpperCase() : 'PENDING'}
                          </Badge>
                        </td>

                        <td className="py-3 px-4 text-right font-mono font-bold">
                          {guess?.pointsAwarded !== null && guess?.pointsAwarded !== undefined ? (
                            <span className={guess.pointsAwarded > 0 ? 'text-emerald-400' : 'text-neutral-400'}>
                              +{guess.pointsAwarded}
                            </span>
                          ) : (
                            <span className="text-neutral-500 text-xs">Unassigned</span>
                          )}
                        </td>

                        <td className="py-3 px-4 text-center">
                          <Badge variant={guess?.isVerified ? 'success' : 'warning'}>
                            {guess?.isVerified ? 'Verified by Marshal' : 'Pending Verification'}
                          </Badge>
                        </td>

                        <td className="py-3 px-4 text-xs text-neutral-400 max-w-xs truncate">
                          {guess?.notes || <span className="text-neutral-600 italic">No notes</span>}
                        </td>

                        <td className="py-3 px-4 text-right">
                          {!config.isFinalized && (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => openAgentModal(rec.teamId)}
                              className="text-xs py-1 px-2.5 border-neutral-700"
                            >
                              Record Entry
                            </Button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 1: RULES & RUBRIC CONFIGURATION */}
      {/* ========================================================================= */}
      {isRulesModalOpen && (
        <Modal
          isOpen={isRulesModalOpen}
          onClose={() => setIsRulesModalOpen(false)}
          title="Round 4 Rules, Rubric & Scoring Configuration"
          subtitle="Configure 100-mark rubric dimensions, aggregation method, and final-score formula parameters."
          maxWidth="2xl"
        >
          <div className="space-y-6 py-2">
            {/* Rubric Categories */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-bold text-white">100-Mark Rubric Dimensions</h4>
                <label className="flex items-center gap-2 text-xs text-neutral-300">
                  <input
                    type="checkbox"
                    checked={formRubricConfirmed}
                    onChange={(e) => setFormRubricConfirmed(e.target.checked)}
                    className="rounded border-neutral-700 bg-neutral-900 text-primary-600 focus:ring-primary-500"
                  />
                  <span>Confirm Rubric as Official</span>
                </label>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {formRubricCategories.map((cat, idx) => (
                  <div key={cat.id} className="p-3 bg-neutral-900 rounded-lg border border-neutral-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-white">{cat.name}</span>
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-neutral-400">Max:</span>
                        <input
                          type="number"
                          value={cat.maxMarks}
                          onChange={(e) => {
                            const val = parseInt(e.target.value) || 0;
                            const updated = [...formRubricCategories];
                            updated[idx].maxMarks = val;
                            setFormRubricCategories(updated);
                          }}
                          className="w-16 px-2 py-0.5 bg-neutral-800 border border-neutral-700 rounded text-xs text-white text-right font-mono"
                        />
                      </div>
                    </div>
                    <p className="text-[11px] text-neutral-500">{cat.description}</p>
                  </div>
                ))}
              </div>

              <div className="text-right text-xs text-neutral-400 font-mono">
                Total Rubric Marks:{' '}
                <span className="text-emerald-400 font-bold">
                  {formRubricCategories.reduce((acc, c) => acc + c.maxMarks, 0)}
                </span>{' '}
                / 100
              </div>
            </div>

            {/* Judge Score Aggregation */}
            <div className="space-y-2 pt-3 border-t border-neutral-800">
              <label className="text-sm font-bold text-white block">Faculty Judge Score Aggregation</label>
              <select
                value={formJudgeAggregation}
                onChange={(e) => setFormJudgeAggregation(e.target.value as any)}
                className="w-full px-3 py-2 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white focus:outline-none focus:border-primary-500"
              >
                <option value="average">Average all submitted judge scorecards (Default)</option>
                <option value="sum">Sum total marks across all judges</option>
                <option value="single_judge">Single primary judge scorecard</option>
              </select>
            </div>

            {/* Final Score Formula */}
            <div className="space-y-3 pt-3 border-t border-neutral-800">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-bold text-white">Final-Score Formula & Weighting</h4>
                <label className="flex items-center gap-2 text-xs text-neutral-300">
                  <input
                    type="checkbox"
                    checked={formFormulaConfirmed}
                    onChange={(e) => setFormFormulaConfirmed(e.target.checked)}
                    className="rounded border-neutral-700 bg-neutral-900 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="font-semibold text-emerald-400">Officially Confirm Scoring Formula</span>
                </label>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 bg-neutral-900 rounded-lg border border-neutral-800 space-y-1">
                  <span className="text-xs text-neutral-400">Panel Weight</span>
                  <input
                    type="number"
                    step="0.1"
                    value={formPanelWeight}
                    onChange={(e) => setFormPanelWeight(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 bg-neutral-800 border border-neutral-700 rounded text-sm text-white font-mono"
                  />
                  <span className="text-[10px] text-neutral-500 block">Multiplier (1.0 = 100%)</span>
                </div>

                <div className="p-3 bg-neutral-900 rounded-lg border border-neutral-800 space-y-1">
                  <span className="text-xs text-neutral-400">Agent Guess Weight</span>
                  <input
                    type="number"
                    step="0.1"
                    value={formAgentWeight}
                    onChange={(e) => setFormAgentWeight(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 bg-neutral-800 border border-neutral-700 rounded text-sm text-white font-mono"
                  />
                  <span className="text-[10px] text-neutral-500 block">Multiplier (1.0 = 100%)</span>
                </div>

                <div className="p-3 bg-neutral-900 rounded-lg border border-neutral-800 space-y-1">
                  <span className="text-xs text-neutral-400">Black Market %</span>
                  <input
                    type="number"
                    step="1"
                    value={formBmWeightPercent}
                    onChange={(e) => setFormBmWeightPercent(parseInt(e.target.value) || 0)}
                    className="w-full px-2 py-1 bg-neutral-800 border border-neutral-700 rounded text-sm text-white font-mono"
                  />
                  <span className="text-[10px] text-neutral-500 block">Percentage (10 = 10%)</span>
                </div>
              </div>
            </div>

            {/* Advancing Teams Count */}
            <div className="space-y-2 pt-3 border-t border-neutral-800">
              <label className="text-sm font-bold text-white block">
                Advancing Finalist Teams Count (Grand Finale Podium)
              </label>
              <input
                type="number"
                min="1"
                max="8"
                value={formAdvancingCount}
                onChange={(e) => setFormAdvancingCount(parseInt(e.target.value) || 3)}
                className="w-32 px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white font-mono"
              />
              <span className="text-xs text-neutral-400 block">
                Top {formAdvancingCount} squads qualify for final trophy honors.
              </span>
            </div>

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-neutral-800">
              <Button variant="secondary" onClick={() => setIsRulesModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveRulesConfig}>
                Save Rules & Rubric
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ========================================================================= */}
      {/* MODAL 2: ENTER / EDIT JUDGE SCORECARD */}
      {/* ========================================================================= */}
      {isScorecardModalOpen && (
        <Modal
          isOpen={isScorecardModalOpen}
          onClose={() => setIsScorecardModalOpen(false)}
          title={`Judge Scorecard: ${data.records.find((r) => r.teamId === selectedTeamId)?.teamName || 'Squad'}`}
          subtitle="Input marks across all 6 rubric categories. Total is validated against category maximums."
          maxWidth="lg"
        >
          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Judge Name / Identity</label>
              <input
                type="text"
                value={scorecardJudgeName}
                onChange={(e) => setScorecardJudgeName(e.target.value)}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white focus:outline-none focus:border-primary-500"
              />
            </div>

            <div className="space-y-3">
              {config.rubricCategories.map((cat) => (
                <div key={cat.id} className="flex items-center justify-between p-2.5 bg-neutral-900 rounded-lg border border-neutral-800">
                  <div>
                    <span className="text-xs font-semibold text-white block">{cat.name}</span>
                    <span className="text-[11px] text-neutral-500">Max: {cat.maxMarks} marks</span>
                  </div>
                  <input
                    type="number"
                    min="0"
                    max={cat.maxMarks}
                    value={scorecardMarks[cat.id] ?? 0}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value) || 0;
                      setScorecardMarks({
                        ...scorecardMarks,
                        [cat.id]: Math.min(cat.maxMarks, Math.max(0, val)),
                      });
                    }}
                    className="w-20 px-2 py-1 bg-neutral-800 border border-neutral-700 rounded text-sm text-right font-mono text-white focus:outline-none focus:border-primary-500"
                  />
                </div>
              ))}
            </div>

            <div className="p-3 bg-neutral-900/80 rounded-lg border border-neutral-800 flex items-center justify-between">
              <span className="text-sm font-semibold text-neutral-300">Total Scorecard Score:</span>
              <span className="text-xl font-bold font-mono text-emerald-400">
                {Object.values(scorecardMarks).reduce((acc, v) => acc + (v || 0), 0)} / 100
              </span>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Judge Comments / Deliberation Notes</label>
              <textarea
                value={scorecardComments}
                onChange={(e) => setScorecardComments(e.target.value)}
                rows={2}
                placeholder="Optional faculty notes on oral arguments or rebuttal sharpness..."
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-primary-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-neutral-800">
              <Button variant="secondary" onClick={() => setIsScorecardModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveScorecard}>
                Submit Scorecard
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ========================================================================= */}
      {/* MODAL 3: EDIT MATCHUP & CASE DETAILS */}
      {/* ========================================================================= */}
      {isEditPairModalOpen && selectedPair && (
        <Modal
          isOpen={isEditPairModalOpen}
          onClose={() => setIsEditPairModalOpen(false)}
          title={`Edit Courtroom Docket: Pair #${selectedPair.pairNumber}`}
          subtitle="Configure official case title, counsel sides, and track case file delivery."
          maxWidth="lg"
        >
          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Official Case Title</label>
              <input
                type="text"
                value={editPairCaseName}
                onChange={(e) => setEditPairCaseName(e.target.value)}
                placeholder="e.g. State vs. CyberCorp Protocol Breach"
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white focus:outline-none focus:border-primary-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Case Docket / Facts Log</label>
              <textarea
                value={editPairCaseDetails}
                onChange={(e) => setEditPairCaseDetails(e.target.value)}
                rows={2}
                placeholder="Docket ID, evidence description, or briefing facts..."
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white focus:outline-none focus:border-primary-500"
              />
            </div>

            {/* Team A Side & File Receipts */}
            <div className="p-3 bg-neutral-900 rounded-lg border border-neutral-800 space-y-2">
              <h5 className="text-xs font-bold text-primary-400">
                Team A ({data.records.find((r) => r.teamId === selectedPair.teamAId)?.teamName || 'Team A'})
              </h5>
              <div className="flex items-center gap-2">
                <label className="text-xs text-neutral-400">Side:</label>
                <select
                  value={editPairSideA}
                  onChange={(e) => setEditPairSideA(e.target.value as LegalSide)}
                  className="bg-neutral-800 border border-neutral-700 rounded text-xs px-2 py-1 text-white"
                >
                  <option value="Prosecution / Plaintiff">Prosecution / Plaintiff</option>
                  <option value="Defense / Respondent">Defense / Respondent</option>
                </select>
              </div>
              <div className="flex items-center gap-4 text-xs text-neutral-300 pt-1">
                <label className="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={editPairFileA}
                    onChange={(e) => setEditPairFileA(e.target.checked)}
                    className="rounded border-neutral-700 bg-neutral-800 text-primary-600"
                  />
                  <span>Received Own Case File</span>
                </label>
                <label className="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={editPairOppFileA}
                    onChange={(e) => setEditPairOppFileA(e.target.checked)}
                    className="rounded border-neutral-700 bg-neutral-800 text-primary-600"
                  />
                  <span>Received Opposing File</span>
                </label>
              </div>
            </div>

            {/* Team B Side & File Receipts */}
            <div className="p-3 bg-neutral-900 rounded-lg border border-neutral-800 space-y-2">
              <h5 className="text-xs font-bold text-amber-400">
                Team B ({data.records.find((r) => r.teamId === selectedPair.teamBId)?.teamName || 'Team B'})
              </h5>
              <div className="flex items-center gap-2">
                <label className="text-xs text-neutral-400">Side:</label>
                <select
                  value={editPairSideB}
                  onChange={(e) => setEditPairSideB(e.target.value as LegalSide)}
                  className="bg-neutral-800 border border-neutral-700 rounded text-xs px-2 py-1 text-white"
                >
                  <option value="Defense / Respondent">Defense / Respondent</option>
                  <option value="Prosecution / Plaintiff">Prosecution / Plaintiff</option>
                </select>
              </div>
              <div className="flex items-center gap-4 text-xs text-neutral-300 pt-1">
                <label className="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={editPairFileB}
                    onChange={(e) => setEditPairFileB(e.target.checked)}
                    className="rounded border-neutral-700 bg-neutral-800 text-primary-600"
                  />
                  <span>Received Own Case File</span>
                </label>
                <label className="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={editPairOppFileB}
                    onChange={(e) => setEditPairOppFileB(e.target.checked)}
                    className="rounded border-neutral-700 bg-neutral-800 text-primary-600"
                  />
                  <span>Received Opposing File</span>
                </label>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-neutral-800">
              <Button variant="secondary" onClick={() => setIsEditPairModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSavePairDetails}>
                Save Details
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ========================================================================= */}
      {/* MODAL 4: ASK RESOURCE PERSON QUESTION */}
      {/* ========================================================================= */}
      {isQuestionModalOpen && (
        <Modal
          isOpen={isQuestionModalOpen}
          onClose={() => setIsQuestionModalOpen(false)}
          title="Log Resource Person Inquiry"
          subtitle={`Squad: ${data.records.find((r) => r.teamId === questionTeamId)?.teamName || 'Squad'}`}
          maxWidth="md"
        >
          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Courtroom Stage</label>
              <select
                value={questionStage}
                onChange={(e) => setQuestionStage(e.target.value as Round4StageId)}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
              >
                <option value="prep_1">Preparation 1</option>
                <option value="hearing_1">Hearing 1</option>
                <option value="file_exchange">Opposing-File Exchange</option>
                <option value="prep_2">Preparation 2</option>
                <option value="hearing_2">Hearing 2</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Question Asked to Resource Person</label>
              <textarea
                value={questionText}
                onChange={(e) => setQuestionText(e.target.value)}
                rows={3}
                placeholder="Enter the specific query or clarification requested by the squad..."
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-primary-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Faculty Notes / Resource Feedback</label>
              <textarea
                value={questionNotes}
                onChange={(e) => setQuestionNotes(e.target.value)}
                rows={2}
                placeholder="Optional notes from resource person..."
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white placeholder-neutral-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-neutral-800">
              <Button variant="secondary" onClick={() => setIsQuestionModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveQuestion}>
                Save Inquiry
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ========================================================================= */}
      {/* MODAL 5: LOG STAGE TIMING */}
      {/* ========================================================================= */}
      {isTimingModalOpen && (
        <Modal
          isOpen={isTimingModalOpen}
          onClose={() => setIsTimingModalOpen(false)}
          title="Update Courtroom Stage Timing"
          subtitle={`Pair: ${timingPairId} | Stage: ${timingStageId}`}
          maxWidth="md"
        >
          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Stage Status</label>
              <select
                value={timingStatus}
                onChange={(e) => setTimingStatus(e.target.value as any)}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
              >
                <option value="not_started">Not Started</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Actual Duration (Minutes)</label>
              <input
                type="number"
                step="0.5"
                value={timingDurationMinutes}
                onChange={(e) => setTimingDurationMinutes(e.target.value)}
                placeholder="e.g. 20"
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white font-mono"
              />
              <span className="text-[11px] text-neutral-500">
                Leave blank to auto-calculate from clock timestamps.
              </span>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Stage Notes / Marshal Incident Flags</label>
              <textarea
                value={timingNotes}
                onChange={(e) => setTimingNotes(e.target.value)}
                rows={2}
                placeholder="Any notable incident or time overrun..."
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-neutral-800">
              <Button variant="secondary" onClick={() => setIsTimingModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveTiming}>
                Update Timing
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ========================================================================= */}
      {/* MODAL 6: SECRET AGENT GUESSING */}
      {/* ========================================================================= */}
      {isAgentModalOpen && (
        <Modal
          isOpen={isAgentModalOpen}
          onClose={() => setIsAgentModalOpen(false)}
          title="Secret Agent Accusation Entry"
          subtitle={`Squad: ${data.records.find((r) => r.teamId === agentTeamId)?.teamName || 'Squad'}`}
          maxWidth="md"
        >
          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Accusation Outcome</label>
              <select
                value={agentOutcome}
                onChange={(e) => setAgentOutcome(e.target.value as AgentGuessingOutcome)}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
              >
                <option value="pending">Pending Deliberation</option>
                <option value="correct">Correct Identification</option>
                <option value="incorrect">Incorrect Identification</option>
                <option value="none">No Guess Made</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Points Awarded</label>
              <input
                type="number"
                value={agentPoints}
                onChange={(e) => setAgentPoints(e.target.value)}
                placeholder="e.g. 50"
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white font-mono"
              />
              <span className="text-[11px] text-neutral-500">
                Points awarded to squad's total score.
              </span>
            </div>

            <label className="flex items-center gap-2 text-xs text-neutral-300 pt-1">
              <input
                type="checkbox"
                checked={agentIsVerified}
                onChange={(e) => setAgentIsVerified(e.target.checked)}
                className="rounded border-neutral-700 bg-neutral-900 text-primary-600 focus:ring-primary-500"
              />
              <span className="font-semibold text-emerald-400">Chief Marshal Sign-Off (Verified)</span>
            </label>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Confidential Marshal Notes</label>
              <textarea
                value={agentNotes}
                onChange={(e) => setAgentNotes(e.target.value)}
                rows={2}
                placeholder="Confidential verification details..."
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-neutral-800">
              <Button variant="secondary" onClick={() => setIsAgentModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveAgentGuess}>
                Save Record
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Confirmation Dialogs */}
      <ConfirmationDialog
        isOpen={isConfirmPairingsOpen}
        onClose={() => setIsConfirmPairingsOpen(false)}
        onConfirm={handleConfirmPairings}
        title="Confirm & Lock Courtroom Matchups"
        message="Are you sure you want to officially confirm the 4 matchup pairings? Once confirmed, matchups will be locked against accidental re-shuffling to preserve courtroom integrity."
        confirmLabel="Confirm & Lock Pairings"
      />

      <ConfirmationDialog
        isOpen={isUnlockPairingsOpen}
        onClose={() => setIsUnlockPairingsOpen(false)}
        onConfirm={handleUnlockPairings}
        title="Unlock Matchup Pairings"
        message="Unlocking pairings will allow re-randomizing or altering courtroom pairings. Any existing stage notes will be preserved."
        confirmLabel="Unlock Pairings"
      />

      <ConfirmationDialog
        isOpen={isFinalizeModalOpen}
        onClose={() => setIsFinalizeModalOpen(false)}
        onConfirm={handleFinalize}
        title="Finalize Round 4: The Legal Battle"
        message={`Sealing Round 4 will officially finalize all courtroom scores and advance the Top ${config.advancingTeamsCount || 3} finalist squads to the Grand Finale. This action cannot be reversed.`}
        confirmLabel="Finalize & Seal Results"
      />

      <ConfirmationDialog
        isOpen={isResetModalOpen}
        onClose={() => setIsResetModalOpen(false)}
        onConfirm={handleResetData}
        title="Reset Legal Battle Courtroom Data"
        message="Are you sure you want to reset all courtroom stage progress, judge scorecards, and secret agent submissions? Configuration and rubric parameters will be preserved."
        confirmLabel="Reset Data"
        isDestructive
      />
    </div>
  );
};
