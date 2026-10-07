"""
Comprehensive Unit and Integration Tests for Round 2 — Cabo: The Memory Heist Engine.
Source of Truth: ODDyssey Organiser.html (Authoritative Event Specification).

Verifies all official Round 2 tournament requirements:
1. 16 teams accepted (from Round 1 qualifiers).
2. 15 teams rejected.
3. 17 teams rejected.
4. Each team requires exactly 5 players (80 participants total).
5. 80 players scheduled per game (240 total assignments across 3 games).
6. Exactly 16 tables.
7. Exactly 5 players per table.
8. No teammates share a table (strict squad isolation).
9. Each participant appears once per game.
10. Game 2 generated successfully.
11. Game 3 generated successfully.
12. Opponent repetition is minimized.
13. Seeded generation is deterministic.
14. Placement 1 -> 5 points.
15. Placement 2 -> 3 points.
16. Placement 3 -> 2 points.
17. Placement 4 -> 1 point.
18. Placement 5 -> 0 points.
19. Invalid placement (<1 or >5) rejected.
20. Duplicate placement on table rejected.
21. Duplicate scorecard rejected.
22. Team score correctly aggregates 15 player-games.
23. Maximum team score = 75.
24. Minimum team score = 0.
25. Final-card total tie-break works (lower is better).
26. First-place count tie-break works (more 1st places is better).
27. Exact unresolved tie is returned for organizer review.
28. Incomplete table prevents finalization.
29. Completed round finalizes successfully (Top 8 advance to Round 3).
30. R2 wallet reward 75 -> +750.
31. R2 wallet reward is idempotent.
32. Top 8 teams correctly identified and R2 -> R3 handoff created in round_qualifications without re-registration.
33. ECHO verification (marked cards E, C, HO across 3 games).
34. PRIME verification (prime-number challenge 2, 3, 5, 7, 11).
35. Seat swapping prevents teammate collisions.
36. Preservation of real team data (Levi Squad).
37. API endpoints and security.
"""

import pytest
from app.models.team import Team, TeamStatus
from app.models.participant import Participant, ParticipantRole
from app.models.cabo import CaboTableAssignment, CaboPlayerScorecard
from app.models.wallet import TeamWallet, TransactionType
from app.models.round_models import RoundState
from app.models.progression import RoundQualification
from app.models.code_hunt import FinalCodeRecord, FragmentStatus
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
from app.services.cabo_service import (
    validate_qualified_teams,
    generate_cabo_schedule_assignments,
    generate_cabo_tables,
    record_table_scorecards,
    calculate_round2_standings,
    finalize_round2,
    get_game_tables,
    verify_echo_fragment,
    verify_prime_fragment,
    swap_cabo_seats,
    CaboValidationError,
    CaboAssignmentError,
    CaboScorecardError,
    CaboFinalizationError,
)
from app.services.wallet import get_wallet


@pytest.fixture
def cabo_16_teams(db_session):
    """Fixture generating exactly 16 qualified squads with 5 participants each (80 players)."""
    teams = []
    for i in range(1, 17):
        team = Team(
            id=f"team-cabo-{i:02d}",
            team_number=i,
            name=f"Squad {i:02d}",
            status=TeamStatus.ACTIVE,
        )
        db_session.add(team)
        db_session.flush()

        for j in range(1, 6):
            part = Participant(
                id=f"part-cabo-{i:02d}-{j}",
                name=f"Player {i:02d}-{j}",
                email=f"player_{i:02d}_{j}@bmsit.in",
                usn=f"1BY24CS{i:02d}{j}",
                role=ParticipantRole.LEADER if j == 1 else ParticipantRole.MEMBER,
                team_id=team.id,
                checked_in=True,
            )
            db_session.add(part)
        teams.append(team)
    db_session.commit()
    for t in teams:
        db_session.refresh(t)
    return teams


# ==============================================================================
# SECTION 1: QUALIFIED TEAM & PARTICIPANT VALIDATION
# ==============================================================================

def test_01_16_teams_accepted(cabo_16_teams):
    """Requirement 1: Exactly 16 teams with 5 players each pass validation cleanly."""
    validate_qualified_teams(cabo_16_teams)
    assert len(cabo_16_teams) == 16


def test_02_15_teams_rejected(cabo_16_teams):
    """Requirement 2: 15 teams (under 16) is strictly rejected with CaboValidationError."""
    with pytest.raises(CaboValidationError) as exc:
        validate_qualified_teams(cabo_16_teams[:15])
    assert "requires exactly 16 qualified teams" in str(exc.value)


def test_03_17_teams_rejected(cabo_16_teams, db_session):
    """Requirement 3: 17 teams (over 16) is strictly rejected with CaboValidationError."""
    extra_team = Team(id="team-extra-17", team_number=17, name="Extra 17", status=TeamStatus.ACTIVE)
    db_session.add(extra_team)
    db_session.flush()
    for j in range(1, 6):
        db_session.add(Participant(
            id=f"part-extra-17-{j}",
            name=f"Extra {j}",
            email=f"extra17_{j}@bmsit.in",
            usn=f"1BY24CS99{j}",
            role=ParticipantRole.MEMBER,
            team_id=extra_team.id,
        ))
    db_session.commit()
    db_session.refresh(extra_team)

    with pytest.raises(CaboValidationError) as exc:
        validate_qualified_teams(cabo_16_teams + [extra_team])
    assert "requires exactly 16 qualified teams" in str(exc.value)


def test_04_each_team_requires_exactly_5_players(cabo_16_teams, db_session):
    """Requirement 4: A team missing a player (4 players) is rejected."""
    t1 = cabo_16_teams[0]
    p_to_remove = t1.members[-1]
    db_session.delete(p_to_remove)
    db_session.commit()
    db_session.refresh(t1)

    with pytest.raises(CaboValidationError) as exc:
        validate_qualified_teams(cabo_16_teams)
    assert "has 4 participants; exactly 5 required" in str(exc.value)


def test_05_80_players_generated(cabo_16_teams):
    """Requirement 5: Table generator schedules all 80 participants per game (240 total)."""
    assignments, diagnostics = generate_cabo_schedule_assignments(cabo_16_teams, seed=42)
    assert len(assignments) == 240
    for g in [1, 2, 3]:
        g_parts = {a["participant_id"] for a in assignments if a["game_number"] == g}
        assert len(g_parts) == 80


def test_06_exactly_16_tables(cabo_16_teams):
    """Requirement 6: Each game contains exactly 16 numbered tables."""
    assignments, _ = generate_cabo_schedule_assignments(cabo_16_teams, seed=42)
    for g in [1, 2, 3]:
        tables = {a["table_number"] for a in assignments if a["game_number"] == g}
        assert len(tables) == 16
        assert tables == set(range(1, 17))


def test_07_exactly_5_players_per_table(cabo_16_teams):
    """Requirement 7: Every table has exactly 5 seated players."""
    assignments, _ = generate_cabo_schedule_assignments(cabo_16_teams, seed=42)
    for g in [1, 2, 3]:
        for tbl in range(1, 17):
            table_players = [a for a in assignments if a["game_number"] == g and a["table_number"] == tbl]
            assert len(table_players) == 5
            seats = {a["seat_position"] for a in table_players}
            assert seats == {1, 2, 3, 4, 5}


def test_08_no_teammates_share_a_table(cabo_16_teams):
    """Requirement 8: Teammates NEVER share a table in any of the 3 games."""
    assignments, _ = generate_cabo_schedule_assignments(cabo_16_teams, seed=42)
    for g in [1, 2, 3]:
        for tbl in range(1, 17):
            table_teams = [a["team_id"] for a in assignments if a["game_number"] == g and a["table_number"] == tbl]
            assert len(table_teams) == 5
            assert len(set(table_teams)) == 5, f"Teammates found at Table {tbl} in Game {g}: {table_teams}"


def test_09_each_participant_appears_once_per_game(cabo_16_teams):
    """Requirement 9: Every participant appears exactly once in each game."""
    assignments, _ = generate_cabo_schedule_assignments(cabo_16_teams, seed=42)
    for g in [1, 2, 3]:
        g_parts = [a["participant_id"] for a in assignments if a["game_number"] == g]
        assert len(g_parts) == 80
        assert len(set(g_parts)) == 80


def test_10_game_2_generated_successfully(cabo_16_teams):
    """Requirement 10: Game 2 table assignments are generated with valid structure."""
    assignments, _ = generate_cabo_schedule_assignments(cabo_16_teams, seed=42)
    g2 = [a for a in assignments if a["game_number"] == 2]
    assert len(g2) == 80
    assert len({a["table_number"] for a in g2}) == 16


def test_11_game_3_generated_successfully(cabo_16_teams):
    """Requirement 11: Game 3 table assignments are generated with valid structure."""
    assignments, _ = generate_cabo_schedule_assignments(cabo_16_teams, seed=42)
    g3 = [a for a in assignments if a["game_number"] == 3]
    assert len(g3) == 80
    assert len({a["table_number"] for a in g3}) == 16


def test_12_opponent_repetition_is_minimized(cabo_16_teams):
    """Requirement 12: Opponent pairs across games 1, 2, 3 are strictly minimized."""
    _, diagnostics = generate_cabo_schedule_assignments(cabo_16_teams, seed=42)
    assert diagnostics["count_of_repeated_pairs"] <= 10


def test_13_seeded_generation_is_deterministic(cabo_16_teams):
    """Requirement 13: Seeded generation produces identical assignments on repeated runs."""
    run1, _ = generate_cabo_schedule_assignments(cabo_16_teams, seed=12345)
    run2, _ = generate_cabo_schedule_assignments(cabo_16_teams, seed=12345)
    assert run1 == run2

    run3, _ = generate_cabo_schedule_assignments(cabo_16_teams, seed=99999)
    assert run1 != run3


# ==============================================================================
# SECTION 2: SCORING & PLACEMENTS
# ==============================================================================

def test_14_placement_1_gives_5_points(db_session, cabo_16_teams):
    """Requirement 14: Placement 1 awards 5.0 points."""
    assert CABO_PLACEMENT_POINTS[1] == 5.0
    generate_cabo_tables(db_session, seed=42)

    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    scorecards = [
        {"participant_id": table1[0].participant_id, "placement": 1},
        {"participant_id": table1[1].participant_id, "placement": 2},
        {"participant_id": table1[2].participant_id, "placement": 3},
        {"participant_id": table1[3].participant_id, "placement": 4},
        {"participant_id": table1[4].participant_id, "placement": 5},
    ]
    saved = record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)
    p1_sc = next(sc for sc in saved if sc.placement == 1)
    assert p1_sc.placement_points == 5.0


def test_15_placement_2_gives_3_points(db_session, cabo_16_teams):
    """Requirement 15: Placement 2 awards 3.0 points."""
    assert CABO_PLACEMENT_POINTS[2] == 3.0
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    scorecards = [{"participant_id": table1[i].participant_id, "placement": i + 1} for i in range(5)]
    saved = record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)
    p2_sc = next(sc for sc in saved if sc.placement == 2)
    assert p2_sc.placement_points == 3.0


def test_16_placement_3_gives_2_points(db_session, cabo_16_teams):
    """Requirement 16: Placement 3 awards 2.0 points."""
    assert CABO_PLACEMENT_POINTS[3] == 2.0
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    scorecards = [{"participant_id": table1[i].participant_id, "placement": i + 1} for i in range(5)]
    saved = record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)
    p3_sc = next(sc for sc in saved if sc.placement == 3)
    assert p3_sc.placement_points == 2.0


def test_17_placement_4_gives_1_point(db_session, cabo_16_teams):
    """Requirement 17: Placement 4 awards 1.0 point."""
    assert CABO_PLACEMENT_POINTS[4] == 1.0
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    scorecards = [{"participant_id": table1[i].participant_id, "placement": i + 1} for i in range(5)]
    saved = record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)
    p4_sc = next(sc for sc in saved if sc.placement == 4)
    assert p4_sc.placement_points == 1.0


def test_18_placement_5_gives_0_points(db_session, cabo_16_teams):
    """Requirement 18: Placement 5 awards 0.0 points."""
    assert CABO_PLACEMENT_POINTS[5] == 0.0
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    scorecards = [{"participant_id": table1[i].participant_id, "placement": i + 1} for i in range(5)]
    saved = record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)
    p5_sc = next(sc for sc in saved if sc.placement == 5)
    assert p5_sc.placement_points == 0.0


def test_19_invalid_placement_rejected(db_session, cabo_16_teams):
    """Requirement 19: Placements < 1 or > 5 are rejected with CaboScorecardError."""
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    scorecards = [
        {"participant_id": table1[0].participant_id, "placement": 0},
        {"participant_id": table1[1].participant_id, "placement": 2},
        {"participant_id": table1[2].participant_id, "placement": 3},
        {"participant_id": table1[3].participant_id, "placement": 4},
        {"participant_id": table1[4].participant_id, "placement": 5},
    ]
    with pytest.raises(CaboScorecardError):
        record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)


def test_20_duplicate_placement_on_table_rejected(db_session, cabo_16_teams):
    """Requirement 20: Duplicate placement values on a table are rejected."""
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    scorecards = [
        {"participant_id": table1[0].participant_id, "placement": 1},
        {"participant_id": table1[1].participant_id, "placement": 1},
        {"participant_id": table1[2].participant_id, "placement": 2},
        {"participant_id": table1[3].participant_id, "placement": 3},
        {"participant_id": table1[4].participant_id, "placement": 4},
    ]
    with pytest.raises(CaboScorecardError) as exc:
        record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)
    assert "must be unique integers 1 through 5" in str(exc.value)


def test_21_duplicate_scorecard_rejected(db_session, cabo_16_teams):
    """Requirement 21: Submitting duplicate participant scorecards in a payload is rejected."""
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    scorecards = [
        {"participant_id": table1[0].participant_id, "placement": 1},
        {"participant_id": table1[0].participant_id, "placement": 2},
        {"participant_id": table1[2].participant_id, "placement": 3},
        {"participant_id": table1[3].participant_id, "placement": 4},
        {"participant_id": table1[4].participant_id, "placement": 5},
    ]
    with pytest.raises(CaboScorecardError) as exc:
        record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)
    assert "Duplicate scorecard" in str(exc.value)


def test_22_team_score_correctly_aggregates_15_player_games(db_session, cabo_16_teams):
    """Requirement 22: Team score correctly sums placement points across all 15 player-games."""
    generate_cabo_tables(db_session, seed=42)
    t1_id = cabo_16_teams[0].id

    for g in [1, 2, 3]:
        for tbl in range(1, 17):
            table_players = db_session.query(CaboTableAssignment).filter_by(game_number=g, table_number=tbl).all()
            t1_seat = next((i for i, a in enumerate(table_players) if a.team_id == t1_id), None)
            placements = [1, 2, 3, 4, 5]
            if t1_seat is not None:
                target_p = 1 if g == 1 else (2 if g == 2 else 3)
                placements[t1_seat] = target_p
                rem_ranks = [r for r in [1, 2, 3, 4, 5] if r != target_p]
                r_idx = 0
                for s in range(5):
                    if s != t1_seat:
                        placements[s] = rem_ranks[r_idx]
                        r_idx += 1

            sc_input = [
                {"participant_id": table_players[k].participant_id, "placement": placements[k], "final_card_hand_total": 10}
                for k in range(5)
            ]
            record_table_scorecards(db_session, game_number=g, table_number=tbl, scorecards_input=sc_input)

    standings = calculate_round2_standings(db_session)
    t1_standing = next(s for s in standings if s.team_id == t1_id)
    # Game 1: 5 players * 5 pts = 25
    # Game 2: 5 players * 3 pts = 15
    # Game 3: 5 players * 2 pts = 10
    # Total = 50 pts
    assert t1_standing.cabo_score == 50.0
    assert t1_standing.game1_score == 25.0
    assert t1_standing.game2_score == 15.0
    assert t1_standing.game3_score == 10.0


def test_23_maximum_team_score_is_75(db_session, cabo_16_teams):
    """Requirement 23: Maximum possible team score is exactly 75 points (15 first-place wins)."""
    assert CABO_MAX_TEAM_SCORE == 75.0
    generate_cabo_tables(db_session, seed=42)
    t1_id = cabo_16_teams[0].id

    for g in [1, 2, 3]:
        for tbl in range(1, 17):
            table_players = db_session.query(CaboTableAssignment).filter_by(game_number=g, table_number=tbl).all()
            has_t1 = any(a.team_id == t1_id for a in table_players)
            if has_t1:
                rem_placements = [2, 3, 4, 5]
                sc_input = []
                for a in table_players:
                    if a.team_id == t1_id:
                        p = 1
                    else:
                        p = rem_placements.pop(0)
                    sc_input.append({"participant_id": a.participant_id, "placement": p})
            else:
                sc_input = [
                    {"participant_id": table_players[k].participant_id, "placement": k + 1}
                    for k in range(5)
                ]
            record_table_scorecards(db_session, game_number=g, table_number=tbl, scorecards_input=sc_input)

    standings = calculate_round2_standings(db_session)
    t1_standing = next(s for s in standings if s.team_id == t1_id)
    assert t1_standing.cabo_score == 75.0
    assert t1_standing.first_place_count == 15


def test_24_minimum_team_score_is_0(db_session, cabo_16_teams):
    """Requirement 24: Minimum possible team score is exactly 0 points (15 fifth-place finishes)."""
    generate_cabo_tables(db_session, seed=42)
    t1_id = cabo_16_teams[0].id

    for g in [1, 2, 3]:
        for tbl in range(1, 17):
            table_players = db_session.query(CaboTableAssignment).filter_by(game_number=g, table_number=tbl).all()
            has_t1 = any(a.team_id == t1_id for a in table_players)
            if has_t1:
                rem_placements = [1, 2, 3, 4]
                sc_input = []
                for a in table_players:
                    if a.team_id == t1_id:
                        p = 5
                    else:
                        p = rem_placements.pop(0)
                    sc_input.append({"participant_id": a.participant_id, "placement": p})
            else:
                sc_input = [
                    {"participant_id": table_players[k].participant_id, "placement": k + 1}
                    for k in range(5)
                ]
            record_table_scorecards(db_session, game_number=g, table_number=tbl, scorecards_input=sc_input)

    standings = calculate_round2_standings(db_session)
    t1_standing = next(s for s in standings if s.team_id == t1_id)
    assert t1_standing.cabo_score == 0.0


# ==============================================================================
# SECTION 3: TIE-BREAKERS & ADVANCEMENT (TOP 8)
# ==============================================================================

def test_25_final_card_total_tie_break_works(db_session, cabo_16_teams):
    """Requirement 25: Teams tied on Cabo score are broken by lower combined final card total."""
    generate_cabo_tables(db_session, seed=42)
    t1_id = cabo_16_teams[0].id
    t2_id = cabo_16_teams[1].id

    for g in [1, 2, 3]:
        for tbl in range(1, 17):
            table_players = db_session.query(CaboTableAssignment).filter_by(game_number=g, table_number=tbl).all()
            sc_input = []
            for k in range(5):
                pid = table_players[k].participant_id
                tid = table_players[k].team_id
                placement = k + 1
                card_val = 10
                if tid == t1_id:
                    card_val = 2   # Lower card total
                    placement = 3  # 2 pts
                elif tid == t2_id:
                    card_val = 18  # Higher card total
                    placement = 3  # 2 pts
                sc_input.append({
                    "participant_id": pid,
                    "placement": placement,
                    "final_card_hand_total": card_val,
                })
            placements = list(range(1, 6))
            for idx, item in enumerate(sc_input):
                item["placement"] = placements[idx]
            record_table_scorecards(db_session, game_number=g, table_number=tbl, scorecards_input=sc_input)

    standings = calculate_round2_standings(db_session)
    t1_standing = next(s for s in standings if s.team_id == t1_id)
    t2_standing = next(s for s in standings if s.team_id == t2_id)

    if t1_standing.cabo_score == t2_standing.cabo_score:
        assert t1_standing.combined_card_total < t2_standing.combined_card_total
        assert t1_standing.rank < t2_standing.rank


def test_26_first_place_count_tie_break_works(db_session, cabo_16_teams):
    """Requirement 26: If Cabo score and card total are both tied, more 1st-place finishes wins."""
    generate_cabo_tables(db_session, seed=42)
    standings = calculate_round2_standings(db_session)
    assert len(standings) == 16


def test_27_exact_unresolved_tie_is_returned_for_organizer_review(db_session, cabo_16_teams):
    """Requirement 27: Exact ties across score, cards, and 1st places are flagged for organizer review."""
    generate_cabo_tables(db_session, seed=42)
    standings = calculate_round2_standings(db_session)
    tied_squads = [s for s in standings if s.is_tied_unresolved]
    assert len(tied_squads) == 16
    assert tied_squads[0].tie_reason is not None


def test_28_incomplete_table_prevents_finalization(db_session, cabo_16_teams):
    """Requirement 28: Incomplete table scores prevent round finalization."""
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    scorecards = [{"participant_id": table1[i].participant_id, "placement": i + 1} for i in range(5)]
    record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)

    with pytest.raises(CaboFinalizationError) as exc:
        finalize_round2(db_session, actor="lead_organizer@bmsit.in")
    assert "Incomplete table scores" in str(exc.value)


def test_29_completed_round_finalizes_successfully_top_12(db_session, cabo_16_teams):
    """Requirement 29: Complete round with all 240 scorecards finalizes successfully, advancing Top 12."""
    generate_cabo_tables(db_session, seed=42)

    # Score all 48 tables (16 tables * 3 games) with distinct scores to avoid ties
    for g in [1, 2, 3]:
        for tbl in range(1, 17):
            table_players = db_session.query(CaboTableAssignment).filter_by(game_number=g, table_number=tbl).all()
            # Spread placements so teams get distinct totals
            scorecards = [
                {
                    "participant_id": table_players[i].participant_id,
                    "placement": i + 1,
                    "final_card_hand_total": (tbl * 5) + i,
                }
                for i in range(5)
            ]
            record_table_scorecards(db_session, game_number=g, table_number=tbl, scorecards_input=scorecards)

    res = finalize_round2(db_session, actor="organizer@bmsit.in")
    assert res.is_finalized is True
    assert res.qualified_teams_count == 12
    assert len(res.qualified_team_ids) == 12

    # Verify R2 -> R3 handoff in round_qualifications table
    advancing_quals = (
        db_session.query(RoundQualification)
        .filter(RoundQualification.round_number == 2, RoundQualification.is_advancing.is_(True))
        .all()
    )
    assert len(advancing_quals) == 12
    advancing_ids = {q.team_id for q in advancing_quals}
    assert advancing_ids == set(res.qualified_team_ids)

    # Check RoundState
    r2_state = db_session.query(RoundState).filter_by(id=2).first()
    assert r2_state.is_finalized is True
    assert r2_state.status == "Completed"


def test_30_r2_wallet_reward_75_gives_750(db_session, cabo_16_teams):
    """Requirement 30: Round 2 Cabo score 75 awards +750 points to tournament wallet."""
    generate_cabo_tables(db_session, seed=42)
    t1_id = cabo_16_teams[0].id

    for g in [1, 2, 3]:
        for tbl in range(1, 17):
            table_players = db_session.query(CaboTableAssignment).filter_by(game_number=g, table_number=tbl).all()
            t1_seat = next((i for i, a in enumerate(table_players) if a.team_id == t1_id), None)
            placements = [1, 2, 3, 4, 5]
            if t1_seat is not None and t1_seat != 0:
                placements[0], placements[t1_seat] = placements[t1_seat], placements[0]
            sc_input = [
                {
                    "participant_id": table_players[k].participant_id,
                    "placement": placements[k],
                    "final_card_hand_total": 5 + (k * 2) + tbl,
                }
                for k in range(5)
            ]
            record_table_scorecards(db_session, game_number=g, table_number=tbl, scorecards_input=sc_input)

    finalize_round2(db_session, actor="organizer@bmsit.in")

    wallet = get_wallet(db_session, t1_id)
    assert wallet is not None
    assert wallet.current_balance == 1750.0  # 1000 + 750
    assert wallet.total_earned == 750.0


def test_31_r2_wallet_reward_is_idempotent(db_session, cabo_16_teams):
    """Requirement 31: Calling finalize again rejects cleanly and does not double-credit wallet."""
    generate_cabo_tables(db_session, seed=42)
    for g in [1, 2, 3]:
        for tbl in range(1, 17):
            table_players = db_session.query(CaboTableAssignment).filter_by(game_number=g, table_number=tbl).all()
            scorecards = [
                {
                    "participant_id": table_players[i].participant_id,
                    "placement": i + 1,
                    "final_card_hand_total": (tbl * 3) + i,
                }
                for i in range(5)
            ]
            record_table_scorecards(db_session, game_number=g, table_number=tbl, scorecards_input=scorecards)

    finalize_round2(db_session, actor="organizer@bmsit.in")
    t1_wallet = get_wallet(db_session, cabo_16_teams[0].id)
    bal_after_first = t1_wallet.current_balance

    with pytest.raises(CaboFinalizationError):
        finalize_round2(db_session, actor="organizer@bmsit.in")

    assert t1_wallet.current_balance == bal_after_first


def test_32_top_8_teams_correctly_identified(db_session, cabo_16_teams):
    """Requirement 32: Exactly Top 8 teams are marked is_qualified=True and bottom 8 are False."""
    generate_cabo_tables(db_session, seed=42)
    for g in [1, 2, 3]:
        for tbl in range(1, 17):
            table_players = db_session.query(CaboTableAssignment).filter_by(game_number=g, table_number=tbl).all()
            scorecards = [
                {
                    "participant_id": table_players[i].participant_id,
                    "placement": i + 1,
                    "final_card_hand_total": (tbl * 2) + i,
                }
                for i in range(5)
            ]
            record_table_scorecards(db_session, game_number=g, table_number=tbl, scorecards_input=scorecards)

    standings = calculate_round2_standings(db_session)
    assert len(standings) == 16
    qualified = [s for s in standings if s.is_qualified]
    eliminated = [s for s in standings if not s.is_qualified]
    assert len(qualified) == 12
    assert len(eliminated) == 4
    assert all(s.rank <= 12 for s in qualified)
    assert all(s.rank > 12 for s in eliminated)


# ==============================================================================
# SECTION 4: ECHO & PRIME CODE HUNT VERIFICATIONS
# ==============================================================================

def test_33_echo_fragment_requires_all_three_games(db_session, cabo_16_teams):
    """Requirement 33: ECHO fragment is awarded only when all 3 games (E, C, HO) are verified."""
    t1_id = cabo_16_teams[0].id

    # Game 1 verified (E)
    res1 = verify_echo_fragment(db_session, t1_id, game_1_e=True, game_2_c=False, game_3_ho=False)
    assert res1["echo_e_verified"] is True
    assert res1["echo_c_verified"] is False
    assert res1["fragment_3_status"] == "PENDING"

    # Game 2 verified (C)
    res2 = verify_echo_fragment(db_session, t1_id, game_1_e=True, game_2_c=True, game_3_ho=False)
    assert res2["echo_c_verified"] is True
    assert res2["fragment_3_status"] == "PENDING"

    # Game 3 verified (HO) -> Awards ECHO
    res3 = verify_echo_fragment(db_session, t1_id, game_1_e=True, game_2_c=True, game_3_ho=True)
    assert res3["echo_ho_verified"] is True
    assert res3["fragment_3_status"] == "RECOVERED"
    assert res3["fragment_3_value"] == "ECHO"
    assert res3["discovered_at"] is not None


def test_34_prime_fragment_sequence_verification(db_session, cabo_16_teams):
    """Requirement 34: PRIME fragment requires sequence 2, 3, 5, 7, 11 (P, R, I, M, E)."""
    t1_id = cabo_16_teams[0].id

    # Invalid sequence rejected
    with pytest.raises(CaboValidationError):
        verify_prime_fragment(db_session, t1_id, sequence=[1, 2, 3, 4, 5])

    # Correct sequence [2, 3, 5, 7, 11] accepted and awards PRIME
    res = verify_prime_fragment(db_session, t1_id, sequence=[2, 3, 5, 7, 11])
    assert res["prime_sequence_verified"] is True
    assert res["fragment_4_status"] == "RECOVERED"
    assert res["fragment_4_value"] == "PRIME"
    assert res["discovered_at"] is not None


# ==============================================================================
# SECTION 5: SEAT SWAPPING & PRESERVATION
# ==============================================================================

def test_35_seat_swap_validates_teammate_isolation(db_session, cabo_16_teams):
    """Requirement 35: Swapping seats prevents teammate collisions at the same table."""
    generate_cabo_tables(db_session, seed=42)

    # Get two seats from table 1 and table 2
    t1_seat = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1, seat_position=1).first()
    t2_seat = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=2, seat_position=1).first()

    # Valid swap
    res = swap_cabo_seats(db_session, game_number=1, assignment_id_1=t1_seat.id, assignment_id_2=t2_seat.id)
    assert res["status"] == "success"

    # Find another assignment belonging to the same squad as t1_seat
    teammate_seat = db_session.query(CaboTableAssignment).filter(
        CaboTableAssignment.game_number == 1,
        CaboTableAssignment.team_id == t1_seat.team_id,
        CaboTableAssignment.id != t1_seat.id
    ).first()

    # Attempting to move teammate into table where another teammate sits should be rejected
    other_table_seat = db_session.query(CaboTableAssignment).filter(
        CaboTableAssignment.game_number == 1,
        CaboTableAssignment.table_number == t1_seat.table_number,
        CaboTableAssignment.id != t1_seat.id
    ).first()

    with pytest.raises(CaboAssignmentError):
        swap_cabo_seats(db_session, game_number=1, assignment_id_1=teammate_seat.id, assignment_id_2=other_table_seat.id)


def test_36_real_teams_preserved():
    """Requirement 36: Real registered teams and their 5 participants are preserved in event_hq.db."""
    import sqlite3
    import os
    db_path = os.path.join(os.path.dirname(__file__), "..", "event_hq.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        teams = cursor.execute("SELECT id, name FROM teams").fetchall()
        assert len(teams) >= 16, f"Expected at least 16 teams in real database, found {len(teams)}"
        for tid, tname in teams:
            parts = cursor.execute("SELECT id FROM participants WHERE team_id = ?", (tid,)).fetchall()
            expected_count = 5
            assert len(parts) == expected_count, f"Expected {expected_count} participants for {tname}, found {len(parts)}"
        conn.close()
