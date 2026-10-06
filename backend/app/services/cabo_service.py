"""
Round 2 — Cabo: The Memory Heist Engine for EVENT HQ.
Source of Truth: ODDyssey Organiser.html (Authoritative Event Specification).

Official Round 2 Rules:
- 16 teams enter (from Round 1 fastest qualifiers).
- Each team has 5 players (total 80 participants).
- 16 tables.
- Teammates from the same team MUST NOT sit at the same table (strict squad isolation).
- 3 Cabo games.
- Avoid repeated opponents across games where possible.
- Each participant plays one position at a table in each game.

Scoring:
- 1st = 5 points
- 2nd = 3 points
- 3rd = 2 points
- 4th = 1 point
- 5th = 0 points
Maximum team score: 5 players * 3 games * 5 points = 75.

Qualification:
- Top 12 teams qualify for Round 3 (The Black Market).

Tie-Breakers:
1. Higher team placement score (/75)
2. Lower combined final card total
3. More first-place finishes
4. One sudden-death Cabo game with one representative from each tied team (flag for tie review)
5. Organizer draw if still tied

Secret Code Fragments:
- Fragment 3 (ECHO): Marked cards across 3 games (Game 1=E, Game 2=C, Game 3=HO)
- Fragment 4 (PRIME): Prime-number challenge cards (2=P, 3=R, 5=I, 7=M, 11=E -> PRIME)
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
from app.models.code_hunt import FinalCodeRecord, FragmentStatus
from app.models.progression import RoundQualification
from app.services.audit_service import log_audit_event
from app.core.constants import (
    R1_QUALIFIERS,
    R2_QUALIFIERS,
    TEAM_SIZE,
    CABO_GAMES,
    CABO_TABLES,
    CABO_TABLE_SIZE,
    CABO_PLACEMENT_POINTS,
    CABO_MAX_TEAM_SCORE,
    PRIME_SEQUENCE,
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
    Validates that exactly 16 qualified teams are provided (R1 qualifiers),
    each possessing exactly 5 registered participants, with no duplicate or
    missing participants across squads (total 80 participants).
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
    Generates deterministic, squad-isolated seating assignments for 16 tables across 3 games.
    Guarantees:
    - 16 tables per game, 5 players per table (80 participants total)
    - Teammates NEVER share a table in any game
    - Each participant plays exactly once per game
    - Opponent repetition across games is mathematically minimized
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

    # Steps coprime to 16 (since 16 = 2^4, any odd number is coprime to 16):
    # Steps: 1, 5, 7.
    steps = [1, 5, 7]
    all_assignments: List[Dict[str, Any]] = []
    pair_counts: Dict[Tuple[str, str], int] = defaultdict(int)

    for g_idx, step in enumerate(steps):
        game_num = g_idx + 1
        # 16 tables, each containing list of (team, participant)
        tables: List[List[Tuple[Team, Participant]]] = [[] for _ in range(R1_QUALIFIERS)]

        for t_idx, team in enumerate(team_order):
            # The 5 tables for this team's 5 players: (t_idx + j * step) % 16
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
    r2_state = db.query(RoundState).filter(RoundState.id == 2).first()
    if r2_state and r2_state.is_finalized:
        raise CaboFinalizationError("Round 2 is already finalized; table regeneration is forbidden.")

    cfg = db.query(CaboConfigModel).filter(CaboConfigModel.id == 1).first()
    if cfg and cfg.is_tables_confirmed and not force_regenerate:
        raise CaboAssignmentError(
            "Cabo tables are confirmed and frozen. Regeneration requires explicit organizer confirmation (force_regenerate=True)."
        )

    existing_scorecards = db.query(CaboPlayerScorecard).count()
    if existing_scorecards > 0 and not force_regenerate:
        raise CaboAssignmentError(
            f"Cannot regenerate tables: {existing_scorecards} player scorecards already exist. "
            "Pass force_regenerate=True if intending to reset all Round 2 data."
        )

    # Fetch qualified teams: prefer R1 finalized qualifiers if available
    r1_qualifiers = (
        db.query(Team)
        .join(RoundQualification, RoundQualification.team_id == Team.id)
        .filter(RoundQualification.round_number == 1, RoundQualification.is_advancing.is_(True))
        .order_by(RoundQualification.rank.asc())
        .all()
    )

    if len(r1_qualifiers) == R1_QUALIFIERS:
        qualified_teams = r1_qualifiers
    else:
        # Fallback to first 16 teams
        qualified_teams = db.query(Team).order_by(Team.team_number.asc()).limit(R1_QUALIFIERS).all()
        if len(qualified_teams) != R1_QUALIFIERS:
            qualified_teams = db.query(Team).all()

    validate_qualified_teams(qualified_teams)

    # Clear existing assignments and scorecards if force_regenerate
    if force_regenerate or existing_scorecards == 0:
        db.query(CaboPlayerScorecard).delete()
        db.query(CaboTableAssignment).delete()
        if cfg:
            cfg.is_tables_confirmed = False
            cfg.tables_confirmed_at = None
            cfg.tables_confirmed_by = None
        db.flush()

    assignments, diagnostics = generate_cabo_schedule_assignments(qualified_teams, seed=seed)

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


def swap_cabo_seats(
    db: Session,
    game_number: int,
    assignment_id_1: str,
    assignment_id_2: str,
    actor_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Allows organizer to swap two player seats in the same Cabo game,
    strictly validating that teammates never share a table after the swap.
    """
    a1 = db.query(CaboTableAssignment).filter(CaboTableAssignment.id == assignment_id_1).first()
    a2 = db.query(CaboTableAssignment).filter(CaboTableAssignment.id == assignment_id_2).first()

    if not a1 or not a2:
        raise CaboAssignmentError("One or both seating assignments not found.")
    if a1.game_number != game_number or a2.game_number != game_number:
        raise CaboAssignmentError(f"Both assignments must belong to Game {game_number}.")

    # Check if swap causes teammate collision at table 1
    t1_teams = [
        a.team_id for a in db.query(CaboTableAssignment)
        .filter(CaboTableAssignment.game_number == game_number, CaboTableAssignment.table_number == a1.table_number)
        .all()
        if a.id != a1.id
    ]
    if a2.team_id in t1_teams and a1.table_number != a2.table_number:
        raise CaboAssignmentError(
            f"Swap invalid: Table {a1.table_number} would contain two members of the same squad."
        )

    # Check if swap causes teammate collision at table 2
    t2_teams = [
        a.team_id for a in db.query(CaboTableAssignment)
        .filter(CaboTableAssignment.game_number == game_number, CaboTableAssignment.table_number == a2.table_number)
        .all()
        if a.id != a2.id
    ]
    if a1.team_id in t2_teams and a1.table_number != a2.table_number:
        raise CaboAssignmentError(
            f"Swap invalid: Table {a2.table_number} would contain two members of the same squad."
        )

    # Perform swap via temporary unused table (table 24) to avoid unique constraint collisions
    t1, s1 = a1.table_number, a1.seat_position
    t2, s2 = a2.table_number, a2.seat_position

    a1.table_number = 24
    a1.seat_position = 5
    db.flush()

    a2.table_number = t1
    a2.seat_position = s1
    db.flush()

    a1.table_number = t2
    a1.seat_position = s2
    db.flush()

    log_audit_event(
        db=db,
        action="CABO_SEATS_SWAPPED",
        entity_type="CaboTableAssignment",
        entity_id=f"{a1.id}:{a2.id}",
        actor_id=actor_id or "organizer",
        actor_role="organizer",
        round_number=2,
        details={
            "game_number": game_number,
            "assignment_1": a1.id,
            "assignment_2": a2.id,
            "table_1": a1.table_number,
            "table_2": a2.table_number,
        }
    )
    db.commit()
    return {"status": "success", "message": "Seats swapped successfully"}


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
        raise CaboScorecardError(f"Invalid table number {table_number}; must be between 1 and {R1_QUALIFIERS}.")

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

    saved_scorecards = []
    for sc in scorecards_input:
        pid = sc["participant_id"]
        placement = sc["placement"]
        pts = float(CABO_PLACEMENT_POINTS[placement])
        hand_total = sc.get("final_card_hand_total")
        notes = sc.get("notes")
        assignment = assigned_part_ids[pid]

        existing = (
            db.query(CaboPlayerScorecard)
            .filter(
                CaboPlayerScorecard.game_number == game_number,
                CaboPlayerScorecard.participant_id == pid
            )
            .first()
        )
        now_dt = utc_now()
        if existing:
            existing.placement = placement
            existing.placement_points = pts
            existing.final_card_hand_total = hand_total
            existing.table_assignment_id = assignment.id
            existing.is_verified = True
            existing.verified_by = recorded_by or "organizer"
            existing.verified_at = now_dt
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
                is_verified=True,
                verified_by=recorded_by or "organizer",
                verified_at=now_dt,
            )
            db.add(new_sc)
            saved_scorecards.append(new_sc)

    log_audit_event(
        db=db,
        action="CABO_TABLE_SCORES_SAVED",
        entity_type="CaboTable",
        entity_id=f"g{game_number}-t{table_number}",
        actor_id=recorded_by or "scorekeeper",
        actor_role="marshal",
        round_number=2,
        details={
            "game_number": game_number,
            "table_number": table_number,
            "placements": {sc["participant_id"]: sc["placement"] for sc in scorecards_input}
        }
    )

    db.commit()
    for sc in saved_scorecards:
        db.refresh(sc)

    return saved_scorecards


# ==============================================================================
# 4. SECRET CODE FRAGMENT VERIFICATION (ECHO & PRIME)
# ==============================================================================
def get_or_create_final_code_record(db: Session, team_id: str) -> FinalCodeRecord:
    rec = db.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team_id).first()
    if not rec:
        rec = FinalCodeRecord(
            id=f"fcr-{uuid.uuid4().hex[:8]}",
            team_id=team_id,
            fragment_1_status=FragmentStatus.PENDING,
            fragment_2_status=FragmentStatus.PENDING,
            fragment_3_status=FragmentStatus.PENDING,
            fragment_4_status=FragmentStatus.PENDING,
        )
        db.add(rec)
        db.flush()
    return rec


def verify_echo_fragment(
    db: Session,
    team_id: str,
    game_1_e: bool,
    game_2_c: bool,
    game_3_ho: bool,
    notes: Optional[str] = None,
    verified_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verifies marked cards across Cabo games:
    Game 1 = E, Game 2 = C, Game 3 = HO.
    Awards ECHO fragment (Fragment 3) only when all 3 are verified.
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise CaboValidationError(f"Team '{team_id}' not found.")

    rec = get_or_create_final_code_record(db, team_id)
    now = utc_now()

    if game_1_e and not rec.echo_e_verified:
        rec.echo_e_verified = True
        rec.echo_e_verified_at = now
    if game_2_c and not rec.echo_c_verified:
        rec.echo_c_verified = True
        rec.echo_c_verified_at = now
    if game_3_ho and not rec.echo_ho_verified:
        rec.echo_ho_verified = True
        rec.echo_ho_verified_at = now

    all_echo_verified = rec.echo_e_verified and rec.echo_c_verified and rec.echo_ho_verified
    if all_echo_verified and rec.fragment_3_status != FragmentStatus.RECOVERED:
        rec.fragment_3_status = FragmentStatus.RECOVERED
        rec.fragment_3_value = "ECHO"
        rec.fragment_3_discovered_at = now

    log_audit_event(
        db=db,
        action="ECHO_FRAGMENT_VERIFIED",
        entity_type="FinalCodeRecord",
        entity_id=rec.id,
        actor_id=verified_by or "volunteer",
        actor_role="volunteer",
        round_number=2,
        details={
            "team_id": team_id,
            "team_name": team.name,
            "echo_e": rec.echo_e_verified,
            "echo_c": rec.echo_c_verified,
            "echo_ho": rec.echo_ho_verified,
            "echo_awarded": all_echo_verified,
            "notes": notes,
        }
    )

    db.commit()
    db.refresh(rec)

    return {
        "team_id": team_id,
        "team_name": team.name,
        "echo_e_verified": rec.echo_e_verified,
        "echo_c_verified": rec.echo_c_verified,
        "echo_ho_verified": rec.echo_ho_verified,
        "fragment_3_status": rec.fragment_3_status.value,
        "fragment_3_value": rec.fragment_3_value,
        "discovered_at": rec.fragment_3_discovered_at.isoformat() if rec.fragment_3_discovered_at else None,
    }


def verify_prime_fragment(
    db: Session,
    team_id: str,
    sequence: Optional[List[int]] = None,
    is_verified: bool = True,
    notes: Optional[str] = None,
    verified_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verifies the prime-number challenge result:
    Cards placed on table: 1, 2, 3, 4, 5, 7, 9, 11
    Prime numbers sorted smallest to largest: 2=P, 3=R, 5=I, 7=M, 11=E -> PRIME.
    Awards PRIME fragment (Fragment 4) when sequence matches [2, 3, 5, 7, 11] or confirmed.
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise CaboValidationError(f"Team '{team_id}' not found.")

    if sequence is not None:
        if sequence != PRIME_SEQUENCE:
            raise CaboValidationError(
                f"Invalid prime sequence {sequence}. Required smallest to largest primes: {PRIME_SEQUENCE}."
            )

    rec = get_or_create_final_code_record(db, team_id)
    now = utc_now()

    if is_verified:
        rec.prime_sequence_verified = True
        rec.prime_sequence_verified_at = now
        rec.fragment_4_status = FragmentStatus.RECOVERED
        rec.fragment_4_value = "PRIME"
        rec.fragment_4_discovered_at = now

    log_audit_event(
        db=db,
        action="PRIME_FRAGMENT_VERIFIED",
        entity_type="FinalCodeRecord",
        entity_id=rec.id,
        actor_id=verified_by or "volunteer",
        actor_role="volunteer",
        round_number=2,
        details={
            "team_id": team_id,
            "team_name": team.name,
            "sequence": sequence,
            "prime_awarded": rec.prime_sequence_verified,
            "notes": notes,
        }
    )

    db.commit()
    db.refresh(rec)

    return {
        "team_id": team_id,
        "team_name": team.name,
        "prime_sequence_verified": rec.prime_sequence_verified,
        "fragment_4_status": rec.fragment_4_status.value,
        "fragment_4_value": rec.fragment_4_value,
        "discovered_at": rec.fragment_4_discovered_at.isoformat() if rec.fragment_4_discovered_at else None,
    }


# ==============================================================================
# 5. TEAM CABO SCORE AGGREGATION & OFFICIAL TIE-BREAKERS
# ==============================================================================
def calculate_round2_standings(db: Session) -> List[CaboTeamStandingResponse]:
    """
    Computes official Round 2 Cabo standings across all 16 qualified teams.
    Aggregation:
    - 5 players * 3 games = 15 player-games per squad
    - Team score: sum of placement points (0.0 to 75.0)
    Official Tie-Break Order:
    1. Primary: Higher team Cabo score (descending)
    2. Secondary: Lower combined final card total across 15 games (ascending)
    3. Tertiary: More first-place finishes across 15 games (descending)
    4. Unresolved tie: Flags is_tied_unresolved for sudden-death Cabo game / draw
    Returns top 12 squads qualified for Round 3.
    """
    teams = db.query(Team).all()
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

    # Fetch code fragment states
    code_records = {
        r.team_id: r for r in db.query(FinalCodeRecord).all()
    }

    team_metrics = []
    for team in cabo_teams:
        scs = team_scorecard_map.get(team.id, [])
        cabo_score = sum(sc.placement_points for sc in scs)
        combined_card_total = sum(sc.final_card_hand_total or 0 for sc in scs)
        first_place_count = sum(1 for sc in scs if sc.placement == 1)

        # Game breakdown
        g1_score = sum(sc.placement_points for sc in scs if sc.game_number == 1)
        g2_score = sum(sc.placement_points for sc in scs if sc.game_number == 2)
        g3_score = sum(sc.placement_points for sc in scs if sc.game_number == 3)

        fcr = code_records.get(team.id)
        echo_status = fcr.fragment_3_status.value if fcr else "PENDING"
        echo_e = fcr.echo_e_verified if fcr else False
        echo_c = fcr.echo_c_verified if fcr else False
        echo_ho = fcr.echo_ho_verified if fcr else False

        prime_status = fcr.fragment_4_status.value if fcr else "PENDING"
        prime_seq = fcr.prime_sequence_verified if fcr else False

        team_metrics.append({
            "team": team,
            "cabo_score": float(cabo_score),
            "game1_score": float(g1_score) if any(sc.game_number == 1 for sc in scs) else None,
            "game2_score": float(g2_score) if any(sc.game_number == 2 for sc in scs) else None,
            "game3_score": float(g3_score) if any(sc.game_number == 3 for sc in scs) else None,
            "combined_card_total": int(combined_card_total),
            "first_place_count": int(first_place_count),
            "echo_status": echo_status,
            "echo_e_verified": echo_e,
            "echo_c_verified": echo_c,
            "echo_ho_verified": echo_ho,
            "prime_status": prime_status,
            "prime_sequence_verified": prime_seq,
        })

    # Sort key:
    # 1. Higher team placement score (descending)
    # 2. Lower combined final card total (ascending)
    # 3. More first-place finishes (descending)
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
                game1_score=item["game1_score"],
                game2_score=item["game2_score"],
                game3_score=item["game3_score"],
                combined_card_total=item["combined_card_total"],
                first_place_count=item["first_place_count"],
                echo_status=item["echo_status"],
                echo_e_verified=item["echo_e_verified"],
                echo_c_verified=item["echo_c_verified"],
                echo_ho_verified=item["echo_ho_verified"],
                prime_status=item["prime_status"],
                prime_sequence_verified=item["prime_sequence_verified"],
                rank=rank,
                is_qualified=is_qualified,
                is_tied_unresolved=is_tied,
                tie_reason=tie_reason,
            )
        )

    return standings


# ==============================================================================
# 6. ROUND FINALIZATION & R2 -> R3 HANDOFF
# ==============================================================================
def finalize_round2(db: Session, actor: str) -> CaboFinalizationResponse:
    """
    Finalizes Round 2 Cabo Tournament:
    1. Verifies that all 3 games and all 16 tables have complete scorecards (240 total).
    2. Calculates official standings and identifies the top 12 qualified teams.
    3. Verifies no unresolved tie spans the 12th-place qualification cutoff boundary.
    4. Automatically records RoundQualification entries for Round 3 (the exact 12 advancing team IDs, no re-registration).
    5. Awards R2 tournament wallet points (score * 10, max 750 pts).
    6. Marks RoundState and CaboConfigModel as finalized.
    """
    r2_state = db.query(RoundState).filter(RoundState.id == 2).first()
    if not r2_state:
        r2_state = RoundState(
            id=2,
            name="Cabo - The Memory Heist",
            codename="ROUND_2_CABO_THE_MEMORY_HEIST",
            initial_teams_count=16,
            qualifying_teams_count=8,
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

    # Completeness verification: 16 tables * 5 players * 3 games = 240 scorecards
    expected_assignments = R1_QUALIFIERS * CABO_TABLE_SIZE * CABO_GAMES
    total_assignments = db.query(CaboTableAssignment).count()
    if total_assignments != expected_assignments:
        raise CaboFinalizationError(
            f"Cannot finalize: Expected {expected_assignments} "
            f"table assignments, found {total_assignments}."
        )

    total_scorecards = db.query(CaboPlayerScorecard).count()
    if total_scorecards != total_assignments:
        raise CaboFinalizationError(
            f"Cannot finalize Round 2: Incomplete table scores. "
            f"Expected {total_assignments} player scorecards, found {total_scorecards}."
        )

    standings = calculate_round2_standings(db)

    # Check for cutoff ties (tie straddling ranks R2_QUALIFIERS and R2_QUALIFIERS + 1)
    if len(standings) >= R2_QUALIFIERS + 1:
        s_cutoff = standings[R2_QUALIFIERS - 1]
        s_next = standings[R2_QUALIFIERS]
        if (
            s_cutoff.cabo_score == s_next.cabo_score
            and s_cutoff.combined_card_total == s_next.combined_card_total
            and s_cutoff.first_place_count == s_next.first_place_count
        ):
            raise CaboFinalizationError(
                f"Cannot finalize Round 2: Cutoff tie detected between {s_cutoff.team_name} (Rank {R2_QUALIFIERS}) "
                f"and {s_next.team_name} (Rank {R2_QUALIFIERS + 1}). Sudden-death Cabo game or organizer draw required."
            )

    top_qualifier_team_ids = [s.team_id for s in standings if s.is_qualified]
    if len(top_qualifier_team_ids) != R2_QUALIFIERS:
        raise CaboFinalizationError(
            f"Expected exactly {R2_QUALIFIERS} qualifiers, identified {len(top_qualifier_team_ids)}."
        )

    now = utc_now()

    # Record RoundQualification entries for progression handoff to Round 3
    # Remove any existing R2 qualifications first (idempotent)
    db.query(RoundQualification).filter(RoundQualification.round_number == 2).delete()
    for s in standings:
        rq = RoundQualification(
            id=f"rq-r2-{s.team_id}",
            round_number=2,
            team_id=s.team_id,
            rank=s.rank,
            status="QUALIFIED" if s.is_qualified else "ELIMINATED",
            score_snapshot=s.cabo_score,
            is_advancing=s.is_qualified,
            finalized_at=now,
            finalized_by=actor,
        )
        db.add(rq)

    # Award R2 wallet points to each squad
    for s in standings:
        award_round2_reward(
            db=db,
            team_id=s.team_id,
            cabo_score=s.cabo_score,
            multiplier=10.0,
            created_by=actor,
        )

    r2_state.is_finalized = True
    r2_state.finalized_at = now
    r2_state.finalized_by = actor
    r2_state.status = "Completed"

    cfg.is_finalized = True
    cfg.finalized_at = now
    cfg.finalized_by = actor

    log_audit_event(
        db=db,
        action="ROUND_FINALIZED",
        entity_type="RoundState",
        entity_id="2",
        actor_id=actor,
        actor_role="organizer",
        round_number=2,
        details={
            "qualified_teams_count": len(top_qualifier_team_ids),
            "qualified_team_ids": top_qualifier_team_ids,
        }
    )

    db.commit()

    return CaboFinalizationResponse(
        is_finalized=True,
        finalized_at=now.isoformat(),
        finalized_by=actor,
        qualified_teams_count=len(top_qualifier_team_ids),
        qualified_team_ids=top_qualifier_team_ids,
        standings=standings,
    )


# ==============================================================================
# 7. GAME OVERVIEW & TABLE DETAIL QUERIES
# ==============================================================================
def get_game_tables(db: Session, game_number: int) -> List[CaboTableDetailResponse]:
    """Retrieves all 16 tables for a given Cabo game with seating and scorecard status."""
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
            participant_usn=a.participant.usn if a.participant else None,
            team_id=a.team_id,
            team_name=a.team.name if a.team else "Unknown",
            placement=sc.placement if sc else None,
            placement_points=sc.placement_points if sc else None,
            final_card_hand_total=sc.final_card_hand_total if sc else None,
            is_verified=sc.is_verified if sc else False,
            verified_by=sc.verified_by if sc else None,
            verified_at=sc.verified_at.isoformat() if (sc and sc.verified_at) else None,
        )
        tables_map[a.table_number].append(player_info)

    response = []
    for tbl_num in range(1, R1_QUALIFIERS + 1):
        players = tables_map.get(tbl_num, [])
        is_completed = len(players) == CABO_TABLE_SIZE and all(p.placement is not None for p in players)
        is_verified = len(players) == CABO_TABLE_SIZE and all(p.is_verified for p in players)
        response.append(
            CaboTableDetailResponse(
                game_number=game_number,
                table_number=tbl_num,
                is_completed=is_completed,
                is_verified=is_verified,
                players=players,
            )
        )

    return response


def get_cabo_summary(db: Session) -> Dict[str, Any]:
    """
    Returns high-level summary of Round 2 Cabo tables and scorecards progress:
    - Tables completed per game (0 to 16)
    - Total completed tables (0 to 48)
    - Total player scorecards recorded (0 to 240)
    - can_finalize boolean and list of incomplete reasons
    """
    game_completed_counts = {}
    incomplete_reasons = []

    total_assignments = db.query(CaboTableAssignment).count()
    expected_assignments = R1_QUALIFIERS * CABO_TABLE_SIZE * CABO_GAMES  # 16 * 5 * 3 = 240

    if total_assignments < expected_assignments:
        incomplete_reasons.append(
            f"Table assignments not fully generated ({total_assignments}/{expected_assignments} seats assigned)."
        )

    for g in [1, 2, 3]:
        tables = get_game_tables(db, game_number=g)
        completed = sum(1 for t in tables if t.is_completed)
        game_completed_counts[g] = completed
        if completed < R1_QUALIFIERS:
            incomplete_reasons.append(
                f"Game {g}: {completed}/{R1_QUALIFIERS} tables completed."
            )

    total_scorecards = db.query(CaboPlayerScorecard).count()
    total_completed_tables = sum(game_completed_counts.values())

    # Check cutoff tie
    has_cutoff_tie = False
    if total_completed_tables == 48:
        standings = calculate_round2_standings(db)
        if len(standings) >= 9:
            s8 = standings[7]
            s9 = standings[8]
            if (
                s8.cabo_score == s9.cabo_score
                and s8.combined_card_total == s9.combined_card_total
                and s8.first_place_count == s9.first_place_count
            ):
                has_cutoff_tie = True
                incomplete_reasons.append(
                    f"Cutoff tie between 8th place ({s8.team_name}) and 9th place ({s9.team_name}). Sudden-death game or tie resolution required."
                )

    r2_state = db.query(RoundState).filter(RoundState.id == 2).first()
    is_finalized = bool(r2_state.is_finalized) if r2_state else False

    can_finalize = (
        not is_finalized
        and total_assignments == expected_assignments
        and total_scorecards == expected_assignments
        and total_completed_tables == 48
        and not has_cutoff_tie
    )

    return {
        "total_tables_per_game": R1_QUALIFIERS,
        "expected_total_tables": R1_QUALIFIERS * CABO_GAMES,
        "expected_total_scorecards": expected_assignments,
        "game1_completed_tables": game_completed_counts.get(1, 0),
        "game2_completed_tables": game_completed_counts.get(2, 0),
        "game3_completed_tables": game_completed_counts.get(3, 0),
        "total_completed_tables": total_completed_tables,
        "total_scorecards": total_scorecards,
        "is_finalized": is_finalized,
        "has_cutoff_tie": has_cutoff_tie,
        "can_finalize": can_finalize,
        "incomplete_reasons": incomplete_reasons,
    }


def validate_cabo_table_allocations(db: Session) -> Dict[str, Any]:
    """
    Validates Cabo seating allocation against all 8 structural constraints:
    1. Exactly 16 qualified teams
    2. Exactly 5 players per team = 80 players total
    3. Exactly 16 tables per game
    4. Exactly 5 players per table
    5. Exactly 5 distinct teams at every table (COUNT(DISTINCT team_id) == 5)
    6. Zero teammate collisions at any table across Games 1, 2, and 3
    7. Each team's 5 players occupy 5 different tables in each game
    8. Complete 3-game coverage (240 total seat assignments)
    """
    errors: List[str] = []
    constraints = {
        "exactly_16_teams": False,
        "exactly_5_players_per_team": False,
        "exactly_16_tables_per_game": False,
        "exactly_5_players_per_table": False,
        "distinct_teams_per_table": False,
        "zero_teammate_collisions": False,
        "team_members_distributed_across_tables": False,
        "complete_seat_assignments": False,
    }

    # Fetch configuration
    cfg = db.query(CaboConfigModel).filter(CaboConfigModel.id == 1).first()
    is_confirmed = bool(cfg.is_tables_confirmed) if cfg else False
    confirmed_at = cfg.tables_confirmed_at.isoformat() if (cfg and cfg.tables_confirmed_at) else None
    confirmed_by = cfg.tables_confirmed_by if cfg else None

    # Fetch assignments
    assignments = db.query(CaboTableAssignment).all()
    total_assignments = len(assignments)

    # 8. Complete assignments check
    expected_total = R1_QUALIFIERS * CABO_TABLE_SIZE * CABO_GAMES  # 16 * 5 * 3 = 240
    if total_assignments == expected_total:
        constraints["complete_seat_assignments"] = True
    else:
        errors.append(f"Expected {expected_total} total assignments across 3 games, found {total_assignments}.")

    unique_teams = {a.team_id for a in assignments}
    unique_players = {a.participant_id for a in assignments}

    # 1. Exactly 16 teams
    if len(unique_teams) == R1_QUALIFIERS:
        constraints["exactly_16_teams"] = True
    else:
        errors.append(f"Expected {R1_QUALIFIERS} unique teams in assignments, found {len(unique_teams)}.")

    # 2. Exactly 5 players per team and 80 total
    team_players: Dict[str, Set[str]] = defaultdict(set)
    for a in assignments:
        team_players[a.team_id].add(a.participant_id)

    if (
        len(unique_players) == (R1_QUALIFIERS * CABO_TABLE_SIZE)
        and all(len(p_set) == CABO_TABLE_SIZE for p_set in team_players.values())
    ):
        constraints["exactly_5_players_per_team"] = True
    else:
        errors.append(
            f"Expected {R1_QUALIFIERS * CABO_TABLE_SIZE} total players with {CABO_TABLE_SIZE} per team; "
            f"found {len(unique_players)} players."
        )

    # Group assignments by game and table
    by_game_table: Dict[Tuple[int, int], List[CaboTableAssignment]] = defaultdict(list)
    by_game_team_tables: Dict[Tuple[int, str], Set[int]] = defaultdict(set)
    for a in assignments:
        by_game_table[(a.game_number, a.table_number)].append(a)
        by_game_team_tables[(a.game_number, a.team_id)].add(a.table_number)

    # 3. Exactly 16 tables per game
    games_table_counts = {g: len([k for k in by_game_table.keys() if k[0] == g]) for g in [1, 2, 3]}
    if all(cnt == R1_QUALIFIERS for cnt in games_table_counts.values()):
        constraints["exactly_16_tables_per_game"] = True
    else:
        errors.append(f"Not all games have {R1_QUALIFIERS} tables: {games_table_counts}.")

    # 4. Exactly 5 players per table
    table_sizes_valid = (
        len(by_game_table) == (R1_QUALIFIERS * CABO_GAMES)
        and all(len(seat_list) == CABO_TABLE_SIZE for seat_list in by_game_table.values())
    )
    if table_sizes_valid:
        constraints["exactly_5_players_per_table"] = True
    else:
        errors.append(f"One or more tables do not contain exactly {CABO_TABLE_SIZE} players.")

    # 5. Distinct teams per table & 6. Zero teammate collisions
    all_tables_distinct_teams = True
    zero_collisions = True
    for (g, t), table_seats in by_game_table.items():
        teams_at_table = [s.team_id for s in table_seats]
        if len(set(teams_at_table)) != len(teams_at_table):
            all_tables_distinct_teams = False
            zero_collisions = False
            errors.append(f"Game {g} Table {t} has duplicate teams: {teams_at_table}")

    if all_tables_distinct_teams:
        constraints["distinct_teams_per_table"] = True
    if zero_collisions:
        constraints["zero_teammate_collisions"] = True

    # 7. Team members distributed across 5 different tables per game
    all_teams_distributed = True
    for (g, tm_id), tbl_set in by_game_team_tables.items():
        if len(tbl_set) != CABO_TABLE_SIZE:
            all_teams_distributed = False
            errors.append(f"Team '{tm_id}' in Game {g} occupies {len(tbl_set)} tables, expected {CABO_TABLE_SIZE}.")

    if all_teams_distributed and constraints["complete_seat_assignments"]:
        constraints["team_members_distributed_across_tables"] = True

    is_valid = all(constraints.values()) and len(errors) == 0

    return {
        "is_valid": is_valid,
        "is_confirmed": is_confirmed,
        "confirmed_at": confirmed_at,
        "confirmed_by": confirmed_by,
        "total_teams": len(unique_teams),
        "total_players": len(unique_players),
        "total_tables": R1_QUALIFIERS,
        "constraints": constraints,
        "errors": errors,
    }


def confirm_cabo_tables(db: Session, actor_id: str) -> Dict[str, Any]:
    """
    Confirms and freezes Cabo seating assignments.
    Requires table validation to pass with zero errors.
    """
    validation = validate_cabo_table_allocations(db)
    if not validation["is_valid"]:
        raise CaboAssignmentError(
            f"Cannot confirm tables: validation failed with errors: {'; '.join(validation['errors'])}"
        )

    cfg = db.query(CaboConfigModel).filter(CaboConfigModel.id == 1).first()
    if not cfg:
        cfg = CaboConfigModel(id=1, point_table=CABO_PLACEMENT_POINTS)
        db.add(cfg)

    now = utc_now()
    cfg.is_tables_confirmed = True
    cfg.tables_confirmed_at = now
    cfg.tables_confirmed_by = actor_id

    log_audit_event(
        db=db,
        action="CABO_TABLES_CONFIRMED",
        entity_type="CaboConfigModel",
        entity_id="1",
        actor_id=actor_id,
        actor_role="organizer",
        round_number=2,
        details={
            "confirmed_at": now.isoformat(),
            "total_teams": validation["total_teams"],
            "total_players": validation["total_players"],
        }
    )

    db.commit()
    db.refresh(cfg)

    return {
        "is_confirmed": True,
        "confirmed_at": cfg.tables_confirmed_at.isoformat(),
        "confirmed_by": cfg.tables_confirmed_by,
        "message": "Round 2 Cabo tables successfully confirmed and frozen.",
    }


def correct_cabo_table_score(
    db: Session,
    game_number: int,
    table_number: int,
    participant_id: str,
    new_placement: int,
    reason: str,
    new_card_total: Optional[int] = None,
    actor_id: str = "organizer",
) -> Dict[str, Any]:
    """
    Organizer correction for an individual player's placement at a table.
    Swaps placement with the player currently holding new_placement at the same table,
    recalculates points, and records a mandatory audit trail.
    """
    if not (1 <= game_number <= 3):
        raise CaboScorecardError(f"Invalid game number {game_number}.")
    if not (1 <= table_number <= R1_QUALIFIERS):
        raise CaboScorecardError(f"Invalid table number {table_number}.")
    if not (1 <= new_placement <= 5):
        raise CaboScorecardError(f"Invalid new placement {new_placement}; must be between 1 and 5.")
    if not reason or len(reason.strip()) < 3:
        raise CaboScorecardError("Mandatory reason (min 3 characters) required for score correction.")

    # Target scorecard
    target_sc = (
        db.query(CaboPlayerScorecard)
        .filter(
            CaboPlayerScorecard.game_number == game_number,
            CaboPlayerScorecard.participant_id == participant_id,
        )
        .first()
    )
    if not target_sc:
        raise CaboScorecardError(
            f"No existing scorecard found for participant '{participant_id}' in Game {game_number}."
        )

    old_placement = target_sc.placement
    if old_placement == new_placement:
        if new_card_total is not None:
            target_sc.final_card_hand_total = new_card_total
            db.commit()
        return {"status": "success", "message": "Placement unchanged; card total updated if provided."}

    # Find the conflicting player holding new_placement at the same table
    table_assignments = (
        db.query(CaboTableAssignment)
        .filter(
            CaboTableAssignment.game_number == game_number,
            CaboTableAssignment.table_number == table_number,
        )
        .all()
    )
    table_part_ids = {a.participant_id for a in table_assignments}
    if participant_id not in table_part_ids:
        raise CaboScorecardError(
            f"Participant '{participant_id}' is not assigned to Table {table_number} in Game {game_number}."
        )

    conflict_sc = (
        db.query(CaboPlayerScorecard)
        .filter(
            CaboPlayerScorecard.game_number == game_number,
            CaboPlayerScorecard.participant_id.in_(table_part_ids),
            CaboPlayerScorecard.placement == new_placement,
        )
        .first()
    )

    now = utc_now()
    if conflict_sc:
        conflict_sc.placement = old_placement
        conflict_sc.placement_points = float(CABO_PLACEMENT_POINTS[old_placement])
        conflict_sc.is_verified = True
        conflict_sc.verified_by = actor_id
        conflict_sc.verified_at = now

    target_sc.placement = new_placement
    target_sc.placement_points = float(CABO_PLACEMENT_POINTS[new_placement])
    if new_card_total is not None:
        target_sc.final_card_hand_total = new_card_total
    target_sc.is_verified = True
    target_sc.verified_by = actor_id
    target_sc.verified_at = now

    log_audit_event(
        db=db,
        action="CABO_SCORECARD_CORRECTED",
        entity_type="CaboPlayerScorecard",
        entity_id=target_sc.id,
        actor_id=actor_id,
        actor_role="organizer",
        round_number=2,
        details={
            "game_number": game_number,
            "table_number": table_number,
            "participant_id": participant_id,
            "old_placement": old_placement,
            "new_placement": new_placement,
            "swapped_with_participant_id": conflict_sc.participant_id if conflict_sc else None,
            "reason": reason,
        }
    )

    db.commit()
    db.refresh(target_sc)

    return {
        "status": "success",
        "participant_id": participant_id,
        "old_placement": old_placement,
        "new_placement": new_placement,
        "points": target_sc.placement_points,
        "message": f"Placement updated to {new_placement}th (reason: {reason})",
    }


def get_player_cabo_detail(db: Session, participant_id: str) -> Dict[str, Any]:
    """
    Returns complete Cabo drill-down details for a single participant across all 3 games.
    """
    participant = db.query(Participant).filter(Participant.id == participant_id).first()
    if not participant:
        raise CaboValidationError(f"Participant '{participant_id}' not found.")

    team = db.query(Team).filter(Team.id == participant.team_id).first()

    assignments = (
        db.query(CaboTableAssignment)
        .filter(CaboTableAssignment.participant_id == participant_id)
        .order_by(CaboTableAssignment.game_number.asc())
        .all()
    )
    scorecards = {
        sc.game_number: sc
        for sc in db.query(CaboPlayerScorecard).filter(CaboPlayerScorecard.participant_id == participant_id).all()
    }

    games_data = []
    total_points = 0.0
    first_places = 0

    for a in assignments:
        sc = scorecards.get(a.game_number)
        pts = sc.placement_points if sc else None
        if pts is not None:
            total_points += pts
        if sc and sc.placement == 1:
            first_places += 1

        games_data.append({
            "game_number": a.game_number,
            "table_number": a.table_number,
            "seat_position": a.seat_position,
            "placement": sc.placement if sc else None,
            "placement_points": pts,
            "final_card_hand_total": sc.final_card_hand_total if sc else None,
            "is_verified": sc.is_verified if sc else False,
        })

    return {
        "participant_id": participant.id,
        "participant_name": participant.name,
        "participant_usn": participant.usn,
        "team_id": team.id if team else participant.team_id,
        "team_name": team.name if team else "Unknown",
        "team_number": team.team_number if team else None,
        "games": games_data,
        "total_points": total_points,
        "first_places_count": first_places,
    }


def get_team_cabo_detail(db: Session, team_id: str) -> Dict[str, Any]:
    """
    Returns complete Cabo drill-down details for a team and all 5 members across 3 games.
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise CaboValidationError(f"Team '{team_id}' not found.")

    members = db.query(Participant).filter(Participant.team_id == team_id).order_by(Participant.name.asc()).all()

    # Standings to get team rank and qualification status
    standings = calculate_round2_standings(db)
    rank = None
    is_qualified = False
    for s in standings:
        if s.team_id == team_id:
            rank = s.rank
            is_qualified = s.is_qualified
            break

    # Get all assignments and scorecards for team's participants
    part_ids = [m.id for m in members]
    assignments = (
        db.query(CaboTableAssignment)
        .filter(CaboTableAssignment.participant_id.in_(part_ids))
        .all()
    )
    scorecards = (
        db.query(CaboPlayerScorecard)
        .filter(CaboPlayerScorecard.participant_id.in_(part_ids))
        .all()
    )

    assign_map: Dict[Tuple[str, int], CaboTableAssignment] = {
        (a.participant_id, a.game_number): a for a in assignments
    }
    score_map: Dict[Tuple[str, int], CaboPlayerScorecard] = {
        (sc.participant_id, sc.game_number): sc for sc in scorecards
    }

    members_detail = []
    g1_total = 0.0
    g2_total = 0.0
    g3_total = 0.0

    for m in members:
        a1 = assign_map.get((m.id, 1))
        s1 = score_map.get((m.id, 1))
        p1 = s1.placement_points if s1 else None
        if p1 is not None:
            g1_total += p1

        a2 = assign_map.get((m.id, 2))
        s2 = score_map.get((m.id, 2))
        p2 = s2.placement_points if s2 else None
        if p2 is not None:
            g2_total += p2

        a3 = assign_map.get((m.id, 3))
        s3 = score_map.get((m.id, 3))
        p3 = s3.placement_points if s3 else None
        if p3 is not None:
            g3_total += p3

        indiv_total = sum(x for x in [p1, p2, p3] if x is not None)

        members_detail.append({
            "participant_id": m.id,
            "participant_name": m.name,
            "participant_usn": m.usn,
            "role": m.role.value if hasattr(m.role, "value") else str(m.role),
            "game1_table": a1.table_number if a1 else None,
            "game1_placement": s1.placement if s1 else None,
            "game1_points": p1,
            "game2_table": a2.table_number if a2 else None,
            "game2_placement": s2.placement if s2 else None,
            "game2_points": p2,
            "game3_table": a3.table_number if a3 else None,
            "game3_placement": s3.placement if s3 else None,
            "game3_points": p3,
            "total_individual_points": indiv_total,
        })

    squad_total = g1_total + g2_total + g3_total

    return {
        "team_id": team.id,
        "team_name": team.name,
        "team_number": team.team_number,
        "members": members_detail,
        "game1_total": g1_total,
        "game2_total": g2_total,
        "game3_total": g3_total,
        "cabo_squad_total": squad_total,
        "rank": rank,
        "is_qualified": is_qualified,
    }


def get_cabo_printable_sheet(db: Session, game_number: int) -> Dict[str, Any]:
    """
    Returns printable table sheets for all 16 tables in a specified Cabo game.
    """
    if not (1 <= game_number <= 3):
        raise CaboValidationError(f"Invalid game number {game_number}; must be 1, 2, or 3.")

    tables = get_game_tables(db, game_number=game_number)
    sheets = []
    for t in tables:
        sheet_players = [
            {
                "seat_position": p.seat_position,
                "participant_name": p.participant_name,
                "participant_usn": p.participant_usn,
                "team_name": p.team_name,
                "team_number": None,
            }
            for p in sorted(t.players, key=lambda x: x.seat_position)
        ]
        sheets.append({
            "table_number": t.table_number,
            "game_number": game_number,
            "players": sheet_players,
        })

    return {
        "game_number": game_number,
        "tables": sheets,
    }


def export_cabo_data(db: Session, export_type: str) -> str:
    """
    Generates CSV export strings for Cabo tournament data:
    - 'assignments': All 3-game table seat assignments
    - 'results': Recorded scorecards with points and placements
    - 'standings': Team aggregated leaderboard and qualification status
    """
    import io
    import csv

    output = io.StringIO()
    writer = csv.writer(output)

    if export_type == "assignments":
        writer.writerow(["Game", "Table", "Seat", "Team ID", "Team Name", "Participant ID", "Participant Name", "USN"])
        assignments = (
            db.query(CaboTableAssignment)
            .order_by(
                CaboTableAssignment.game_number.asc(),
                CaboTableAssignment.table_number.asc(),
                CaboTableAssignment.seat_position.asc(),
            )
            .all()
        )
        for a in assignments:
            writer.writerow([
                a.game_number,
                a.table_number,
                a.seat_position,
                a.team_id,
                a.team.name if a.team else "",
                a.participant_id,
                a.participant.name if a.participant else "",
                a.participant.usn if a.participant else "",
            ])

    elif export_type == "results":
        writer.writerow([
            "Game", "Table", "Seat", "Team Name", "Participant Name", "USN",
            "Placement", "Points", "Card Hand Total", "Verified", "Verified By"
        ])
        assignments = (
            db.query(CaboTableAssignment)
            .order_by(
                CaboTableAssignment.game_number.asc(),
                CaboTableAssignment.table_number.asc(),
                CaboTableAssignment.seat_position.asc(),
            )
            .all()
        )
        scorecard_map = {
            (sc.game_number, sc.participant_id): sc
            for sc in db.query(CaboPlayerScorecard).all()
        }
        for a in assignments:
            sc = scorecard_map.get((a.game_number, a.participant_id))
            writer.writerow([
                a.game_number,
                a.table_number,
                a.seat_position,
                a.team.name if a.team else "",
                a.participant.name if a.participant else "",
                a.participant.usn if a.participant else "",
                sc.placement if sc else "",
                sc.placement_points if sc else "",
                sc.final_card_hand_total if (sc and sc.final_card_hand_total is not None) else "",
                sc.is_verified if sc else False,
                sc.verified_by if sc else "",
            ])

    elif export_type == "standings":
        writer.writerow([
            "Rank", "Team Number", "Team Name", "Cabo Score (/75)",
            "Combined Card Total", "1st Places", "Qualified", "Advancing To R3"
        ])
        standings = calculate_round2_standings(db)
        for s in standings:
            writer.writerow([
                s.rank,
                s.team_number,
                s.team_name,
                s.cabo_score,
                s.combined_card_total,
                s.first_place_count,
                "YES" if s.is_qualified else "NO",
                "YES" if (s.rank <= 8 and s.is_qualified) else "NO",
            ])
    else:
        raise CaboValidationError(f"Invalid export type '{export_type}'. Supported: 'assignments', 'results', 'standings'.")

    return output.getvalue()

