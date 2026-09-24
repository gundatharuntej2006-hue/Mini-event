from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.common import ApiResponse, FinalizationResponse
from app.schemas.rounds.round2 import (
    Round2OverviewResponse, CaboConfigSchema, UpdateCaboConfigInput,
    CaboGameResponse, RecordGamePlacementsInput, TeamRound2RecordResponse
)
from app.schemas.tournament_extensions import (
    CaboGenerateTablesRequest,
    CaboTableDetailResponse,
    CaboRecordTableScoresRequest,
    CaboTeamStandingResponse,
    CaboFinalizationResponse,
    CaboPlayerScorecardResponse,
)
from app.services import round2_service, cabo_service
from app.services.cabo_service import (
    CaboError,
    CaboValidationError,
    CaboAssignmentError,
    CaboScorecardError,
    CaboFinalizationError,
)

router = APIRouter(prefix="/rounds/2", tags=["Round 2 — Cabo"])

@router.get("", response_model=ApiResponse[Round2OverviewResponse])
def get_round2(db: Session = Depends(get_db)):
    """Get complete Round 2 Cabo overview, 3-game placements, and live standings."""
    data = round2_service.get_round2_overview(db)
    return ApiResponse(data=data, message="Round 2 Cabo overview loaded")

@router.get("/config", response_model=ApiResponse[CaboConfigSchema])
def get_config(db: Session = Depends(get_db)):
    """Get Round 2 Cabo configuration."""
    cfg = round2_service.get_or_create_cabo_config(db)
    res = CaboConfigSchema(
        scoring_direction=cfg.scoring_direction,
        tie_policy=cfg.tie_policy,
        point_table=cfg.point_table or {},
        is_finalized=cfg.is_finalized,
        finalized_at=cfg.finalized_at.isoformat() if cfg.finalized_at else None,
        finalized_by=cfg.finalized_by
    )
    return ApiResponse(data=res)

@router.put("/config", response_model=ApiResponse[CaboConfigSchema])
def update_config(
    payload: UpdateCaboConfigInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Update Cabo scoring direction or placement points table (Organizers only)."""
    cfg = round2_service.update_cabo_config(
        db=db,
        scoring_direction=payload.scoring_direction,
        point_table=payload.point_table,
        actor=actor
    )
    res = CaboConfigSchema(
        scoring_direction=cfg.scoring_direction,
        tie_policy=cfg.tie_policy,
        point_table=cfg.point_table or {},
        is_finalized=cfg.is_finalized,
        finalized_at=cfg.finalized_at.isoformat() if cfg.finalized_at else None,
        finalized_by=cfg.finalized_by
    )
    return ApiResponse(data=res, message="Round 2 Cabo configuration updated")

@router.get("/teams", response_model=ApiResponse[List[TeamRound2RecordResponse]])
def get_teams(db: Session = Depends(get_db)):
    """Get all 24 qualified squads for Round 2."""
    overview = round2_service.get_round2_overview(db)
    return ApiResponse(data=overview["records"])

@router.get("/games", response_model=ApiResponse[List[CaboGameResponse]])
def get_games(db: Session = Depends(get_db)):
    """Get all 3 Cabo games with team placements and status."""
    overview = round2_service.get_round2_overview(db)
    return ApiResponse(data=overview["games"])

@router.post("/games", response_model=ApiResponse[Dict[str, Any]])
def submit_game_placements(
    game_number: int,
    payload: RecordGamePlacementsInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "marshal", "scorekeeper", "admin"]))
):
    """Submit placement results for a Cabo game (1, 2, or 3)."""
    if game_number not in [1, 2, 3]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game number must be 1, 2, or 3.")
    round2_service.record_game_placements(db, game_number, payload, actor)
    return ApiResponse(data={"game_number": game_number, "placements_recorded": len(payload.placements)}, message="Placements recorded")

@router.put("/games/{game_id}", response_model=ApiResponse[Dict[str, Any]])
def update_game_placements(
    game_id: str,
    payload: RecordGamePlacementsInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "marshal", "scorekeeper", "admin"]))
):
    """Update placement results for a specific Cabo game (r2-game-1, r2-game-2, r2-game-3)."""
    try:
        gnum = int(game_id.split("-")[-1])
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid game_id format. Expected 'r2-game-1', etc.")
    round2_service.record_game_placements(db, gnum, payload, actor)
    return ApiResponse(data={"game_id": game_id, "placements_recorded": len(payload.placements)}, message="Placements updated")

@router.get("/leaderboard", response_model=ApiResponse[List[TeamRound2RecordResponse]])
def get_leaderboard(db: Session = Depends(get_db)):
    """Get official server-side ranked leaderboard for Round 2."""
    overview = round2_service.get_round2_overview(db)
    return ApiResponse(data=overview["records"])

@router.get("/qualification", response_model=ApiResponse[Dict[str, Any]])
def get_qualification(db: Session = Depends(get_db)):
    """Check Round 2 qualification readiness, top 12 cutoff, and tie flags."""
    overview = round2_service.get_round2_overview(db)
    return ApiResponse(data={
        "can_finalize": overview["can_finalize"],
        "issues": overview["issues"],
        "ties_affecting_cutoff": overview["ties_affecting_cutoff"],
        "complete_count": overview["complete_count"],
        "incomplete_count": overview["incomplete_count"]
    })

@router.post("/finalize", response_model=ApiResponse[FinalizationResponse])
def finalize_round2(
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Officially seal Round 2 Cabo results and advance 12 squads to Round 3."""
    res = round2_service.finalize_round2(db, actor, payload)
    return ApiResponse(data=res, message=res.get("message"))


# ==============================================================================
# OFFICIAL CABO TOURNAMENT ENGINE ENDPOINTS (STEP 10)
# ==============================================================================
@router.post("/cabo/generate", response_model=ApiResponse[Dict[str, Any]])
def generate_cabo_tournament_tables(
    payload: Optional[CaboGenerateTablesRequest] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "marshal", "admin"])),
):
    """
    Generates deterministic, squad-isolated seating assignments for 24 tables across 3 games.
    Ensures 0 teammates at the same table and minimizes opponent repeat pairings.
    """
    seed = payload.seed if payload else None
    force = payload.force_regenerate if payload else False
    try:
        result = cabo_service.generate_cabo_tables(db, seed=seed, force_regenerate=force)
        return ApiResponse(data=result, message="Round 2 Cabo tables successfully generated")
    except CaboValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except (CaboAssignmentError, CaboFinalizationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/cabo/games/{game_number}", response_model=ApiResponse[List[CaboTableDetailResponse]])
def get_cabo_game_tables(
    game_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves all 24 tables for a specific Cabo game with seating and scorecard status."""
    try:
        tables = cabo_service.get_game_tables(db, game_number=game_number)
        return ApiResponse(data=tables, message=f"Retrieved 24 tables for Cabo Game {game_number}")
    except CaboValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/cabo/games/{game_number}/scores", response_model=ApiResponse[List[CaboPlayerScorecardResponse]])
def record_cabo_table_scores(
    game_number: int,
    payload: CaboRecordTableScoresRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "marshal", "admin"])),
):
    """
    Records scorecards for a table of 5 players in a Cabo game.
    Enforces unique placements 1st through 5th and awards placement points.
    """
    try:
        scorecards_data = [s.model_dump() for s in payload.scores]
        saved = cabo_service.record_table_scorecards(
            db=db,
            game_number=game_number,
            table_number=payload.table_number,
            scorecards_input=scorecards_data,
            recorded_by=actor.email,
        )
        return ApiResponse(
            data=[CaboPlayerScorecardResponse.model_validate(sc) for sc in saved],
            message=f"Recorded scores for Table {payload.table_number} in Game {game_number}"
        )
    except (CaboScorecardError, CaboAssignmentError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/cabo/standings", response_model=ApiResponse[List[CaboTeamStandingResponse]])
def get_cabo_standings(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Retrieves official Round 2 Cabo standings across all 24 teams.
    Applies multi-stage tie-breaking and identifies top 12 squads qualified for Round 3.
    """
    standings = cabo_service.calculate_round2_standings(db)
    return ApiResponse(
        data=standings,
        message=f"Retrieved Cabo standings for {len(standings)} teams"
    )


@router.post("/cabo/finalize", response_model=ApiResponse[CaboFinalizationResponse])
def finalize_cabo_round(
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"])),
):
    """
    Officially finalizes Round 2 Cabo Tournament:
    - Verifies complete scoring for all 72 tables (360 scorecards)
    - Computes final rankings and top 12 qualifiers
    - Awards R2 tournament wallet points (score * 10, max 750 pts)
    - Locks Round 2 results
    """
    try:
        final_res = cabo_service.finalize_round2(db, actor=actor.email)
        return ApiResponse(
            data=final_res,
            message="Round 2 Cabo tournament finalized and wallet rewards awarded"
        )
    except CaboFinalizationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
