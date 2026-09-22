from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.common import ApiResponse
from app.schemas.rounds import (
    RoundSummary,
    RoundUpdateRequest,
    FinalizeRoundRequest,
    FinalizeRoundResponse,
    Round1RecordResponse,
    Round1RecordUpdateRequest,
    Round1BatchUpdateRequest,
    Round2PlacementCreate,
    Round2PlacementResponse,
    Round2GameSubmitRequest,
    Round2TeamSummary,
    Round3TransactionCreate,
    Round3TransferRequest,
    Round3TransactionResponse,
    Round3CodeRecordResponse,
    Round3CodeFragmentUpdate,
    Round3TeamSummary,
    Round4PairCreate,
    Round4PairUpdate,
    Round4PairResponse,
    Round4JudgeScoreSubmit,
    Round4JudgeScoreResponse,
    Round4AgentGuessSubmit,
    Round4AgentGuessResponse,
    Round4TeamSummary,
    FinaleScorecardSubmit,
    FinaleScorecardResponse,
    FinaleAgentVerdictSubmit,
    FinaleAgentVerdictResponse,
    FinaleTeamSummary,
)
from app.services import round_service

router = APIRouter(prefix="/rounds", tags=["Tournament Rounds & Scoring"])


# =========================================================================
# Generic Round State Endpoints
# =========================================================================

@router.get("", response_model=ApiResponse[List[RoundSummary]])
def get_rounds(db: Session = Depends(get_db)):
    rounds = round_service.get_all_rounds(db)
    return ApiResponse(data=rounds)


@router.get("/{round_num}", response_model=ApiResponse[RoundSummary])
def get_round(round_num: int, db: Session = Depends(get_db)):
    r = round_service.get_round_by_number(db, round_num)
    return ApiResponse(data=r)


@router.put("/{round_num}", response_model=ApiResponse[RoundSummary])
def update_round(
    round_num: int,
    req: RoundUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER])),
):
    r = round_service.update_round_state(db, round_num, req)
    return ApiResponse(data=r, message=f"Round {round_num} updated successfully")


@router.post("/{round_num}/finalize", response_model=ApiResponse[FinalizeRoundResponse])
def finalize_round(
    round_num: int,
    req: FinalizeRoundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER])),
):
    res = round_service.finalize_round(db, round_num, current_user, req)
    return ApiResponse(data=res, message=res.message)


# =========================================================================
# Round 1: Clue Hunt / Expedition Endpoints
# =========================================================================

@router.get("/1/records", response_model=ApiResponse[List[Round1RecordResponse]])
def get_round1_records(db: Session = Depends(get_db)):
    records = round_service.get_round1_records(db)
    # Map team details into response
    res = []
    for r in records:
        item = Round1RecordResponse(
            id=r.id,
            teamId=r.team_id,
            teamName=r.team.name if r.team else None,
            teamIdentifier=f"T{r.team.team_number:02d}" if r.team else None,
            mini_rounds_json=r.mini_rounds_json or [],
            rawTotalSeconds=r.raw_total_seconds,
            totalPenaltySeconds=r.total_penalty_seconds,
            adjustedTotalSeconds=r.adjusted_total_seconds,
            fastestMiniRoundSeconds=r.fastest_mini_round_seconds,
            isComplete=r.is_complete,
            rank=r.rank,
            qualificationStatus=r.qualification_status,
            tieRequiresReview=r.tie_requires_review,
            tieReason=r.tie_reason,
            hiddenCodeRecovered=r.hidden_code_recovered,
            hiddenCodeRecoveredAt=r.hidden_code_recovered_at,
            hiddenCodeNotes=r.hidden_code_notes,
            lastEditedBy=r.last_edited_by,
            updatedAt=r.updated_at,
        )
        res.append(item)
    return ApiResponse(data=res)


@router.put("/1/records/{team_id}", response_model=ApiResponse[Round1RecordResponse])
def update_round1_record(
    team_id: str,
    req: Round1RecordUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    r = round_service.update_round1_record(db, team_id, req, current_user)
    item = Round1RecordResponse(
        id=r.id,
        teamId=r.team_id,
        teamName=r.team.name if r.team else None,
        teamIdentifier=f"T{r.team.team_number:02d}" if r.team else None,
        mini_rounds_json=r.mini_rounds_json or [],
        rawTotalSeconds=r.raw_total_seconds,
        totalPenaltySeconds=r.total_penalty_seconds,
        adjustedTotalSeconds=r.adjusted_total_seconds,
        fastestMiniRoundSeconds=r.fastest_mini_round_seconds,
        isComplete=r.is_complete,
        rank=r.rank,
        qualificationStatus=r.qualification_status,
        tieRequiresReview=r.tie_requires_review,
        tieReason=r.tie_reason,
        hiddenCodeRecovered=r.hidden_code_recovered,
        hiddenCodeRecoveredAt=r.hidden_code_recovered_at,
        hiddenCodeNotes=r.hidden_code_notes,
        lastEditedBy=r.last_edited_by,
        updatedAt=r.updated_at,
    )
    return ApiResponse(data=item, message="Round 1 record updated successfully")


@router.post("/1/records/batch", response_model=ApiResponse[List[Round1RecordResponse]])
def batch_update_round1(
    req: Round1BatchUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    updated = round_service.batch_update_round1_records(db, req, current_user)
    res = [
        Round1RecordResponse(
            id=r.id,
            teamId=r.team_id,
            teamName=r.team.name if r.team else None,
            teamIdentifier=f"T{r.team.team_number:02d}" if r.team else None,
            mini_rounds_json=r.mini_rounds_json or [],
            rawTotalSeconds=r.raw_total_seconds,
            totalPenaltySeconds=r.total_penalty_seconds,
            adjustedTotalSeconds=r.adjusted_total_seconds,
            fastestMiniRoundSeconds=r.fastest_mini_round_seconds,
            isComplete=r.is_complete,
            rank=r.rank,
            qualificationStatus=r.qualification_status,
            tieRequiresReview=r.tie_requires_review,
            tieReason=r.tie_reason,
            hiddenCodeRecovered=r.hidden_code_recovered,
            hiddenCodeRecoveredAt=r.hidden_code_recovered_at,
            hiddenCodeNotes=r.hidden_code_notes,
            lastEditedBy=r.last_edited_by,
            updatedAt=r.updated_at,
        )
        for r in updated
    ]
    return ApiResponse(data=res, message=f"Batch updated {len(res)} Round 1 records")


# =========================================================================
# Round 2: Cabo Endpoints
# =========================================================================

@router.get("/2/placements", response_model=ApiResponse[List[Round2PlacementResponse]])
def get_round2_placements(
    gameNumber: Optional[int] = Query(None, alias="gameNumber"),
    db: Session = Depends(get_db)
):
    placements = round_service.get_round2_placements(db, gameNumber)
    res = [
        Round2PlacementResponse(
            id=p.id,
            gameNumber=p.game_number,
            teamId=p.team_id,
            teamName=p.team.name if p.team else None,
            teamIdentifier=f"T{p.team.team_number:02d}" if p.team else None,
            placement=p.placement,
            points=p.points,
            notes=p.notes,
            recordedBy=p.recorded_by,
            recordedAt=p.recorded_at,
        )
        for p in placements
    ]
    return ApiResponse(data=res)


@router.post("/2/placements", response_model=ApiResponse[Round2PlacementResponse])
def record_round2_placement(
    req: Round2PlacementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    p = round_service.record_round2_placement(db, req, current_user)
    item = Round2PlacementResponse(
        id=p.id,
        gameNumber=p.game_number,
        teamId=p.team_id,
        teamName=p.team.name if p.team else None,
        teamIdentifier=f"T{p.team.team_number:02d}" if p.team else None,
        placement=p.placement,
        points=p.points,
        notes=p.notes,
        recordedBy=p.recorded_by,
        recordedAt=p.recorded_at,
    )
    return ApiResponse(data=item, message="Round 2 placement recorded successfully")


@router.post("/2/game/submit", response_model=ApiResponse[List[Round2PlacementResponse]])
def submit_round2_game(
    req: Round2GameSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    results = round_service.submit_round2_game(db, req, current_user)
    res = [
        Round2PlacementResponse(
            id=p.id,
            gameNumber=p.game_number,
            teamId=p.team_id,
            teamName=p.team.name if p.team else None,
            teamIdentifier=f"T{p.team.team_number:02d}" if p.team else None,
            placement=p.placement,
            points=p.points,
            notes=p.notes,
            recordedBy=p.recorded_by,
            recordedAt=p.recorded_at,
        )
        for p in results
    ]
    return ApiResponse(data=res, message=f"Submitted Game {req.game_number} results ({len(res)} teams)")


@router.get("/2/standings", response_model=ApiResponse[List[Round2TeamSummary]])
def get_round2_standings(db: Session = Depends(get_db)):
    standings = round_service.get_round2_standings(db)
    return ApiResponse(data=standings)


# =========================================================================
# Round 3: The Black Market Endpoints
# =========================================================================

@router.get("/3/transactions", response_model=ApiResponse[List[Round3TransactionResponse]])
def get_round3_transactions(
    teamId: Optional[str] = Query(None, alias="teamId"),
    db: Session = Depends(get_db)
):
    transactions = round_service.get_round3_transactions(db, teamId)
    res = [
        Round3TransactionResponse(
            id=t.id,
            teamId=t.team_id,
            teamName=t.team.name if t.team else None,
            teamIdentifier=f"T{t.team.team_number:02d}" if t.team else None,
            amount=t.amount,
            type=t.type,
            reason=t.reason,
            organizerRef=t.organizer_ref,
            timestamp=t.timestamp,
            isReversed=t.is_reversed,
            reversalTransactionId=t.reversal_transaction_id,
            reversedTransactionId=t.reversed_transaction_id,
            notes=t.notes,
        )
        for t in transactions
    ]
    return ApiResponse(data=res)


@router.post("/3/transactions", response_model=ApiResponse[Round3TransactionResponse])
def create_round3_transaction(
    req: Round3TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    t = round_service.create_round3_transaction(db, req, current_user)
    item = Round3TransactionResponse(
        id=t.id,
        teamId=t.team_id,
        teamName=t.team.name if t.team else None,
        teamIdentifier=f"T{t.team.team_number:02d}" if t.team else None,
        amount=t.amount,
        type=t.type,
        reason=t.reason,
        organizerRef=t.organizer_ref,
        timestamp=t.timestamp,
        isReversed=t.is_reversed,
        reversalTransactionId=t.reversal_transaction_id,
        reversedTransactionId=t.reversed_transaction_id,
        notes=t.notes,
    )
    return ApiResponse(data=item, message="Transaction recorded successfully")


@router.post("/3/transactions/{tx_id}/reverse", response_model=ApiResponse[Round3TransactionResponse])
def reverse_round3_transaction(
    tx_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER])),
):
    rev = round_service.reverse_round3_transaction(db, tx_id, current_user)
    item = Round3TransactionResponse(
        id=rev.id,
        teamId=rev.team_id,
        teamName=rev.team.name if rev.team else None,
        teamIdentifier=f"T{rev.team.team_number:02d}" if rev.team else None,
        amount=rev.amount,
        type=rev.type,
        reason=rev.reason,
        organizerRef=rev.organizer_ref,
        timestamp=rev.timestamp,
        isReversed=rev.is_reversed,
        reversalTransactionId=rev.reversal_transaction_id,
        reversedTransactionId=rev.reversed_transaction_id,
        notes=rev.notes,
    )
    return ApiResponse(data=item, message=f"Transaction {tx_id} successfully reversed")


@router.post("/3/transfer", response_model=ApiResponse[Dict[str, Any]])
def transfer_round3_funds(
    req: Round3TransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    s_tx, r_tx = round_service.transfer_round3_funds(db, req, current_user)
    return ApiResponse(
        data={"senderTransactionId": s_tx.id, "receiverTransactionId": r_tx.id, "amount": req.amount},
        message=f"Transferred {req.amount} points from Team {req.from_team_id} to Team {req.to_team_id}"
    )


@router.get("/3/codes", response_model=ApiResponse[List[Round3CodeRecordResponse]])
def get_round3_codes(db: Session = Depends(get_db)):
    codes = round_service.get_round3_code_records(db)
    res = [
        Round3CodeRecordResponse(
            id=c.id,
            teamId=c.team_id,
            teamName=c.team.name if c.team else None,
            fragments_json=c.fragments_json or [],
            isComplete=c.is_complete,
            verifiedAt=c.verified_at,
            verifiedBy=c.verified_by,
            updatedAt=c.updated_at,
        )
        for c in codes
    ]
    return ApiResponse(data=res)


@router.put("/3/codes/fragment", response_model=ApiResponse[Round3CodeRecordResponse])
def update_round3_code_fragment(
    req: Round3CodeFragmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    c = round_service.update_round3_code_fragment(db, req, current_user)
    item = Round3CodeRecordResponse(
        id=c.id,
        teamId=c.team_id,
        teamName=c.team.name if c.team else None,
        fragments_json=c.fragments_json or [],
        isComplete=c.is_complete,
        verifiedAt=c.verified_at,
        verifiedBy=c.verified_by,
        updatedAt=c.updated_at,
    )
    return ApiResponse(data=item, message="Code fragment updated successfully")


@router.get("/3/standings", response_model=ApiResponse[List[Round3TeamSummary]])
def get_round3_standings(db: Session = Depends(get_db)):
    standings = round_service.get_round3_standings(db)
    return ApiResponse(data=standings)


# =========================================================================
# Round 4: The Legal Battle Endpoints
# =========================================================================

@router.get("/4/pairs", response_model=ApiResponse[List[Round4PairResponse]])
def get_round4_pairs(db: Session = Depends(get_db)):
    pairs = round_service.get_round4_pairs(db)
    res = [
        Round4PairResponse(
            id=p.id,
            pairNumber=p.pair_number,
            teamAId=p.team_a_id,
            teamAName=p.team_a.name if p.team_a else None,
            teamBId=p.team_b_id,
            teamBName=p.team_b.name if p.team_b else None,
            isConfirmed=p.is_confirmed,
            confirmedAt=p.confirmed_at,
            confirmedBy=p.confirmed_by,
            caseId=p.case_id,
            caseName=p.case_name,
            caseDetails=p.case_details,
            teamASide=p.team_a_side,
            teamBSide=p.team_b_side,
            teamAHasCaseFile=p.team_a_has_case_file,
            teamACaseFileAt=p.team_a_case_file_at,
            teamAHasOpposingFile=p.team_a_has_opposing_file,
            teamAOpposingFileAt=p.team_a_opposing_file_at,
            teamBHasCaseFile=p.team_b_has_case_file,
            teamBCaseFileAt=p.team_b_case_file_at,
            teamBHasOpposingFile=p.team_b_has_opposing_file,
            teamBOpposingFileAt=p.team_b_opposing_file_at,
            stages_json=p.stages_json or {},
            resourcePersonName=p.resource_person_name,
            resourcePersonNotes=p.resource_person_notes,
            resource_person_questions_json=p.resource_person_questions_json or [],
            isQuestioningComplete=p.is_questioning_complete,
            updatedAt=p.updated_at,
        )
        for p in pairs
    ]
    return ApiResponse(data=res)


@router.put("/4/pairs/{pair_number}", response_model=ApiResponse[Round4PairResponse])
def update_round4_pair(
    pair_number: int,
    req: Round4PairUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    p = round_service.update_round4_pair(db, pair_number, req, current_user)
    item = Round4PairResponse(
        id=p.id,
        pairNumber=p.pair_number,
        teamAId=p.team_a_id,
        teamAName=p.team_a.name if p.team_a else None,
        teamBId=p.team_b_id,
        teamBName=p.team_b.name if p.team_b else None,
        isConfirmed=p.is_confirmed,
        confirmedAt=p.confirmed_at,
        confirmedBy=p.confirmed_by,
        caseId=p.case_id,
        caseName=p.case_name,
        caseDetails=p.case_details,
        teamASide=p.team_a_side,
        teamBSide=p.team_b_side,
        teamAHasCaseFile=p.team_a_has_case_file,
        teamACaseFileAt=p.team_a_case_file_at,
        teamAHasOpposingFile=p.team_a_has_opposing_file,
        teamAOpposingFileAt=p.team_a_opposing_file_at,
        teamBHasCaseFile=p.team_b_has_case_file,
        teamBCaseFileAt=p.team_b_case_file_at,
        teamBHasOpposingFile=p.team_b_has_opposing_file,
        teamBOpposingFileAt=p.team_b_opposing_file_at,
        stages_json=p.stages_json or {},
        resourcePersonName=p.resource_person_name,
        resourcePersonNotes=p.resource_person_notes,
        resource_person_questions_json=p.resource_person_questions_json or [],
        isQuestioningComplete=p.is_questioning_complete,
        updatedAt=p.updated_at,
    )
    return ApiResponse(data=item, message=f"Pair {pair_number} updated successfully")


@router.post("/4/pairs/auto", response_model=ApiResponse[List[Round4PairResponse]])
def auto_generate_round4_pairs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER])),
):
    pairs = round_service.auto_pair_round4_teams(db, current_user)
    res = [
        Round4PairResponse(
            id=p.id,
            pairNumber=p.pair_number,
            teamAId=p.team_a_id,
            teamAName=p.team_a.name if p.team_a else None,
            teamBId=p.team_b_id,
            teamBName=p.team_b.name if p.team_b else None,
            isConfirmed=p.is_confirmed,
            confirmedAt=p.confirmed_at,
            confirmedBy=p.confirmed_by,
            caseId=p.case_id,
            caseName=p.case_name,
            caseDetails=p.case_details,
            teamASide=p.team_a_side,
            teamBSide=p.team_b_side,
            teamAHasCaseFile=p.team_a_has_case_file,
            teamACaseFileAt=p.team_a_case_file_at,
            teamAHasOpposingFile=p.team_a_has_opposing_file,
            teamAOpposingFileAt=p.team_a_opposing_file_at,
            teamBHasCaseFile=p.team_b_has_case_file,
            teamBCaseFileAt=p.team_b_case_file_at,
            teamBHasOpposingFile=p.team_b_has_opposing_file,
            teamBOpposingFileAt=p.team_b_opposing_file_at,
            stages_json=p.stages_json or {},
            resourcePersonName=p.resource_person_name,
            resourcePersonNotes=p.resource_person_notes,
            resource_person_questions_json=p.resource_person_questions_json or [],
            isQuestioningComplete=p.is_questioning_complete,
            updatedAt=p.updated_at,
        )
        for p in pairs
    ]
    return ApiResponse(data=res, message="4 matchups generated and confirmed for Round 4")


@router.post("/4/scores", response_model=ApiResponse[Round4JudgeScoreResponse])
def submit_round4_judge_score(
    req: Round4JudgeScoreSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL, UserRole.JUDGE])),
):
    sc = round_service.submit_round4_judge_score(db, req, current_user)
    item = Round4JudgeScoreResponse(
        id=sc.id,
        judgeId=sc.judge_id,
        judgeName=sc.judge_name,
        teamId=sc.team_id,
        scores_json=sc.scores_json or {},
        totalScore=sc.total_score,
        comments=sc.comments,
        submittedAt=sc.submitted_at,
        isSubmitted=sc.is_submitted,
    )
    return ApiResponse(data=item, message="Judge scorecard submitted successfully")


@router.post("/4/agent-guess", response_model=ApiResponse[Round4AgentGuessResponse])
def submit_round4_agent_guess(
    req: Round4AgentGuessSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL, UserRole.JUDGE])),
):
    g = round_service.submit_round4_agent_guess(db, req, current_user)
    item = Round4AgentGuessResponse(
        id=g.id,
        teamId=g.team_id,
        outcome=g.outcome,
        pointsAwarded=g.points_awarded,
        isVerified=g.is_verified,
        verifiedBy=g.verified_by,
        verifiedAt=g.verified_at,
        notes=g.notes,
    )
    return ApiResponse(data=item, message="Agent guess recorded successfully")


@router.get("/4/standings", response_model=ApiResponse[List[Round4TeamSummary]])
def get_round4_standings(db: Session = Depends(get_db)):
    standings = round_service.get_round4_standings(db)
    return ApiResponse(data=standings)


# =========================================================================
# Grand Finale (Round 5) Endpoints
# =========================================================================

@router.get("/5/scorecards", response_model=ApiResponse[List[FinaleScorecardResponse]])
def get_finale_scorecards(db: Session = Depends(get_db)):
    cards = round_service.get_finale_scorecards(db)
    res = [
        FinaleScorecardResponse(
            id=c.id,
            teamId=c.team_id,
            judgeName=c.judge_name,
            scores_json=c.scores_json or {},
            totalScore=c.total_score,
            isComplete=c.is_complete,
            submittedAt=c.submitted_at,
            comments=c.comments,
            lastEditedBy=c.last_edited_by,
            lastEditedAt=c.last_edited_at,
        )
        for c in cards
    ]
    return ApiResponse(data=res)


@router.post("/5/scorecards", response_model=ApiResponse[FinaleScorecardResponse])
def submit_finale_scorecard(
    req: FinaleScorecardSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL, UserRole.JUDGE])),
):
    c = round_service.submit_finale_scorecard(db, req, current_user)
    item = FinaleScorecardResponse(
        id=c.id,
        teamId=c.team_id,
        judgeName=c.judge_name,
        scores_json=c.scores_json or {},
        totalScore=c.total_score,
        isComplete=c.is_complete,
        submittedAt=c.submitted_at,
        comments=c.comments,
        lastEditedBy=c.last_edited_by,
        lastEditedAt=c.last_edited_at,
    )
    return ApiResponse(data=item, message="Finale scorecard recorded successfully")


@router.post("/5/agent-verdict", response_model=ApiResponse[FinaleAgentVerdictResponse])
def submit_finale_agent_verdict(
    req: FinaleAgentVerdictSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL, UserRole.JUDGE])),
):
    v = round_service.submit_finale_agent_verdict(db, req, current_user)
    item = FinaleAgentVerdictResponse(
        id=v.id,
        teamId=v.team_id,
        suspectedAgent=v.suspected_agent,
        actualAgent=v.actual_agent,
        isCorrect=v.is_correct,
        bonusPoints=v.bonus_points,
        penaltyPoints=v.penalty_points,
        isVerified=v.is_verified,
        verifiedBy=v.verified_by,
        verifiedAt=v.verified_at,
        notes=v.notes,
    )
    return ApiResponse(data=item, message="Finale secret agent verdict submitted successfully")


@router.get("/5/standings", response_model=ApiResponse[List[FinaleTeamSummary]])
def get_finale_standings(db: Session = Depends(get_db)):
    standings = round_service.get_finale_standings(db)
    return ApiResponse(data=standings)
