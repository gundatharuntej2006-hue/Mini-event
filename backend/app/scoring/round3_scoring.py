from typing import List, Dict, Any, Optional

def compute_team_ledger(
    team_id: str,
    transactions: List[Dict[str, Any]],
    starting_balance: float
) -> Dict[str, Any]:
    team_tx = [t for t in transactions if t.get("team_id") == team_id]

    total_earned = 0.0
    total_spent = 0.0
    net_adjustments = 0.0
    active_transaction_count = 0
    reversal_count = 0

    for tx in team_tx:
        tx_type = tx.get("type")
        if tx_type == "reversal":
            reversal_count += 1
            continue

        if tx.get("is_reversed"):
            continue  # Reversed transactions do not impact active balances

        active_transaction_count += 1
        amt = float(tx.get("amount", 0.0))

        if tx_type == "earn":
            total_earned += amt
        elif tx_type == "spend":
            total_spent += amt
        elif tx_type == "adjustment":
            net_adjustments += amt  # Can be positive or negative

    current_balance = starting_balance + total_earned - total_spent + net_adjustments

    return {
        "team_id": team_id,
        "opening_balance": starting_balance,
        "total_earned": total_earned,
        "total_spent": total_spent,
        "net_adjustments": net_adjustments,
        "current_balance": current_balance,
        "active_transaction_count": active_transaction_count,
        "reversal_count": reversal_count,
        "transactions": sorted(team_tx, key=lambda t: str(t.get("timestamp", "")), reverse=True)
    }

def compute_ranking_metric_value(ledger: Dict[str, Any], metric: str) -> float:
    if metric == "total_earned":
        return float(ledger.get("total_earned", 0.0))
    elif metric == "net_profit":
        return float(ledger.get("total_earned", 0.0) - ledger.get("total_spent", 0.0))
    return float(ledger.get("current_balance", 0.0))

def evaluate_team_code_status(
    fragments: List[int],
    config: Dict[str, Any],
    manually_verified: bool = False
) -> Dict[str, Any]:
    code_config = config.get("hidden_code_config", {})
    is_configured = code_config.get("isConfigured", False)
    req_count = code_config.get("requiredFragmentCount")

    unique_frags = set(fragments)
    is_complete = manually_verified
    if not is_complete and is_configured and req_count is not None and req_count > 0:
        is_complete = len(unique_frags) >= req_count

    return {
        "fragments": sorted(list(unique_frags)),
        "is_complete": is_complete,
        "unique_count": len(unique_frags)
    }

def process_round3_standings(
    records: List[Dict[str, Any]],
    config: Dict[str, Any],
    round2_finalized: bool
) -> Dict[str, Any]:
    scoring_direction = config.get("scoring_direction", "higher_is_better")
    is_higher_better = scoring_direction == "higher_is_better"
    ranking_metric = config.get("ranking_metric", "current_balance")
    is_scoring_configured = config.get("is_scoring_configured", False)
    code_config = config.get("hidden_code_config", {})
    code_required = code_config.get("isRequiredForQualification", False)
    is_finalized = config.get("is_finalized", False)

    # Sort records
    def sort_key(r):
        metric_val = compute_ranking_metric_value(r["ledger"], ranking_metric)
        return (-metric_val if is_higher_better else metric_val, r["team_number"])

    sorted_records = list(records)
    sorted_records.sort(key=sort_key)

    metric_groups = {}
    for r in sorted_records:
        val = compute_ranking_metric_value(r["ledger"], ranking_metric)
        metric_groups.setdefault(val, []).append(r)

    current_rank = 1
    for r in sorted_records:
        r["rank"] = current_rank
        r["tie_requires_review"] = False
        r["tie_reason"] = None
        current_rank += 1

    ties_affecting_cutoff = False
    tied_teams_at_cutoff = []

    # Cutoff is between Rank #8 (advancing) and Rank #9 (eliminated)
    for val, group in metric_groups.items():
        if len(group) > 1:
            ranks = [r["rank"] for r in group]
            min_rank = min(ranks)
            max_rank = max(ranks)
            spans_cutoff = (min_rank <= 8 and max_rank >= 9)

            for r in group:
                if spans_cutoff:
                    r["tie_requires_review"] = True
                    r["tie_reason"] = f"Tied on {val} points spanning the 8th-place cutoff (Ranks #{min_rank}-#{max_rank}). Manual review required."
                    ties_affecting_cutoff = True
                    tied_teams_at_cutoff.append(r["team_id"])
                elif max_rank <= 8:
                    r["tie_reason"] = f"Tied on {val} points with {len(group) - 1} other squad(s) inside Top 8."
                else:
                    r["tie_reason"] = f"Tied on {val} points in elimination zone."

    for r in sorted_records:
        code_complete = r.get("code_record", {}).get("is_complete", False)
        if not round2_finalized:
            r["qualification_status"] = "Round 2 Pending"
        elif is_finalized:
            r["qualification_status"] = "Finalized Qualified" if r["rank"] <= 8 else "Finalized Eliminated"
        elif r.get("tie_requires_review"):
            r["qualification_status"] = "Tie Review Needed"
        elif code_required and not code_complete:
            r["qualification_status"] = "Code Incomplete"
        elif not is_scoring_configured:
            r["qualification_status"] = "Standings Provisional"
        elif r["rank"] <= 8:
            r["qualification_status"] = "Provisional Top 8"
        else:
            r["qualification_status"] = "Provisional Cutoff"

    can_finalize = True
    issues = []

    if not round2_finalized:
        can_finalize = False
        issues.append({
            "code": "PREVIOUS_ROUND_UNFINALIZED",
            "message": "Round 2 (Cabo) results are not yet officially finalized. Finalize Round 2 first."
        })
    if len(records) != 12:
        can_finalize = False
        issues.append({
            "code": "INVALID_TEAM_COUNT",
            "message": f"Expected exactly 12 qualified squads from Round 2, but found {len(records)}."
        })
    if not is_scoring_configured:
        can_finalize = False
        issues.append({
            "code": "CONFIG_UNCONFIRMED",
            "message": "Scoring and ranking rules have not been officially confirmed by organizers."
        })
    if ties_affecting_cutoff:
        can_finalize = False
        issues.append({
            "code": "CUTOFF_TIE",
            "message": "An unresolved tie affects the 8th-place qualification cutoff boundary. Manual marshal review required."
        })
    if code_required:
        if not code_config.get("isConfigured") or code_config.get("requiredFragmentCount") is None:
            can_finalize = False
            issues.append({
                "code": "CODE_CONFIG_MISSING",
                "message": "Hidden code completion is mandatory for qualification, but official fragment requirements have not been configured."
            })
        else:
            incomplete_top8 = [r for r in sorted_records if r["rank"] <= 8 and not r.get("code_record", {}).get("is_complete")]
            if incomplete_top8:
                can_finalize = False
                issues.append({
                    "code": "CODE_INCOMPLETE",
                    "message": f"{len(incomplete_top8)} squad(s) currently in the Top 8 have not satisfied the mandatory hidden code requirement."
                })

    block_reason = issues[0]["message"] if issues else None
    top8_team_ids = [r["team_id"] for r in sorted_records if r.get("rank") and r["rank"] <= 8]
    eliminated_team_ids = [r["team_id"] for r in sorted_records if r.get("rank") and r["rank"] > 8]

    return {
        "records": sorted_records,
        "can_finalize": can_finalize,
        "issues": issues,
        "block_reason": block_reason,
        "ties_affecting_cutoff": ties_affecting_cutoff,
        "tied_teams_at_cutoff": list(set(tied_teams_at_cutoff)),
        "top8_team_ids": top8_team_ids,
        "eliminated_team_ids": eliminated_team_ids
    }
