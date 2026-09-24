"""
Code Hunt, Fragment Management & Final Code Gate Service for EVENT HQ.
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Manages:
- Fragment 1 recording (discovered in Round 1)
- Fragment 2 recording (discovered in Round 2)
- Assembly of the 2-fragment Final Code
- Organizer verification of the Final Code
- Mandatory Final Code qualification gate for Round 4
- Recovery of missing fragments via the Black Market points economy
- Confidentiality and audit logging
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.code_hunt import FinalCodeRecord, FragmentStatus
from app.models.team import Team
from app.models.black_market import BlackMarketPurchase, BlackMarketAssetType, PurchaseStatus
from app.core.constants import BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED
from app.services.wallet import debit_black_market_purchase, InsufficientFundsError
from app.services.audit_service import log_audit_event


# ==============================================================================
# DOMAIN EXCEPTIONS
# ==============================================================================
class CodeHuntError(Exception):
    """Base domain exception for Code Hunt operations."""
    pass


class CodeHuntNotFoundError(CodeHuntError):
    """Raised when a team or code hunt record is not found."""
    pass


class FragmentAlreadyRecordedError(CodeHuntError):
    """Raised when attempting to record an already recorded fragment without explicit overwrite."""
    pass


class FinalCodeVerificationError(CodeHuntError):
    """Raised when final code verification fails."""
    pass


class MissingFragmentPurchaseError(CodeHuntError):
    """Raised when an invalid missing fragment purchase is attempted."""
    pass


class Round4GateError(CodeHuntError):
    """Raised when a team fails the mandatory Final Code gate for Round 4."""
    pass


# ==============================================================================
# FRAGMENT RECORDING
# ==============================================================================
def get_or_create_final_code_record(db: Session, team_id: str) -> FinalCodeRecord:
    """Retrieves existing FinalCodeRecord or initializes a new one for the squad."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise CodeHuntNotFoundError(f"Team '{team_id}' not found.")

    record = db.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team_id).first()
    if not record:
        record = FinalCodeRecord(
            team_id=team_id,
            fragment_1_status=FragmentStatus.PENDING,
            fragment_2_status=FragmentStatus.PENDING,
            final_code_verified=False,
        )
        db.add(record)
        db.flush()
    return record


def record_fragment_1(
    db: Session,
    team_id: str,
    fragment_value: str,
    actor: Optional[str] = None,
    overwrite: bool = False,
) -> FinalCodeRecord:
    """
    Records Fragment 1 (discovered during Round 1: The Great Expedition).
    Prevents silent overwrite unless explicit organizer override is requested.
    Idempotent if the same fragment value is submitted again.
    """
    if not fragment_value or not fragment_value.strip():
        raise CodeHuntError("Fragment 1 value cannot be empty.")

    clean_val = fragment_value.strip()
    record = get_or_create_final_code_record(db, team_id)

    if record.fragment_1_status in (FragmentStatus.RECOVERED, FragmentStatus.PURCHASED):
        if record.fragment_1_value == clean_val:
            return record  # Idempotent
        if not overwrite:
            raise FragmentAlreadyRecordedError(
                f"Fragment 1 already recorded for team '{team_id}'. Use overwrite=True to modify."
            )

    now = datetime.now(timezone.utc)
    record.fragment_1_value = clean_val
    record.fragment_1_status = FragmentStatus.RECOVERED
    record.fragment_1_discovered_at = now
    record.updated_at = now

    # Try assembling final code if Fragment 2 is also available
    if record.fragment_2_value:
        record.final_code_assembled = f"{clean_val}{record.fragment_2_value}"

    log_audit_event(
        db=db,
        action="FRAGMENT_1_RECORDED",
        entity_type="FinalCodeRecord",
        entity_id=record.id,
        actor_id=actor or "system",
        actor_role="ORGANIZER",
        round_number=1,
        details={"team_id": team_id, "status": record.fragment_1_status.value}
    )

    db.commit()
    db.refresh(record)
    return record


def record_fragment_2(
    db: Session,
    team_id: str,
    fragment_value: str,
    actor: Optional[str] = None,
    overwrite: bool = False,
) -> FinalCodeRecord:
    """
    Records Fragment 2 (discovered during Round 2: Cabo Tournament).
    Prevents silent overwrite unless explicit organizer override is requested.
    Idempotent if the same fragment value is submitted again.
    """
    if not fragment_value or not fragment_value.strip():
        raise CodeHuntError("Fragment 2 value cannot be empty.")

    clean_val = fragment_value.strip()
    record = get_or_create_final_code_record(db, team_id)

    if record.fragment_2_status in (FragmentStatus.RECOVERED, FragmentStatus.PURCHASED):
        if record.fragment_2_value == clean_val:
            return record  # Idempotent
        if not overwrite:
            raise FragmentAlreadyRecordedError(
                f"Fragment 2 already recorded for team '{team_id}'. Use overwrite=True to modify."
            )

    now = datetime.now(timezone.utc)
    record.fragment_2_value = clean_val
    record.fragment_2_status = FragmentStatus.RECOVERED
    record.fragment_2_discovered_at = now
    record.updated_at = now

    # Try assembling final code if Fragment 1 is also available
    if record.fragment_1_value:
        record.final_code_assembled = f"{record.fragment_1_value}{clean_val}"

    log_audit_event(
        db=db,
        action="FRAGMENT_2_RECORDED",
        entity_type="FinalCodeRecord",
        entity_id=record.id,
        actor_id=actor or "system",
        actor_role="ORGANIZER",
        round_number=2,
        details={"team_id": team_id, "status": record.fragment_2_status.value}
    )

    db.commit()
    db.refresh(record)
    return record


# ==============================================================================
# FINAL CODE ASSEMBLY & VERIFICATION
# ==============================================================================
def assemble_final_code(db: Session, team_id: str) -> Optional[str]:
    """
    Assembles the 2-fragment Final Code if and only if both Fragment 1 and Fragment 2 exist.
    Returns assembled code string or None if incomplete.
    """
    record = db.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team_id).first()
    if not record or not record.fragment_1_value or not record.fragment_2_value:
        return None

    assembled = f"{record.fragment_1_value.strip()}{record.fragment_2_value.strip()}"
    if record.final_code_assembled != assembled:
        record.final_code_assembled = assembled
        db.commit()
        db.refresh(record)
    return assembled


def verify_final_code(
    db: Session,
    team_id: str,
    supplied_code: str,
    actor: str,
    notes: Optional[str] = None,
) -> bool:
    """
    Verifies the team's supplied code against the stored two-fragment combination.
    On success: final_code_verified = True, verified_at, verified_by recorded.
    On failure: raises FinalCodeVerificationError without exposing expected code.
    Idempotent: Already-verified final code returns True without degradation.
    """
    if not supplied_code or not supplied_code.strip():
        raise FinalCodeVerificationError("Final Code verification failed.")

    record = get_or_create_final_code_record(db, team_id)

    # Idempotency safeguard: once verified, do not accidentally downgrade
    if record.final_code_verified:
        return True

    expected_code = assemble_final_code(db, team_id)
    if not expected_code:
        log_audit_event(
            db=db,
            action="FINAL_CODE_VERIFICATION_FAILED",
            entity_type="FinalCodeRecord",
            entity_id=record.id,
            actor_id=actor,
            actor_role="ORGANIZER",
            round_number=3,
            details={"team_id": team_id, "reason": "Missing fragments"}
        )
        db.commit()
        raise FinalCodeVerificationError("Final Code verification failed.")

    clean_supplied = supplied_code.strip()
    if clean_supplied == expected_code:
        now = datetime.now(timezone.utc)
        record.final_code_verified = True
        record.verified_at = now
        record.verified_by = actor
        record.verification_notes = notes
        record.updated_at = now

        log_audit_event(
            db=db,
            action="FINAL_CODE_VERIFIED",
            entity_type="FinalCodeRecord",
            entity_id=record.id,
            actor_id=actor,
            actor_role="ORGANIZER",
            round_number=3,
            details={"team_id": team_id, "verified": True}
        )
        db.commit()
        db.refresh(record)
        return True
    else:
        log_audit_event(
            db=db,
            action="FINAL_CODE_VERIFICATION_FAILED",
            entity_type="FinalCodeRecord",
            entity_id=record.id,
            actor_id=actor,
            actor_role="ORGANIZER",
            round_number=3,
            details={"team_id": team_id, "verified": False}
        )
        db.commit()
        raise FinalCodeVerificationError("Final Code verification failed.")


# ==============================================================================
# MISSING FRAGMENT RECOVERY (BLACK MARKET)
# ==============================================================================
def recover_missing_fragment(
    db: Session,
    team_id: str,
    fragment_number: int,
    price: Optional[float] = None,
    actor: Optional[str] = None,
    recovered_value: Optional[str] = None,
) -> FinalCodeRecord:
    """
    Purchases a missing code fragment using tournament wallet points in Round 3.
    Requirements:
    - Team must actually be missing that fragment (PENDING or MISSING).
    - Prevents purchasing an already recovered/purchased fragment.
    - Debits wallet dynamically (default 400.0 suggested price, configurable).
    - Creates BLACK_MARKET_PURCHASE ledger record.
    - Sets fragment status to PURCHASED.
    """
    if fragment_number not in (1, 2):
        raise ValueError("Fragment number must be 1 or 2.")

    record = get_or_create_final_code_record(db, team_id)

    if fragment_number == 1 and record.fragment_1_status in (FragmentStatus.RECOVERED, FragmentStatus.PURCHASED):
        raise MissingFragmentPurchaseError(
            f"Fragment 1 is already owned by team '{team_id}' (status: {record.fragment_1_status.value})."
        )
    elif fragment_number == 2 and record.fragment_2_status in (FragmentStatus.RECOVERED, FragmentStatus.PURCHASED):
        raise MissingFragmentPurchaseError(
            f"Fragment 2 is already owned by team '{team_id}' (status: {record.fragment_2_status.value})."
        )

    actual_price = float(price) if price is not None else float(BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED)

    # Debit tournament wallet via safe WalletService
    purchase_ref = f"frag-rec-{fragment_number}-{team_id}"
    tx = debit_black_market_purchase(
        db=db,
        team_id=team_id,
        amount=actual_price,
        purchase_id=purchase_ref,
        asset_description=f"Missing Fragment #{fragment_number} Recovery",
        created_by=actor,
        notes=f"Purchased missing code fragment {fragment_number} via Black Market"
    )

    # Create BlackMarketPurchase record
    bmp = BlackMarketPurchase(
        team_id=team_id,
        asset_type=BlackMarketAssetType.MISSING_CODE_FRAGMENT,
        price=actual_price,
        quantity=1,
        transaction_id=tx.id,
        status=PurchaseStatus.COMPLETED,
        details={"fragment_number": fragment_number},
        purchased_by=actor
    )
    db.add(bmp)

    now = datetime.now(timezone.utc)
    if fragment_number == 1:
        record.fragment_1_status = FragmentStatus.PURCHASED
        record.fragment_1_discovered_at = now
        if recovered_value:
            record.fragment_1_value = recovered_value.strip()
    else:
        record.fragment_2_status = FragmentStatus.PURCHASED
        record.fragment_2_discovered_at = now
        if recovered_value:
            record.fragment_2_value = recovered_value.strip()

    record.updated_at = now

    if record.fragment_1_value and record.fragment_2_value:
        record.final_code_assembled = f"{record.fragment_1_value.strip()}{record.fragment_2_value.strip()}"

    log_audit_event(
        db=db,
        action="MISSING_FRAGMENT_PURCHASED",
        entity_type="FinalCodeRecord",
        entity_id=record.id,
        actor_id=actor or "system",
        actor_role="ORGANIZER",
        round_number=3,
        details={"team_id": team_id, "fragment_number": fragment_number, "price": actual_price}
    )

    db.commit()
    db.refresh(record)
    return record


# ==============================================================================
# ROUND 4 QUALIFICATION GATE
# ==============================================================================
def can_enter_round4(db: Session, team_id: str) -> bool:
    """
    Domain-level qualification gate for Round 4 (The Legal Battle).
    Strict requirement: FinalCodeRecord.final_code_verified MUST BE True.
    """
    record = db.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team_id).first()
    return bool(record and record.final_code_verified)


def verify_round4_gate(db: Session, team_id: str) -> None:
    """
    Enforces the Round 4 qualification gate, raising Round4GateError if unverified.
    """
    if not can_enter_round4(db, team_id):
        raise Round4GateError(
            f"Team '{team_id}' is ineligible for Round 4: Final Code must be verified before entering Round 4."
        )


# ==============================================================================
# CODE HUNT STATUS & CONFIDENTIALITY
# ==============================================================================
def get_code_hunt_status(db: Session, team_id: str, is_organizer: bool = False) -> Dict[str, Any]:
    """
    Retrieves squad code hunt status with strict confidentiality masking.
    Non-organizer callers see fragment status and verification state, but NOT secret code strings.
    """
    record = db.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team_id).first()
    if not record:
        return {
            "team_id": team_id,
            "fragment_1_status": FragmentStatus.PENDING,
            "fragment_1_discovered_at": None,
            "fragment_2_status": FragmentStatus.PENDING,
            "fragment_2_discovered_at": None,
            "final_code_verified": False,
            "is_complete": False,
            "verified_at": None,
            "verified_by": None,
            "fragment_1_value": None,
            "fragment_2_value": None,
            "final_code_assembled": None,
        }

    is_complete = bool(
        record.fragment_1_status in (FragmentStatus.RECOVERED, FragmentStatus.PURCHASED)
        and record.fragment_2_status in (FragmentStatus.RECOVERED, FragmentStatus.PURCHASED)
    )

    return {
        "team_id": record.team_id,
        "fragment_1_status": record.fragment_1_status,
        "fragment_1_discovered_at": record.fragment_1_discovered_at,
        "fragment_2_status": record.fragment_2_status,
        "fragment_2_discovered_at": record.fragment_2_discovered_at,
        "final_code_verified": record.final_code_verified,
        "is_complete": is_complete,
        "verified_at": record.verified_at,
        "verified_by": record.verified_by,
        "fragment_1_value": record.fragment_1_value if is_organizer else None,
        "fragment_2_value": record.fragment_2_value if is_organizer else None,
        "final_code_assembled": record.final_code_assembled if is_organizer else None,
    }
