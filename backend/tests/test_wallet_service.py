"""
Unit and Integration Tests for EVENT HQ Tournament Wallet & Points Economy Engine (Step 9).
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Verifies all 26 mandatory tournament wallet requirements:
1. Wallet starts at 1000.
2. Initial wallet creation is idempotent.
3. Credit increases balance.
4. Debit decreases balance.
5. Negative balance is rejected.
6. R1 rank 1 gives 300.
7. R1 rank 32 gives 52.
8. R1 intermediate ranks follow the default formula.
9. Invalid R1 rank is rejected.
10. R2 score 75 produces 750 default wallet points.
11. R2 score 0 produces 0.
12. R2 score >75 is rejected.
13. Agent reward gives +50.
14. Penalty -50 works.
15. Penalty -200 works.
16. Penalty outside range is rejected.
17. Black Market debit works.
18. Insufficient Black Market balance is rejected.
19. Transaction before/after balances are correct.
20. Duplicate reward does not double-credit.
21. Duplicate purchase does not double-debit.
22. Transaction reversal restores balance.
23. Double reversal is rejected.
24. Organizer adjustment works.
25. Adjustment without reason is rejected.
26. Ledger remains auditable after reversal.
Plus API endpoints and RBAC security tests.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.team import Team, TeamStatus
from app.models.user import User, UserRole
from app.models.wallet import TeamWallet, WalletTransaction, TransactionType
from app.core.constants import (
    STARTING_WALLET_BALANCE,
    AGENT_TASK_REWARD,
    PENALTY_MIN,
    PENALTY_MAX,
    CABO_MAX_TEAM_SCORE,
)
from app.services.wallet import (
    get_wallet,
    get_or_create_wallet,
    get_wallet_transactions,
    credit,
    debit,
    calculate_r1_reward,
    calculate_r2_cabo_reward,
    award_round1_reward,
    award_round2_reward,
    award_agent_task_reward,
    apply_penalty,
    debit_black_market_purchase,
    reverse_transaction,
    manual_adjustment,
    WalletError,
    WalletNotFoundError,
    InsufficientFundsError,
    InvalidAmountError,
    InvalidRankError,
    InvalidScoreError,
    InvalidPenaltyError,
    InvalidAdjustmentError,
    TransactionReversalError,
)
from app.core.security import create_access_token


@pytest.fixture
def test_team(db_session):
    """Fixture providing a test squad."""
    team = Team(
        id="team-squad-alpha",
        team_number=1,
        name="Alpha Vanguard",
        status=TeamStatus.ACTIVE,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


# ==============================================================================
# SECTION 18 MANDATORY TESTS (1 - 26)
# ==============================================================================

def test_01_wallet_starts_at_1000(db_session, test_team):
    """Requirement 1: Wallet starts strictly at canonical 1000.0 points with INITIAL_BALANCE transaction."""
    wallet = get_or_create_wallet(db_session, test_team.id)
    assert wallet is not None
    assert wallet.current_balance == STARTING_WALLET_BALANCE
    assert wallet.current_balance == 1000.0
    assert wallet.total_earned == 0.0
    assert wallet.total_spent == 0.0
    assert wallet.total_penalties == 0.0

    txs = get_wallet_transactions(db_session, test_team.id)
    assert len(txs) == 1
    init_tx = txs[0]
    assert init_tx.transaction_type == TransactionType.INITIAL_BALANCE
    assert init_tx.amount == 1000.0
    assert init_tx.balance_before == 0.0
    assert init_tx.balance_after == 1000.0


def test_02_initial_wallet_creation_is_idempotent(db_session, test_team):
    """Requirement 2: Initial wallet creation is idempotent and does not create duplicate transactions."""
    w1 = get_or_create_wallet(db_session, test_team.id)
    w2 = get_or_create_wallet(db_session, test_team.id)
    assert w1.id == w2.id

    txs = get_wallet_transactions(db_session, test_team.id)
    assert len(txs) == 1
    assert w2.current_balance == 1000.0


def test_03_credit_increases_balance(db_session, test_team):
    """Requirement 3: Credit increases wallet balance and tracks total_earned for rewards."""
    wallet = get_or_create_wallet(db_session, test_team.id)
    tx = credit(
        db=db_session,
        team_id=test_team.id,
        amount=150.0,
        transaction_type=TransactionType.ROUND1_REWARD,
        description="Bonus expedition points",
    )
    assert tx.balance_before == 1000.0
    assert tx.balance_after == 1150.0
    assert tx.amount == 150.0
    assert wallet.current_balance == 1150.0
    assert wallet.total_earned == 150.0


def test_04_debit_decreases_balance(db_session, test_team):
    """Requirement 4: Debit decreases wallet balance and records negative transaction amount."""
    wallet = get_or_create_wallet(db_session, test_team.id)
    tx = debit(
        db=db_session,
        team_id=test_team.id,
        amount=250.0,
        transaction_type=TransactionType.BLACK_MARKET_PURCHASE,
        description="Market item purchase",
    )
    assert tx.balance_before == 1000.0
    assert tx.balance_after == 750.0
    assert tx.amount == -250.0
    assert wallet.current_balance == 750.0
    assert wallet.total_spent == 250.0


def test_05_negative_balance_is_rejected(db_session, test_team):
    """Requirement 5: Debiting more points than current balance raises InsufficientFundsError."""
    wallet = get_or_create_wallet(db_session, test_team.id)
    with pytest.raises(InsufficientFundsError) as exc_info:
        debit(
            db=db_session,
            team_id=test_team.id,
            amount=1200.0,
            transaction_type=TransactionType.BLACK_MARKET_PURCHASE,
            description="Expensive market item",
        )
    assert "Insufficient funds" in str(exc_info.value)
    assert wallet.current_balance == 1000.0  # Balance untouched


def test_06_r1_rank_1_gives_300(db_session, test_team):
    """Requirement 6: Round 1 rank 1 awards 300 points."""
    pts = calculate_r1_reward(1)
    assert pts == 300.0

    tx = award_round1_reward(db_session, test_team.id, rank=1)
    assert tx.amount == 300.0
    assert tx.balance_after == 1300.0
    assert tx.transaction_type == TransactionType.ROUND1_REWARD


def test_07_r1_rank_32_gives_52(db_session, test_team):
    """Requirement 7: Round 1 rank 32 awards 52 points."""
    pts = calculate_r1_reward(32)
    assert pts == 52.0

    tx = award_round1_reward(db_session, test_team.id, rank=32)
    assert tx.amount == 52.0
    assert tx.balance_after == 1052.0


def test_08_r1_intermediate_ranks_follow_default_formula(db_session):
    """Requirement 8: R1 intermediate ranks follow 300 - 8 * (rank - 1)."""
    assert calculate_r1_reward(2) == 292.0
    assert calculate_r1_reward(3) == 284.0
    assert calculate_r1_reward(10) == 228.0
    assert calculate_r1_reward(16) == 180.0
    assert calculate_r1_reward(24) == 116.0
    assert calculate_r1_reward(31) == 60.0


def test_09_invalid_r1_rank_is_rejected(db_session, test_team):
    """Requirement 9: Invalid R1 ranks (<1 or >32) raise InvalidRankError."""
    with pytest.raises(InvalidRankError):
        calculate_r1_reward(0)

    with pytest.raises(InvalidRankError):
        calculate_r1_reward(33)

    with pytest.raises(InvalidRankError):
        award_round1_reward(db_session, test_team.id, rank=-5)


def test_10_r2_score_75_produces_750_default_wallet_points(db_session, test_team):
    """Requirement 10: R2 score 75 produces 750 default wallet points (score x 10)."""
    pts = calculate_r2_cabo_reward(75.0)
    assert pts == 750.0

    tx = award_round2_reward(db_session, test_team.id, cabo_score=75.0)
    assert tx.amount == 750.0
    assert tx.balance_after == 1750.0
    assert tx.transaction_type == TransactionType.ROUND2_REWARD


def test_11_r2_score_0_produces_0(db_session, test_team):
    """Requirement 11: R2 score 0 produces 0 points."""
    pts = calculate_r2_cabo_reward(0.0)
    assert pts == 0.0

    tx = award_round2_reward(db_session, test_team.id, cabo_score=0.0)
    assert tx.amount == 0.0
    assert tx.balance_after == 1000.0


def test_12_r2_score_greater_than_75_is_rejected(db_session, test_team):
    """Requirement 12: Cabo team score > 75 or < 0 is rejected."""
    with pytest.raises(InvalidScoreError):
        calculate_r2_cabo_reward(76.0)

    with pytest.raises(InvalidScoreError):
        calculate_r2_cabo_reward(-1.0)

    with pytest.raises(InvalidScoreError):
        award_round2_reward(db_session, test_team.id, cabo_score=80.0)


def test_13_agent_reward_gives_plus_50(db_session, test_team):
    """Requirement 13: Secret Agent task bounty awards +50 points."""
    tx = award_agent_task_reward(
        db=db_session,
        team_id=test_team.id,
        task_id="task-sabotage-001",
    )
    assert tx.amount == 50.0
    assert tx.amount == AGENT_TASK_REWARD
    assert tx.balance_after == 1050.0
    assert tx.transaction_type == TransactionType.AGENT_TASK_REWARD


def test_14_penalty_minus_50_works(db_session, test_team):
    """Requirement 14: Penalty -50 works and reduces balance by 50."""
    tx = apply_penalty(
        db=db_session,
        team_id=test_team.id,
        penalty_amount=-50.0,
        reason="Minor unsporting conduct",
        created_by="lead_organizer@bmsit.in",
    )
    assert tx.amount == -50.0
    assert tx.balance_after == 950.0
    assert tx.transaction_type == TransactionType.PENALTY

    wallet = get_wallet(db_session, test_team.id)
    assert wallet.total_penalties == 50.0


def test_15_penalty_minus_200_works(db_session, test_team):
    """Requirement 15: Maximum penalty -200 works and reduces balance by 200."""
    tx = apply_penalty(
        db=db_session,
        team_id=test_team.id,
        penalty_amount=-200.0,
        reason="Major intentional rule violation",
        created_by="chief_marshal@bmsit.in",
    )
    assert tx.amount == -200.0
    assert tx.balance_after == 800.0


def test_16_penalty_outside_range_is_rejected(db_session, test_team):
    """Requirement 16: Penalties outside [-200, -50] are rejected."""
    # Too small penalty
    with pytest.raises(InvalidPenaltyError):
        apply_penalty(
            db=db_session,
            team_id=test_team.id,
            penalty_amount=-25.0,
            reason="Too small",
            created_by="organizer@bmsit.in",
        )

    # Too severe penalty beyond maximum
    with pytest.raises(InvalidPenaltyError):
        apply_penalty(
            db=db_session,
            team_id=test_team.id,
            penalty_amount=-250.0,
            reason="Excessive",
            created_by="organizer@bmsit.in",
        )

    # Zero penalty
    with pytest.raises(InvalidPenaltyError):
        apply_penalty(
            db=db_session,
            team_id=test_team.id,
            penalty_amount=0.0,
            reason="Zero",
            created_by="organizer@bmsit.in",
        )


def test_17_black_market_debit_works(db_session, test_team):
    """Requirement 17: Black Market debit works and tracks total_spent."""
    tx = debit_black_market_purchase(
        db=db_session,
        team_id=test_team.id,
        amount=400.0,
        purchase_id="purchase-frag-01",
        asset_description="Missing Code Fragment #1",
        created_by="market_vendor",
    )
    assert tx.amount == -400.0
    assert tx.balance_before == 1000.0
    assert tx.balance_after == 600.0
    assert tx.transaction_type == TransactionType.BLACK_MARKET_PURCHASE

    wallet = get_wallet(db_session, test_team.id)
    assert wallet.total_spent == 400.0
    assert wallet.current_balance == 600.0


def test_18_insufficient_black_market_balance_is_rejected(db_session, test_team):
    """Requirement 18: Insufficient Black Market balance is rejected."""
    # First spend 900 points
    debit_black_market_purchase(
        db=db_session,
        team_id=test_team.id,
        amount=900.0,
        purchase_id="purchase-bulk",
        asset_description="Heavy intel package",
    )
    wallet = get_wallet(db_session, test_team.id)
    assert wallet.current_balance == 100.0

    # Attempt to purchase 150 pts item with only 100 pts
    with pytest.raises(InsufficientFundsError):
        debit_black_market_purchase(
            db=db_session,
            team_id=test_team.id,
            amount=150.0,
            purchase_id="purchase-witness",
            asset_description="Extra Witness Question",
        )
    assert wallet.current_balance == 100.0


def test_19_transaction_before_after_balances_are_correct(db_session, test_team):
    """Requirement 19: All transactions accurately log balance_before and balance_after matching amounts."""
    w = get_or_create_wallet(db_session, test_team.id)
    b0 = w.current_balance  # 1000.0

    tx1 = award_round1_reward(db_session, test_team.id, rank=1)
    assert tx1.balance_before == 1000.0
    assert tx1.balance_after == 1300.0
    assert tx1.balance_after == tx1.balance_before + tx1.amount

    tx2 = debit_black_market_purchase(
        db=db_session,
        team_id=test_team.id,
        amount=400.0,
        purchase_id="p-unique-19",
        asset_description="Fragment",
    )
    assert tx2.balance_before == 1300.0
    assert tx2.balance_after == 900.0
    assert tx2.balance_after == tx2.balance_before + tx2.amount  # amount is -400.0


def test_20_duplicate_reward_does_not_double_credit(db_session, test_team):
    """Requirement 20: Retrying the same reward operation is idempotent and does not double-credit."""
    tx1 = award_round1_reward(db_session, test_team.id, rank=2)
    assert tx1.amount == 292.0
    assert tx1.balance_after == 1292.0

    # Retry same reward
    tx2 = award_round1_reward(db_session, test_team.id, rank=2)
    assert tx1.id == tx2.id

    wallet = get_wallet(db_session, test_team.id)
    assert wallet.current_balance == 1292.0  # Not 1584.0


def test_21_duplicate_purchase_does_not_double_debit(db_session, test_team):
    """Requirement 21: Retried purchase with identical purchase ID does not double-debit."""
    tx1 = debit_black_market_purchase(
        db=db_session,
        team_id=test_team.id,
        amount=200.0,
        purchase_id="tx-order-duplicate-check",
        asset_description="Extra Prep Time",
    )
    assert tx1.balance_after == 800.0

    # Retry same purchase
    tx2 = debit_black_market_purchase(
        db=db_session,
        team_id=test_team.id,
        amount=200.0,
        purchase_id="tx-order-duplicate-check",
        asset_description="Extra Prep Time",
    )
    assert tx1.id == tx2.id

    wallet = get_wallet(db_session, test_team.id)
    assert wallet.current_balance == 800.0  # Not 600.0


def test_22_transaction_reversal_restores_balance(db_session, test_team):
    """Requirement 22: Transaction reversal safely restores balance and records REVERSAL entry."""
    # Debit 400 points
    orig_tx = debit_black_market_purchase(
        db=db_session,
        team_id=test_team.id,
        amount=400.0,
        purchase_id="p-reversal-target",
        asset_description="Erroneous Purchase",
    )
    assert orig_tx.balance_after == 600.0

    # Reverse transaction
    rev_tx = reverse_transaction(
        db=db_session,
        transaction_id=orig_tx.id,
        reason="Vendor inventory stockout error",
        created_by="lead_organizer@bmsit.in",
    )

    assert rev_tx.transaction_type == TransactionType.REVERSAL
    assert rev_tx.amount == 400.0
    assert rev_tx.balance_before == 600.0
    assert rev_tx.balance_after == 1000.0
    assert rev_tx.reversed_transaction_id == orig_tx.id

    wallet = get_wallet(db_session, test_team.id)
    assert wallet.current_balance == 1000.0
    assert wallet.total_spent == 0.0

    # Verify original transaction was marked reversed
    db_session.refresh(orig_tx)
    assert orig_tx.is_reversed is True
    assert orig_tx.reversal_id == rev_tx.id


def test_23_double_reversal_is_rejected(db_session, test_team):
    """Requirement 23: Double reversal of the same transaction raises TransactionReversalError."""
    orig_tx = debit_black_market_purchase(
        db=db_session,
        team_id=test_team.id,
        amount=200.0,
        purchase_id="p-double-rev",
        asset_description="Asset",
    )
    reverse_transaction(
        db=db_session,
        transaction_id=orig_tx.id,
        reason="First reversal",
        created_by="organizer",
    )

    with pytest.raises(TransactionReversalError):
        reverse_transaction(
            db=db_session,
            transaction_id=orig_tx.id,
            reason="Second reversal attempt",
            created_by="organizer",
        )


def test_24_organizer_adjustment_works(db_session, test_team):
    """Requirement 24: Organizer manual adjustment updates balance and logs ADJUSTMENT transaction."""
    # Positive adjustment
    tx_pos = manual_adjustment(
        db=db_session,
        team_id=test_team.id,
        amount=75.0,
        reason="Organizer discretionary compensation for hardware glitch",
        created_by="tech_lead@bmsit.in",
    )
    assert tx_pos.amount == 75.0
    assert tx_pos.balance_after == 1075.0
    assert tx_pos.transaction_type == TransactionType.ADJUSTMENT

    # Negative adjustment
    tx_neg = manual_adjustment(
        db=db_session,
        team_id=test_team.id,
        amount=-25.0,
        reason="Correction of excess score entry",
        created_by="tech_lead@bmsit.in",
    )
    assert tx_neg.amount == -25.0
    assert tx_neg.balance_after == 1050.0


def test_25_adjustment_without_reason_is_rejected(db_session, test_team):
    """Requirement 25: Manual adjustment without explicit reason is rejected."""
    with pytest.raises(InvalidAdjustmentError):
        manual_adjustment(
            db=db_session,
            team_id=test_team.id,
            amount=50.0,
            reason="",
            created_by="organizer@bmsit.in",
        )

    with pytest.raises(InvalidAdjustmentError):
        manual_adjustment(
            db=db_session,
            team_id=test_team.id,
            amount=50.0,
            reason="   ",
            created_by="organizer@bmsit.in",
        )

    with pytest.raises(InvalidAdjustmentError):
        manual_adjustment(
            db=db_session,
            team_id=test_team.id,
            amount=50.0,
            reason="Valid reason",
            created_by="",
        )


def test_26_ledger_remains_auditable_after_reversal(db_session, test_team):
    """Requirement 26: Complete audit trail is preserved after reversals."""
    w = get_or_create_wallet(db_session, test_team.id)

    # 1. Spend 400
    tx1 = debit_black_market_purchase(
        db=db_session,
        team_id=test_team.id,
        amount=400.0,
        purchase_id="order-audit-1",
        asset_description="Intel",
    )
    # 2. Reverse it
    rev = reverse_transaction(
        db=db_session,
        transaction_id=tx1.id,
        reason="Disputed vendor quote",
        created_by="organizer",
    )

    all_txs = get_wallet_transactions(db_session, test_team.id)
    # Expect 3 transactions: REVERSAL, BLACK_MARKET_PURCHASE, INITIAL_BALANCE
    assert len(all_txs) == 3

    types = [t.transaction_type for t in all_txs]
    assert TransactionType.REVERSAL in types
    assert TransactionType.BLACK_MARKET_PURCHASE in types
    assert TransactionType.INITIAL_BALANCE in types

    # Original is intact in the database
    orig = next(t for t in all_txs if t.id == tx1.id)
    assert orig.is_reversed is True
    assert orig.reversal_id == rev.id


# ==============================================================================
# API LAYER TESTS (FASTAPI ROUTER & RBAC)
# ==============================================================================

def test_api_get_team_wallet(client, test_team):
    """Verify GET /api/v1/teams/{team_id}/wallet returns starting wallet state."""
    res = client.get(f"/api/v1/teams/{test_team.id}/wallet")
    assert res.status_code == 200
    payload = res.json()
    assert payload["success"] is True
    assert payload["data"]["teamId"] == test_team.id
    assert payload["data"]["currentBalance"] == 1000.0


def test_api_get_wallet_transactions(client, test_team):
    """Verify GET /api/v1/teams/{team_id}/wallet/transactions lists ledger entries."""
    # Trigger creation
    client.get(f"/api/v1/teams/{test_team.id}/wallet")

    res = client.get(f"/api/v1/teams/{test_team.id}/wallet/transactions")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) >= 1
    assert data[0]["transactionType"] == "INITIAL_BALANCE"


def test_api_organizer_adjust_endpoint(client, test_team, organizer_headers):
    """Verify POST /api/v1/teams/{team_id}/wallet/adjust allows organizers to adjust points."""
    res = client.post(
        f"/api/v1/teams/{test_team.id}/wallet/adjust",
        json={"amount": 120.0, "reason": "Authorized team adjustment"},
        headers=organizer_headers,
    )
    assert res.status_code == 200
    payload = res.json()["data"]
    assert payload["amount"] == 120.0
    assert payload["balanceAfter"] == 1120.0


def test_api_organizer_penalty_endpoint(client, test_team, organizer_headers):
    """Verify POST /api/v1/teams/{team_id}/wallet/penalty applies penalty."""
    res = client.post(
        f"/api/v1/teams/{test_team.id}/wallet/penalty",
        json={"amount": -100.0, "reason": "Late arrival to stage"},
        headers=organizer_headers,
    )
    assert res.status_code == 200
    payload = res.json()["data"]
    assert payload["amount"] == -100.0
    assert payload["balanceAfter"] == 900.0


def test_api_unauthorized_mutation_rejected(client, test_team, marshal_headers):
    """Verify non-organizers cannot adjust or penalize wallets."""
    res = client.post(
        f"/api/v1/teams/{test_team.id}/wallet/adjust",
        json={"amount": 50.0, "reason": "Attempted marshal adjust"},
        headers=marshal_headers,
    )
    assert res.status_code == 403