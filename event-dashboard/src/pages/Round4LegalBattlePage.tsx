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
  Shield,
  Sliders,
  ChevronDown,
  ChevronUp,
  Award,
  Eye,
  EyeOff,
  Edit3,
} from 'lucide-react';
import { eventService } from '../services/eventService';
import {
  Round4Data,
  TeamPair,
  Round4StageId,
  StageStatus,
  LegalSide,
  JudgeScoreRecord,
  RubricCategoryConfig,
} from '../types/round4';
import { formatTeamNumber } from '../utils/formatters';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { ConfirmationDialog } from '../components/ui/ConfirmationDialog';
import { PageHeader } from '../components/ui/PageHeader';
import { SummaryMetric } from '../components/ui/SummaryMetric';
import { Card, CardHeader, CardContent } from '../components/ui/Card';

type TabView = 'leaderboard' | 'courtrooms' | 'judging' | 'timekeeper_rp' | 'agent_portal';
type SortField = 'rank' | 'teamNumber' | 'name' | 'r4Legal' | 'finalScore' | 'r3Balance';

export const Round4LegalBattlePage: React.FC = () => {
  // Data State
  const [data, setData] = useState<Round4Data | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Navigation / Tabs
  const [activeTab, setActiveTab] = useState<TabView>('leaderboard');
  const [isPublicScoreboard, setIsPublicScoreboard] = useState(false);

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('rank');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Modals & Drawers
  const [isRulesModalOpen, setIsRulesModalOpen] = useState(false);
  const [isScorecardModalOpen, setIsScorecardModalOpen] = useState(false);
  const [isCorrectionModalOpen, setIsCorrectionModalOpen] = useState(false);
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
  const [selectedScoreRecord, setSelectedScoreRecord] = useState<JudgeScoreRecord | null>(null);

  // Form States
  // Rules Config Form
  const [formAdvancingCount, setFormAdvancingCount] = useState<number>(1);
  const [formJudgeAggregation, setFormJudgeAggregation] = useState<'average' | 'sum' | 'single_judge'>('average');
  const [formFormulaConfirmed, setFormFormulaConfirmed] = useState<boolean>(true);
  const [formRubricConfirmed, setFormRubricConfirmed] = useState<boolean>(true);
  const [formPanelWeight, setFormPanelWeight] = useState<number>(1.0);
  const [formAgentWeight, setFormAgentWeight] = useState<number>(1.0);
  const [formBmWeightPercent, setFormBmWeightPercent] = useState<number>(10);
  const [formRubricCategories, setFormRubricCategories] = useState<RubricCategoryConfig[]>([]);

  // Scorecard Form
  const [scorecardMarks, setScorecardMarks] = useState<Record<string, number>>({});
  const [scorecardComments, setScorecardComments] = useState<string>('');
  const [scorecardJudgeName, setScorecardJudgeName] = useState<string>('Faculty Judge 1');
  const [scorecardShouldLock, setScorecardShouldLock] = useState<boolean>(false);

  // Audited Correction Form
  const [correctionMarks, setCorrectionMarks] = useState<Record<string, number>>({});
  const [correctionComments, setCorrectionComments] = useState<string>('');
  const [correctionNotes, setCorrectionNotes] = useState<string>('');
  const [correctionActor, setCorrectionActor] = useState<string>('Chief Marshal');

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
  const [timingTimekeeperName, setTimingTimekeeperName] = useState<string>('Court Clerk / Timekeeper');
  const [timingViolationsNotes, setTimingViolationsNotes] = useState<string>('');
  const [timingPenaltySeconds, setTimingPenaltySeconds] = useState<number>(0);

  // Agent Guessing Form (1-5 guesses)
  const [agentTeamId, setAgentTeamId] = useState<string>('');
  const [agentGuessesList, setAgentGuessesList] = useState<Array<{ suspectId: string; suspectName: string; isCorrect: boolean }>>([
    { suspectId: 'suspect-1', suspectName: 'Suspect Agent Alpha', isCorrect: true },
  ]);
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
      setFormAdvancingCount(res.config.advancingTeamsCount ?? 1);
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
      } else if (sortField === 'r4Legal') {
        valA = a.finalScoreBreakdown.r4LegalScore ?? a.panelScore ?? -1;
        valB = b.finalScoreBreakdown.r4LegalScore ?? b.panelScore ?? -1;
      } else if (sortField === 'finalScore') {
        valA = a.finalScoreBreakdown.finalScore ?? -1;
        valB = b.finalScoreBreakdown.finalScore ?? -1;
      } else if (sortField === 'r3Balance') {
        valA = a.finalScoreBreakdown.r3Balance ?? a.blackMarketBalance;
        valB = b.finalScoreBreakdown.r3Balance ?? b.blackMarketBalance;
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
      showToast('2 semifinal pairings formed successfully. Organizers must review and confirm.', 'success');
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
          confirmedBy: formFormulaConfirmed ? 'Organizing Lead' : null,
        },
      });
      setIsRulesModalOpen(false);
      showToast('Rules, rubric, and composite formula configuration saved.', 'success');
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

      if (scorecardShouldLock) {
        await eventService.lockJudgeScore(selectedTeamId, selectedJudgeId, scorecardJudgeName);
      }

      setIsScorecardModalOpen(false);
      showToast(`Scorecard submitted ${scorecardShouldLock ? 'and LOCKED ' : ''}for "${scorecardJudgeName}".`, 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to record judge scorecard', 'error');
    }
  };

  const handleLockScorecard = async (teamId: string, judgeId: string, judgeName: string) => {
    try {
      await eventService.lockJudgeScore(teamId, judgeId, judgeName);
      showToast(`Scorecard for judge ${judgeName} locked against tampering.`, 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to lock scorecard', 'error');
    }
  };

  const handleUnlockScorecard = async (teamId: string, judgeId: string) => {
    try {
      await eventService.unlockJudgeScore(teamId, judgeId);
      showToast('Scorecard unlocked for edits.', 'info');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to unlock scorecard', 'error');
    }
  };

  const handleSaveAuditedCorrection = async () => {
    if (!selectedTeamId || !selectedJudgeId || !correctionNotes.trim()) {
      showToast('Mandatory correction notes are required for audited override.', 'error');
      return;
    }
    try {
      await eventService.correctJudgeScore(selectedTeamId, selectedJudgeId, {
        scores: correctionMarks,
        comments: correctionComments,
        correctionNotes: correctionNotes.trim(),
        actorName: correctionActor.trim() || 'Chief Marshal',
      });
      setIsCorrectionModalOpen(false);
      showToast('Audited correction logged and applied with audit trail.', 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to apply audited correction', 'error');
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
        timekeeperName: timingTimekeeperName,
        timeViolationsNotes: timingViolationsNotes,
        penaltySeconds: timingPenaltySeconds,
        endedAt: timingStatus === 'completed' ? new Date().toISOString() : null,
      });
      setIsTimingModalOpen(false);
      showToast('Timekeeper interval logs and overtime penalties updated.', 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to update stage timing', 'error');
    }
  };

  const handleSaveAgentGuesses = async () => {
    if (!agentTeamId) return;
    if (agentGuessesList.length < 1 || agentGuessesList.length > 5) {
      showToast('Each squad must submit between 1 and 5 secret agent guesses.', 'error');
      return;
    }
    try {
      await eventService.submitTeamAgentGuesses(agentTeamId, {
        guesses: agentGuessesList,
        notes: agentNotes,
      });
      setIsAgentModalOpen(false);
      showToast(`Audited ${agentGuessesList.length} secret agent guesses (+30 correct, -20 incorrect).`, 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Failed to save secret agent guesses', 'error');
    }
  };

  const handleFinalize = async () => {
    try {
      const res = await eventService.finalizeRound4();
      setIsFinalizeModalOpen(false);
      showToast(`Round 4 successfully finalized! Top ${res.advancingTeamsCount} champion advances.`, 'success');
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
      showToast('Simulated complete oral arguments, scorecards, and verified guesses for 4 finalist squads.', 'success');
      await loadData();
    } catch (err: any) {
      showToast(err.message || 'Simulation failed', 'error');
    }
  };

  // Open Modals
  const openScorecardModal = (teamId: string, judgeId: string = 'judge-1') => {
    if (!data) return;
    setSelectedTeamId(teamId);
    setSelectedJudgeId(judgeId);

    const existingScorecard = data.judgeScores[teamId]?.find((js: JudgeScoreRecord) => js.judgeId === judgeId);
    if (existingScorecard) {
      setScorecardMarks({ ...existingScorecard.scores });
      setScorecardComments(existingScorecard.comments || '');
      setScorecardJudgeName(existingScorecard.judgeName);
      setScorecardShouldLock(!!existingScorecard.isLocked);
    } else {
      const initialMarks: Record<string, number> = {};
      data.config.rubricCategories.forEach((cat) => {
        initialMarks[cat.id] = Math.round(cat.maxMarks * 0.85);
      });
      setScorecardMarks(initialMarks);
      setScorecardComments('');
      const judgeObj = data.config.judgesList.find((j) => j.id === judgeId);
      setScorecardJudgeName(judgeObj?.name || `Faculty Judge (${judgeId})`);
      setScorecardShouldLock(false);
    }
    setIsScorecardModalOpen(true);
  };

  const openCorrectionModal = (teamId: string, js: JudgeScoreRecord) => {
    setSelectedTeamId(teamId);
    setSelectedJudgeId(js.judgeId);
    setSelectedScoreRecord(js);
    setCorrectionMarks({ ...js.scores });
    setCorrectionComments(js.comments || '');
    setCorrectionNotes('');
    setCorrectionActor('Chief Marshal / Arbiter');
    setIsCorrectionModalOpen(true);
  };

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

  const openTimingModal = (pairId: string, stageId: Round4StageId) => {
    const pair = data?.pairs.find((p) => p.pairId === pairId);
    const stage = pair?.stages[stageId];
    setTimingPairId(pairId);
    setTimingStageId(stageId);
    setTimingStatus(stage?.status || 'not_started');
    setTimingDurationMinutes(
      stage?.actualDurationSeconds ? (stage.actualDurationSeconds / 60).toString() : (stage?.configuredDurationMinutes?.toString() || '20')
    );
    setTimingNotes(stage?.notes || '');
    setTimingTimekeeperName(stage?.timekeeperName || 'Court Clerk / Timekeeper');
    setTimingViolationsNotes(stage?.timeViolationsNotes || '');
    setTimingPenaltySeconds(stage?.penaltySeconds || 0);
    setIsTimingModalOpen(true);
  };

  const openQuestionModal = (pairId: string, teamId: string) => {
    setQuestionPairId(pairId);
    setQuestionTeamId(teamId);
    setQuestionText('');
    setQuestionStage('prep_1');
    setQuestionNotes('');
    setIsQuestionModalOpen(true);
  };

  const openAgentModal = (teamId: string) => {
    setAgentTeamId(teamId);
    const rec = data?.agentGuesses[teamId];
    if (rec && rec.guesses && rec.guesses.length > 0) {
      setAgentGuessesList(rec.guesses.map((g, i) => ({
        suspectId: g.suspectId || g.agentId || `suspect-${i + 1}`,
        suspectName: g.suspectName || `Suspect Agent ${i + 1}`,
        isCorrect: !!g.isCorrect,
      })));
      setAgentNotes(rec.notes || '');
    } else {
      setAgentGuessesList([
        { suspectId: 'suspect-1', suspectName: 'Suspect Agent Alpha', isCorrect: true },
        { suspectId: 'suspect-2', suspectName: 'Suspect Agent Beta', isCorrect: false },
      ]);
      setAgentNotes('');
    }
    setIsAgentModalOpen(true);
  };

  if (isLoading || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-400 font-medium text-sm">Loading Round 4: The Legal Battle data...</p>
      </div>
    );
  }

  const { config, pairs, stats, engine, round3Finalized } = data;

  return (
    <div className="space-y-6">
      {/* Toast Feedback */}
      {toastMessage && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-2.5 rounded-lg shadow-xl text-sm font-medium border flex items-center gap-2 ${
            toastMessage.type === 'success'
              ? 'bg-emerald-950/90 text-emerald-200 border-emerald-500/50'
              : toastMessage.type === 'error'
              ? 'bg-rose-950/90 text-rose-200 border-rose-500/50'
              : 'bg-cyan-950/90 text-cyan-200 border-cyan-500/50'
          }`}
        >
          {toastMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          )}
          {toastMessage.text}
        </div>
      )}

      {/* Header */}
      <PageHeader
        title="Round 4: The Legal Battle"
        subtitle="4 finalist squads • 2 semifinal matchups • 100-point rubric • multi-round composite final scoreboard"
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
              : '2 Semifinals In Progress'}
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setIsPublicScoreboard(!isPublicScoreboard)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 border transition-all ${
                isPublicScoreboard
                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 shadow-[0_0_12px_rgba(34,211,238,0.2)]'
                  : 'bg-neutral-800 text-neutral-300 border-neutral-700 hover:text-white'
              }`}
            >
              {isPublicScoreboard ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              {isPublicScoreboard ? 'Public Mode: ON' : 'Public Mode: OFF'}
            </button>

            {!config.isFinalized && !config.pairingsConfirmed && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleRandomizePairings}
              >
                <ArrowUpDown className="w-3.5 h-3.5 mr-1.5 text-primary-500" />
                Randomize 2 Semifinals
              </Button>
            )}

            {!config.isFinalized && !config.pairingsConfirmed && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsConfirmPairingsOpen(true)}
              >
                <Lock className="w-3.5 h-3.5 mr-1.5" />
                Confirm 2 Pairings
              </Button>
            )}

            {!config.isFinalized && config.pairingsConfirmed && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsUnlockPairingsOpen(true)}
                className="text-slate-400 hover:text-amber-400"
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
              <Settings className="w-3.5 h-3.5 mr-1.5 text-slate-400" />
              Rules & Rubric
            </Button>

            {!config.isFinalized && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSimulate}
                >
                  <Sparkles className="w-3.5 h-3.5 mr-1.5 text-primary-400" />
                  Simulate Field
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsResetModalOpen(true)}
                  className="text-slate-400 hover:text-rose-400"
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
                className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold"
              >
                <Award className="w-3.5 h-3.5 mr-1.5" />
                Finalize Round 4
              </Button>
            )}
          </div>
        }
      />

      {/* Warning Banner: Round 3 Not Finalized */}
      {!round3Finalized && (
        <div className="bg-amber-950/30 border border-amber-800/60 rounded-xl p-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-amber-200">
                Prerequisite Incomplete: Round 3 (The Black Market) is Not Finalized
              </p>
              <p className="text-xs text-amber-300/80">
                The 4 participating finalist squads shown below are provisional based on current Black Market ledgers. Finalize Round 3 to seal official qualification.
              </p>
            </div>
          </div>
          <Link to="/round-3">
            <Button variant="outline" size="sm" className="border-amber-700 text-amber-300 hover:bg-amber-900/40">
              Go to Round 3 <ExternalLink className="w-3.5 h-3.5 ml-1.5" />
            </Button>
          </Link>
        </div>
      )}

      {/* Warning Banner: Pairings Not Confirmed */}
      {!config.isFinalized && !config.pairingsConfirmed && (
        <div className="bg-amber-950/30 border border-amber-800/60 rounded-xl p-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-amber-200">
                2 Semifinal Matchups Require Organizer Confirmation
              </p>
              <p className="text-xs text-amber-300/80">
                Official tournament rules require organizers to confirm the 2 head-to-head pairs (Seed 1 vs 4, Seed 2 vs 3) before oral hearings begin.
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsConfirmPairingsOpen(true)}
            className="border-amber-700 text-amber-300 hover:bg-amber-900/40 shrink-0"
          >
            <Lock className="w-3.5 h-3.5 mr-1.5" /> Confirm 2 Pairings
          </Button>
        </div>
      )}

      {/* 6-Metric KPI Bar */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <SummaryMetric
          label="Finalist Squads"
          value={`${stats.eligibleTeamsCount} / 4`}
          subtext={stats.eligibleTeamsCount === 4 ? 'Top 4 from R3' : 'Roster pending'}
          icon={Trophy}
          variant="blue"
        />
        <SummaryMetric
          label="Semifinal Matches"
          value={`${stats.pairsConfiguredCount} / 2`}
          subtext={stats.pairingsConfirmed ? 'Confirmed & Locked' : 'Pending lock'}
          icon={Scale}
          variant={stats.pairingsConfirmed ? 'emerald' : 'amber'}
        />
        <SummaryMetric
          label="Cases Assigned"
          value={`${stats.casesAssignedCount} / 2`}
          subtext="Prosecution & Defense"
          icon={FileText}
          variant="default"
        />
        <SummaryMetric
          label="Hearings Done"
          value={`${stats.hearing2CompletedCount} / 2`}
          subtext={`Exch: ${stats.fileExchangeCompletedCount}/2`}
          icon={Gavel}
          variant="purple"
        />
        <SummaryMetric
          label="Scorecards"
          value={`${stats.judgingCompletedCount} / 4`}
          subtext="100-mark rubric"
          icon={Award}
          variant="blue"
        />
        <SummaryMetric
          label="Agent Guesses"
          value={`${stats.agentGuessesVerifiedCount} / 4`}
          subtext="+30 / -20 scored"
          icon={ShieldAlert}
          variant="rose"
        />
      </div>

      {/* Pre-Finalization Safeguards Drawer */}
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
      <div className="flex items-center gap-2 border-b border-cyan-500/20 overflow-x-auto">
        <button
          onClick={() => setActiveTab('leaderboard')}
          className={`px-4 py-2.5 text-xs font-bold border-b-2 flex items-center gap-2 transition-all rounded-t-lg shrink-0 ${
            activeTab === 'leaderboard'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/40 shadow-[0_0_15px_rgba(34,211,238,0.15)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Trophy className="w-3.5 h-3.5" />
          Official Leaderboard (9 Columns)
        </button>
        <button
          onClick={() => setActiveTab('courtrooms')}
          className={`px-4 py-2.5 text-xs font-bold border-b-2 flex items-center gap-2 transition-all rounded-t-lg shrink-0 ${
            activeTab === 'courtrooms'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/40 shadow-[0_0_15px_rgba(34,211,238,0.15)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Gavel className="w-3.5 h-3.5" />
          Semifinal Matchups ({pairs.length})
        </button>
        <button
          onClick={() => setActiveTab('judging')}
          className={`px-4 py-2.5 text-xs font-bold border-b-2 flex items-center gap-2 transition-all rounded-t-lg shrink-0 ${
            activeTab === 'judging'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/40 shadow-[0_0_15px_rgba(34,211,238,0.15)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          Faculty Judging & Rubric (100 pts)
        </button>
        <button
          onClick={() => setActiveTab('timekeeper_rp')}
          className={`px-4 py-2.5 text-xs font-bold border-b-2 flex items-center gap-2 transition-all rounded-t-lg shrink-0 ${
            activeTab === 'timekeeper_rp'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/40 shadow-[0_0_15px_rgba(34,211,238,0.15)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          Timekeeper & Resource Person
        </button>
        <button
          onClick={() => setActiveTab('agent_portal')}
          className={`px-4 py-2.5 text-xs font-bold border-b-2 flex items-center gap-2 transition-all rounded-t-lg shrink-0 ${
            activeTab === 'agent_portal'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/40 shadow-[0_0_15px_rgba(34,211,238,0.15)]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          Secret Agent Final Guesses (+30 / -20)
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: OFFICIAL LEADERBOARD (9 COLUMNS) */}
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
                placeholder="Search finalist squad..."
                className="w-full pl-9 pr-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white placeholder-neutral-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex items-center gap-3">
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="bg-neutral-900 border border-neutral-700 rounded-lg text-xs px-3 py-1.5 text-neutral-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="all">All Statuses</option>
                <option value="qualified">Qualified / Advancing</option>
                <option value="review">Review Needed</option>
                <option value="incomplete">Incomplete Hearings</option>
              </select>

              <select
                value={sortField}
                onChange={(e) => setSortField(e.target.value as SortField)}
                className="bg-neutral-900 border border-neutral-700 rounded-lg text-xs px-3 py-1.5 text-neutral-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="rank">Sort by Rank</option>
                <option value="finalScore">Sort by Final Score</option>
                <option value="r4Legal">Sort by R4 Legal Score</option>
                <option value="r3Balance">Sort by R3 Balance</option>
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

          {/* Standings Table: Exact 9 Columns */}
          <div className="bg-navy-900/40 border border-neutral-800 rounded-xl overflow-hidden shadow-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-neutral-300">
                <thead className="bg-neutral-900/90 text-xs uppercase font-semibold text-neutral-400 border-b border-neutral-800">
                  <tr>
                    <th className="py-3 px-4">Team</th>
                    <th className="py-3 px-3 text-right">R1 Points</th>
                    <th className="py-3 px-3 text-right">R2 Cabo Score</th>
                    <th className="py-3 px-3 text-right">Agent Task Credits</th>
                    <th className="py-3 px-3 text-right">R3 Final Balance</th>
                    <th className="py-3 px-3 text-right">R4 Legal Battle</th>
                    <th className="py-3 px-3 text-right">Agent Guessing</th>
                    <th className="py-3 px-4 text-right font-bold text-white bg-cyan-950/30">FINAL SCORE</th>
                    <th className="py-3 px-4 text-center font-bold">Final Rank</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/60">
                  {filteredRecords.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-12 text-center text-neutral-500">
                        No finalist squads matched filter criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredRecords.map((rec) => {
                      const fs = rec.finalScoreBreakdown;
                      const r1Pts = fs.r1Points ?? 0;
                      const r2Pts = fs.r2Cabo ?? 0;
                      const agentCredits = fs.agentTaskCredits ?? 0;
                      const r3Bal = fs.r3Balance ?? rec.blackMarketBalance;
                      const r4Legal = fs.r4LegalScore ?? rec.panelScore ?? 0;
                      const agentGuessPts = fs.agentGuessPoints ?? (rec.agentGuessingRecord?.pointsAwarded ?? 0);
                      const finalScoreVal = fs.finalScore;

                      return (
                        <tr
                          key={rec.teamId}
                          className={`hover:bg-neutral-800/30 transition-colors ${
                            rec.rank === 1 && config.isFinalized
                              ? 'bg-amber-950/20'
                              : ''
                          }`}
                        >
                          {/* Column 1: Team */}
                          <td className="py-3.5 px-4">
                            <div className="font-semibold text-white flex items-center gap-2">
                              {rec.teamName}
                              {!isPublicScoreboard && rec.side && (
                                <span className={`text-[10px] px-1.5 py-0.5 rounded border ${
                                  rec.side.includes('Prosecution')
                                    ? 'bg-blue-950/60 text-blue-300 border-blue-800'
                                    : 'bg-amber-950/60 text-amber-300 border-amber-800'
                                }`}>
                                  {rec.side.includes('Prosecution') ? 'Pros' : 'Def'}
                                </span>
                              )}
                            </div>
                            <div className="text-xs font-mono text-cyan-400 mt-0.5">
                              {formatTeamNumber(rec.teamNumber)}
                              {!isPublicScoreboard && rec.pairNumber && (
                                <span className="text-neutral-500 ml-2">Pair #{rec.pairNumber}</span>
                              )}
                            </div>
                          </td>

                          {/* Column 2: R1 Points */}
                          <td className="py-3.5 px-3 text-right font-mono text-neutral-300">
                            {r1Pts}
                          </td>

                          {/* Column 3: R2 Cabo Score */}
                          <td className="py-3.5 px-3 text-right font-mono text-neutral-300">
                            {r2Pts}
                          </td>

                          {/* Column 4: Secret Agent Task Credits */}
                          <td className="py-3.5 px-3 text-right font-mono text-emerald-400 font-medium">
                            +{agentCredits}
                          </td>

                          {/* Column 5: R3 Final Balance */}
                          <td className="py-3.5 px-3 text-right font-mono text-primary-300">
                            {r3Bal}
                          </td>

                          {/* Column 6: R4 Legal Battle Score */}
                          <td className="py-3.5 px-3 text-right font-mono font-medium text-white">
                            {r4Legal !== null ? (
                              <span>{r4Legal}</span>
                            ) : (
                              <span className="text-neutral-500 text-xs">Pending</span>
                            )}
                          </td>

                          {/* Column 7: Agent Guessing Points */}
                          <td className="py-3.5 px-3 text-right font-mono">
                            <span
                              className={
                                agentGuessPts > 0
                                  ? 'text-emerald-400 font-medium'
                                  : agentGuessPts < 0
                                  ? 'text-rose-400 font-medium'
                                  : 'text-neutral-400'
                              }
                            >
                              {agentGuessPts > 0 ? `+${agentGuessPts}` : agentGuessPts}
                            </span>
                          </td>

                          {/* Column 8: FINAL SCORE */}
                          <td className="py-3.5 px-4 text-right font-mono font-bold text-base bg-cyan-950/20 text-cyan-300">
                            {finalScoreVal !== null ? (
                              <span>{finalScoreVal}</span>
                            ) : (
                              <span className="text-neutral-500 text-xs font-normal">Pending</span>
                            )}
                          </td>

                          {/* Column 9: Final Rank */}
                          <td className="py-3.5 px-4 text-center font-bold">
                            {rec.rank !== null && rec.rank !== undefined ? (
                              <span
                                className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs ${
                                  rec.rank === 1
                                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/50 shadow-[0_0_10px_rgba(245,158,11,0.2)]'
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
                        </tr>
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
      {/* TAB 2: SEMIFINAL MATCHUPS (2 PAIRS) */}
      {/* ========================================================================= */}
      {activeTab === 'courtrooms' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-neutral-400">
              2 official semifinal legal battles (Seed 1 vs Seed 4, Seed 2 vs Seed 3). Teams progress through 5 courtroom stages.
            </p>
            {!config.isFinalized && !config.pairingsConfirmed && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsConfirmPairingsOpen(true)}
                className="bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                <Lock className="w-4 h-4 mr-1.5" /> Confirm 2 Semifinal Pairings
              </Button>
            )}
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {pairs.map((pair) => {
              const teamA = data.records.find((r) => r.teamId === pair.teamAId);
              const teamB = data.records.find((r) => r.teamId === pair.teamBId);

              return (
                <Card
                  key={pair.pairId}
                  className="bg-navy-900/50 border-neutral-800 rounded-2xl overflow-hidden shadow-xl"
                >
                  <CardHeader className="bg-neutral-900/80 border-b border-neutral-800/80 p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <span className="w-7 h-7 rounded-lg bg-cyan-950/80 border border-cyan-800 text-cyan-300 font-bold text-xs flex items-center justify-center">
                          #{pair.pairNumber}
                        </span>
                        <div>
                          <h3 className="text-base font-bold text-white flex items-center gap-2">
                            {pair.caseName || `Semifinal Matchup #${pair.pairNumber}`}
                          </h3>
                          <span className="text-xs text-neutral-400 font-mono">
                            {pair.caseId || `CASE-40${pair.pairNumber}`}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <Badge variant={pair.isConfirmed ? 'success' : 'warning'}>
                          {pair.isConfirmed ? 'Pairing Confirmed' : 'Unconfirmed'}
                        </Badge>
                        {!config.isFinalized && !isPublicScoreboard && (
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
                          <span className="text-xs font-bold text-blue-400">
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
                            <span>Case Docket:</span>
                            <span className={pair.teamAAssignment.hasReceivedCaseFile ? 'text-emerald-400 font-medium' : 'text-neutral-500'}>
                              {pair.teamAAssignment.hasReceivedCaseFile ? 'Received' : 'Pending'}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-neutral-400">
                            <span>Opposing File:</span>
                            <span className={pair.teamAAssignment.hasReceivedOpposingFile ? 'text-emerald-400 font-medium' : 'text-neutral-500'}>
                              {pair.teamAAssignment.hasReceivedOpposingFile ? 'Exchanged' : 'Pending'}
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
                            <span>Case Docket:</span>
                            <span className={pair.teamBAssignment.hasReceivedCaseFile ? 'text-emerald-400 font-medium' : 'text-neutral-500'}>
                              {pair.teamBAssignment.hasReceivedCaseFile ? 'Received' : 'Pending'}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-neutral-400">
                            <span>Opposing File:</span>
                            <span className={pair.teamBAssignment.hasReceivedOpposingFile ? 'text-emerald-400 font-medium' : 'text-neutral-500'}>
                              {pair.teamBAssignment.hasReceivedOpposingFile ? 'Exchanged' : 'Pending'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 5 Stages Progress */}
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between text-xs text-neutral-400 font-medium">
                        <span>Trial Progression (5 Stages)</span>
                        <span>Click stage to log timing</span>
                      </div>

                      <div className="grid grid-cols-5 gap-2">
                        {Object.entries(pair.stages).map(([sId, stage]) => {
                          const isDone = stage.status === 'completed';
                          const isRunning = stage.status === 'in_progress';

                          return (
                            <button
                              key={sId}
                              disabled={config.isFinalized || isPublicScoreboard}
                              onClick={() => openTimingModal(pair.pairId, sId as Round4StageId)}
                              className={`p-2 rounded-lg border text-left transition-all ${
                                isDone
                                  ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
                                  : isRunning
                                  ? 'bg-cyan-950/40 border-cyan-500/40 text-cyan-300 animate-pulse'
                                  : 'bg-neutral-900 border-neutral-800 text-neutral-400 hover:border-neutral-700'
                              }`}
                            >
                              <div className="text-[10px] font-semibold truncate">{stage.name}</div>
                              <div className="text-[11px] font-mono mt-1">
                                {stage.actualDurationSeconds
                                  ? `${Math.round(stage.actualDurationSeconds / 60)}m`
                                  : `${stage.configuredDurationMinutes || '—'}m`}
                              </div>
                            </button>
                          );
                        })}
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
      {/* TAB 3: FACULTY JUDGING & 100-PT RUBRIC CONSOLE */}
      {/* ========================================================================= */}
      {activeTab === 'judging' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-navy-900/40 p-4 rounded-xl border border-neutral-800">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-cyan-400" />
                Official 100-Mark Faculty Judging Rubric & Locked Scorecards
              </h3>
              <p className="text-xs text-neutral-400 mt-0.5">
                Each squad is scored out of 100 across 6 categories. Scorecards must be locked upon submission. Corrections are audited.
              </p>
            </div>
            {!isPublicScoreboard && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsRulesModalOpen(true)}
                className="border-neutral-700 text-xs"
              >
                <Sliders className="w-3.5 h-3.5 mr-1.5 text-neutral-400" />
                Configure Rubric
              </Button>
            )}
          </div>

          {/* Rubric Category Reference Bar */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {config.rubricCategories.map((cat) => (
              <div key={cat.id} className="bg-neutral-900/60 p-3 rounded-lg border border-neutral-800">
                <p className="text-xs text-neutral-400 font-medium truncate" title={cat.name}>
                  {cat.name}
                </p>
                <div className="mt-1 flex items-baseline justify-between">
                  <span className="text-base font-bold text-white">{cat.maxMarks} pts</span>
                  <span className="text-[10px] text-cyan-400 font-mono">Max</span>
                </div>
              </div>
            ))}
          </div>

          {/* Finalist Squads Scorecards Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {data.records.map((rec) => {
              const teamScores = data.judgeScores[rec.teamId] || [];

              return (
                <Card key={rec.teamId} className="bg-navy-900/50 border-neutral-800 p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-cyan-400 font-bold">
                          {formatTeamNumber(rec.teamNumber)}
                        </span>
                        <h4 className="text-sm font-bold text-white">{rec.teamName}</h4>
                      </div>
                      <p className="text-xs text-neutral-400 mt-0.5">
                        {rec.side} | {rec.caseName || 'Case Docket TBD'}
                      </p>
                    </div>

                    <div className="text-right">
                      <div className="text-lg font-bold font-mono text-white">
                        {rec.panelScore !== null ? `${rec.panelScore} / 100` : 'Pending'}
                      </div>
                      <Badge variant={rec.isJudgePanelComplete ? 'success' : 'warning'} size="sm">
                        {rec.isJudgePanelComplete ? 'Scores Submitted' : 'Awaiting Scores'}
                      </Badge>
                    </div>
                  </div>

                  {/* Scorecards List */}
                  <div className="space-y-3">
                    {teamScores.length === 0 ? (
                      <p className="text-neutral-500 italic text-xs py-3 text-center">
                        No faculty scorecards entered for this squad yet.
                      </p>
                    ) : (
                      teamScores.map((js: JudgeScoreRecord) => {
                        const isLocked = !!js.isLocked;

                        return (
                          <div
                            key={js.id}
                            className="p-3 rounded-lg bg-neutral-900/60 border border-neutral-800 space-y-2.5"
                          >
                            <div className="flex items-center justify-between text-xs">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-white">{js.judgeName}</span>
                                {isLocked ? (
                                  <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800 font-semibold">
                                    <Lock className="w-2.5 h-2.5" /> LOCKED
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-800 font-semibold">
                                    <Unlock className="w-2.5 h-2.5" /> UNLOCKED
                                  </span>
                                )}
                              </div>

                              <span className="font-mono text-emerald-400 font-bold text-sm">
                                {js.totalScore} / 100
                              </span>
                            </div>

                            {/* Category Marks Pills */}
                            <div className="grid grid-cols-6 gap-1.5 text-center text-[10px] font-mono">
                              <div className="bg-neutral-800/80 p-1 rounded">
                                <div className="text-neutral-400 text-[9px]">Log</div>
                                <div className="font-bold text-white">{js.scores?.logical_structure ?? '—'}</div>
                              </div>
                              <div className="bg-neutral-800/80 p-1 rounded">
                                <div className="text-neutral-400 text-[9px]">Evid</div>
                                <div className="font-bold text-white">{js.scores?.evidence_use ?? '—'}</div>
                              </div>
                              <div className="bg-neutral-800/80 p-1 rounded">
                                <div className="text-neutral-400 text-[9px]">Rebut</div>
                                <div className="font-bold text-white">{js.scores?.rebuttal ?? '—'}</div>
                              </div>
                              <div className="bg-neutral-800/80 p-1 rounded">
                                <div className="text-neutral-400 text-[9px]">RP</div>
                                <div className="font-bold text-white">{js.scores?.resource_questioning ?? '—'}</div>
                              </div>
                              <div className="bg-neutral-800/80 p-1 rounded">
                                <div className="text-neutral-400 text-[9px]">Pres</div>
                                <div className="font-bold text-white">{js.scores?.presentation_teamwork ?? '—'}</div>
                              </div>
                              <div className="bg-neutral-800/80 p-1 rounded">
                                <div className="text-neutral-400 text-[9px]">Time</div>
                                <div className="font-bold text-white">{js.scores?.time_management ?? '—'}</div>
                              </div>
                            </div>

                            {/* Correction note if audited */}
                            {js.correctionNotes && (
                              <div className="text-[11px] p-2 rounded bg-amber-950/20 border border-amber-800/40 text-amber-300">
                                <span className="font-semibold">Audited Correction ({js.correctedBy || 'Organizer'}): </span>
                                {js.correctionNotes}
                              </div>
                            )}

                            {/* Action Buttons */}
                            {!config.isFinalized && !isPublicScoreboard && (
                              <div className="flex items-center justify-end gap-2 pt-1 border-t border-neutral-800/60">
                                {!isLocked ? (
                                  <>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => openScorecardModal(rec.teamId, js.judgeId)}
                                      className="text-xs text-cyan-400 hover:text-white py-1"
                                    >
                                      Edit Scores
                                    </Button>
                                    <Button
                                      variant="secondary"
                                      size="sm"
                                      onClick={() => handleLockScorecard(rec.teamId, js.judgeId, js.judgeName)}
                                      className="text-xs bg-emerald-950/60 text-emerald-300 border-emerald-800 hover:bg-emerald-900 py-1"
                                    >
                                      <Lock className="w-3 h-3 mr-1" /> Lock Scorecard
                                    </Button>
                                  </>
                                ) : (
                                  <>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => handleUnlockScorecard(rec.teamId, js.judgeId)}
                                      className="text-xs text-amber-400 hover:text-amber-300 py-1"
                                    >
                                      <Unlock className="w-3 h-3 mr-1" /> Unlock
                                    </Button>
                                    <Button
                                      variant="secondary"
                                      size="sm"
                                      onClick={() => openCorrectionModal(rec.teamId, js)}
                                      className="text-xs bg-cyan-950/60 text-cyan-300 border-cyan-800 hover:bg-cyan-900 py-1"
                                    >
                                      <Edit3 className="w-3 h-3 mr-1" /> Audited Correction
                                    </Button>
                                  </>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>

                  {!config.isFinalized && !isPublicScoreboard && (
                    <div className="flex items-center gap-2 pt-2 border-t border-neutral-800">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => openScorecardModal(rec.teamId, 'judge-1')}
                        className="text-xs flex-1 border-neutral-700"
                      >
                        Score as Judge 1
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => openScorecardModal(rec.teamId, 'judge-2')}
                        className="text-xs flex-1 border-neutral-700"
                      >
                        Score as Judge 2
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
      {/* TAB 4: TIMEKEEPER & RESOURCE PERSON CONSOLE */}
      {/* ========================================================================= */}
      {activeTab === 'timekeeper_rp' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Section A: Timekeeper Controls */}
            <Card className="bg-navy-900/50 border-neutral-800 p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                <div className="flex items-center gap-2">
                  <Clock className="w-5 h-5 text-cyan-400" />
                  <div>
                    <h3 className="text-sm font-bold text-white">Courtroom Timekeeper Console</h3>
                    <p className="text-xs text-neutral-400">Track preparation, hearings, file exchange, and overtime penalties</p>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                {pairs.map((pair) => (
                  <div key={pair.pairId} className="bg-neutral-900/60 p-4 rounded-xl border border-neutral-800 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs text-white">
                        Matchup #{pair.pairNumber}: {pair.caseName}
                      </span>
                      <span className="text-[11px] font-mono text-cyan-400">Pair #{pair.pairNumber}</span>
                    </div>

                    <div className="space-y-2">
                      {Object.entries(pair.stages).map(([sId, stage]) => (
                        <div
                          key={sId}
                          className="flex items-center justify-between p-2.5 rounded bg-neutral-800/40 text-xs border border-neutral-800"
                        >
                          <div>
                            <div className="font-medium text-white">{stage.name}</div>
                            <div className="text-[11px] text-neutral-400">
                              Status: <span className="capitalize text-neutral-300">{stage.status}</span>
                              {stage.penaltySeconds ? ` • Penalty: ${stage.penaltySeconds}s` : ''}
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="font-mono text-cyan-300 font-semibold">
                              {stage.actualDurationSeconds
                                ? `${Math.round(stage.actualDurationSeconds / 60)} min`
                                : `${stage.configuredDurationMinutes || 0} min`}
                            </span>
                            {!config.isFinalized && !isPublicScoreboard && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openTimingModal(pair.pairId, sId as Round4StageId)}
                                className="text-xs text-cyan-400 hover:text-white p-1"
                              >
                                Edit
                              </Button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            {/* Section B: Resource Person Cross-Examination */}
            <Card className="bg-navy-900/50 border-neutral-800 p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
                <div className="flex items-center gap-2">
                  <UserCheck className="w-5 h-5 text-emerald-400" />
                  <div>
                    <h3 className="text-sm font-bold text-white">Faculty Resource Person Docket</h3>
                    <p className="text-xs text-neutral-400">Log witness inquiries and discovery cross-examination</p>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                {pairs.map((pair) => {
                  const rp = data.resourcePersons[pair.pairId];
                  const questions = rp?.questions || [];

                  return (
                    <div key={pair.pairId} className="bg-neutral-900/60 p-4 rounded-xl border border-neutral-800 space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-bold text-xs text-white">
                            {rp?.nameOrIdentifier || `Resource Person (Pair #${pair.pairNumber})`}
                          </div>
                          <div className="text-[11px] text-neutral-400">{pair.caseName}</div>
                        </div>
                        {!config.isFinalized && !isPublicScoreboard && (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => openQuestionModal(pair.pairId, pair.teamAId || '')}
                            className="text-xs border-neutral-700"
                          >
                            + Log Query
                          </Button>
                        )}
                      </div>

                      <div className="space-y-2">
                        {questions.length === 0 ? (
                          <p className="text-neutral-500 italic text-xs py-2 text-center">
                            No inquiries logged with resource person for this matchup.
                          </p>
                        ) : (
                          questions.map((q) => {
                            const qTeam = data.records.find((r) => r.teamId === q.teamId);
                            return (
                              <div key={q.id} className="p-2.5 rounded bg-neutral-800/40 border border-neutral-800 text-xs space-y-1">
                                <div className="flex items-center justify-between font-semibold text-white">
                                  <span>{qTeam?.teamName || 'Squad'}</span>
                                  <span className="text-[10px] text-neutral-400 font-mono capitalize">{q.stage}</span>
                                </div>
                                <p className="text-neutral-300">"{q.questionText}"</p>
                                {q.notes && (
                                  <p className="text-[11px] text-neutral-400 italic">Response: {q.notes}</p>
                                )}
                              </div>
                            );
                          })
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 5: SECRET AGENT FINAL GUESSING PORTAL */}
      {/* ========================================================================= */}
      {activeTab === 'agent_portal' && (
        <div className="space-y-6">
          <div className="bg-amber-950/20 border border-amber-800/60 rounded-xl p-4 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <ShieldAlert className="w-6 h-6 text-amber-400 shrink-0" />
              <div>
                <h3 className="text-sm font-bold text-amber-200">
                  Restricted Organizer Console: Secret Agent Final Guessing
                </h3>
                <p className="text-xs text-amber-300/80">
                  Rules: 1 to 5 guesses per squad. Correct = +30 pts • Incorrect = -20 pts • No guess = 0 pts. Agent identities strictly shielded from public view.
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
                    <th className="py-3 px-4 text-center">Total Guesses (1–5)</th>
                    <th className="py-3 px-4 text-center">Correct (+30) / Wrong (-20)</th>
                    <th className="py-3 px-4 text-right">Points Awarded</th>
                    <th className="py-3 px-4 text-center">Verification Status</th>
                    <th className="py-3 px-4">Audit Notes</th>
                    {!isPublicScoreboard && <th className="py-3 px-4 text-right">Action</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/60">
                  {data.records.map((rec) => {
                    const guess = rec.agentGuessingRecord;
                    const tot = guess?.totalGuesses ?? (guess?.guesses?.length ?? (guess?.outcome === 'pending' ? 0 : 1));
                    const corr = guess?.correctGuesses ?? (guess?.outcome === 'correct' ? 1 : 0);
                    const wrg = guess?.wrongGuesses ?? (guess?.outcome === 'incorrect' ? 1 : 0);
                    const pts = guess?.pointsAwarded ?? 0;

                    return (
                      <tr key={rec.teamId} className="hover:bg-neutral-800/30 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-semibold text-white">{rec.teamName}</div>
                          <div className="text-xs font-mono text-cyan-400">
                            {formatTeamNumber(rec.teamNumber)}
                          </div>
                        </td>

                        <td className="py-3 px-4 text-center font-mono">
                          {tot > 0 ? `${tot} guess(es)` : 'None'}
                        </td>

                        <td className="py-3 px-4 text-center font-mono text-xs">
                          {tot > 0 ? (
                            <span>
                              <span className="text-emerald-400 font-semibold">{corr} correct</span> /{' '}
                              <span className="text-rose-400 font-semibold">{wrg} wrong</span>
                            </span>
                          ) : (
                            <span className="text-neutral-500">—</span>
                          )}
                        </td>

                        <td className="py-3 px-4 text-right font-mono font-bold">
                          <span
                            className={
                              pts > 0
                                ? 'text-emerald-400'
                                : pts < 0
                                ? 'text-rose-400'
                                : 'text-neutral-400'
                            }
                          >
                            {pts > 0 ? `+${pts}` : pts}
                          </span>
                        </td>

                        <td className="py-3 px-4 text-center">
                          <Badge variant={guess?.isVerified ? 'success' : 'warning'}>
                            {guess?.isVerified ? 'Verified by Marshal' : 'Pending Verification'}
                          </Badge>
                        </td>

                        <td className="py-3 px-4 text-xs text-neutral-400 max-w-xs truncate">
                          {guess?.notes || <span className="text-neutral-600 italic">No notes</span>}
                        </td>

                        {!isPublicScoreboard && (
                          <td className="py-3 px-4 text-right">
                            {!config.isFinalized && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openAgentModal(rec.teamId)}
                                className="text-xs text-cyan-400 hover:text-white"
                              >
                                Audit Guesses
                              </Button>
                            )}
                          </td>
                        )}
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
      {/* MODAL 0: RULES & RUBRIC CONFIGURATION */}
      {/* ========================================================================= */}
      {isRulesModalOpen && (
        <Modal
          isOpen={isRulesModalOpen}
          onClose={() => setIsRulesModalOpen(false)}
          title="Round 4 Rules & Composite Formula Configuration"
          subtitle="Configure advancing teams count, judging aggregation, and final composite score formula."
          maxWidth="lg"
        >
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-neutral-400">Advancing Champions Count</label>
                <input
                  type="number"
                  min="1"
                  max="4"
                  value={formAdvancingCount}
                  onChange={(e) => setFormAdvancingCount(parseInt(e.target.value) || 1)}
                  className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white font-mono"
                />
                <span className="text-[11px] text-neutral-500">Official tournament plan: 1 champion</span>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-neutral-400">Judge Panel Aggregation</label>
                <select
                  value={formJudgeAggregation}
                  onChange={(e) => setFormJudgeAggregation(e.target.value as any)}
                  className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
                >
                  <option value="average">Average Score</option>
                  <option value="sum">Sum of Marks</option>
                  <option value="single_judge">Single Judge</option>
                </select>
              </div>
            </div>

            <div className="p-3 bg-neutral-900/60 rounded-xl border border-neutral-800 space-y-2">
              <div className="text-xs font-semibold text-cyan-400">Official Multi-Round Composite Scoring Formula:</div>
              <p className="text-xs text-neutral-300 font-mono">
                Final Score = R1 Points + R2 Cabo Score + Secret Agent Task Credits + R3 Balance + R4 Legal Score + Secret Agent Guess Points
              </p>
            </div>

            <div className="space-y-2 pt-2 border-t border-neutral-800">
              <div className="text-xs font-semibold text-neutral-300">100-Point Rubric Dimensions:</div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {formRubricCategories.map((cat) => (
                  <div key={cat.id} className="p-2 rounded bg-neutral-900 border border-neutral-800 text-xs">
                    <span className="text-neutral-400 block truncate">{cat.name}</span>
                    <span className="font-mono font-bold text-white">{cat.maxMarks} pts</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-neutral-800">
              <Button variant="secondary" onClick={() => setIsRulesModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveRulesConfig}>
                Save Rules Configuration
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ========================================================================= */}
      {/* MODAL 1: JUDGE SCORECARD ENTRY */}
      {/* ========================================================================= */}
      {isScorecardModalOpen && (
        <Modal
          isOpen={isScorecardModalOpen}
          onClose={() => setIsScorecardModalOpen(false)}
          title={`Judge Scorecard: ${data.records.find((r) => r.teamId === selectedTeamId)?.teamName || 'Squad'}`}
          subtitle="Input marks across all 6 rubric categories. Total is validated against 100 marks maximum."
          maxWidth="lg"
        >
          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Judge Name / Identity</label>
              <input
                type="text"
                value={scorecardJudgeName}
                onChange={(e) => setScorecardJudgeName(e.target.value)}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white focus:outline-none focus:border-cyan-500"
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
                    className="w-20 px-2 py-1 bg-neutral-800 border border-neutral-700 rounded text-sm text-right font-mono text-white focus:outline-none focus:border-cyan-500"
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
                placeholder="Optional notes on oral arguments or cross-examination sharpness..."
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <label className="flex items-center gap-2 text-xs text-neutral-300 pt-1">
              <input
                type="checkbox"
                checked={scorecardShouldLock}
                onChange={(e) => setScorecardShouldLock(e.target.checked)}
                className="rounded border-neutral-700 bg-neutral-900 text-cyan-600 focus:ring-cyan-500"
              />
              <span className="font-semibold text-emerald-400">Lock Scorecard immediately upon submission</span>
            </label>

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
      {/* MODAL 2: AUDITED ORGANIZER CORRECTION */}
      {/* ========================================================================= */}
      {isCorrectionModalOpen && (
        <Modal
          isOpen={isCorrectionModalOpen}
          onClose={() => setIsCorrectionModalOpen(false)}
          title={`Audited Correction: ${selectedScoreRecord?.judgeName || 'Judge'}`}
          subtitle={`Squad: ${data.records.find((r) => r.teamId === selectedTeamId)?.teamName || 'Squad'}`}
          maxWidth="lg"
        >
          <div className="space-y-4 py-2">
            <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-800/40 text-xs text-amber-300">
              <AlertTriangle className="w-4 h-4 inline mr-1 text-amber-400" />
              Organizer overrides are strictly audited. Mandatory correction notes must document the rationale.
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
                    value={correctionMarks[cat.id] ?? 0}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value) || 0;
                      setCorrectionMarks({
                        ...correctionMarks,
                        [cat.id]: Math.min(cat.maxMarks, Math.max(0, val)),
                      });
                    }}
                    className="w-20 px-2 py-1 bg-neutral-800 border border-neutral-700 rounded text-sm text-right font-mono text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>
              ))}
            </div>

            <div className="p-3 bg-neutral-900/80 rounded-lg border border-neutral-800 flex items-center justify-between">
              <span className="text-sm font-semibold text-neutral-300">Adjusted Total Score:</span>
              <span className="text-xl font-bold font-mono text-emerald-400">
                {Object.values(correctionMarks).reduce((acc, v) => acc + (v || 0), 0)} / 100
              </span>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Audited By (Marshal / Lead)</label>
              <input
                type="text"
                value={correctionActor}
                onChange={(e) => setCorrectionActor(e.target.value)}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-rose-400">Mandatory Correction Notes *</label>
              <textarea
                value={correctionNotes}
                onChange={(e) => setCorrectionNotes(e.target.value)}
                rows={2}
                placeholder="Required explanation for adjusting locked judge marks..."
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-rose-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-neutral-800">
              <Button variant="secondary" onClick={() => setIsCorrectionModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveAuditedCorrection} className="bg-rose-600 hover:bg-rose-500 text-white">
                Apply Audited Correction
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ========================================================================= */}
      {/* MODAL 3: EDIT MATCHUP & CASE DETAILS */}
      {/* ========================================================================= */}
      {isEditPairModalOpen && (
        <Modal
          isOpen={isEditPairModalOpen}
          onClose={() => setIsEditPairModalOpen(false)}
          title={`Edit Courtroom Docket: Matchup #${selectedPair?.pairNumber}`}
          subtitle="Configure fictional case title, discovery brief, and counsel assignments."
          maxWidth="lg"
        >
          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Fictional Legal Case Name</label>
              <input
                type="text"
                value={editPairCaseName}
                onChange={(e) => setEditPairCaseName(e.target.value)}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Discovery Docket Brief</label>
              <textarea
                value={editPairCaseDetails}
                onChange={(e) => setEditPairCaseDetails(e.target.value)}
                rows={2}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
              />
            </div>

            <div className="grid grid-cols-2 gap-4 pt-2 border-t border-neutral-800">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-blue-400">Team A Counsel Side</label>
                <select
                  value={editPairSideA}
                  onChange={(e) => setEditPairSideA(e.target.value as LegalSide)}
                  className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
                >
                  <option value="Prosecution / Plaintiff">Prosecution / Plaintiff</option>
                  <option value="Defense / Respondent">Defense / Respondent</option>
                </select>
                <label className="flex items-center gap-2 text-xs text-neutral-300">
                  <input
                    type="checkbox"
                    checked={editPairFileA}
                    onChange={(e) => setEditPairFileA(e.target.checked)}
                    className="rounded border-neutral-700 bg-neutral-900 text-cyan-600"
                  />
                  <span>Received Case File</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-neutral-300">
                  <input
                    type="checkbox"
                    checked={editPairOppFileA}
                    onChange={(e) => setEditPairOppFileA(e.target.checked)}
                    className="rounded border-neutral-700 bg-neutral-900 text-cyan-600"
                  />
                  <span>Received Opposing File</span>
                </label>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-amber-400">Team B Counsel Side</label>
                <select
                  value={editPairSideB}
                  onChange={(e) => setEditPairSideB(e.target.value as LegalSide)}
                  className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
                >
                  <option value="Defense / Respondent">Defense / Respondent</option>
                  <option value="Prosecution / Plaintiff">Prosecution / Plaintiff</option>
                </select>
                <label className="flex items-center gap-2 text-xs text-neutral-300">
                  <input
                    type="checkbox"
                    checked={editPairFileB}
                    onChange={(e) => setEditPairFileB(e.target.checked)}
                    className="rounded border-neutral-700 bg-neutral-900 text-cyan-600"
                  />
                  <span>Received Case File</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-neutral-300">
                  <input
                    type="checkbox"
                    checked={editPairOppFileB}
                    onChange={(e) => setEditPairOppFileB(e.target.checked)}
                    className="rounded border-neutral-700 bg-neutral-900 text-cyan-600"
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
                Save Docket
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ========================================================================= */}
      {/* MODAL 4: TIMEKEEPER INTERVAL & PENALTIES */}
      {/* ========================================================================= */}
      {isTimingModalOpen && (
        <Modal
          isOpen={isTimingModalOpen}
          onClose={() => setIsTimingModalOpen(false)}
          title="Timekeeper Interval & Penalties Console"
          subtitle={`Matchup #${data.pairs.find((p) => p.pairId === timingPairId)?.pairNumber} • Stage: ${timingStageId}`}
          maxWidth="md"
        >
          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Courtroom Stage Status</label>
              <select
                value={timingStatus}
                onChange={(e) => setTimingStatus(e.target.value as StageStatus)}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
              >
                <option value="not_started">Not Started</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Duration (Minutes)</label>
              <input
                type="number"
                value={timingDurationMinutes}
                onChange={(e) => setTimingDurationMinutes(e.target.value)}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white font-mono"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Timekeeper Name</label>
              <input
                type="text"
                value={timingTimekeeperName}
                onChange={(e) => setTimingTimekeeperName(e.target.value)}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-amber-400">Time Violations / Overtime Notes</label>
              <input
                type="text"
                value={timingViolationsNotes}
                onChange={(e) => setTimingViolationsNotes(e.target.value)}
                placeholder="e.g. Defense exceeded closing argument by 45s..."
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Penalty Seconds (if applicable)</label>
              <input
                type="number"
                value={timingPenaltySeconds}
                onChange={(e) => setTimingPenaltySeconds(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-sm text-white font-mono"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">General Notes</label>
              <textarea
                value={timingNotes}
                onChange={(e) => setTimingNotes(e.target.value)}
                rows={2}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-neutral-800">
              <Button variant="secondary" onClick={() => setIsTimingModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveTiming}>
                Save Timing Log
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ========================================================================= */}
      {/* MODAL 5: RESOURCE PERSON INQUIRY */}
      {/* ========================================================================= */}
      {isQuestionModalOpen && (
        <Modal
          isOpen={isQuestionModalOpen}
          onClose={() => setIsQuestionModalOpen(false)}
          title="Log Faculty Resource Person Inquiry"
          subtitle="Record clarification or discovery question asked during preparation or hearing."
          maxWidth="md"
        >
          <div className="space-y-4 py-2">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Inquiring Squad</label>
              <select
                value={questionTeamId}
                onChange={(e) => setQuestionTeamId(e.target.value)}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
              >
                {data.records.map((r) => (
                  <option key={r.teamId} value={r.teamId}>
                    {r.teamName} ({formatTeamNumber(r.teamNumber)})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Trial Stage</label>
              <select
                value={questionStage}
                onChange={(e) => setQuestionStage(e.target.value as Round4StageId)}
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
              >
                <option value="prep_1">Preparation 1</option>
                <option value="hearing_1">Hearing 1</option>
                <option value="prep_2">Preparation 2</option>
                <option value="hearing_2">Hearing 2</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Question / Clarification *</label>
              <textarea
                value={questionText}
                onChange={(e) => setQuestionText(e.target.value)}
                rows={3}
                placeholder="Specific evidentiary inquiry asked to the expert..."
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Resource Person Answer Notes</label>
              <textarea
                value={questionNotes}
                onChange={(e) => setQuestionNotes(e.target.value)}
                rows={2}
                placeholder="Clarification or evidence guidance provided..."
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-neutral-800">
              <Button variant="secondary" onClick={() => setIsQuestionModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveQuestion}>
                Log Query
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ========================================================================= */}
      {/* MODAL 6: SECRET AGENT 1-5 GUESSES AUDIT */}
      {/* ========================================================================= */}
      {isAgentModalOpen && (
        <Modal
          isOpen={isAgentModalOpen}
          onClose={() => setIsAgentModalOpen(false)}
          title="Secret Agent Accusation & Guessing Console"
          subtitle={`Squad: ${data.records.find((r) => r.teamId === agentTeamId)?.teamName || 'Squad'}`}
          maxWidth="lg"
        >
          <div className="space-y-4 py-2">
            <div className="p-3 rounded-lg bg-cyan-950/20 border border-cyan-800/40 text-xs text-cyan-300">
              Scoring Rules: Each squad submits 1 to 5 suspect guesses. Correct: <span className="font-bold text-emerald-400">+30 pts</span> • Incorrect: <span className="font-bold text-rose-400">-20 pts</span>.
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs font-semibold text-neutral-400">
                <span>Suspect Accusations ({agentGuessesList.length}/5)</span>
                {agentGuessesList.length < 5 && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      const newIdx = agentGuessesList.length + 1;
                      setAgentGuessesList([
                        ...agentGuessesList,
                        { suspectId: `suspect-${newIdx}`, suspectName: `Suspect Agent ${newIdx}`, isCorrect: true },
                      ]);
                    }}
                    className="text-xs py-1"
                  >
                    + Add Guess
                  </Button>
                )}
              </div>

              {agentGuessesList.map((g, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-neutral-900 border border-neutral-800 gap-3">
                  <div className="flex items-center gap-2 flex-1">
                    <span className="text-xs font-bold text-neutral-400">#{idx + 1}</span>
                    <input
                      type="text"
                      value={g.suspectName}
                      onChange={(e) => {
                        const updated = [...agentGuessesList];
                        updated[idx].suspectName = e.target.value;
                        setAgentGuessesList(updated);
                      }}
                      className="flex-1 px-2.5 py-1 bg-neutral-800 border border-neutral-700 rounded text-xs text-white"
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        const updated = [...agentGuessesList];
                        updated[idx].isCorrect = !updated[idx].isCorrect;
                        setAgentGuessesList(updated);
                      }}
                      className={`px-2.5 py-1 rounded text-xs font-bold border transition-colors ${
                        g.isCorrect
                          ? 'bg-emerald-950/60 text-emerald-300 border-emerald-700'
                          : 'bg-rose-950/60 text-rose-300 border-rose-700'
                      }`}
                    >
                      {g.isCorrect ? 'Correct (+30)' : 'Incorrect (-20)'}
                    </button>

                    {agentGuessesList.length > 1 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setAgentGuessesList(agentGuessesList.filter((_, i) => i !== idx));
                        }}
                        className="text-xs text-rose-400 hover:text-white p-1"
                      >
                        Remove
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Calculated Points Summary */}
            {(() => {
              const corr = agentGuessesList.filter((g) => g.isCorrect).length;
              const wrg = agentGuessesList.filter((g) => !g.isCorrect).length;
              const pts = corr * 30 - wrg * 20;

              return (
                <div className="p-3 bg-neutral-900/80 rounded-lg border border-neutral-800 flex items-center justify-between">
                  <span className="text-xs text-neutral-300 font-semibold">
                    Live Score Calculation ({corr} correct × +30, {wrg} wrong × -20):
                  </span>
                  <span className={`text-xl font-bold font-mono ${pts >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {pts >= 0 ? `+${pts}` : pts} pts
                  </span>
                </div>
              );
            })()}

            <div className="space-y-1">
              <label className="text-xs font-semibold text-neutral-400">Chief Marshal Audit Notes</label>
              <textarea
                value={agentNotes}
                onChange={(e) => setAgentNotes(e.target.value)}
                rows={2}
                placeholder="Audited suspect envelope verification details..."
                className="w-full px-3 py-1.5 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-white"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-neutral-800">
              <Button variant="secondary" onClick={() => setIsAgentModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveAgentGuesses}>
                Save & Verify Guesses
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
        title="Confirm & Lock 2 Semifinal Matchups"
        message="Are you sure you want to officially confirm the 2 semifinal pairings (Seed 1 vs 4, Seed 2 vs 3)? Once confirmed, matchups will be locked against accidental re-shuffling to preserve courtroom integrity."
        confirmLabel="Confirm & Lock Pairings"
      />

      <ConfirmationDialog
        isOpen={isUnlockPairingsOpen}
        onClose={() => setIsUnlockPairingsOpen(false)}
        onConfirm={handleUnlockPairings}
        title="Unlock Matchup Pairings"
        message="Unlocking pairings will allow altering courtroom assignments. Any existing stage notes will be preserved."
        confirmLabel="Unlock Pairings"
      />

      <ConfirmationDialog
        isOpen={isFinalizeModalOpen}
        onClose={() => setIsFinalizeModalOpen(false)}
        onConfirm={handleFinalize}
        title="Finalize Round 4: The Legal Battle"
        message="Are you sure you want to finalize Round 4? This will seal judge scorecards, composite final scores, and qualify the champion."
        confirmLabel="Finalize & Seal Round 4"
      />

      <ConfirmationDialog
        isOpen={isResetModalOpen}
        onClose={() => setIsResetModalOpen(false)}
        onConfirm={handleResetData}
        title="Reset Round 4 Data"
        message="Are you sure you want to reset Round 4? This will clear submitted scorecards and timing logs."
        confirmLabel="Reset Data"
      />
    </div>
  );
};
