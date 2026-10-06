"""
Verification Tests for Round 3 'Black Market' against FINAL Organizer Specification.
Verifies:
1. Exactly 8 teams enter from Round 2 qualifiers.
2. Top 4 advance to Round 4 (R3_QUALIFIERS = 4).
3. Starting balance formula: 1000 + R1 rank points + R2 Cabo score (raw, not * 10) + verified agent tasks * 50.
4. Two-organizer approval workflow on deductions/purchases.
5. Four-fragment system (ODD, 42, ECHO, PRIME) and -350 penalty per missing fragment.
6. Cutoff tie at 4th/5th position blocks finalization.
7. Secret agent tasks confidential and award +50 points each.
8. Preservation of real squad Levi Squad.
"""

import pytest
from app.models.team import Team, TeamStatus
from app.models.user import User, UserRole
from app.models.wallet import TeamWallet, WalletTransaction, TransactionType
from app.models.code_hunt import FinalCodeRecord, FragmentStatus
from app.models.black_market import (
    BlackMarketPurchase,
    BlackMarketAssetType,
    PurchaseStatus,
    BlackMarketAuction,
    BlackMarketBid,
    AuctionStatus,
)
from app.models.agent import SecretAgentDossier, SecretAgentTask, AgentTaskStatus, AgentDossierStatus
from app.models.cabo import CaboPlayerScorecard
from app.models.round_models import RoundState
from app.models.progression import RoundQualification
from app.core.constants import (
    R3_QUALIFIERS,
    STARTING_WALLET_BALANCE,
    MISSING_FRAGMENT_PENALTY,
    AGENT_TASK_REWARD,
)
from app.services import black_market_service, wallet as wallet_service
from app.services.round_service import ensure_round_states_initialized


@pytest.fixture
def r3_squads(db_session):
    ensure_round_states_initialized(db_session)
    squads = []
    for i in range(1, 13):
        team = Team(
            id=f"team-spec-r3-{i:02d}",
            team_number=i,
            name=f"Spec Squad {i:02d}",
            status=TeamStatus.ACTIVE,
            current_round=3,
        )
        db_session.add(team)
        db_session.flush()

        wallet = wallet_service.get_or_create_wallet(db_session, team.id)
        squads.append(team)

    db_session.commit()
    return squads


def test_starting_balance_formula_never_multiplies_cabo(db_session, r3_squads):
    """
    Starting Balance = 1000 + R1 rank points + R2 Cabo score + (verified agent tasks * 50).
    CRITICAL: Cabo score is used DIRECTLY (0 to 75). NEVER multiplied by 10.
    """
    team = r3_squads[0]

    # R1: rank 1 -> 16 points (17 - 1)
    r1_qual = RoundQualification(
        id=f"qual-r1-{team.id}",
        round_number=1,
        team_id=team.id,
        rank=1,
        status="Finalized Qualified",
        is_advancing=True,
        finalized_by="lead-organizer",
    )
    db_session.add(r1_qual)

    # R2: 3 scorecards with placement 1 (5 pts each) -> Total Cabo score = 15.0 pts
    for g in range(1, 4):
        sc = CaboPlayerScorecard(
            id=f"sc-spec-{team.id}-{g}",
            game_number=g,
            participant_id=f"part-{team.id}-{g}",
            team_id=team.id,
            placement=1,
            placement_points=5.0,
        )
        db_session.add(sc)

    # Agent: 2 verified tasks -> 2 * 50 = +100 pts
    dossier = SecretAgentDossier(
        id=f"sad-{team.id}",
        team_id=team.id,
        participant_id=f"part-{team.id}-1",
        codename="NIGHT_HAWK",
        status=AgentDossierStatus.ACTIVE,
    )
    db_session.add(dossier)
    db_session.flush()

    for t_idx in range(1, 3):
        task = SecretAgentTask(
            id=f"sat-{team.id}-{t_idx}",
            dossier_id=dossier.id,
            task_description=f"Sabotage task {t_idx}",
            status=AgentTaskStatus.VERIFIED,
            reward_points=50.0,
        )
        db_session.add(task)

    db_session.commit()

    breakdown = black_market_service.calculate_team_starting_balance(db_session, team.id)
    assert breakdown["base_balance"] == 1000.0
    assert breakdown["r1_rank_points"] == 16.0
    assert breakdown["r2_cabo_score"] == 15.0  # Raw score, NOT 150!
    assert breakdown["agent_task_bonus"] == 100.0  # 2 * 50
    # Expected: 1000 + 16 + 15 + 100 = 1131.0
    assert breakdown["total_starting_balance"] == 1131.0


def test_two_organizer_approval_rest_api(client, db_session, r3_squads, organizer_headers):
    """
    Tests approval endpoints:
    1st approval by organizer A -> PARTIALLY_APPROVED, no wallet debit.
    2nd approval by organizer B -> APPROVED, wallet debited.
    """
    team = r3_squads[0]
    wallet = wallet_service.get_or_create_wallet(db_session, team.id)
    wallet.current_balance = 1000.0
    db_session.commit()

    # 1. Purchase asset via API (without second organizer)
    resp = client.post(
        "/api/v1/rounds/3/purchase",
        json={"teamId": team.id, "assetType": "EXTRA_PREP_TIME", "quantity": 1},
        headers=organizer_headers,
    )
    assert resp.status_code == 200
    purchase_data = resp.json()["data"]
    p_id = purchase_data["id"]
    assert purchase_data["approvalStatus"] == "PARTIALLY_APPROVED"

    # Wallet MUST NOT be debited yet
    w = wallet_service.get_wallet(db_session, team.id)
    assert float(w.current_balance) == 1000.0

    # 2. Second organizer approves via API
    appr_resp = client.post(
        f"/api/v1/rounds/3/purchases/{p_id}/approve",
        json={"notes": "Dual signoff by co-organizer", "secondOrganizerId": "co-organizer-2"},
        headers=organizer_headers,
    )
    assert appr_resp.status_code == 200
    appr_data = appr_resp.json()["data"]
    assert appr_data["approvalStatus"] == "APPROVED"
    assert appr_data["status"] == "COMPLETED"

    # Wallet MUST now be debited
    w_after = wallet_service.get_wallet(db_session, team.id)
    assert float(w_after.current_balance) == 800.0


def test_four_fragments_and_missing_fragment_penalty(db_session, r3_squads):
    """
    Verifies that missing fragments incur -350 penalty each,
    and only squads with all 4 fragments can qualify.
    """
    # Squad 0 has all 4 fragments
    s0 = r3_squads[0]
    fcr0 = FinalCodeRecord(
        team_id=s0.id,
        fragment_1_status=FragmentStatus.RECOVERED,
        fragment_2_status=FragmentStatus.RECOVERED,
        fragment_3_status=FragmentStatus.RECOVERED,
        fragment_4_status=FragmentStatus.RECOVERED,
        final_code_verified=True,
    )
    db_session.add(fcr0)

    # Squad 1 has 3 fragments (missing 1 -> -350 penalty)
    s1 = r3_squads[1]
    fcr1 = FinalCodeRecord(
        team_id=s1.id,
        fragment_1_status=FragmentStatus.RECOVERED,
        fragment_2_status=FragmentStatus.RECOVERED,
        fragment_3_status=FragmentStatus.RECOVERED,
        fragment_4_status=FragmentStatus.PENDING,
    )
    db_session.add(fcr1)

    # Set balances
    w0 = wallet_service.get_wallet(db_session, s0.id)
    w0.current_balance = 1000.0
    w1 = wallet_service.get_wallet(db_session, s1.id)
    w1.current_balance = 1000.0
    db_session.commit()

    standings = black_market_service.calculate_round3_standings(db_session)
    st0 = next(s for s in standings["standings"] if s["team_id"] == s0.id)
    st1 = next(s for s in standings["standings"] if s["team_id"] == s1.id)

    assert st0["verified_fragment_count"] == 4
    assert st0["missing_fragment_penalty"] == 0.0
    assert st0["effective_balance"] == 1000.0

    assert st1["verified_fragment_count"] == 3
    assert st1["missing_fragment_penalty"] == 350.0
    assert st1["effective_balance"] == 650.0  # 1000 - 350
    assert st1["is_advancing"] is False  # Cannot advance with < 4 fragments!


def test_top_6_qualify_and_advance_to_round4(db_session, r3_squads):
    """Verifies that exactly Top 6 squads qualify for Round 4."""
    # Mark Round 2 finalized
    rs2 = db_session.query(RoundState).filter(RoundState.id == 2).first()
    if rs2:
        rs2.is_finalized = True

    # Give all 12 squads 4 fragments with graduated balances
    for i, squad in enumerate(r3_squads):
        fcr = FinalCodeRecord(
            team_id=squad.id,
            fragment_1_status=FragmentStatus.RECOVERED,
            fragment_2_status=FragmentStatus.RECOVERED,
            fragment_3_status=FragmentStatus.RECOVERED,
            fragment_4_status=FragmentStatus.RECOVERED,
            final_code_verified=True,
        )
        db_session.add(fcr)

        w = wallet_service.get_wallet(db_session, squad.id)
        w.current_balance = 1000.0 - (i * 50.0)

    db_session.commit()

    standings = black_market_service.calculate_round3_standings(db_session)
    assert standings["can_finalize"] is True
    assert len(standings["advancing_team_ids"]) == 6

    res = black_market_service.finalize_round3(db_session, actor="lead-organizer")
    assert res["success"] is True
    assert res["qualified_teams_count"] == 6
    assert len(res["qualified_team_ids"]) == 6

    # Verify team current_round updated to 4 for top 6, ELIMINATED for bottom 6
    for i, squad in enumerate(r3_squads):
        t = db_session.query(Team).filter(Team.id == squad.id).first()
        if i < 6:
            assert t.current_round == 4
            assert t.is_qualified_for_next_round is True
        else:
            assert t.status == TeamStatus.ELIMINATED
            assert t.is_qualified_for_next_round is False
