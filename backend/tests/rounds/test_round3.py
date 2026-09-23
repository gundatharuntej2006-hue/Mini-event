import pytest
from app.scoring.round3_scoring import compute_team_ledger, process_round3_standings

def test_ledger_computation_and_reversals():
    txs = [
        {"id": "tx-1", "team_id": "team-1", "amount": 50, "type": "earn", "is_reversed": False},
        {"id": "tx-2", "team_id": "team-1", "amount": 30, "type": "spend", "is_reversed": False},
        {"id": "tx-3", "team_id": "team-1", "amount": 20, "type": "earn", "is_reversed": True},       # Reversed, must not count
        {"id": "tx-4", "team_id": "team-1", "amount": 20, "type": "reversal", "is_reversed": False},   # Reversal record, must not count
        {"id": "tx-5", "team_id": "team-1", "amount": 10, "type": "adjustment", "is_reversed": False}, # +10 adjustment
    ]
    ledger = compute_team_ledger("team-1", txs, starting_balance=100.0)
    # Balance: 100 + 50 - 30 + 10 = 130
    assert ledger["current_balance"] == 130.0
    assert ledger["total_earned"] == 50.0
    assert ledger["total_spent"] == 30.0
    assert ledger["net_adjustments"] == 10.0
    assert ledger["reversal_count"] == 1
    assert ledger["active_transaction_count"] == 3

def test_round3_unconfirmed_scoring_blocks_finalization():
    records = [
        {
            "team_id": f"team-{i + 1}",
            "team_number": i + 1,
            "team_name": f"Team {i + 1}",
            "ledger": {"current_balance": 150 - i * 5, "total_earned": 50, "total_spent": 10},
            "code_record": {"is_complete": False}
        }
        for i in range(12)
    ]
    # is_scoring_configured = False (unconfirmed demo default)
    standings = process_round3_standings(
        records=records,
        config={
            "scoring_direction": "higher_is_better",
            "ranking_metric": "current_balance",
            "is_scoring_configured": False,
            "hidden_code_config": {"isRequiredForQualification": False},
            "is_finalized": False
        },
        round2_finalized=True
    )
    assert standings["can_finalize"] is False
    assert any(i["code"] == "CONFIG_UNCONFIRMED" for i in standings["issues"])

def test_round3_cutoff_tie_blocks_finalization():
    records = []
    for i in range(12):
        # Tie at 8th cutoff (ranks 8 and 9 share 110 pts)
        bal = 110.0 if (i == 7 or i == 8) else float(150 - i * 5)
        records.append({
            "team_id": f"team-{i + 1}",
            "team_number": i + 1,
            "team_name": f"Team {i + 1}",
            "ledger": {"current_balance": bal, "total_earned": 50, "total_spent": 10},
            "code_record": {"is_complete": False}
        })

    standings = process_round3_standings(
        records=records,
        config={
            "scoring_direction": "higher_is_better",
            "ranking_metric": "current_balance",
            "is_scoring_configured": True,
            "hidden_code_config": {"isRequiredForQualification": False},
            "is_finalized": False
        },
        round2_finalized=True
    )
    assert standings["can_finalize"] is False
    assert standings["ties_affecting_cutoff"] is True
    assert any(i["code"] == "CUTOFF_TIE" for i in standings["issues"])
