"""
Round 2 — Cabo Tournament Table Generation and Scoring Engine for EVENT HQ.
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Implements:
1. Qualified-team validation (exactly 24 teams, 5 players per team = 120 participants)
2. 24-table generation across 3 Cabo games with 5 players per table
3. Strict squad isolation: teammates never share a table in any game
4. Seeded deterministic scheduling and opponent-repetition minimization
5. Player scorecards and placement point conversion (1st=5, 2nd=3, 3rd=2, 4th=1, 5th=0)
6. Team Cabo score aggregation (max 75.0 points across 15 player-games)
7. Official multi-stage tie-breaking:
   - Primary: Higher team Cabo score
   - Secondary: Lower combined final-card total
   - Tertiary: More first-place finishes
   - Quaternary: Flag unresolved tie for organizer review (no random break)
8. R2 wallet reward integration (score * 10, max 750 pts)
9. Controlled finalization flow with completeness guards
"""

import uuid
import random
import itertools
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.cabo import CaboTableAssignment, CaboPlayerScorecard
from app.models.team import Team
from app.models.participant import Participant
from app.models.round_models import RoundState
from app.models.round2 import CaboConfigModel
from app.core.constants import (
    R1_QUALIFIERS,
    R2_QUALIFIERS,
    TEAM_SIZE,
    CABO_GAMES,
    CABO_TABLE_SIZE,
    CABO_PLACEMENT_POINTS,
    CABO_MAX_TEAM_SCORE,
)
from app.services.wallet import award_round2_reward
from app.schemas.tournament_extensions import (
    CaboTablePlayerInfo,
    CaboTableDetailResponse,
    CaboTeamStandingResponse,
    CaboFinalizationResponse,
    CaboPlayerScorecardCreate,
)
from app.db.base import utc_now


# ==============================================================================
# DOMAIN EXCEPTIONS
# ==============================================================================
class CaboError(Exception):
    """Base exception for Round 2 Cabo domain operations."""
    pass


class CaboValidationError(CaboError):
    """Raised when team or participant qualifications fail Cabo prerequisites."""
    pass


class CaboAssignmentError(CaboError):
    """Raised when table generation or seating assignment operations encounter an error."""
    pass


class CaboScorecardError(CaboError):
    """Raised when a scorecard entry or placement validation fails."""
    pass


class CaboFinalizationError(CaboError):
    """Raised when round finalization guards are violated."""
    pass


# ==============================================================================
# 1. QUALIFIED TEAM & PARTICIPANT VALIDATION
# ==============================================================================
def validate_qualified_teams(teams: List[Team]) -> None:
    """
    Validates that exactly 24 qualified teams are provided, each possessing exactly 5
    registered participants, with no duplicate or missing participants across squads.
    """
    if len(teams) != R1_QUALIFIERS:
        raise CaboValidationError(
            f"Round 2 Cabo tournament requires exactly {R1_QUALIFIERS} qualified teams, got {len(teams)}."
        )

    team_ids = [t.id for t in teams]
    if len(set(team_ids)) != R1_QUALIFIERS:
        raise CaboValidationError("Duplicate team records detected among qualified teams.")

    seen_participants: Set[str] = set()
    for team in teams:
        members = team.members or []
        if len(members) != TEAM_SIZE:
            raise CaboValidationError(
                f"Team '{team.name}' ({team.id}) has {len(members)} participants; "
                f"exactly {TEAM_SIZE} required."
            )
        for p in members:
            if p.id in seen_participants:
                raise CaboValidationError(
                    f"Duplicate participant '{p.name}' ({p.id}) detected across squads."
                )
            seen_participants.add(p.id)

    total_expected = R1_QUALIFIERS * TEAM_SIZE
    if len(seen_participants) != total_expected:
        raise CaboValidationError(
            f"Expected exactly {total_expected} unique participants, found {len(seen_participants)}."
        )


# ==============================================================================
# 2. TABLE GENERATION ALGORITHM & SCHEDULING
# ==============================================================================
def generate_cabo_schedule_assignments(
    teams: List[Team],
    seed: Optional[int] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Generates deterministic, squad-isolated seating assignments for 24 tables across 3 games.
    Guarantees:
    - 24 tables per game, 5 players per table
    - Teammates never share a table in any game
    - Each participant plays exactly once per game
    - Opponent repetition across games is mathematically minimized (0 or near 0 repeats)
    """
    validate_qualified_teams(teams)

    # Sort teams deterministically by (team_number, id)
    sorted_teams = sorted(teams, key=lambda t: (t.team_number or 0, t.id))
    team_player_map: Dict[str, List[Participant]] = {
        t.id: sorted(t.members, key=lambda p: (p.role.value if hasattr(p.role, 'value') else str(p.role), p.id))
        for t in sorted_teams
    }

    rng = random.Random(seed)
    team_order = list(sorted_teams)
    if seed is not None:
        rng.shuffle(team_order)

    # Three steps coprime to 24: 5, 7, 11
    steps = [5, 7, 11]
    all_assignments: List[Dict[str, Any]] = []
    pair_counts: Dict[Tuple[str, str], int] = defaultdict(int)

    for g_idx, step in enumerate(steps):
        game_num = g_idx + 1
        # 24 tables, each containing list of (team, participant)
        tables: List[List[Tuple[Team, Participant]]] = [[] for _ in range(R1_QUALIFIERS)]

        for t_idx, team in enumerate(team_order):
            # The 5 tables for this team's 5 players: (t_idx + j * step) % 24
            assigned_table_indices = [(t_idx + j * step) % R1_QUALIFIERS for j in range(TEAM_SIZE)]
            players = list(team_player_map[team.id])

            if g_idx == 0:
                if seed is not None:
                    rng.shuffle(players)
                for tbl_idx, player in zip(assigned_table_indices, players):
                    tables[tbl_idx].append((team, player))
            else:
                # Permutation optimization to minimize previous opponent pairs
                best_perm = players
                best_cost = 999999
                perms = list(itertools.permutations(players))
                if seed is not None:
                    rng.shuffle(perms)

                for perm in perms:
                    cost = 0
                    for tbl_idx, p in zip(assigned_table_indices, perm):
                        for _, existing_p in tables[tbl_idx]:
                            pair = tuple(sorted([p.id, existing_p.id]))
                            cost += pair_counts[pair]
                    if cost < best_cost:
                        best_cost = cost
                        best_perm = list(perm)
                        if cost == 0:
                            break

                for tbl_idx, player in zip(assigned_table_indices, best_perm):
                    tables[tbl_idx].append((team, player))

        # Record assignments and update opponent pair tracking
        for tbl_idx, table_players in enumerate(tables):
            table_num = tbl_idx + 1
            for seat_idx, (team, player) in enumerate(table_players):
                seat_pos = seat_idx + 1
                all_assignments.append({
                    "game_number": game_num,
                    "table_number": table_num,
                    "seat_position": seat_pos,
                    "team_id": team.id,
                    "participant_id": player.id,
                })

            for i1 in range(len(table_players)):
                for i2 in range(i1 + 1, len(table_players)):
                    pair = tuple(sorted([table_players[i1][1].id, table_players[i2][1].id]))
                    pair_counts[pair] += 1

    # Diagnostics
    repeated_pairs = [pair for pair, cnt in pair_counts.items() if cnt > 1]
    diagnostics = {
        "total_games": CABO_GAMES,
        "tables_per_game": R1_QUALIFIERS,
        "players_per_table": CABO_TABLE_SIZE,
        "total_assignments": len(all_assignments),
        "repeated_opponent_pairs": repeated_pairs,
        "count_of_repeated_pairs": len(repeated_pairs),
        "table_distribution": {
            f"game_{g}": {t: CABO_TABLE_SIZE for t in range(1, R1_QUALIFIERS + 1)}
            for g in range(1, CABO_GAMES + 1)
        }
    }

    return all_assignments, diagnostics


def generate_cabo_tables(
    db: Session,
    seed: Optional[int] = None,
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """
    Generates and persists Cabo table assignments for all 3 games in the database.
    Rejects regeneration if the round is finalized or if scores exist without force_regenerate.
    """
    # Check if Round 2 is finalized
    r2_state = db.query(RoundState).filter(RoundState.id == 2).first()
    if r2_state and r2_state.is_finalized:
        raise CaboFinalizationError("Round 2 is already finalized; table regeneration is forbidden.")

    # Check for existing scorecards
    existing_scorecards = db.query(CaboPlayerScorecard).count()
    if existing_scorecards > 0 and not force_regenerate:
        raise CaboAssignmentError(
            f"Cannot regenerate tables: {existing_scorecards} player scorecards already exist. "
            "Pass force_regenerate=True if intending to reset all Round 2 data."
        )

    # Fetch qualified teams
    qualified_teams = db.query(Team).order_by(Team.team_number.asc()).limit(R1_QUALIFIERS).all()
    if len(qualified_teams) != R1_QUALIFIERS:
        # If fewer than 24 exist, query all teams
        qualified_teams = db.query(Team).all()

    validate_qualified_teams(qualified_teams)

    # Clear existing assignments and scorecards if force_regenerate
    if force_regenerate or existing_scorecards == 0:
        db.query(CaboPlayerScorecard).delete()
        db.query(CaboTableAssignment).delete()
        db.flush()

    assignments, diagnostics = generate_cabo_schedule_assignments(qualified_teams, seed=seed)

    # Persist assignments
    db_assignments = [
        CaboTableAssignment(
            id=f"cba-g{a['game_number']}-t{a['table_number']}-s{a['seat_position']}-{uuid.uuid4().hex[:4]}",
            game_number=a["game_number"],
            table_number=a["table_number"],
            seat_position=a["seat_position"],
            team_id=a["team_id"],
            participant_id=a["participant_id"],
        )
        for a in assignments
    ]
    db.add_all(db_assignments)
    db.commit()

    return {
        "status": "success",
        "assignments_created": len(db_assignments),
        "diagnostics": diagnostics,
    }


# ==============================================================================
# 3. SCORECARD RECORDING & PLACEMENT POINTS
# ==============================================================================
def record_table_scorecards(
    db: Session,
    game_number: int,
    table_number: int,
    scorecards_input: List[Dict[str, Any]],
    recorded_by: Optional[str] = None
) -> List[CaboPlayerScorecard]:
    """
    Records scorecards for all 5 players at a specific table in a Cabo game.
    Validations:
    - Exactly 5 scorecards matching the assigned participants
    - Placements must be unique and strictly cover {1, 2, 3, 4, 5}
    - Awards official placement points: 1st=5, 2nd=3, 3rd=2, 4th=1, 5th=0
    """
    if game_number not in [1, 2, 3]:
        raise CaboScorecardError(f"Invalid game number {game_number}; must be 1, 2, or 3.")
    if not (1 <= table_number <= R1_QUALIFIERS):
        raise CaboScorecardError(f"Invalid table number {table_number}; must be between 1 and 24.")

    # Fetch assigned players at this table
    assignments = (
        db.query(CaboTableAssignment)
        .filter(
            CaboTableAssignment.game_number == game_number,
            CaboTableAssignment.table_number == table_number
        )
        .all()
    )
    if len(assignments) != CABO_TABLE_SIZE:
        raise CaboAssignmentError(
            f"Table {table_number} in Game {game_number} has {len(assignments)} assigned players; "
            f"expected {CABO_TABLE_SIZE}."
        )

    assigned_part_ids = {a.participant_id: a for a in assignments}

    if len(scorecards_input) != CABO_TABLE_SIZE:
        raise CaboScorecardError(
            f"Table score submission requires exactly {CABO_TABLE_SIZE} scorecards, got {len(scorecards_input)}."
        )

    input_part_ids = set()
    placements = []

    for sc in scorecards_input:
        pid = sc.get("participant_id")
        placement = sc.get("placement")

        if not pid or pid not in assigned_part_ids:
            raise CaboScorecardError(
                f"Participant '{pid}' is not assigned to Table {table_number} in Game {game_number}."
            )
        if pid in input_part_ids:
            raise CaboScorecardError(f"Duplicate scorecard submitted for participant '{pid}'.")
        input_part_ids.add(pid)

        if placement is None or placement < 1 or placement > 5:
            raise CaboScorecardError(
                f"Invalid placement {placement} for participant '{pid}'. Placements must be 1 to 5."
            )
        placements.append(placement)

    # Enforce strictly unique placements forming {1, 2, 3, 4, 5}
    if set(placements) != {1, 2, 3, 4, 5}:
        raise CaboScorecardError(
            f"Table {table_number} placements must be unique integers 1 through 5, got {sorted(placements)}."
        )

    # Persist or update scorecards
    saved_scorecards = []
    for sc in scorecards_input:
        pid = sc["participant_id"]
        placement = sc["placement"]
        pts = float(CABO_PLACEMENT_POINTS[placement])
        hand_total = sc.get("final_card_hand_total")
        notes = sc.get("notes")
        assignment = assigned_part_ids[pid]

        # Check existing
        existing = (
            db.query(CaboPlayerScorecard)
            .filter(
                CaboPlayerScorecard.game_number == game_number,
                CaboPlayerScorecard.participant_id == pid
            )
            .first()
        )
        if existing:
            existing.placement = placement
            existing.placement_points = pts
            existing.final_card_hand_total = hand_total
            existing.notes = notes
            existing.table_assignment_id = assignment.id
            saved_scorecards.append(existing)
        else:
            new_sc = CaboPlayerScorecard(
                id=f"cbsc-g{game_number}-t{table_number}-{uuid.uuid4().hex[:6]}",
                game_number=game_number,
                participant_id=pid,
                team_id=assignment.team_id,
                table_assignment_id=assignment.id,
                placement=placement,
                placement_points=pts,
                final_card_hand_total=hand_total,
                notes=notes,
            )
            db.add(new_sc)
            saved_scorecards.append(new_sc)

    db.commit()
    for sc in saved_scorecards:
        db.refresh(sc)

    return saved_scorecards


# ==============================================================================
# 4. TEAM CABO SCORE AGGREGATION & OFFICIAL TIE-BREAKERS
# ==============================================================================
def calculate_round2_standings(db: Session) -> List[CaboTeamStandingResponse]:
    """
    Computes official Round 2 Cabo standings across all 24 qualified teams.
    Aggregation:
    - 5 players * 3 games = 15 player-games per squad
    - Team score: sum of placement points (0.0 to 75.0)
    Official Tie-Break Order:
    1. Primary: Higher team Cabo score (descending)
    2. Tie-break 1: Lower combined final-card total across 15 games (ascending)
    3. Tie-break 2: More first-place finishes across 15 games (descending)
    4. Unresolved tie: Flags is_tied_unresolved for organizer review
    Returns top 12 squads qualified for Round 3.
    """
    # Fetch all assignments and scorecards
    teams = db.query(Team).all()
    # If more than 24 exist in DB, take only teams that have Cabo assignments
    team_ids_with_cabo = {
        row[0] for row in db.query(CaboTableAssignment.team_id).distinct().all()
    }
    if team_ids_with_cabo:
        cabo_teams = [t for t in teams if t.id in team_ids_with_cabo]
    else:
        cabo_teams = teams[:R1_QUALIFIERS]

    all_scorecards = db.query(CaboPlayerScorecard).all()
    team_scorecard_map = defaultdict(list)
    for sc in all_scorecards:
        team_scorecard_map[sc.team_id].append(sc)

    team_metrics = []
    for team in cabo_teams:
        scs = team_scorecard_map.get(team.id, [])
        cabo_score = sum(sc.placement_points for sc in scs)
        combined_card_total = sum(sc.final_card_hand_total or 0 for sc in scs)
        first_place_count = sum(1 for sc in scs if sc.placement == 1)

        team_metrics.append({
            "team": team,
            "cabo_score": float(cabo_score),
            "combined_card_total": int(combined_card_total),
            "first_place_count": int(first_place_count),
        })

    # Sort by:
    # 1. cabo_score (descending)
    # 2. combined_card_total (ascending)
    # 3. first_place_count (descending)
    def sort_key(item):
        return (
            -item["cabo_score"],
            item["combined_card_total"],
            -item["first_place_count"],
        )

    team_metrics.sort(key=sort_key)

    standings: List[CaboTeamStandingResponse] = []
    for idx, item in enumerate(team_metrics):
        team = item["team"]
        rank = idx + 1
        is_qualified = rank <= R2_QUALIFIERS

        # Check for unresolved ties with adjacent squads
        is_tied = False
        tie_reason = None
        if idx > 0:
            prev = team_metrics[idx - 1]
            if (
                prev["cabo_score"] == item["cabo_score"]
                and prev["combined_card_total"] == item["combined_card_total"]
                and prev["first_place_count"] == item["first_place_count"]
            ):
                is_tied = True
                tie_reason = f"Unresolved tie with {prev['team'].name} (all metrics identical)"

        if idx < len(team_metrics) - 1:
            nxt = team_metrics[idx + 1]
            if (
                nxt["cabo_score"] == item["cabo_score"]
                and nxt["combined_card_total"] == item["combined_card_total"]
                and nxt["first_place_count"] == item["first_place_count"]
            ):
                is_tied = True
                tie_reason = f"Unresolved tie with {nxt['team'].name} (all metrics identical)"

        standings.append(
            CaboTeamStandingResponse(
                team_id=team.id,
                team_name=team.name,
                team_number=team.team_number or (idx + 1),
                cabo_score=item["cabo_score"],
                combined_card_total=item["combined_card_total"],
                first_place_count=item["first_place_count"],
                rank=rank,
                is_qualified=is_qualified,
                is_tied_unresolved=is_tied,
                tie_reason=tie_reason,
            )
        )

    return standings


# ==============================================================================
# 5. ROUND FINALIZATION & R2 WALLET REWARD
# ==============================================================================
def finalize_round2(db: Session, actor: str) -> CaboFinalizationResponse:
    """
    Finalizes Round 2 Cabo Tournament:
    1. Verifies that all 3 games and all 24 tables have complete scorecards (360 total)
    2. Calculates official standings and identifies the top 12 qualified teams
    3. Awards R2 tournament wallet points via Step 9 wallet service (score * 10)
    4. Marks RoundState and CaboConfigModel as finalized
    """
    r2_state = db.query(RoundState).filter(RoundState.id == 2).first()
    if not r2_state:
        r2_state = RoundState(
            id=2,
            name="Round 2 — Cabo Tournament",
            codename="cabo",
            initial_teams_count=24,
            qualifying_teams_count=12,
            status="Scheduled",
            is_finalized=False,
        )
        db.add(r2_state)
        db.flush()

    cfg = db.query(CaboConfigModel).filter(CaboConfigModel.id == 1).first()
    if not cfg:
        cfg = CaboConfigModel(id=1, is_finalized=False)
        db.add(cfg)
        db.flush()

    if r2_state.is_finalized or cfg.is_finalized:
        raise CaboFinalizationError("Round 2 is already finalized.")

    # Verify score completeness: 24 tables * 5 players * 3 games = 360 scorecards
    total_assignments = db.query(CaboTableAssignment).count()
    if total_assignments != (R1_QUALIFIERS * CABO_TABLE_SIZE * CABO_GAMES):
        raise CaboFinalizationError(
            f"Cannot finalize: Expected {R1_QUALIFIERS * CABO_TABLE_SIZE * CABO_GAMES} "
            f"table assignments, found {total_assignments}."
        )

    total_scorecards = db.query(CaboPlayerScorecard).count()
    if total_scorecards != total_assignments:
        raise CaboFinalizationError(
            f"Cannot finalize Round 2: Incomplete table scores. "
            f"Expected {total_assignments} player scorecards, found {total_scorecards}."
        )

    standings = calculate_round2_standings(db)
    top_12_team_ids = [s.team_id for s in standings if s.is_qualified]

    # Award R2 wallet points to each squad
    for s in standings:
        award_round2_reward(
            db=db,
            team_id=s.team_id,
            cabo_score=s.cabo_score,
            multiplier=10.0,
            created_by=actor,
        )

    now = utc_now()
    r2_state.is_finalized = True
    r2_state.finalized_at = now
    r2_state.finalized_by = actor
    r2_state.status = "Completed"

    cfg.is_finalized = True
    cfg.finalized_at = now
    cfg.finalized_by = actor

    db.commit()

    return CaboFinalizationResponse(
        is_finalized=True,
        finalized_at=now.isoformat(),
        finalized_by=actor,
        qualified_teams_count=len(top_12_team_ids),
        qualified_team_ids=top_12_team_ids,
        standings=standings,
    )


# ==============================================================================
# 6. GAME OVERVIEW & TABLE DETAIL QUERIES
# ==============================================================================
def get_game_tables(db: Session, game_number: int) -> List[CaboTableDetailResponse]:
    """Retrieves all 24 tables for a given Cabo game with seating and scorecard status."""
    if game_number not in [1, 2, 3]:
        raise CaboValidationError(f"Invalid game number {game_number}; must be 1, 2, or 3.")

    assignments = (
        db.query(CaboTableAssignment)
        .filter(CaboTableAssignment.game_number == game_number)
        .order_by(CaboTableAssignment.table_number.asc(), CaboTableAssignment.seat_position.asc())
        .all()
    )

    scorecards = (
        db.query(CaboPlayerScorecard)
        .filter(CaboPlayerScorecard.game_number == game_number)
        .all()
    )
    scorecard_map = {sc.participant_id: sc for sc in scorecards}

    tables_map: Dict[int, List[CaboTablePlayerInfo]] = defaultdict(list)
    for a in assignments:
        sc = scorecard_map.get(a.participant_id)
        player_info = CaboTablePlayerInfo(
            seat_position=a.seat_position,
            participant_id=a.participant_id,
            participant_name=a.participant.name if a.participant else "Unknown",
            team_id=a.team_id,
            team_name=a.team.name if a.team else "Unknown",
            placement=sc.placement if sc else None,
            placement_points=sc.placement_points if sc else None,
            final_card_hand_total=sc.final_card_hand_total if sc else None,
        )
        tables_map[a.table_number].append(player_info)

    response = []
    for tbl_num in range(1, R1_QUALIFIERS + 1):
        players = tables_map.get(tbl_num, [])
        is_completed = len(players) == CABO_TABLE_SIZE and all(p.placement is not None for p in players)
        response.append(
            CaboTableDetailResponse(
                game_number=game_number,
                table_number=tbl_num,
                is_completed=is_completed,
                players=players,
            )
        )

    return response
