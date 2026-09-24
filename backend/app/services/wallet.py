"""
Tournament Wallet and Points Economy Service for EVENT HQ.
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Manages single-wallet-per-team lifecycle, starting balance (1000.0), immutable transaction
ledger auditing, idempotent credits/debits, R1 rank rewards, R2 Cabo multipliers, Secret Agent
rewards, organizer penalties, Black Market asset debits, reversals, and manual adjustments.

Concurrency / Database Atomicity Note:
All balance mutations occur within atomic database transactions (db.commit() / db.rollback()).
In SQLite (the current test/local database engine), write operations serialize through a database-wide
write lock rather than row-level locks. When migrating to PostgreSQL for high-concurrency production,
`session.query(TeamWallet).with_for_update()` can be applied in `_lock_wallet` to guarantee row-level
isolation under concurrent load without changing service semantics.
"""

import uuid
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.wallet import TeamWallet, WalletTransaction, TransactionType
from app.models.team import Team
from app.core.constants import (
    STARTING_WALLET_BALANCE,
    AGENT_TASK_REWARD,
    PENALTY_MIN,
    PENALTY_MAX,
    CABO_MAX_TEAM_SCORE,
)


# ==============================================================================
# DOMAIN EXCEPTIONS
# ==============================================================================
class WalletError(Exception):
    """Base domain exception for tournament wallet operations."""
    pass


class WalletNotFoundError(WalletError):
    """Raised when a team wallet or required team entity does not exist."""
    pass


class InsufficientFundsError(WalletError):
    """Raised when a debit, purchase, or adjustment would result in a negative balance."""
    def __init__(self, current_balance: float, required_amount: float, message: Optional[str] = None):
        self.current_balance = current_balance
        self.required_amount = required_amount
        super().__init__(
            message or f"Insufficient funds: current balance {current_balance:.2f} is less than required {required_amount:.2f}"
        )


class InvalidAmountError(WalletError):
    """Raised when an invalid transaction amount is specified."""
    pass


class InvalidRankError(WalletError):
    """Raised when a Round 1 expedition rank is outside 1..32."""
    pass


class InvalidScoreError(WalletError):
    """Raised when a Round 2 Cabo team score is outside 0..75."""
    pass


class InvalidPenaltyError(WalletError):
    """Raised when an organizer penalty amount is outside the official range [-200, -50]."""
    pass


class InvalidAdjustmentError(WalletError):
    """Raised when a manual adjustment request is invalid (e.g., missing reason or creator)."""
    pass


class TransactionReversalError(WalletError):
    """Raised when attempting an invalid transaction reversal."""
    pass


class DuplicateTransactionError(WalletError):
    """Raised when an idempotent transaction operation encounters a duplicate entry."""
    pass


# ==============================================================================
# CALCULATION & SCHEDULE HELPERS
# ==============================================================================
def calculate_r1_reward(rank: int, rank_schedule: Optional[Dict[int, float]] = None) -> float:
    """
    Calculates the Round 1 Expedition points award based on squad finishing rank.
    Official suggested formula: 300 - 8 * (rank - 1), resulting in:
      Rank 1  -> 300 pts
      Rank 2  -> 292 pts
      ...
      Rank 32 -> 52 pts
    Supports configurable custom rank schedules.
    """
    if not (1 <= rank <= 32):
        raise InvalidRankError(f"Round 1 rank must be between 1 and 32, got {rank}")

    if rank_schedule is not None and rank in rank_schedule:
        return float(rank_schedule[rank])

    # Official default formula
    return float(300 - 8 * (rank - 1))


def calculate_r2_cabo_reward(cabo_score: float, multiplier: float = 10.0) -> float:
    """
    Calculates the Round 2 Cabo wallet reward from validated Cabo team score.
    Official rule: Cabo team score * 10 (where 0 <= Cabo team score <= 75).
    Default max points: 75 * 10 = 750 pts.
    """
    if not (0.0 <= cabo_score <= float(CABO_MAX_TEAM_SCORE)):
        raise InvalidScoreError(
            f"Cabo team score must be between 0.0 and {CABO_MAX_TEAM_SCORE}, got {cabo_score}"
        )
    if multiplier < 0:
        raise ValueError(f"Multiplier must be non-negative, got {multiplier}")

    return float(cabo_score * multiplier)


# ==============================================================================
# WALLET LIFECYCLE & RETRIEVAL
# ==============================================================================
def get_wallet(db: Session, team_id: str) -> Optional[TeamWallet]:
    """Retrieve existing TeamWallet by team_id, or None if not yet created."""
    return db.query(TeamWallet).filter(TeamWallet.team_id == team_id).first()


def get_or_create_wallet(
    db: Session,
    team_id: str,
    created_by: Optional[str] = None
) -> TeamWallet:
    """
    Idempotently retrieves or initializes the team wallet.
    Initial balance is set strictly to canonical STARTING_WALLET_BALANCE (1000.0).
    Creates an immutable INITIAL_BALANCE audit ledger transaction upon first creation.
    """
    # Verify team exists
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise WalletNotFoundError(f"Team '{team_id}' does not exist.")

    wallet = db.query(TeamWallet).filter(TeamWallet.team_id == team_id).first()
    if wallet:
        return wallet

    # Initialize new wallet with canonical starting balance
    wallet = TeamWallet(
        team_id=team_id,
        current_balance=STARTING_WALLET_BALANCE,
        total_earned=0.0,
        total_spent=0.0,
        total_penalties=0.0,
    )
    db.add(wallet)
    db.flush()

    # Record INITIAL_BALANCE transaction in the ledger
    init_tx = WalletTransaction(
        wallet_id=wallet.id,
        team_id=team_id,
        transaction_type=TransactionType.INITIAL_BALANCE,
        amount=STARTING_WALLET_BALANCE,
        balance_before=0.0,
        balance_after=STARTING_WALLET_BALANCE,
        reference_type="INITIALIZATION",
        reference_id=f"init-{team_id}",
        description="Initial tournament wallet allocation",
        notes=f"Starting balance set to {STARTING_WALLET_BALANCE:.2f} pts",
        created_by=created_by,
        is_reversed=False,
    )
    db.add(init_tx)
    db.commit()
    db.refresh(wallet)
    return wallet


def get_wallet_transactions(
    db: Session,
    team_id: str,
    limit: int = 100,
    offset: int = 0
) -> List[WalletTransaction]:
    """Retrieve chronologically descending ledger transactions for a team."""
    return (
        db.query(WalletTransaction)
        .filter(WalletTransaction.team_id == team_id)
        .order_by(WalletTransaction.created_at.desc(), WalletTransaction.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


# ==============================================================================
# GENERIC MUTATION OPERATIONS (CREDIT / DEBIT)
# ==============================================================================
def credit(
    db: Session,
    team_id: str,
    amount: float,
    transaction_type: TransactionType,
    description: str,
    reference_type: Optional[str] = None,
    reference_id: Optional[str] = None,
    notes: Optional[str] = None,
    created_by: Optional[str] = None,
) -> WalletTransaction:
    """
    Safely credits points to a team's tournament wallet.
    Idempotent: If reference_type and reference_id are supplied and already exist
    in an active transaction, returns the existing transaction without double-crediting.
    """
    amount = float(amount)
    if amount < 0:
        raise InvalidAmountError(f"Credit amount cannot be negative, got {amount}")

    # Idempotency check
    if reference_type and reference_id:
        existing = (
            db.query(WalletTransaction)
            .filter(
                WalletTransaction.team_id == team_id,
                WalletTransaction.reference_type == reference_type,
                WalletTransaction.reference_id == reference_id,
                WalletTransaction.is_reversed == False,
            )
            .first()
        )
        if existing:
            return existing

    wallet = get_or_create_wallet(db, team_id, created_by=created_by)
    balance_before = float(wallet.current_balance)
    balance_after = balance_before + amount

    wallet.current_balance = balance_after
    if transaction_type in [
        TransactionType.ROUND1_REWARD,
        TransactionType.ROUND2_REWARD,
        TransactionType.AGENT_TASK_REWARD,
    ]:
        wallet.total_earned = float(wallet.total_earned) + amount

    tx = WalletTransaction(
        wallet_id=wallet.id,
        team_id=team_id,
        transaction_type=transaction_type,
        amount=amount,
        balance_before=balance_before,
        balance_after=balance_after,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        notes=notes,
        created_by=created_by,
        is_reversed=False,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    db.refresh(wallet)
    return tx


def debit(
    db: Session,
    team_id: str,
    amount: float,
    transaction_type: TransactionType,
    description: str,
    reference_type: Optional[str] = None,
    reference_id: Optional[str] = None,
    notes: Optional[str] = None,
    created_by: Optional[str] = None,
    allow_negative_balance: bool = False,
) -> WalletTransaction:
    """
    Safely debits points from a team's tournament wallet.
    Prevents negative balance unless explicitly authorized.
    Idempotent: If reference_type and reference_id already exist in an active transaction,
    returns the existing transaction without double-debiting.
    """
    amount = float(amount)
    if amount <= 0:
        raise InvalidAmountError(f"Debit amount must be strictly positive, got {amount}")

    # Idempotency check
    if reference_type and reference_id:
        existing = (
            db.query(WalletTransaction)
            .filter(
                WalletTransaction.team_id == team_id,
                WalletTransaction.reference_type == reference_type,
                WalletTransaction.reference_id == reference_id,
                WalletTransaction.is_reversed == False,
            )
            .first()
        )
        if existing:
            return existing

    wallet = get_or_create_wallet(db, team_id, created_by=created_by)
    balance_before = float(wallet.current_balance)

    if not allow_negative_balance and balance_before < amount:
        raise InsufficientFundsError(current_balance=balance_before, required_amount=amount)

    balance_after = balance_before - amount
    wallet.current_balance = balance_after

    if transaction_type == TransactionType.BLACK_MARKET_PURCHASE:
        wallet.total_spent = float(wallet.total_spent) + amount
    elif transaction_type == TransactionType.PENALTY:
        wallet.total_penalties = float(wallet.total_penalties) + amount

    # Transaction ledger amount is recorded as negative for debits
    tx = WalletTransaction(
        wallet_id=wallet.id,
        team_id=team_id,
        transaction_type=transaction_type,
        amount=-amount,
        balance_before=balance_before,
        balance_after=balance_after,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        notes=notes,
        created_by=created_by,
        is_reversed=False,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    db.refresh(wallet)
    return tx


# ==============================================================================
# DOMAIN-SPECIFIC REWARDS & OPERATIONS
# ==============================================================================
def award_round1_reward(
    db: Session,
    team_id: str,
    rank: int,
    rank_schedule: Optional[Dict[int, float]] = None,
    created_by: Optional[str] = None,
) -> WalletTransaction:
    """
    Awards Round 1 Expedition finish-rank points to the squad wallet.
    Idempotent per (team_id, ROUND_1_RANK, r1-rank-{team_id}).
    """
    pts = calculate_r1_reward(rank, rank_schedule=rank_schedule)
    return credit(
        db=db,
        team_id=team_id,
        amount=pts,
        transaction_type=TransactionType.ROUND1_REWARD,
        description=f"Round 1 Expedition Rank {rank} Reward (+{pts:.1f} pts)",
        reference_type="ROUND_1_RANK",
        reference_id=f"r1-rank-{team_id}",
        notes=f"Finish Rank: {rank}/32",
        created_by=created_by,
    )


def award_round2_reward(
    db: Session,
    team_id: str,
    cabo_score: float,
    multiplier: float = 10.0,
    created_by: Optional[str] = None,
) -> WalletTransaction:
    """
    Awards Round 2 Cabo points to the squad wallet.
    Idempotent per (team_id, ROUND_2_CABO, r2-cabo-{team_id}).
    """
    pts = calculate_r2_cabo_reward(cabo_score, multiplier=multiplier)
    return credit(
        db=db,
        team_id=team_id,
        amount=pts,
        transaction_type=TransactionType.ROUND2_REWARD,
        description=f"Round 2 Cabo Reward (+{pts:.1f} pts, score: {cabo_score:.1f} x {multiplier:.1f})",
        reference_type="ROUND_2_CABO",
        reference_id=f"r2-cabo-{team_id}",
        notes=f"Cabo Score: {cabo_score:.1f}, Multiplier: {multiplier:.1f}",
        created_by=created_by,
    )


def award_agent_task_reward(
    db: Session,
    team_id: str,
    task_id: str,
    reward_amount: float = AGENT_TASK_REWARD,
    description: Optional[str] = None,
    created_by: Optional[str] = None,
) -> WalletTransaction:
    """
    Awards verified undercover Secret Agent task bounty (+50 pts canonical default).
    Idempotent per (team_id, AGENT_TASK, task_id).
    """
    reward_amount = float(reward_amount)
    if reward_amount <= 0:
        raise InvalidAmountError("Agent task reward must be strictly positive")

    desc = description or f"Secret Agent Task Bounty (+{reward_amount:.1f} pts)"
    return credit(
        db=db,
        team_id=team_id,
        amount=reward_amount,
        transaction_type=TransactionType.AGENT_TASK_REWARD,
        description=desc,
        reference_type="AGENT_TASK",
        reference_id=str(task_id),
        notes=f"Verified Agent Mission: {task_id}",
        created_by=created_by,
    )


def apply_penalty(
    db: Session,
    team_id: str,
    penalty_amount: float,
    reason: str,
    penalty_ref: Optional[str] = None,
    created_by: Optional[str] = None,
    allow_negative_balance: bool = False,
) -> WalletTransaction:
    """
    Debits an organizer-issued infraction penalty from the squad wallet.
    Official penalty range: -50.0 to -200.0 (or 50.0 to 200.0).
    Requires explicit reason and authorized organizer identifier.
    """
    if not reason or not reason.strip():
        raise InvalidPenaltyError("Penalty reason is mandatory and cannot be empty")
    if not created_by or not created_by.strip():
        raise InvalidPenaltyError("Responsible organizer (created_by) must be specified for penalties")

    penalty_amount = float(penalty_amount)
    # Support both negative format (-50 to -200) and positive magnitude (50 to 200)
    min_penalty = min(PENALTY_MIN, PENALTY_MAX) # -200.0
    max_penalty = max(PENALTY_MIN, PENALTY_MAX) # -50.0

    if min_penalty <= penalty_amount <= max_penalty:
        magnitude = abs(penalty_amount)
    elif 50.0 <= penalty_amount <= 200.0:
        magnitude = penalty_amount
    else:
        raise InvalidPenaltyError(
            f"Penalty amount {penalty_amount} is outside official range [{min_penalty}, {max_penalty}]"
        )

    ref_id = penalty_ref or f"pen-{uuid.uuid4().hex[:8]}"
    return debit(
        db=db,
        team_id=team_id,
        amount=magnitude,
        transaction_type=TransactionType.PENALTY,
        description=f"Rule Infraction Penalty (-{magnitude:.1f} pts): {reason}",
        reference_type="PENALTY",
        reference_id=ref_id,
        notes=f"Authorized by organizer: {created_by}. Reason: {reason}",
        created_by=created_by,
        allow_negative_balance=allow_negative_balance,
    )


def debit_black_market_purchase(
    db: Session,
    team_id: str,
    amount: float,
    purchase_id: str,
    asset_description: str,
    created_by: Optional[str] = None,
    notes: Optional[str] = None,
) -> WalletTransaction:
    """
    Debits the price of a Black Market purchase from the squad wallet.
    Accepts price dynamically passed from the Black Market engine (suggested prices are configurable).
    Enforces strict non-negative balance constraint.
    Idempotent per (team_id, BLACK_MARKET, purchase_id).
    """
    amount = float(amount)
    if amount <= 0:
        raise InvalidAmountError("Black Market purchase price must be strictly positive")

    return debit(
        db=db,
        team_id=team_id,
        amount=amount,
        transaction_type=TransactionType.BLACK_MARKET_PURCHASE,
        description=f"Black Market Acquisition: {asset_description} (-{amount:.1f} pts)",
        reference_type="BLACK_MARKET",
        reference_id=str(purchase_id),
        notes=notes,
        created_by=created_by,
        allow_negative_balance=False,
    )


def reverse_transaction(
    db: Session,
    transaction_id: str,
    reason: str,
    created_by: Optional[str] = None,
) -> WalletTransaction:
    """
    Safely reverses an existing transaction without altering historical ledger rows.
    Creates a new REVERSAL transaction restoring the balance, flags the target as is_reversed=True,
    and prevents double reversal.
    """
    if not reason or not reason.strip():
        raise TransactionReversalError("Reversal reason is mandatory")

    target_tx = db.query(WalletTransaction).filter(WalletTransaction.id == transaction_id).first()
    if not target_tx:
        raise WalletNotFoundError(f"Transaction '{transaction_id}' not found")

    if target_tx.is_reversed:
        raise TransactionReversalError(f"Transaction '{transaction_id}' has already been reversed")

    if target_tx.transaction_type == TransactionType.REVERSAL:
        raise TransactionReversalError("Cannot reverse a reversal transaction")

    if target_tx.transaction_type == TransactionType.INITIAL_BALANCE:
        raise TransactionReversalError("Cannot reverse initial balance allocation")

    wallet = get_or_create_wallet(db, target_tx.team_id, created_by=created_by)
    balance_before = float(wallet.current_balance)

    # Invert the original balance delta:
    # If target_tx.amount was -400 (debit), reversal is +400.
    # If target_tx.amount was +300 (credit), reversal is -300.
    reversal_amount = -float(target_tx.amount)
    balance_after = balance_before + reversal_amount

    if balance_after < 0:
        raise InsufficientFundsError(
            current_balance=balance_before,
            required_amount=abs(reversal_amount),
            message=f"Cannot reverse transaction: resulting balance would be negative ({balance_after:.2f})"
        )

    wallet.current_balance = balance_after

    # Adjust category totals if applicable
    if target_tx.transaction_type == TransactionType.BLACK_MARKET_PURCHASE:
        wallet.total_spent = max(0.0, float(wallet.total_spent) - abs(target_tx.amount))
    elif target_tx.transaction_type == TransactionType.PENALTY:
        wallet.total_penalties = max(0.0, float(wallet.total_penalties) - abs(target_tx.amount))
    elif target_tx.transaction_type in [
        TransactionType.ROUND1_REWARD,
        TransactionType.ROUND2_REWARD,
        TransactionType.AGENT_TASK_REWARD,
    ]:
        wallet.total_earned = max(0.0, float(wallet.total_earned) - abs(target_tx.amount))

    reversal_id = f"wtx-{uuid.uuid4().hex[:8]}"
    reversal_tx = WalletTransaction(
        id=reversal_id,
        wallet_id=wallet.id,
        team_id=target_tx.team_id,
        transaction_type=TransactionType.REVERSAL,
        amount=reversal_amount,
        balance_before=balance_before,
        balance_after=balance_after,
        reference_type="REVERSAL",
        reference_id=target_tx.id,
        reversed_transaction_id=target_tx.id,
        description=f"Reversal of {target_tx.id}: {reason}",
        notes=f"Original tx type: {target_tx.transaction_type.value}, original amount: {target_tx.amount}",
        created_by=created_by,
        is_reversed=False,
    )
    db.add(reversal_tx)

    # Flag original transaction
    target_tx.is_reversed = True
    target_tx.reversal_id = reversal_id

    db.commit()
    db.refresh(reversal_tx)
    db.refresh(target_tx)
    db.refresh(wallet)
    return reversal_tx


def manual_adjustment(
    db: Session,
    team_id: str,
    amount: float,
    reason: str,
    created_by: str,
    reference_id: Optional[str] = None,
    allow_negative_balance: bool = False,
) -> WalletTransaction:
    """
    Organizer-only manual balance adjustment with mandatory audit explanation.
    Never bypasses the ledger; records before/after balances.
    """
    if not reason or not reason.strip():
        raise InvalidAdjustmentError("Adjustment reason is mandatory")
    if not created_by or not created_by.strip():
        raise InvalidAdjustmentError("Responsible organizer (created_by) is required")

    amount = float(amount)
    if amount == 0:
        raise InvalidAmountError("Adjustment amount cannot be zero")

    wallet = get_or_create_wallet(db, team_id, created_by=created_by)
    balance_before = float(wallet.current_balance)
    balance_after = balance_before + amount

    if not allow_negative_balance and balance_after < 0:
        raise InsufficientFundsError(
            current_balance=balance_before,
            required_amount=abs(amount),
            message=f"Manual adjustment would result in negative balance ({balance_after:.2f})"
        )

    wallet.current_balance = balance_after

    adj_tx = WalletTransaction(
        wallet_id=wallet.id,
        team_id=team_id,
        transaction_type=TransactionType.ADJUSTMENT,
        amount=amount,
        balance_before=balance_before,
        balance_after=balance_after,
        reference_type="MANUAL_ADJUSTMENT",
        reference_id=reference_id or f"adj-{uuid.uuid4().hex[:8]}",
        description=f"Manual Adjustment ({'+' if amount > 0 else ''}{amount:.1f} pts): {reason}",
        notes=f"Authorized by organizer: {created_by}",
        created_by=created_by,
        is_reversed=False,
    )
    db.add(adj_tx)
    db.commit()
    db.refresh(adj_tx)
    db.refresh(wallet)
    return adj_tx