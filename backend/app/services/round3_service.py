import uuid
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.models.round3 import (
    BlackMarketConfigModel, BlackMarketTransactionModel,
    BlackMarketCodeFragmentModel, TeamCodeVerificationModel,
    default_hidden_code_config
)
from app.core.constants import STARTING_WALLET_BALANCE
from app.models.core import Team
from app.models.progression import TieReview
from app.scoring.round3_scoring import (
    compute_team_ledger, evaluate_team_code_status, process_round3_standings
)
from app.services.audit_service import log_audit_event
from app.services.progression_service import is_round_finalized, get_eligible_team_ids, record_round_finalization
from app.services.tie_review_service import get_or_create_tie_review

def get_or_create_black_market_config(db: Session) -> BlackMarketConfigModel:
    cfg = db.query(BlackMarketConfigModel).filter(BlackMarketConfigModel.id == 1).first()
    if not cfg:
        cfg = BlackMarketConfigModel(
            id=1,
            # Section 3.3: every team starts on 1,000. This seeded the
            # deprecated 100, and compute_team_ledger builds the Round 3 and
            # Round 4 balances from it - so the 10% carryover in Round 4's own
            # final-score breakdown ran off a different number from the wallet
            # the championship service uses.
            starting_balance=STARTING_WALLET_BALANCE,
            allow_negative_balance=False,
            ranking_metric="current_balance",
            scoring_direction="higher_is_better",
            is_scoring_configured=False,
            hidden_code_config=default_hidden_code_config(),
            is_finalized=False
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg

def update_black_market_config(db: Session, updates: Dict[str, Any], actor) -> BlackMarketConfigModel:
    cfg = get_or_create_black_market_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Round 3 is finalized. Configuration locked.")

    if "starting_balance" in updates and updates["starting_balance"] is not None:
        cfg.starting_balance = float(updates["starting_balance"])
    if "allow_negative_balance" in updates and updates["allow_negative_balance"] is not None:
        cfg.allow_negative_balance = bool(updates["allow_negative_balance"])
    if "ranking_metric" in updates and updates["ranking_metric"]:
        cfg.ranking_metric = updates["ranking_metric"]
    if "scoring_direction" in updates and updates["scoring_direction"]:
        cfg.scoring_direction = updates["scoring_direction"]
    if "is_scoring_configured" in updates and updates["is_scoring_configured"] is not None:
        cfg.is_scoring_configured = bool(updates["is_scoring_configured"])
    if "hidden_code_config" in updates and updates["hidden_code_config"]:
        cfg.hidden_code_config = updates["hidden_code_config"]

    log_audit_event(
        db=db,
        action="ROUND3_CONFIG_UPDATED",
        entity_type="BlackMarketConfig",
        entity_id="1",
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=3,
        details={"is_scoring_configured": cfg.is_scoring_configured}
    )
    db.commit()
    db.refresh(cfg)
    return cfg

def get_team_transactions(db: Session, team_id: str) -> List[Dict[str, Any]]:
    txs = (
        db.query(BlackMarketTransactionModel)
        .filter(BlackMarketTransactionModel.team_id == team_id)
        .order_by(BlackMarketTransactionModel.timestamp.desc())
        .all()
    )
    return [
        {
            "id": t.id,
            "team_id": t.team_id,
            "amount": t.amount,
            "type": t.type,
            "reason": t.reason,
            "organizer_ref": t.organizer_ref,
            "timestamp": t.timestamp.isoformat(),
            "is_reversed": t.is_reversed,
            "reversal_transaction_id": t.reversal_transaction_id,
            "reversed_transaction_id": t.reversed_transaction_id,
            "notes": t.notes
        }
        for t in txs
    ]

def create_transaction(
    db: Session,
    team_id: str,
    amount: float,
    tx_type: str,
    reason: str,
    notes: Optional[str],
    actor
) -> BlackMarketTransactionModel:
    cfg = get_or_create_black_market_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Round 3 is finalized.")

    if not is_round_finalized(db, 2):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Round 2 must be finalized before Round 3 transactions can execute.")

    eligible = set(get_eligible_team_ids(db, 3))
    if team_id not in eligible:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Team '{team_id}' is not qualified for Round 3.")

    # Enforce overdraft policy if spend
    if tx_type == "spend" and not cfg.allow_negative_balance:
        existing_txs = get_team_transactions(db, team_id)
        ledger = compute_team_ledger(team_id, existing_txs, cfg.starting_balance)
        if ledger["current_balance"] < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient balance. Team balance is {ledger['current_balance']}, cannot spend {amount}."
            )

    tx_id = f"tx-{uuid.uuid4().hex[:10]}"
    new_tx = BlackMarketTransactionModel(
        id=tx_id,
        team_id=team_id,
        amount=amount,
        type=tx_type,
        reason=reason,
        organizer_ref=actor.id,
        timestamp=datetime.now(timezone.utc),
        notes=notes
    )
    db.add(new_tx)

    log_audit_event(
        db=db,
        action="TRANSACTION_CREATED",
        entity_type="BlackMarketTransaction",
        entity_id=tx_id,
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=3,
        details={"team_id": team_id, "amount": amount, "type": tx_type, "reason": reason}
    )
    db.commit()
    db.refresh(new_tx)
    return new_tx

def reverse_transaction(
    db: Session,
    transaction_id: str,
    reason: str,
    actor
) -> BlackMarketTransactionModel:
    cfg = get_or_create_black_market_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Round 3 is finalized. Transactions are immutable.")

    target_tx = db.query(BlackMarketTransactionModel).filter(BlackMarketTransactionModel.id == transaction_id).first()
    if not target_tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transaction '{transaction_id}' not found.")

    if target_tx.is_reversed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction has already been reversed.")

    if target_tx.type == "reversal":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot reverse a reversal transaction.")

    reversal_id = f"rev-{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)

    # Mark original transaction as reversed
    target_tx.is_reversed = True
    target_tx.reversal_transaction_id = reversal_id

    # Create compensating reversal transaction
    reversal_tx = BlackMarketTransactionModel(
        id=reversal_id,
        team_id=target_tx.team_id,
        amount=target_tx.amount,
        type="reversal",
        reason=f"Reversal of {target_tx.id}: {reason}",
        organizer_ref=actor.id,
        timestamp=now,
        reversed_transaction_id=target_tx.id,
        notes=f"Reversed by {getattr(actor, 'name', getattr(actor, 'username', str(actor.id)))} ({actor.role.value if hasattr(actor.role, 'value') else str(actor.role)})"
    )
    db.add(reversal_tx)

    log_audit_event(
        db=db,
        action="TRANSACTION_REVERSED",
        entity_type="BlackMarketTransaction",
        entity_id=target_tx.id,
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=3,
        details={"reversal_id": reversal_id, "amount": target_tx.amount, "reason": reason}
    )
    db.commit()
    db.refresh(reversal_tx)
    return reversal_tx

def add_code_fragment(db: Session, team_id: str, fragment_index: int, notes: Optional[str], actor):
    frag_id = f"frag-{team_id}-{fragment_index}"
    existing = db.query(BlackMarketCodeFragmentModel).filter(BlackMarketCodeFragmentModel.id == frag_id).first()
    if not existing:
        frag = BlackMarketCodeFragmentModel(
            id=frag_id,
            team_id=team_id,
            fragment_index=fragment_index,
            recovered_at=datetime.now(timezone.utc),
            recovered_by=actor.id,
            notes=notes
        )
        db.add(frag)
        log_audit_event(
            db=db,
            action="FRAGMENT_RECOVERED",
            entity_type="BlackMarketCodeFragment",
            entity_id=frag_id,
            actor_id=actor.id,
            actor_role=actor.role,
            round_number=3,
            details={"team_id": team_id, "fragment_index": fragment_index}
        )
        db.commit()

def verify_code_status(db: Session, team_id: str, is_complete: bool, actor):
    rec = db.query(TeamCodeVerificationModel).filter(TeamCodeVerificationModel.team_id == team_id).first()
    now = datetime.now(timezone.utc)
    if not rec:
        rec = TeamCodeVerificationModel(
            team_id=team_id,
            is_complete=is_complete,
            verified_at=now,
            verified_by=actor.id
        )
        db.add(rec)
    else:
        rec.is_complete = is_complete
        rec.verified_at = now
        rec.verified_by = actor.id

    log_audit_event(
        db=db,
        action="CODE_STATUS_VERIFIED",
        entity_type="TeamCodeVerification",
        entity_id=team_id,
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=3,
        details={"is_complete": is_complete}
    )
    db.commit()

def get_round3_overview(db: Session) -> Dict[str, Any]:
    cfg = get_or_create_black_market_config(db)
    r2_finalized = is_round_finalized(db, 2)
    eligible_team_ids = get_eligible_team_ids(db, 3)

    teams = db.query(Team).filter(Team.id.in_(eligible_team_ids)).all() if eligible_team_ids else []
    if not r2_finalized:
        teams = db.query(Team).limit(12).all()

    all_txs = [
        {
            "id": t.id,
            "team_id": t.team_id,
            "amount": t.amount,
            "type": t.type,
            "reason": t.reason,
            "organizer_ref": t.organizer_ref,
            "timestamp": t.timestamp.isoformat(),
            "is_reversed": t.is_reversed,
            "reversal_transaction_id": t.reversal_transaction_id,
            "reversed_transaction_id": t.reversed_transaction_id,
            "notes": t.notes
        }
        for t in db.query(BlackMarketTransactionModel).all()
    ]

    all_fragments = db.query(BlackMarketCodeFragmentModel).all()
    fragments_by_team = {}
    for f in all_fragments:
        fragments_by_team.setdefault(f.team_id, []).append(f.fragment_index)

    verifications = {v.team_id: v for v in db.query(TeamCodeVerificationModel).all()}

    raw_records = []
    total_volume = 0.0
    for tx in all_txs:
        if not tx["is_reversed"] and tx["type"] != "reversal":
            total_volume += tx["amount"]

    for team in teams:
        ledger = compute_team_ledger(team.id, all_txs, cfg.starting_balance)
        team_frags = fragments_by_team.get(team.id, [])
        is_verified = verifications.get(team.id).is_complete if verifications.get(team.id) else False
        code_status = evaluate_team_code_status(
            team_frags,
            {"hidden_code_config": cfg.hidden_code_config},
            manually_verified=is_verified
        )

        raw_records.append({
            "team_id": team.id,
            "team_number": team.team_number,
            "team_name": team.name,
            "round2_qualified": team.id in eligible_team_ids,
            "ledger": ledger,
            "code_record": {
                "team_id": team.id,
                "fragments": code_status["fragments"],
                "is_complete": code_status["is_complete"],
                "verified_at": verifications.get(team.id).verified_at.isoformat() if verifications.get(team.id) and verifications.get(team.id).verified_at else None,
                "verified_by": verifications.get(team.id).verified_by if verifications.get(team.id) else None
            }
        })

    standings = process_round3_standings(
        records=raw_records,
        config={
            "scoring_direction": cfg.scoring_direction,
            "ranking_metric": cfg.ranking_metric,
            "is_scoring_configured": cfg.is_scoring_configured,
            "hidden_code_config": cfg.hidden_code_config,
            "is_finalized": cfg.is_finalized
        },
        round2_finalized=r2_finalized
    )

    if standings.get("ties_affecting_cutoff"):
        tied_teams = [r for r in standings["records"] if r["team_id"] in standings["tied_teams_at_cutoff"]]
        get_or_create_tie_review(
            db=db,
            round_number=3,
            teams_involved=tied_teams,
            ranking_metric=cfg.ranking_metric,
            cutoff_position=8,
            notes="Metric balance tie straddles 8th and 9th place cutoff for Round 4: The Legal Battle."
        )

    tie_rev = db.query(TieReview).filter(TieReview.id == "tie-r3-cutoff8").first()
    if tie_rev and tie_rev.review_status == "RESOLVED" and standings.get("ties_affecting_cutoff"):
        standings["can_finalize"] = len([i for i in standings["issues"] if i["code"] != "CUTOFF_TIE"]) == 0
        standings["issues"] = [i for i in standings["issues"] if i["code"] != "CUTOFF_TIE"]

    return {
        "config": {
            "starting_balance": cfg.starting_balance,
            "allow_negative_balance": cfg.allow_negative_balance,
            "ranking_metric": cfg.ranking_metric,
            "scoring_direction": cfg.scoring_direction,
            "is_scoring_configured": cfg.is_scoring_configured,
            "hidden_code_config": cfg.hidden_code_config or {},
            "is_finalized": cfg.is_finalized,
            "finalized_at": cfg.finalized_at.isoformat() if cfg.finalized_at else None,
            "finalized_by": cfg.finalized_by
        },
        "records": standings["records"],
        "can_finalize": standings["can_finalize"],
        "issues": standings["issues"],
        "ties_affecting_cutoff": standings["ties_affecting_cutoff"],
        "total_volume": total_volume,
        "total_transactions": len(all_txs)
    }

def finalize_round3(db: Session, actor, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = get_or_create_black_market_config(db)
    if cfg.is_finalized:
        eligible = get_eligible_team_ids(db, 4)
        return {
            "can_finalize": True,
            "issues": [],
            "finalized": True,
            "advancing_team_ids": eligible,
            "message": "Round 3 is already finalized and has already been finalized.",
            "success": True,
            "round_number": 3,
            "roundNumber": 3,
            "qualified_team_ids": eligible,
            "qualifiedTeamIds": eligible,
            "total_eligible": len(eligible) if eligible else 8,
            "totalEligible": len(eligible) if eligible else 8,
        }

    override = bool(payload and (payload.get("overrideDiscrepancy") or payload.get("override_discrepancy")))
    if not is_round_finalized(db, 2) and not override:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot finalize Round 3: Round 2 is not finalized yet."
        )

    overview = get_round3_overview(db)
    if not overview["can_finalize"] and not override:
        return {
            "can_finalize": False,
            "issues": overview["issues"],
            "finalized": False,
            "message": "Finalization blocked by server-side safeguards.",
            "success": False,
            "round_number": 3,
            "roundNumber": 3,
            "qualified_team_ids": [],
            "qualifiedTeamIds": [],
            "total_eligible": 0,
            "totalEligible": 0,
        }

    records = overview["records"]
    advancing_team_ids = [r["team_id"] for r in records if r.get("rank") and r["rank"] <= 8]

    tie_rev = db.query(TieReview).filter(TieReview.id == "tie-r3-cutoff8").first()
    if tie_rev and tie_rev.review_status == "RESOLVED" and tie_rev.advancing_team_ids:
        resolved_adv = set(tie_rev.advancing_team_ids)
        advancing_team_ids = [r["team_id"] for r in records if (r.get("rank") and r["rank"] < 8) or (r["team_id"] in resolved_adv)]

    if not advancing_team_ids and override:
        all_teams = db.query(Team).order_by(Team.team_number.asc()).limit(8).all()
        advancing_team_ids = [t.id for t in all_teams]

    record_round_finalization(
        db=db,
        round_number=3,
        records=records,
        advancing_team_ids=advancing_team_ids,
        finalized_by=actor.id
    )

    cfg.is_finalized = True
    cfg.finalized_at = datetime.now(timezone.utc)
    cfg.finalized_by = actor.id

    from app.services.round_service import ensure_round_states_initialized
    ensure_round_states_initialized(db)
    from app.models.round_models import RoundState
    rs = db.query(RoundState).filter(RoundState.id == 3).first()
    if rs:
        rs.is_finalized = True
        rs.finalized_at = cfg.finalized_at
        rs.finalized_by = actor.id
        rs.status = "Completed"

    log_audit_event(
        db=db,
        action="ROUND_FINALIZED",
        entity_type="BlackMarketConfig",
        entity_id="1",
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=3,
        details={"advancing_team_ids": advancing_team_ids, "advancing_count": len(advancing_team_ids)}
    )
    db.commit()

    return {
        "can_finalize": True,
        "issues": [],
        "finalized": True,
        "advancing_team_ids": advancing_team_ids,
        "message": "Round 3 successfully finalized. 8 squads advance to Round 4: The Legal Battle.",
        "success": True,
        "round_number": 3,
        "roundNumber": 3,
        "qualified_team_ids": advancing_team_ids,
        "qualifiedTeamIds": advancing_team_ids,
        "total_eligible": len(advancing_team_ids),
        "totalEligible": len(advancing_team_ids),
    }
