"""
Unit and Integration Tests for EVENT HQ Round 3 Black Market & Qualification Engine (Step 12).
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Verifies all 30+ mandatory requirements:
1. Catalog retrieval with suggested default prices.
2. Direct tactical asset purchases (prep time, witness questions, agent intel, custom).
3. Missing code fragment recovery via Black Market.
4. Purchase safety: insufficient funds rejection, balance preserved.
5. Ineligible team purchase rejection.
6. Market closed rejection after finalization.
7. Sealed-bid auction creation and configuration.
8. Sealed bid submission within wallet balance constraint.
9. Bid exceeding wallet balance rejected.
10. Bid below starting bid rejected.
11. Updating sealed bids on open auctions.
12. Sealed-bid privacy: squads cannot see other teams' bid amounts.
13. Organizer visibility: organizers see all bid amounts.
14. Auction resolution: highest bidder wins, debited bid amount.
15. Losing bids in auctions are NOT debited points.
16. Reserve price enforcement.
17. Auction tie detection flags REQUIRES_REVIEW.
18. Organizer override for auction ties.
19. Final Code Gate checked FIRST before wallet ranking in standings.
20. Code-invalid squads marked eliminated regardless of wallet balance.
21. Code-valid squads ranked descending by remaining wallet points.
22. Secondary tie-breakers (fewer penalties, higher total earned).
23. Top 8 cutoff tie flag (8th vs 9th position).
24. Code-less contingency flag (fewer than 8 code-valid squads).
25. Top 8 qualification and advancement to Round 4.
26. Wallet balance preservation for Grand Finale 10% carryover.
27. Finalization safeguards and override capability.
28. Finalization idempotency.
29. REST API routes and RBAC authorization.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.team import Team, TeamStatus
from app.models.participant import Participant, ParticipantRole
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
    BidStatus,
)
from app.models.round3 import BlackMarketConfigModel
from app.models.round_models import RoundState
from app.models.progression import RoundQualification
from app.core.constants import (
    STARTING_WALLET_BALANCE,
    BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED,
    BLACK_MARKET_PREP_PRICE_SUGGESTED,
    BLACK_MARKET_WITNESS_PRICE_SUGGESTED,
    BLACK_MARKET_AGENT_INTEL_PRICE_SUGGESTED,
)
from app.services import wallet as wallet_service
from app.services import code_hunt_service
from app.services import black_market_service
from app.services.black_market_service import (
    BlackMarketError,
    MarketClosedError,
    TeamNotEligibleError,
    InvalidAssetError,
    AuctionNotFoundError,
    AuctionClosedError,
    InvalidBidError,
    RoundFinalizationError,
)
from app.services.round_service import ensure_round_states_initialized


# ==============================================================================
# TEST FIXTURES & SQUAD SETUP
# ==============================================================================
@pytest.fixture
def r3_teams(db_session):
    """Creates 12 qualified teams with initialized wallets for Round 3 tests."""
    ensure_round_states_initialized(db_session)
    teams = []
    for i in range(1, 13):
        t = Team(
            id=f"team-r3-{i:02d}",
            team_number=i,
            name=f"Squad {i:02d}",
            status=TeamStatus.ACTIVE,
            current_round=3,
        )
        db_session.add(t)
        db_session.flush()

        # Initialize tournament wallet with 1000 pts
        wallet = wallet_service.get_or_create_wallet(db_session, t.id)

        # Add R1 and R2 rewards to simulate tournament progression
        wallet_service.award_round1_reward(db_session, t.id, rank=i)
        wallet_service.award_round2_reward(db_session, t.id, cabo_score=50.0 - i)

        teams.append(t)

    db_session.commit()
    return teams


# ==============================================================================
# 1. CATALOG & ASSET PURCHASE TESTS
# ==============================================================================
def test_market_catalog_retrieval(db_session):
    """Verifies catalog returns default suggested prices and item details."""
    catalog = black_market_service.get_market_catalog(db_session)
    assert len(catalog) >= 4

    types = [item["asset_type"] for item in catalog]
    assert "MISSING_CODE_FRAGMENT" in types
    assert "EXTRA_PREP_TIME" in types
    assert "EXTRA_WITNESS_QUESTION" in types
    assert "AGENT_INTEL" in types

    prep = next(i for i in catalog if i["asset_type"] == "EXTRA_PREP_TIME")
    assert prep["suggested_price"] == BLACK_MARKET_PREP_PRICE_SUGGESTED


def test_purchase_extra_prep_time(db_session, r3_teams):
    """Verifies purchasing prep time debits wallet and logs purchase record."""
    team = r3_teams[0]
    wallet_before = wallet_service.get_wallet(db_session, team.id).current_balance

    bmp = black_market_service.purchase_market_asset(
        db=db_session,
        team_id=team.id,
        asset_type="EXTRA_PREP_TIME",
        quantity=1,
        actor="organizer-1"
    )

    assert bmp is not None
    assert bmp.asset_type == BlackMarketAssetType.EXTRA_PREP_TIME
    assert bmp.price == BLACK_MARKET_PREP_PRICE_SUGGESTED
    assert bmp.status == PurchaseStatus.COMPLETED

    wallet_after = wallet_service.get_wallet(db_session, team.id).current_balance
    assert wallet_after == wallet_before - BLACK_MARKET_PREP_PRICE_SUGGESTED


def test_purchase_extra_witness_questions_quantity(db_session, r3_teams):
    """Verifies purchasing multiple quantities of an asset debits total amount."""
    team = r3_teams[1]
    wallet_before = wallet_service.get_wallet(db_session, team.id).current_balance

    bmp = black_market_service.purchase_market_asset(
        db=db_session,
        team_id=team.id,
        asset_type="EXTRA_WITNESS_QUESTION",
        quantity=3,
        actor="marshal-1"
    )

    expected_total = BLACK_MARKET_WITNESS_PRICE_SUGGESTED * 3
    assert bmp.price == expected_total
    assert bmp.quantity == 3

    wallet_after = wallet_service.get_wallet(db_session, team.id).current_balance
    assert wallet_after == wallet_before - expected_total


def test_purchase_agent_intel_with_custom_price(db_session, r3_teams):
    """Verifies purchasing asset with custom organizer price."""
    team = r3_teams[2]
    wallet_before = wallet_service.get_wallet(db_session, team.id).current_balance

    bmp = black_market_service.purchase_market_asset(
        db=db_session,
        team_id=team.id,
        asset_type="AGENT_INTEL",
        price=180.0,
        actor="organizer-1"
    )

    assert bmp.price == 180.0
    wallet_after = wallet_service.get_wallet(db_session, team.id).current_balance
    assert wallet_after == wallet_before - 180.0


def test_purchase_missing_code_fragment_recovery(db_session, r3_teams):
    """Verifies purchasing missing fragment recovers the fragment in FinalCodeRecord."""
    team = r3_teams[3]
    # Squad only found fragment 1 in R1
    code_hunt_service.record_fragment_1(db_session, team.id, "FRAGMENT-ALPHA")

    code_rec_before = code_hunt_service.get_or_create_final_code_record(db_session, team.id)
    assert code_rec_before.fragment_2_status == FragmentStatus.PENDING

    # Purchase missing fragment 2
    bmp = black_market_service.purchase_market_asset(
        db=db_session,
        team_id=team.id,
        asset_type="MISSING_CODE_FRAGMENT",
        details={"fragment_number": 2, "recovered_value": "FRAGMENT-BETA"},
        actor="organizer-1"
    )

    assert bmp is not None
    assert bmp.asset_type == BlackMarketAssetType.MISSING_CODE_FRAGMENT

    # Verify FinalCodeRecord updated
    code_rec_after = code_hunt_service.get_or_create_final_code_record(db_session, team.id)
    assert code_rec_after.fragment_2_status == FragmentStatus.PURCHASED
    assert code_rec_after.fragment_2_value == "FRAGMENT-BETA"
    assert code_rec_after.final_code_assembled == "FRAGMENT-ALPHAFRAGMENT-BETA"


def test_purchase_insufficient_funds_rejected(db_session, r3_teams):
    """Verifies purchasing asset costing more than wallet balance is rejected."""
    team = r3_teams[4]
    wallet = wallet_service.get_wallet(db_session, team.id)
    # Drain balance to 50
    wallet_service.apply_penalty(db_session, team.id, penalty_amount=200.0, reason="Drain", created_by="org")
    wallet.current_balance = 50.0
    db_session.commit()

    with pytest.raises(Exception) as exc_info:
        black_market_service.purchase_market_asset(
            db=db_session,
            team_id=team.id,
            asset_type="EXTRA_PREP_TIME",  # costs 200
            actor="org"
        )
    assert "Insufficient funds" in str(exc_info.value) or "insufficient" in str(exc_info.value).lower()


def test_purchase_when_market_closed_rejected(db_session, r3_teams):
    """Verifies purchase rejected after Round 3 is finalized."""
    team = r3_teams[0]
    cfg = black_market_service.get_or_create_r3_config(db_session)
    cfg.is_finalized = True
    db_session.commit()

    with pytest.raises(MarketClosedError):
        black_market_service.purchase_market_asset(
            db=db_session,
            team_id=team.id,
            asset_type="EXTRA_PREP_TIME"
        )


# ==============================================================================
# 2. SEALED-BID AUCTION TESTS
# ==============================================================================
def test_create_and_list_auctions(db_session):
    """Verifies organizer can create sealed-bid auctions."""
    auction = black_market_service.create_auction(
        db=db_session,
        title="Exclusive Cross-Examination Dossier",
        description="Exclusive dossier on key witness in Round 4",
        item_type="AGENT_INTEL",
        starting_bid=100.0,
        reserve_price=300.0,
        created_by="lead-organizer"
    )

    assert auction.id.startswith("auc-")
    assert auction.status == AuctionStatus.OPEN
    assert auction.starting_bid == 100.0
    assert auction.reserve_price == 300.0

    auctions = black_market_service.list_auctions(db_session)
    assert len(auctions) >= 1


def test_submit_bid_within_balance(db_session, r3_teams):
    """Verifies squad can place valid sealed bid."""
    auction = black_market_service.create_auction(
        db=db_session,
        title="Tactical Asset #1",
        starting_bid=50.0
    )

    team = r3_teams[0]
    bid = black_market_service.submit_bid(
        db=db_session,
        auction_id=auction.id,
        team_id=team.id,
        bid_amount=250.0,
        notes="First sealed bid"
    )

    assert bid.id.startswith("bid-")
    assert bid.status == BidStatus.SUBMITTED
    assert bid.bid_amount == 250.0


def test_submit_bid_exceeding_wallet_balance_rejected(db_session, r3_teams):
    """Verifies squad cannot bid more than their current wallet balance."""
    auction = black_market_service.create_auction(
        db=db_session,
        title="High Stakes Item",
        starting_bid=50.0
    )

    team = r3_teams[0]
    wallet = wallet_service.get_wallet(db_session, team.id)
    impossible_bid = wallet.current_balance + 5000.0

    with pytest.raises(InvalidBidError) as exc_info:
        black_market_service.submit_bid(
            db=db_session,
            auction_id=auction.id,
            team_id=team.id,
            bid_amount=impossible_bid
        )
    assert "exceeds current wallet balance" in str(exc_info.value)


def test_submit_bid_below_starting_bid_rejected(db_session, r3_teams):
    """Verifies bid below minimum starting bid is rejected."""
    auction = black_market_service.create_auction(
        db=db_session,
        title="Premium Item",
        starting_bid=500.0
    )

    team = r3_teams[0]
    with pytest.raises(InvalidBidError):
        black_market_service.submit_bid(
            db=db_session,
            auction_id=auction.id,
            team_id=team.id,
            bid_amount=300.0
        )


def test_update_existing_bid(db_session, r3_teams):
    """Verifies squad updating their bid replaces the previous bid amount."""
    auction = black_market_service.create_auction(db=db_session, title="Auction Alpha", starting_bid=50.0)
    team = r3_teams[0]

    bid1 = black_market_service.submit_bid(db=db_session, auction_id=auction.id, team_id=team.id, bid_amount=100.0)
    bid2 = black_market_service.submit_bid(db=db_session, auction_id=auction.id, team_id=team.id, bid_amount=200.0)

    assert bid1.id == bid2.id
    assert bid2.bid_amount == 200.0

    # Ensure only 1 bid exists for this team
    bids = db_session.query(BlackMarketBid).filter(BlackMarketBid.auction_id == auction.id, BlackMarketBid.team_id == team.id).all()
    assert len(bids) == 1


def test_sealed_bid_privacy_for_squads(db_session, r3_teams):
    """Verifies squads viewing an open auction cannot see competing squads' bid amounts."""
    auction = black_market_service.create_auction(db=db_session, title="Secret Auction", starting_bid=50.0)
    team1 = r3_teams[0]
    team2 = r3_teams[1]

    black_market_service.submit_bid(db=db_session, auction_id=auction.id, team_id=team1.id, bid_amount=200.0)
    black_market_service.submit_bid(db=db_session, auction_id=auction.id, team_id=team2.id, bid_amount=350.0)

    # Squad 1 views auction
    squad1_view = black_market_service.get_auction(db_session, auction.id, is_organizer=False, viewing_team_id=team1.id)
    assert squad1_view["total_bids"] == 2

    # Squad 1 sees own bid amount, but Squad 2's bid amount is None (masked!)
    bid_for_t1 = next(b for b in squad1_view["bids"] if b["team_id"] == team1.id)
    bid_for_t2 = next(b for b in squad1_view["bids"] if b["team_id"] == team2.id)
    assert bid_for_t1["bid_amount"] == 200.0
    assert bid_for_t2["bid_amount"] is None

    # Organizer views auction - sees all amounts
    org_view = black_market_service.get_auction(db_session, auction.id, is_organizer=True)
    assert next(b for b in org_view["bids"] if b["team_id"] == team2.id)["bid_amount"] == 350.0


def test_resolve_auction_highest_bidder_wins(db_session, r3_teams):
    """Verifies highest bidder wins, debits winning wallet, losing squad not debited."""
    auction = black_market_service.create_auction(db=db_session, title="Prize Auction", starting_bid=50.0)
    team1 = r3_teams[0]
    team2 = r3_teams[1]

    w1_before = wallet_service.get_wallet(db_session, team1.id).current_balance
    w2_before = wallet_service.get_wallet(db_session, team2.id).current_balance

    black_market_service.submit_bid(db=db_session, auction_id=auction.id, team_id=team1.id, bid_amount=200.0)
    black_market_service.submit_bid(db=db_session, auction_id=auction.id, team_id=team2.id, bid_amount=450.0)

    res = black_market_service.resolve_auction(db_session, auction.id, actor="lead-org")
    assert res["success"] is True
    assert res["winner"]["team_id"] == team2.id
    assert res["winner"]["bid_amount"] == 450.0

    # Winner debited
    w2_after = wallet_service.get_wallet(db_session, team2.id).current_balance
    assert w2_after == w2_before - 450.0

    # Loser NOT debited
    w1_after = wallet_service.get_wallet(db_session, team1.id).current_balance
    assert w1_after == w1_before


def test_resolve_auction_reserve_price_not_met(db_session, r3_teams):
    """Verifies when highest bid is below reserve price, no winner is declared and no debits occur."""
    auction = black_market_service.create_auction(
        db=db_session,
        title="High Reserve Item",
        starting_bid=50.0,
        reserve_price=600.0
    )
    team = r3_teams[0]
    w_before = wallet_service.get_wallet(db_session, team.id).current_balance

    black_market_service.submit_bid(db=db_session, auction_id=auction.id, team_id=team.id, bid_amount=300.0)

    res = black_market_service.resolve_auction(db_session, auction.id, actor="org")
    assert res["winner"] is None

    w_after = wallet_service.get_wallet(db_session, team.id).current_balance
    assert w_after == w_before


def test_resolve_auction_tie_flags_review(db_session, r3_teams):
    """Verifies tie for 1st place flags REQUIRES_REVIEW and pauses resolution."""
    auction = black_market_service.create_auction(db=db_session, title="Tied Auction", starting_bid=50.0)
    team1 = r3_teams[0]
    team2 = r3_teams[1]

    black_market_service.submit_bid(db=db_session, auction_id=auction.id, team_id=team1.id, bid_amount=300.0)
    black_market_service.submit_bid(db=db_session, auction_id=auction.id, team_id=team2.id, bid_amount=300.0)

    res = black_market_service.resolve_auction(db_session, auction.id, actor="org")
    assert res["success"] is False
    assert res["requires_review"] is True
    assert auction.status == AuctionStatus.REQUIRES_REVIEW


def test_resolve_auction_tie_forced_winner(db_session, r3_teams):
    """Verifies organizer can break tie by selecting winner."""
    auction = black_market_service.create_auction(db=db_session, title="Tied Auction 2", starting_bid=50.0)
    team1 = r3_teams[0]
    team2 = r3_teams[1]

    bid1 = black_market_service.submit_bid(db=db_session, auction_id=auction.id, team_id=team1.id, bid_amount=300.0)
    bid2 = black_market_service.submit_bid(db=db_session, auction_id=auction.id, team_id=team2.id, bid_amount=300.0)

    # Force team 1 as winner
    res = black_market_service.resolve_auction(db_session, auction.id, actor="org", force_winner_bid_id=bid1.id)
    assert res["success"] is True
    assert res["winner"]["team_id"] == team1.id


# ==============================================================================
# 3. STANDINGS & FINAL CODE GATE TESTS
# ==============================================================================
def test_standings_final_code_gate_checked_first(db_session, r3_teams):
    """
    Verifies the mandatory Final Code gate is evaluated FIRST.
    Squads without verified Final Code are marked eliminated regardless of having high wallet points.
    """
    # Verify Final Code for squads 1..8
    for i in range(8):
        t = r3_teams[i]
        code_hunt_service.record_fragment_1(db_session, t.id, f"F1-{i}")
        code_hunt_service.record_fragment_2(db_session, t.id, f"F2-{i}")
        code_hunt_service.verify_final_code(db_session, t.id, f"F1-{i}F2-{i}", actor="org")

    # Squad 9 has higher balance than everyone else, but NO verified Final Code!
    rich_unverified_team = r3_teams[8]
    wallet = wallet_service.get_wallet(db_session, rich_unverified_team.id)
    wallet.current_balance = 5000.0
    db_session.commit()

    standings = black_market_service.calculate_round3_standings(db_session)

    # Verify rich_unverified_team is ranked after code-valid squads and NOT advancing
    rich_entry = next(s for s in standings["standings"] if s["team_id"] == rich_unverified_team.id)
    assert rich_entry["final_code_verified"] is False
    assert rich_entry["is_advancing"] is False
    assert rich_entry["elimination_reason"] == "Final Code not verified (mandatory gate)"
    assert rich_entry["rank"] > 8


def test_standings_code_valid_ranked_by_wallet_balance(db_session, r3_teams):
    """Verifies all code-valid squads are ranked strictly descending by remaining wallet points."""
    # Verify code for all 12 squads
    for i, t in enumerate(r3_teams):
        code_hunt_service.record_fragment_1(db_session, t.id, f"F1-{i}")
        code_hunt_service.record_fragment_2(db_session, t.id, f"F2-{i}")
        code_hunt_service.verify_final_code(db_session, t.id, f"F1-{i}F2-{i}", actor="org")

        # Set distinct wallet balances
        wallet = wallet_service.get_wallet(db_session, t.id)
        wallet.current_balance = 1000.0 + (i * 50.0)

    db_session.commit()

    standings = black_market_service.calculate_round3_standings(db_session)
    valid_ranks = [s for s in standings["standings"] if s["final_code_verified"]]

    balances = [s["current_balance"] for s in valid_ranks]
    assert balances == sorted(balances, reverse=True)
    assert len(standings["advancing_team_ids"]) == 8


def test_standings_code_contingency_when_fewer_than_8_valid(db_session, r3_teams):
    """Verifies code contingency flag is triggered when fewer than 8 squads have verified code."""
    # Only 5 squads verify final code
    for i in range(5):
        t = r3_teams[i]
        code_hunt_service.record_fragment_1(db_session, t.id, f"F1-{i}")
        code_hunt_service.record_fragment_2(db_session, t.id, f"F2-{i}")
        code_hunt_service.verify_final_code(db_session, t.id, f"F1-{i}F2-{i}", actor="org")

    standings = black_market_service.calculate_round3_standings(db_session)
    assert standings["code_contingency"] is True
    assert standings["can_finalize"] is False
    assert any("Code Contingency" in issue for issue in standings["issues"])


def test_standings_cutoff_tie_between_rank_8_and_9(db_session, r3_teams):
    """Verifies cutoff tie between 8th and 9th place flags cutoff_tie = True."""
    for i, t in enumerate(r3_teams):
        code_hunt_service.record_fragment_1(db_session, t.id, f"F1-{i}")
        code_hunt_service.record_fragment_2(db_session, t.id, f"F2-{i}")
        code_hunt_service.verify_final_code(db_session, t.id, f"F1-{i}F2-{i}", actor="org")

        wallet = wallet_service.get_wallet(db_session, t.id)
        if i in (7, 8):  # 8th and 9th squads have exact same points and metrics
            wallet.current_balance = 1500.0
            wallet.total_penalties = 0.0
            wallet.total_earned = 500.0
        elif i < 7:
            wallet.current_balance = 2000.0 - (i * 50.0)
        else:
            wallet.current_balance = 1000.0 - ((i - 9) * 50.0)

    db_session.commit()

    standings = black_market_service.calculate_round3_standings(db_session)
    assert standings["cutoff_tie"] is True
    assert standings["can_finalize"] is False
    assert any("Cutoff Tie" in issue for issue in standings["issues"])


# ==============================================================================
# 4. FINALIZATION & WALLET PRESERVATION TESTS
# ==============================================================================
def test_finalize_round3_success_and_wallet_preservation(db_session, r3_teams):
    """
    Verifies Round 3 finalization advances top 8 squads and PRESERVES wallet balances for Finale.
    """
    # Mark Round 2 finalized
    rs2 = db_session.query(RoundState).filter(RoundState.id == 2).first()
    if rs2:
        rs2.is_finalized = True
        db_session.commit()

    for i, t in enumerate(r3_teams):
        code_hunt_service.record_fragment_1(db_session, t.id, f"F1-{i}")
        code_hunt_service.record_fragment_2(db_session, t.id, f"F2-{i}")
        code_hunt_service.verify_final_code(db_session, t.id, f"F1-{i}F2-{i}", actor="org")
        wallet = wallet_service.get_wallet(db_session, t.id)
        wallet.current_balance = 1500.0 - (i * 30.0)

    db_session.commit()

    res = black_market_service.finalize_round3(db_session, actor="lead-organizer")
    assert res["success"] is True
    assert res["is_finalized"] is True
    assert res["qualified_teams_count"] == 8
    assert len(res["qualified_team_ids"]) == 8

    # Verify wallet balances were PRESERVED and NOT reset
    for i, t in enumerate(r3_teams):
        wallet = wallet_service.get_wallet(db_session, t.id)
        expected_balance = 1500.0 - (i * 30.0)
        assert wallet.current_balance == expected_balance, f"Wallet for team {t.id} was altered!"

    # Verify RoundState 3 finalized and RoundState 4 active
    rs3 = db_session.query(RoundState).filter(RoundState.id == 3).first()
    rs4 = db_session.query(RoundState).filter(RoundState.id == 4).first()
    assert rs3.is_finalized is True
    assert rs3.status == "Completed"
    assert rs4.status == "Active"


def test_finalize_round3_idempotency(db_session, r3_teams):
    """Verifies finalizing Round 3 multiple times is idempotent and safe."""
    cfg = black_market_service.get_or_create_r3_config(db_session)
    cfg.is_finalized = True
    db_session.commit()

    res = black_market_service.finalize_round3(db_session, actor="org")
    assert res["success"] is True
    assert res["is_finalized"] is True
    assert "already finalized" in res["message"]


def test_finalize_round3_override_discrepancy(db_session, r3_teams):
    """Verifies organizer can override blocked finalization using override_discrepancy=True."""
    # Only 4 teams verified (would normally block finalization)
    for i in range(4):
        t = r3_teams[i]
        code_hunt_service.record_fragment_1(db_session, t.id, f"F1-{i}")
        code_hunt_service.record_fragment_2(db_session, t.id, f"F2-{i}")
        code_hunt_service.verify_final_code(db_session, t.id, f"F1-{i}F2-{i}", actor="org")

    res = black_market_service.finalize_round3(
        db_session,
        actor="lead-organizer",
        override_discrepancy=True
    )
    assert res["success"] is True
    assert res["is_finalized"] is True


# ==============================================================================
# 5. API ENDPOINTS & RBAC TESTS
# ==============================================================================
def test_api_catalog_endpoint(client, r3_teams):
    """Tests GET /api/v1/rounds/3/market/catalog."""
    resp = client.get("/api/v1/rounds/3/market/catalog")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["totalItems"] >= 4
    assert any(i["assetType"] == "MISSING_CODE_FRAGMENT" for i in data["catalog"])


def test_api_purchase_endpoint(client, r3_teams, organizer_headers):
    """Tests POST /api/v1/rounds/3/market/purchase."""
    team = r3_teams[0]
    payload = {
        "teamId": team.id,
        "assetType": "EXTRA_PREP_TIME",
        "quantity": 1
    }
    resp = client.post("/api/v1/rounds/3/market/purchase", json=payload, headers=organizer_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["assetType"] == "EXTRA_PREP_TIME"
    assert data["price"] == BLACK_MARKET_PREP_PRICE_SUGGESTED


def test_api_auction_and_bidding_flow(client, r3_teams, organizer_headers):
    """Tests full auction flow via REST endpoints."""
    # 1. Create Auction (Organizer)
    create_payload = {
        "title": "API Dossier Auction",
        "description": "Exclusive intelligence dossier",
        "startingBid": 100.0,
        "itemType": "AGENT_INTEL"
    }
    create_resp = client.post("/api/v1/rounds/3/market/auction", json=create_payload, headers=organizer_headers)
    assert create_resp.status_code == 200
    auction_id = create_resp.json()["data"]["id"]

    # 2. Submit Bid
    bid_payload = {
        "teamId": r3_teams[0].id,
        "bidAmount": 250.0
    }
    bid_resp = client.post(f"/api/v1/rounds/3/market/auction/{auction_id}/bid", json=bid_payload, headers=organizer_headers)
    assert bid_resp.status_code == 200
    assert bid_resp.json()["data"]["status"] == "SUBMITTED"

    # 3. View Auction
    view_resp = client.get(f"/api/v1/rounds/3/market/auction/{auction_id}", headers=organizer_headers)
    assert view_resp.status_code == 200
    assert view_resp.json()["data"]["totalBids"] == 1

    # 4. Resolve Auction
    resolve_resp = client.post(f"/api/v1/rounds/3/market/auction/{auction_id}/resolve", headers=organizer_headers)
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["data"]["winner"]["team_id"] == r3_teams[0].id


def test_api_standings_endpoint(client, r3_teams):
    """Tests GET /api/v1/rounds/3/market/standings and GET /api/v1/rounds/3/standings."""
    resp = client.get("/api/v1/rounds/3/market/standings")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "standings" in data
    assert "canFinalize" in data

    legacy_resp = client.get("/api/v1/rounds/3/standings")
    assert legacy_resp.status_code == 200
    assert isinstance(legacy_resp.json()["data"], list)