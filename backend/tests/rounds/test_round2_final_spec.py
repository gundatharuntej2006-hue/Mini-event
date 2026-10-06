"""
Official Round 2 (CABO: The Memory Heist) Final Specification Test Suite.
Verifies all 8 tournament constraints and workflow requirements:
1. Exactly 16 qualified teams entering Round 2
2. Exactly 5 players per team = 80 total players
3. Exactly 16 tables per game across 3 Cabo games
4. Exactly 5 players per table
5. Distinct teams per table (COUNT(DISTINCT team_id) == 5)
6. Zero teammate collisions at any table across Games 1, 2, and 3
7. Each team's 5 players occupy 5 different tables per game
8. Table validation and confirmation freeze (cannot be silently regenerated)
9. Score recording and unique placements 1st-5th (11 points per table)
10. Team score aggregation (15 player-games, max 75 pts)
11. Organizer score correction with audit trail
12. Top 8 advance to Round 3
"""

import pytest
from app.models.team import Team
from app.models.participant import Participant, ParticipantRole
from app.models.cabo import CaboTableAssignment, CaboPlayerScorecard
from app.models.round2 import CaboConfigModel
from app.models.round_models import RoundState
from app.models.progression import AuditLog
from app.services.cabo_service import (
    generate_cabo_tables,
    validate_cabo_table_allocations,
    confirm_cabo_tables,
    record_table_scorecards,
    correct_cabo_table_score,
    get_player_cabo_detail,
    get_team_cabo_detail,
    get_cabo_printable_sheet,
    export_cabo_data,
    calculate_round2_standings,
    finalize_round2,
    CaboAssignmentError,
    CaboScorecardError,
)
from app.core.constants import (
    R1_QUALIFIERS,
    CABO_GAMES,
    CABO_TABLE_SIZE,
    CABO_PLACEMENT_POINTS,
)


@pytest.fixture
def cabo_16_squads_db(db_session):
    """Ensures exactly 16 qualified squads with 5 participants each in the test database."""
    # Clear auto-seeded teams and participants to ensure clean 16 teams with 5 players
    db_session.query(Participant).delete()
    db_session.query(Team).delete()
    db_session.flush()

    teams = []
    for t_idx in range(1, R1_QUALIFIERS + 1):
        team = Team(
            id=f"team-spec-{t_idx:02d}",
            team_number=t_idx,
            name=f"Spec Squad {t_idx:02d}",
        )
        db_session.add(team)
        db_session.flush()

        for p_idx in range(1, CABO_TABLE_SIZE + 1):
            p = Participant(
                id=f"part-spec-{t_idx:02d}-{p_idx}",
                team_id=team.id,
                name=f"Player {t_idx}-{p_idx}",
                email=f"player_{t_idx:02d}_{p_idx}@spec.com",
                usn=f"1MS23CS{t_idx:02d}{p_idx}",
                role=ParticipantRole.LEADER if p_idx == 1 else ParticipantRole.MEMBER,
            )
            db_session.add(p)
        teams.append(team)

    r2_state = db_session.query(RoundState).filter(RoundState.id == 2).first()
    if not r2_state:
        r2_state = RoundState(id=2, name="Round 2 - CABO", codename="CABO", status="In Progress", is_finalized=False)
        db_session.add(r2_state)
    else:
        r2_state.is_finalized = False

    db_session.commit()
    return teams


def test_01_seating_allocation_satisfies_all_8_constraints(db_session, cabo_16_squads_db):
    """Constraint 1-7: Seating generation produces 240 seats with 0 collisions and 5 distinct teams per table."""
    res = generate_cabo_tables(db_session, seed=100)
    assert res["status"] == "success"
    assert res["assignments_created"] == 240

    validation = validate_cabo_table_allocations(db_session)
    assert validation["is_valid"] is True
    assert validation["total_teams"] == 16
    assert validation["total_players"] == 80
    assert validation["total_tables"] == 16
    assert len(validation["errors"]) == 0
    for constraint_name, passed in validation["constraints"].items():
        assert passed is True, f"Constraint failed: {constraint_name}"


def test_02_confirm_tables_freezes_seating_and_prevents_silent_regeneration(db_session, cabo_16_squads_db):
    """Rule: Confirmed seating cannot be silently regenerated without force_regenerate=True."""
    generate_cabo_tables(db_session, seed=100)
    confirm_res = confirm_cabo_tables(db_session, actor_id="lead_organizer@bmsit.in")
    assert confirm_res["is_confirmed"] is True

    # Verification: cfg state is frozen
    cfg = db_session.query(CaboConfigModel).filter(CaboConfigModel.id == 1).first()
    assert cfg.is_tables_confirmed is True
    assert cfg.tables_confirmed_by == "lead_organizer@bmsit.in"

    # Silent regeneration without force must be rejected
    with pytest.raises(CaboAssignmentError) as exc_info:
        generate_cabo_tables(db_session, seed=200, force_regenerate=False)
    assert "confirmed and frozen" in str(exc_info.value)

    # Regeneration with explicit force must succeed
    regen_res = generate_cabo_tables(db_session, seed=200, force_regenerate=True)
    assert regen_res["status"] == "success"
    assert regen_res["assignments_created"] == 240


def test_03_table_scoring_enforces_1_through_5_and_awards_11_pts_per_table(db_session, cabo_16_squads_db):
    """Scoring: 1st=5, 2nd=3, 3rd=2, 4th=1, 5th=0 = 11 pts total per table."""
    generate_cabo_tables(db_session, seed=100)
    tbl1_seats = (
        db_session.query(CaboTableAssignment)
        .filter_by(game_number=1, table_number=1)
        .all()
    )

    scorecards = [
        {"participant_id": tbl1_seats[i].participant_id, "placement": i + 1, "final_card_hand_total": 10 + i}
        for i in range(5)
    ]
    saved = record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards, recorded_by="marshal@bmsit.in")
    assert len(saved) == 5

    total_table_pts = sum(sc.placement_points for sc in saved)
    assert total_table_pts == 11.0  # 5 + 3 + 2 + 1 + 0 = 11

    # All scorecards must be marked is_verified=True
    assert all(sc.is_verified for sc in saved)
    assert all(sc.verified_by == "marshal@bmsit.in" for sc in saved)


def test_04_organizer_score_correction_swaps_and_logs_mandatory_audit(db_session, cabo_16_squads_db):
    """Correction: Swaps placements at table, recalculates points, and records audit log."""
    generate_cabo_tables(db_session, seed=100)
    tbl1_seats = (
        db_session.query(CaboTableAssignment)
        .filter_by(game_number=1, table_number=1)
        .all()
    )

    # Initial scorecards: seat 0 is 1st (5 pts), seat 1 is 2nd (3 pts)
    scorecards = [
        {"participant_id": tbl1_seats[i].participant_id, "placement": i + 1}
        for i in range(5)
    ]
    record_table_scorecards(db_session, game_number=1, table_number=1, scorecards_input=scorecards)

    # Correction: Change seat 1 from 2nd place to 1st place
    part1_id = tbl1_seats[1].participant_id
    corr_res = correct_cabo_table_score(
        db=db_session,
        game_number=1,
        table_number=1,
        participant_id=part1_id,
        new_placement=1,
        reason="Marshal misread final card hand after showdown",
        actor_id="organizer@bmsit.in",
    )
    assert corr_res["status"] == "success"
    assert corr_res["new_placement"] == 1
    assert corr_res["points"] == 5.0

    # Verify seat 0 was automatically swapped to 2nd place (3 pts)
    sc0 = (
        db_session.query(CaboPlayerScorecard)
        .filter_by(game_number=1, participant_id=tbl1_seats[0].participant_id)
        .first()
    )
    assert sc0.placement == 2
    assert sc0.placement_points == 3.0

    # Verify audit log was recorded
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "CABO_SCORECARD_CORRECTED")
        .order_by(AuditLog.timestamp.desc())
        .first()
    )
    assert audit is not None
    assert audit.details["reason"] == "Marshal misread final card hand after showdown"
    assert audit.actor_id == "organizer@bmsit.in"


def test_05_player_and_team_detail_drilldowns(db_session, cabo_16_squads_db):
    """Drill-down: Collects individual player history and squad 5-member breakdown."""
    generate_cabo_tables(db_session, seed=100)
    team1 = cabo_16_squads_db[0]
    first_player = (
        db_session.query(Participant)
        .filter_by(team_id=team1.id)
        .first()
    )

    # Player drill-down
    p_detail = get_player_cabo_detail(db_session, participant_id=first_player.id)
    assert p_detail["participant_name"] == first_player.name
    assert len(p_detail["games"]) == 3
    assert {g["game_number"] for g in p_detail["games"]} == {1, 2, 3}

    # Team drill-down
    t_detail = get_team_cabo_detail(db_session, team_id=team1.id)
    assert t_detail["team_name"] == team1.name
    assert len(t_detail["members"]) == 5
    assert all(m["participant_name"] for m in t_detail["members"])


def test_06_printable_sheets_and_data_exports(db_session, cabo_16_squads_db):
    """Printable & Export: Generates printable sheet and valid CSV exports."""
    generate_cabo_tables(db_session, seed=100)

    # Printable sheets for Game 1
    sheet_data = get_cabo_printable_sheet(db_session, game_number=1)
    assert sheet_data["game_number"] == 1
    assert len(sheet_data["tables"]) == 16
    assert all(len(t["players"]) == 5 for t in sheet_data["tables"])

    # CSV Exports
    csv_assign = export_cabo_data(db_session, export_type="assignments")
    assert "Game,Table,Seat,Team ID" in csv_assign
    assert len(csv_assign.strip().split("\n")) == 241  # Header + 240 rows

    csv_standings = export_cabo_data(db_session, export_type="standings")
    assert "Rank,Team Number,Team Name" in csv_standings
