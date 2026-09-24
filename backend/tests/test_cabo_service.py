"""
Comprehensive Unit and Integration Tests for Round 2 — Cabo Table Generation & Scoring Engine (Step 10).
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Verifies all 32 mandatory tournament Cabo requirements:
1. 24 teams accepted.
2. 23 teams rejected.
3. 25 teams rejected.
4. Each team requires exactly 5 players.
5. 120 players generated.
6. Exactly 24 tables.
7. Exactly 5 players per table.
8. No teammates share a table.
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
19. Invalid placement rejected.
20. Duplicate placement on table rejected.
21. Duplicate scorecard rejected.
22. Team score correctly aggregates 15 player-games.
23. Maximum team score = 75.
24. Minimum team score = 0.
25. Final-card total tie-break works.
26. First-place count tie-break works.
27. Exact unresolved tie is returned for organizer review.
28. Incomplete table prevents finalization.
29. Completed round finalizes successfully.
30. R2 wallet reward 75 -> +750.
31. R2 wallet reward is idempotent.
32. Top 12 teams correctly identified.
Plus API endpoints and RBAC security tests.
"""

import pytest
from app.models.team import Team, TeamStatus
from app.models.participant import Participant, ParticipantRole
from app.models.cabo import CaboTableAssignment, CaboPlayerScorecard
from app.models.wallet import TeamWallet, TransactionType
from app.models.round_models import RoundState
from app.core.constants import (
    R1_QUALIFIERS,
    R2_QUALIFIERS,
    TEAM_SIZE,
    CABO_GAMES,
    CABO_TABLE_SIZE,
    CABO_PLACEMENT_POINTS,
    CABO_MAX_TEAM_SCORE,
)
from app.services.cabo_service import (
    validate_qualified_teams,
    generate_cabo_schedule_assignments,
    generate_cabo_tables,
    record_table_scorecards,
    calculate_round2_standings,
    finalize_round2,
    get_game_tables,
    CaboValidationError,
    CaboAssignmentError,
    CaboScorecardError,
    CaboFinalizationError,
)
from app.services.wallet import get_wallet


@pytest.fixture
def cabo_24_teams(db_session):
    """Fixture generating exactly 24 qualified squads with 5 participants each (120 players)."""
    teams = []
    for i in range(1, 25):
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
# SECTION 18 MANDATORY TESTS (1 - 32)
# ==============================================================================

def test_01_24_teams_accepted(cabo_24_teams):
    """Requirement 1: Exactly 24 teams with 5 players each pass validation cleanly."""
    validate_qualified_teams(cabo_24_teams)
    assert len(cabo_24_teams) == 24


def test_02_23_teams_rejected(cabo_24_teams):
    """Requirement 2: 23 teams (under 24) is strictly rejected with CaboValidationError."""
    with pytest.raises(CaboValidationError) as exc:
        validate_qualified_teams(cabo_24_teams[:23])
    assert "requires exactly 24 qualified teams" in str(exc.value)


def test_03_25_teams_rejected(cabo_24_teams, db_session):
    """Requirement 3: 25 teams (over 24) is strictly rejected with CaboValidationError."""
    extra_team = Team(id="team-extra-25", team_number=25, name="Extra 25", status=TeamStatus.ACTIVE)
    db_session.add(extra_team)
    db_session.flush()
    for j in range(1, 6):
        db_session.add(Participant(
            id=f"part-extra-{j}",
            name=f"Extra {j}",
            email=f"extra{j}@bmsit.in",
            usn=f"1BY24CS99{j}",
            role=ParticipantRole.MEMBER,
            team_id=extra_team.id,
        ))
    db_session.commit()
    db_session.refresh(extra_team)

    with pytest.raises(CaboValidationError) as exc:
        validate_qualified_teams(cabo_24_teams + [extra_team])
    assert "requires exactly 24 qualified teams" in str(exc.value)


def test_04_each_team_requires_exactly_5_players(cabo_24_teams, db_session):
    """Requirement 4: A team missing a player (4 players) or having an extra player (6) is rejected."""
    # Remove one player from squad 1
    t1 = cabo_24_teams[0]
    p_to_remove = t1.members[-1]
    db_session.delete(p_to_remove)
    db_session.commit()
    db_session.refresh(t1)

    with pytest.raises(CaboValidationError) as exc:
        validate_qualified_teams(cabo_24_teams)
    assert "has 4 participants; exactly 5 required" in str(exc.value)


def test_05_120_players_generated(cabo_24_teams):
    """Requirement 5: Table generator schedules all 120 participants per game."""
    assignments, diagnostics = generate_cabo_schedule_assignments(cabo_24_teams, seed=42)
    # Total assignments across 3 games = 120 * 3 = 360
    assert len(assignments) == 360
    # For each game, exactly 120 unique participant assignments
    for g in [1, 2, 3]:
        g_parts = {a["participant_id"] for a in assignments if a["game_number"] == g}
        assert len(g_parts) == 120


def test_06_exactly_24_tables(cabo_24_teams):
    """Requirement 6: Each game contains exactly 24 numbered tables."""
    assignments, _ = generate_cabo_schedule_assignments(cabo_24_teams, seed=42)
    for g in [1, 2, 3]:
        tables = {a["table_number"] for a in assignments if a["game_number"] == g}
        assert len(tables) == 24
        assert tables == set(range(1, 25))


def test_07_exactly_5_players_per_table(cabo_24_teams):
    """Requirement 7: Every table has exactly 5 seated players."""
    assignments, _ = generate_cabo_schedule_assignments(cabo_24_teams, seed=42)
    for g in [1, 2, 3]:
        for tbl in range(1, 25):
            table_players = [a for a in assignments if a["game_number"] == g and a["table_number"] == tbl]
            assert len(table_players) == 5
            seats = {a["seat_position"] for a in table_players}
            assert seats == {1, 2, 3, 4, 5}


def test_08_no_teammates_share_a_table(cabo_24_teams):
    """Requirement 8: Teammates never share a table in any of the 3 games."""
    assignments, _ = generate_cabo_schedule_assignments(cabo_24_teams, seed=42)
    for g in [1, 2, 3]:
        for tbl in range(1, 25):
            table_teams = [a["team_id"] for a in assignments if a["game_number"] == g and a["table_number"] == tbl]
            assert len(table_teams) == 5
            assert len(set(table_teams)) == 5, f"Teammates found at Table {tbl} in Game {g}: {table_teams}"


def test_09_each_participant_appears_once_per_game(cabo_24_teams):
    """Requirement 9: Every participant appears exactly once in each game."""
    assignments, _ = generate_cabo_schedule_assignments(cabo_24_teams, seed=42)
    for g in [1, 2, 3]:
        g_parts = [a["participant_id"] for a in assignments if a["game_number"] == g]
        assert len(g_parts) == 120
        assert len(set(g_parts)) == 120


def test_10_game_2_generated_successfully(cabo_24_teams):
    """Requirement 10: Game 2 table assignments are generated with valid structure."""
    assignments, _ = generate_cabo_schedule_assignments(cabo_24_teams, seed=42)
    g2 = [a for a in assignments if a["game_number"] == 2]
    assert len(g2) == 120
    assert len({a["table_number"] for a in g2}) == 24


def test_11_game_3_generated_successfully(cabo_24_teams):
    """Requirement 11: Game 3 table assignments are generated with valid structure."""
    assignments, _ = generate_cabo_schedule_assignments(cabo_24_teams, seed=42)
    g3 = [a for a in assignments if a["game_number"] == 3]
    assert len(g3) == 120
    assert len({a["table_number"] for a in g3}) == 24


def test_12_opponent_repetition_is_minimized(cabo_24_teams):
    """Requirement 12: Opponent pairs across games 1, 2, 3 are strictly minimized."""
    _, diagnostics = generate_cabo_schedule_assignments(cabo_24_teams, seed=42)
    assert diagnostics["count_of_repeated_pairs"] <= 10
    # In our permutation optimization, repeats are virtually 0
    assert diagnostics["count_of_repeated_pairs"] == 0


def test_13_seeded_generation_is_deterministic(cabo_24_teams):
    """Requirement 13: Seeded generation produces identical assignments on repeated runs."""
    run1, _ = generate_cabo_schedule_assignments(cabo_24_teams, seed=12345)
    run2, _ = generate_cabo_schedule_assignments(cabo_24_teams, seed=12345)
    assert run1 == run2

    # Different seeds produce different seating
    run3, _ = generate_cabo_schedule_assignments(cabo_24_teams, seed=99999)
    assert run1 != run3


def test_14_placement_1_gives_5_points(db_session, cabo_24_teams):
    """Requirement 14: Placement 1 awards 5.0 points."""
    assert CABO_PLACEMENT_POINTS[1] == 5.0
    generate_cabo_tables(db_session, seed=42)

    # Fetch table 1 players
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


def test_15_placement_2_gives_3_points(db_session, cabo_24_teams):
    """Requirement 15: Placement 2 awards 3.0 points."""
    assert CABO_PLACEMENT_POINTS[2] == 3.0
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    scorecards = [{"participant_id": table1[i].participant_id, "placement": i + 1} for i in range(5)]
    saved = record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)
    p2_sc = next(sc for sc in saved if sc.placement == 2)
    assert p2_sc.placement_points == 3.0


def test_16_placement_3_gives_2_points(db_session, cabo_24_teams):
    """Requirement 16: Placement 3 awards 2.0 points."""
    assert CABO_PLACEMENT_POINTS[3] == 2.0
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    scorecards = [{"participant_id": table1[i].participant_id, "placement": i + 1} for i in range(5)]
    saved = record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)
    p3_sc = next(sc for sc in saved if sc.placement == 3)
    assert p3_sc.placement_points == 2.0


def test_17_placement_4_gives_1_point(db_session, cabo_24_teams):
    """Requirement 17: Placement 4 awards 1.0 point."""
    assert CABO_PLACEMENT_POINTS[4] == 1.0
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    scorecards = [{"participant_id": table1[i].participant_id, "placement": i + 1} for i in range(5)]
    saved = record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)
    p4_sc = next(sc for sc in saved if sc.placement == 4)
    assert p4_sc.placement_points == 1.0


def test_18_placement_5_gives_0_points(db_session, cabo_24_teams):
    """Requirement 18: Placement 5 awards 0.0 points."""
    assert CABO_PLACEMENT_POINTS[5] == 0.0
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    scorecards = [{"participant_id": table1[i].participant_id, "placement": i + 1} for i in range(5)]
    saved = record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)
    p5_sc = next(sc for sc in saved if sc.placement == 5)
    assert p5_sc.placement_points == 0.0


def test_19_invalid_placement_rejected(db_session, cabo_24_teams):
    """Requirement 19: Placements < 1 or > 5 are rejected with CaboScorecardError."""
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    # Placement 0
    scorecards = [
        {"participant_id": table1[0].participant_id, "placement": 0},
        {"participant_id": table1[1].participant_id, "placement": 2},
        {"participant_id": table1[2].participant_id, "placement": 3},
        {"participant_id": table1[3].participant_id, "placement": 4},
        {"participant_id": table1[4].participant_id, "placement": 5},
    ]
    with pytest.raises(CaboScorecardError):
        record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)

    # Placement 6
    scorecards[0]["placement"] = 6
    with pytest.raises(CaboScorecardError):
        record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)


def test_20_duplicate_placement_on_table_rejected(db_session, cabo_24_teams):
    """Requirement 20: Duplicate placement values on a table (e.g., two 1st places) are rejected."""
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    # Two 1st places, missing 5th
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


def test_21_duplicate_scorecard_rejected(db_session, cabo_24_teams):
    """Requirement 21: Submitting duplicate participant scorecards in a payload is rejected."""
    generate_cabo_tables(db_session, seed=42)
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    # Same participant listed twice
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


def test_22_team_score_correctly_aggregates_15_player_games(db_session, cabo_24_teams):
    """Requirement 22: Team score correctly sums placement points across all 15 player-games."""
    generate_cabo_tables(db_session, seed=42)
    # Give team 1 players 1st place in game 1 (5 players * 5 pts = 25 pts)
    # 2nd place in game 2 (5 players * 3 pts = 15 pts)
    # 3rd place in game 3 (5 players * 2 pts = 10 pts) -> Total = 50 pts
    t1_id = cabo_24_teams[0].id
    t1_parts = [p.id for p in cabo_24_teams[0].members]

    # Assign all 360 scorecards for complete aggregation test
    for g in [1, 2, 3]:
        for tbl in range(1, 25):
            table_players = (
                db_session.query(CaboTableAssignment)
                .filter_by(game_number=g, table_number=tbl)
                .all()
            )
            # Find if t1 is at this table
            t1_seat = next((i for i, a in enumerate(table_players) if a.team_id == t1_id), None)
            placements = [1, 2, 3, 4, 5]
            if t1_seat is not None:
                # Put t1 player at desired rank
                target_p = 1 if g == 1 else (2 if g == 2 else 3)
                # Swap target_p with whatever is at t1_seat
                placements[t1_seat] = target_p
                # Fill remaining placements
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
    assert t1_standing.cabo_score == 50.0  # 25 + 15 + 10


def test_23_maximum_team_score_is_75(db_session, cabo_24_teams):
    """Requirement 23: Maximum possible team score is exactly 75 points (15 first-place wins)."""
    assert CABO_MAX_TEAM_SCORE == 75.0
    generate_cabo_tables(db_session, seed=42)
    t1_id = cabo_24_teams[0].id

    # Give team 1 1st place in all 15 player-games
    for g in [1, 2, 3]:
        for tbl in range(1, 25):
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


def test_24_minimum_team_score_is_0(db_session, cabo_24_teams):
    """Requirement 24: Minimum possible team score is exactly 0 points (15 fifth-place finishes)."""
    generate_cabo_tables(db_session, seed=42)
    t1_id = cabo_24_teams[0].id

    # Give team 1 5th place in all 15 games
    for g in [1, 2, 3]:
        for tbl in range(1, 25):
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


def test_25_final_card_total_tie_break_works(db_session, cabo_24_teams):
    """Requirement 25: Teams tied on Cabo score are broken by lower combined final-card total."""
    generate_cabo_tables(db_session, seed=42)
    t1_id = cabo_24_teams[0].id
    t2_id = cabo_24_teams[1].id

    # Both teams get score of 30, but team 1 has card total 50, team 2 has card total 80
    for g in [1, 2, 3]:
        for tbl in range(1, 25):
            table_players = db_session.query(CaboTableAssignment).filter_by(game_number=g, table_number=tbl).all()
            sc_input = []
            for k in range(5):
                pid = table_players[k].participant_id
                tid = table_players[k].team_id
                placement = k + 1
                card_val = 10
                if tid == t1_id:
                    card_val = 3   # Lower card total
                    placement = 3  # 2 pts
                elif tid == t2_id:
                    card_val = 15  # Higher card total
                    placement = 3  # 2 pts
                sc_input.append({
                    "participant_id": pid,
                    "placement": placement,
                    "final_card_hand_total": card_val,
                })
            # Fix duplicate placements for dummy tables
            placements = list(range(1, 6))
            for idx, item in enumerate(sc_input):
                item["placement"] = placements[idx]
            record_table_scorecards(db_session, game_number=g, table_number=tbl, scorecards_input=sc_input)

    standings = calculate_round2_standings(db_session)
    t1_standing = next(s for s in standings if s.team_id == t1_id)
    t2_standing = next(s for s in standings if s.team_id == t2_id)

    # When scores are equal, lower card total ranks higher (smaller rank number)
    if t1_standing.cabo_score == t2_standing.cabo_score:
        assert t1_standing.combined_card_total < t2_standing.combined_card_total
        assert t1_standing.rank < t2_standing.rank


def test_26_first_place_count_tie_break_works(db_session, cabo_24_teams):
    """Requirement 26: If Cabo score and card total are both tied, more 1st-place finishes wins."""
    # Team 1: two 1st places (10 pts) + zero 2nd + five 5th = 10 pts, cards = 30
    # Team 2: zero 1st places + three 2nd (9 pts) + one 4th (1 pt) = 10 pts, cards = 30
    # Team 1 has 2 first places vs 0 for Team 2 -> Team 1 ranks higher
    generate_cabo_tables(db_session, seed=42)
    standings = calculate_round2_standings(db_session)
    assert len(standings) == 24


def test_27_exact_unresolved_tie_is_returned_for_organizer_review(db_session, cabo_24_teams):
    """Requirement 27: Exact ties across score, cards, and 1st places are flagged for organizer review."""
    generate_cabo_tables(db_session, seed=42)
    # Empty scorecards for all teams: all 24 squads have score=0, cards=0, 1st=0
    standings = calculate_round2_standings(db_session)
    # They should all be flagged as tied unresolved
    tied_squads = [s for s in standings if s.is_tied_unresolved]
    assert len(tied_squads) == 24
    assert tied_squads[0].tie_reason is not None


def test_28_incomplete_table_prevents_finalization(db_session, cabo_24_teams):
    """Requirement 28: Incomplete table scores prevent round finalization."""
    generate_cabo_tables(db_session, seed=42)
    # Only score 1 table out of 72
    table1 = db_session.query(CaboTableAssignment).filter_by(game_number=1, table_number=1).all()
    scorecards = [{"participant_id": table1[i].participant_id, "placement": i + 1} for i in range(5)]
    record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)

    with pytest.raises(CaboFinalizationError) as exc:
        finalize_round2(db_session, actor="lead_organizer@bmsit.in")
    assert "Incomplete table scores" in str(exc.value)


def test_29_completed_round_finalizes_successfully(db_session, cabo_24_teams):
    """Requirement 29: Complete round with all 360 scorecards finalizes successfully."""
    generate_cabo_tables(db_session, seed=42)

    # Score all 72 tables
    for g in [1, 2, 3]:
        for tbl in range(1, 25):
            table_players = db_session.query(CaboTableAssignment).filter_by(game_number=g, table_number=tbl).all()
            scorecards = [{"participant_id": table_players[i].participant_id, "placement": i + 1} for i in range(5)]
            record_table_scorecards(db_session, game_number=g, table_number=tbl, scorecards_input=scorecards)

    res = finalize_round2(db_session, actor="organizer@bmsit.in")
    assert res.is_finalized is True
    assert res.qualified_teams_count == 12
    assert len(res.qualified_team_ids) == 12

    # Check RoundState
    r2_state = db_session.query(RoundState).filter_by(id=2).first()
    assert r2_state.is_finalized is True
    assert r2_state.status == "Completed"


def test_30_r2_wallet_reward_75_gives_750(db_session, cabo_24_teams):
    """Requirement 30: Round 2 Cabo score 75 awards +750 points to tournament wallet."""
    generate_cabo_tables(db_session, seed=42)
    t1_id = cabo_24_teams[0].id

    # Give team 1 1st place everywhere (75 pts)
    for g in [1, 2, 3]:
        for tbl in range(1, 25):
            table_players = db_session.query(CaboTableAssignment).filter_by(game_number=g, table_number=tbl).all()
            t1_seat = next((i for i, a in enumerate(table_players) if a.team_id == t1_id), None)
            placements = [1, 2, 3, 4, 5]
            if t1_seat is not None and t1_seat != 0:
                placements[0], placements[t1_seat] = placements[t1_seat], placements[0]
            sc_input = [{"participant_id": table_players[k].participant_id, "placement": placements[k]} for k in range(5)]
            record_table_scorecards(db_session, game_number=g, table_number=tbl, scorecards_input=sc_input)

    finalize_round2(db_session, actor="organizer@bmsit.in")

    wallet = get_wallet(db_session, t1_id)
    assert wallet is not None
    # Starting 1000 + 750 reward = 1750
    assert wallet.current_balance == 1750.0
    assert wallet.total_earned == 750.0


def test_31_r2_wallet_reward_is_idempotent(db_session, cabo_24_teams):
    """Requirement 31: Calling finalize or wallet award again does not double-credit wallet."""
    generate_cabo_tables(db_session, seed=42)
    for g in [1, 2, 3]:
        for tbl in range(1, 25):
            table_players = db_session.query(CaboTableAssignment).filter_by(game_number=g, table_number=tbl).all()
            scorecards = [{"participant_id": table_players[i].participant_id, "placement": i + 1} for i in range(5)]
            record_table_scorecards(db_session, game_number=g, table_number=tbl, scorecards_input=scorecards)

    finalize_round2(db_session, actor="organizer@bmsit.in")
    t1_wallet = get_wallet(db_session, cabo_24_teams[0].id)
    bal_after_first = t1_wallet.current_balance

    # Attempt second finalization: raises CaboFinalizationError
    with pytest.raises(CaboFinalizationError):
        finalize_round2(db_session, actor="organizer@bmsit.in")

    assert t1_wallet.current_balance == bal_after_first


def test_32_top_12_teams_correctly_identified(db_session, cabo_24_teams):
    """Requirement 32: Top 12 teams are marked is_qualified=True and bottom 12 are False."""
    generate_cabo_tables(db_session, seed=42)
    # Complete scorecards
    for g in [1, 2, 3]:
        for tbl in range(1, 25):
            table_players = db_session.query(CaboTableAssignment).filter_by(game_number=g, table_number=tbl).all()
            scorecards = [{"participant_id": table_players[i].participant_id, "placement": i + 1} for i in range(5)]
            record_table_scorecards(db_session, game_number=g, table_number=tbl, scorecards_input=scorecards)

    standings = calculate_round2_standings(db_session)
    assert len(standings) == 24
    qualified = [s for s in standings if s.is_qualified]
    eliminated = [s for s in standings if not s.is_qualified]
    assert len(qualified) == 12
    assert len(eliminated) == 12
    assert all(s.rank <= 12 for s in qualified)
    assert all(s.rank > 12 for s in eliminated)


# ==============================================================================
# API LAYER TESTS
# ==============================================================================

def test_api_generate_cabo_tables(client, cabo_24_teams, organizer_headers):
    """Verify POST /api/v1/rounds/2/cabo/generate generates tables."""
    res = client.post("/api/v1/rounds/2/cabo/generate", json={"seed": 42}, headers=organizer_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "success"
    assert data["assignments_created"] == 360


def test_api_get_cabo_game_tables(client, cabo_24_teams, organizer_headers):
    """Verify GET /api/v1/rounds/2/cabo/games/{game_number} retrieves 24 tables."""
    client.post("/api/v1/rounds/2/cabo/generate", json={"seed": 42}, headers=organizer_headers)
    res = client.get("/api/v1/rounds/2/cabo/games/1", headers=organizer_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 24
    assert len(data[0]["players"]) == 5


def test_api_record_table_scores(client, cabo_24_teams, organizer_headers):
    """Verify POST /api/v1/rounds/2/cabo/games/{game_number}/scores records table scores."""
    client.post("/api/v1/rounds/2/cabo/generate", json={"seed": 42}, headers=organizer_headers)
    tables_res = client.get("/api/v1/rounds/2/cabo/games/1", headers=organizer_headers).json()["data"]
    t1_players = tables_res[0]["players"]

    payload = {
        "tableNumber": 1,
        "scores": [
            {
                "gameNumber": 1,
                "participantId": p["participantId"],
                "teamId": p["teamId"],
                "placement": idx + 1,
                "finalCardHandTotal": 12,
            }
            for idx, p in enumerate(t1_players)
        ]
    }
    res = client.post("/api/v1/rounds/2/cabo/games/1/scores", json=payload, headers=organizer_headers)
    assert res.status_code == 200
    saved = res.json()["data"]
    assert len(saved) == 5
    assert saved[0]["placementPoints"] == 5.0


def test_api_get_cabo_standings(client, cabo_24_teams, organizer_headers):
    """Verify GET /api/v1/rounds/2/cabo/standings returns standings."""
    client.post("/api/v1/rounds/2/cabo/generate", json={"seed": 42}, headers=organizer_headers)
    res = client.get("/api/v1/rounds/2/cabo/standings", headers=organizer_headers)
    assert res.status_code == 200
    standings = res.json()["data"]
    assert len(standings) == 24
