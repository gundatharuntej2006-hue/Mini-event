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
from app.core.constants import (
    BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED,
    CODE_FRAGMENT_COUNT,
    COMPLETE_SECRET_CODE,
)
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
#: The fragments that make up the Final Code, in code order.
#: ODDyssey Section 2: ODD - 42 - ECHO - PRIME.
FRAGMENT_NUMBERS = tuple(range(1, CODE_FRAGMENT_COUNT + 1))
_OWNED = (FragmentStatus.RECOVERED, FragmentStatus.PURCHASED)


def _validate_fragment_number(n: int) -> None:
    if n not in FRAGMENT_NUMBERS:
        raise ValueError(
            f"Fragment number must be one of {list(FRAGMENT_NUMBERS)}; got {n}. "
            f"The Final Code is {COMPLETE_SECRET_CODE}."
        )


def frag_status(record: FinalCodeRecord, n: int) -> FragmentStatus:
    return getattr(record, f"fragment_{n}_status")


def frag_value(record: FinalCodeRecord, n: int) -> Optional[str]:
    return getattr(record, f"fragment_{n}_value")


def owns_fragment(record: FinalCodeRecord, n: int) -> bool:
    return frag_status(record, n) in _OWNED


def owns_all_fragments(record: FinalCodeRecord) -> bool:
    return all(owns_fragment(record, n) for n in FRAGMENT_NUMBERS)


def missing_fragments(record: FinalCodeRecord) -> list:
    """Fragment numbers the team does not yet hold, in code order."""
    return [n for n in FRAGMENT_NUMBERS if not owns_fragment(record, n)]


def get_or_create_final_code_record(db: Session, team_id: str) -> FinalCodeRecord:
    """Retrieves existing FinalCodeRecord or initializes a new one for the squad."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise CodeHuntNotFoundError(f"Team '{team_id}' not found.")

    record = db.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team_id).first()
    if not record:
        record = FinalCodeRecord(
            team_id=team_id,
            final_code_verified=False,
            **{f"fragment_{n}_status": FragmentStatus.PENDING for n in FRAGMENT_NUMBERS},
        )
        db.add(record)
        db.flush()
    return record


def record_fragment(
    db: Session,
    team_id: str,
    fragment_number: int,
    fragment_value: str,
    actor: Optional[str] = None,
    overwrite: bool = False,
) -> FinalCodeRecord:
    """
    Record any one of the Final Code fragments.

    ODDyssey Section 2 has four - ODD and 42 from Round 1, ECHO and PRIME from
    Round 2 - so recording them is one generic operation rather than a function
    per fragment. record_fragment_1 and record_fragment_2 remain as thin
    wrappers so existing callers keep working.
    """
    _validate_fragment_number(fragment_number)
    if not fragment_value or not fragment_value.strip():
        raise CodeHuntError(f"Fragment {fragment_number} value cannot be empty.")

    clean_val = fragment_value.strip()
    record = get_or_create_final_code_record(db, team_id)

    if owns_fragment(record, fragment_number):
        if frag_value(record, fragment_number) == clean_val:
            return record  # Idempotent
        if not overwrite:
            raise FragmentAlreadyRecordedError(
                f"Fragment {fragment_number} already recorded for team '{team_id}'. "
                "Use overwrite=True to modify."
            )

    now = datetime.now(timezone.utc)
    setattr(record, f"fragment_{fragment_number}_value", clean_val)
    setattr(record, f"fragment_{fragment_number}_status", FragmentStatus.RECOVERED)
    setattr(record, f"fragment_{fragment_number}_discovered_at", now)
    record.updated_at = now

    # Assemble as soon as every fragment is present.
    if all(frag_value(record, n) for n in FRAGMENT_NUMBERS):
        record.final_code_assembled = "".join(
            frag_value(record, n).strip() for n in FRAGMENT_NUMBERS
        )

    log_audit_event(
        db=db,
        action=f"FRAGMENT_{fragment_number}_RECORDED",
        entity_type="FinalCodeRecord",
        entity_id=record.id,
        actor_id=actor or "system",
        actor_role="ORGANIZER",
        # Fragments 1-2 are hidden in Round 1, fragments 3-4 in Round 2.
        round_number=1 if fragment_number <= 2 else 2,
        details={"team_id": team_id, "status": frag_status(record, fragment_number).value},
    )

    db.commit()
    db.refresh(record)
    return record


def record_fragment_3(db: Session, team_id: str, fragment_value: str,
                      actor: Optional[str] = None, overwrite: bool = False) -> FinalCodeRecord:
    """ECHO - Round 2, marked Cabo cards."""
    return record_fragment(db, team_id, 3, fragment_value, actor, overwrite)


def record_fragment_4(db: Session, team_id: str, fragment_value: str,
                      actor: Optional[str] = None, overwrite: bool = False) -> FinalCodeRecord:
    """PRIME - Round 2, Prime Number Challenge."""
    return record_fragment(db, team_id, 4, fragment_value, actor, overwrite)


def record_fragment_1(db: Session, team_id: str, fragment_value: str,
                      actor: Optional[str] = None, overwrite: bool = False) -> FinalCodeRecord:
    """ODD - Round 1, The Signal Scramble."""
    return record_fragment(db, team_id, 1, fragment_value, actor, overwrite)


def record_fragment_2(db: Session, team_id: str, fragment_value: str,
                      actor: Optional[str] = None, overwrite: bool = False) -> FinalCodeRecord:
    """42 - Round 1, The Route Riddle."""
    return record_fragment(db, team_id, 2, fragment_value, actor, overwrite)

def assemble_final_code(db: Session, team_id: str) -> Optional[str]:
    """
    Assemble the Final Code once EVERY fragment is held.

    ODDyssey Section 2: ODD - 42 - ECHO - PRIME. This checked only fragments 1
    and 2, so a team holding half the code would have had a "complete" one.
    Returns the assembled string, or None if any fragment is still missing.
    """
    record = db.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team_id).first()
    if not record or not all(frag_value(record, n) for n in FRAGMENT_NUMBERS):
        return None

    assembled = "".join(frag_value(record, n).strip() for n in FRAGMENT_NUMBERS)
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
    countersigned_by: Optional[str] = None,
) -> FinalCodeRecord:
    """
    Purchases a missing code fragment using tournament wallet points in Round 3.
    Requirements:
    - Team must actually be missing that fragment (PENDING or MISSING).
    - Prevents purchasing an already recovered/purchased fragment.
    - Debits wallet at the documented price (350 under ODDyssey, configurable).
    - Creates BLACK_MARKET_PURCHASE ledger record.
    - Sets fragment status to PURCHASED.

    Works for any of the four fragments. "Teams may purchase more than one
    missing fragment" (ODDyssey Section 2), so a team short of several can buy
    each of them.
    """
    _validate_fragment_number(fragment_number)

    record = get_or_create_final_code_record(db, team_id)

    if owns_fragment(record, fragment_number):
        raise MissingFragmentPurchaseError(
            f"Fragment {fragment_number} is already owned by team '{team_id}' "
            f"(status: {frag_status(record, fragment_number).value})."
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
        purchased_by=actor,
        # ODDyssey Section 5: every Black Market transaction carries two
        # organiser signatures. The fragment is the most expensive item on
        # sale and the one that decides Round 4 eligibility, so it is exactly
        # the transaction that needs both names on it.
        countersigned_by=countersigned_by,
    )
    db.add(bmp)

    now = datetime.now(timezone.utc)
    setattr(record, f"fragment_{fragment_number}_status", FragmentStatus.PURCHASED)
    setattr(record, f"fragment_{fragment_number}_discovered_at", now)
    if recovered_value:
        setattr(record, f"fragment_{fragment_number}_value", recovered_value.strip())

    record.updated_at = now

    # A purchased fragment has no physical QR to read, so give it a value if the
    # caller supplied none - otherwise the code can never assemble and the team
    # stays locked out of Round 4 despite having paid for it.
    if not frag_value(record, fragment_number):
        setattr(
            record,
            f"fragment_{fragment_number}_value",
            f"PURCHASED-{fragment_number}-{team_id[:8]}",
        )

    if all(frag_value(record, n) for n in FRAGMENT_NUMBERS):
        record.final_code_assembled = "".join(
            frag_value(record, n).strip() for n in FRAGMENT_NUMBERS
        )

        # ODDyssey Section 5 sells the missing fragment as the thing that
        # "Completes one code section", and Section 2 requires all four to
        # qualify. So completing the set by purchase has to satisfy the gate,
        # which checks final_code_verified.
        #
        # It did not. A team that bought its missing fragments still read as
        # ineligible, because verification was a separate desk step an organiser
        # had to remember AFTER taking the money. Found by
        # scripts/rehearsal.py: buy the lot, gate stays False.
        #
        # There is nothing left to verify by hand - the organiser sold the
        # fragments, so the platform already knows the team holds them.
        if owns_all_fragments(record) and not record.final_code_verified:
            record.final_code_verified = True
            # The columns are verified_at / verified_by, not
            # final_code_verified_at / _by. Assigning the longer names would
            # have set instance attributes that never reach the database, so
            # the gate would open while the audit trail stayed empty.
            record.verified_at = now
            record.verified_by = actor or "black-market"

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

    # Reported per fragment, for however many the Final Code has - four under
    # ODDyssey. Hardcoding 1 and 2 meant the dashboard could only ever show
    # half a team's progress.
    if not record:
        status: Dict[str, Any] = {
            "team_id": team_id,
            "final_code_verified": False,
            "is_complete": False,
            "verified_at": None,
            "verified_by": None,
            "final_code_assembled": None,
            "fragments_held": 0,
            "fragments_required": CODE_FRAGMENT_COUNT,
            "missing_fragments": list(FRAGMENT_NUMBERS),
        }
        for n in FRAGMENT_NUMBERS:
            status[f"fragment_{n}_status"] = FragmentStatus.PENDING
            status[f"fragment_{n}_discovered_at"] = None
            status[f"fragment_{n}_value"] = None
        return status

    held = [n for n in FRAGMENT_NUMBERS if owns_fragment(record, n)]

    status = {
        "team_id": record.team_id,
        "final_code_verified": record.final_code_verified,
        "is_complete": owns_all_fragments(record),
        "verified_at": record.verified_at,
        "verified_by": record.verified_by,
        "final_code_assembled": record.final_code_assembled if is_organizer else None,
        "fragments_held": len(held),
        "fragments_required": CODE_FRAGMENT_COUNT,
        "missing_fragments": missing_fragments(record),
    }
    for n in FRAGMENT_NUMBERS:
        status[f"fragment_{n}_status"] = frag_status(record, n)
        status[f"fragment_{n}_discovered_at"] = getattr(record, f"fragment_{n}_discovered_at")
        status[f"fragment_{n}_value"] = frag_value(record, n) if is_organizer else None
    return status
