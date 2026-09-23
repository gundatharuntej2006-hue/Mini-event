from datetime import datetime
from typing import List, Dict, Any, Optional

def compute_mini_round(
    mini_round: Dict[str, Any],
    penalty_per_hint_seconds: int
) -> Dict[str, Any]:
    mr = dict(mini_round)
    hints = max(0, mr.get("hints_used", 0) or 0)
    mr["hints_used"] = hints
    hint_penalty = hints * penalty_per_hint_seconds
    mr["hint_penalty_seconds"] = hint_penalty

    start_str = mr.get("start_time")
    end_str = mr.get("completion_time")

    if start_str and end_str:
        try:
            # Parse ISO timestamps
            start_dt = datetime.fromisoformat(str(start_str).replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(str(end_str).replace("Z", "+00:00"))
            if end_dt >= start_dt:
                duration = round((end_dt - start_dt).total_seconds())
                mr["duration_seconds"] = duration
                mr["adjusted_seconds"] = duration + hint_penalty
                mr["status"] = "Completed"
            else:
                mr["duration_seconds"] = None
                mr["adjusted_seconds"] = None
                mr["status"] = "In Progress"
        except Exception:
            mr["duration_seconds"] = None
            mr["adjusted_seconds"] = None
            mr["status"] = "In Progress"
    elif start_str:
        mr["duration_seconds"] = None
        mr["adjusted_seconds"] = None
        mr["status"] = "In Progress"
    else:
        mr["duration_seconds"] = None
        mr["adjusted_seconds"] = None
        mr["status"] = "Not Started"

    return mr

def compute_team_totals(
    record: Dict[str, Any],
    penalty_per_hint_seconds: int
) -> Dict[str, Any]:
    updated_mini_rounds = [
        compute_mini_round(mr, penalty_per_hint_seconds)
        for mr in record.get("mini_rounds", [])
    ]

    all_three_completed = (
        len(updated_mini_rounds) == 3 and
        all(
            mr.get("status") == "Completed" and
            isinstance(mr.get("duration_seconds"), (int, float)) and
            mr.get("duration_seconds") >= 0
            for mr in updated_mini_rounds
        )
    )

    total_penalty_seconds = sum(mr.get("hint_penalty_seconds", 0) or 0 for mr in updated_mini_rounds)
    raw_total_seconds = None
    adjusted_total_seconds = None
    fastest_mini_round_seconds = None

    if all_three_completed:
        raw_total_seconds = sum(mr["duration_seconds"] for mr in updated_mini_rounds)
        adjusted_total_seconds = raw_total_seconds + total_penalty_seconds
        fastest_mini_round_seconds = min(mr["duration_seconds"] for mr in updated_mini_rounds)

    res = dict(record)
    res["mini_rounds"] = updated_mini_rounds
    res["raw_total_seconds"] = raw_total_seconds
    res["total_penalty_seconds"] = total_penalty_seconds
    res["adjusted_total_seconds"] = adjusted_total_seconds
    res["fastest_mini_round_seconds"] = fastest_mini_round_seconds
    res["is_complete"] = all_three_completed
    return res

def process_round1_standings(
    records: List[Dict[str, Any]],
    penalty_per_hint_seconds: int,
    is_finalized: bool
) -> Dict[str, Any]:
    processed = [compute_team_totals(r, penalty_per_hint_seconds) for r in records]

    completed = [r for r in processed if r.get("is_complete")]
    incomplete = [r for r in processed if not r.get("is_complete")]

    # Sort completed teams: adjustedTotal ASC, fastestMiniRound ASC, teamNumber ASC
    def sort_key(r):
        return (
            r["adjusted_total_seconds"],
            r["fastest_mini_round_seconds"],
            r["team_number"]
        )
    completed.sort(key=sort_key)

    ties_count = 0
    cutoff_boundary_tie = False
    tied_teams_at_cutoff = []

    for i in range(len(completed)):
        current = completed[i]
        rank = i + 1

        if i > 0:
            prev = completed[i - 1]
            if (
                prev["adjusted_total_seconds"] == current["adjusted_total_seconds"] and
                prev["fastest_mini_round_seconds"] == current["fastest_mini_round_seconds"]
            ):
                rank = prev["rank"]
                current["tie_requires_review"] = True
                prev["tie_requires_review"] = True
                current["tie_reason"] = f"Tied with {prev['team_name']} (Adj: {current['adjusted_total_seconds']}s, Fastest: {current['fastest_mini_round_seconds']}s)"
                prev["tie_reason"] = f"Tied with {current['team_name']} (Adj: {prev['adjusted_total_seconds']}s, Fastest: {prev['fastest_mini_round_seconds']}s)"
                ties_count += 1

                # Check if straddles 24th cutoff (rank 24 and rank 25)
                if i == 23 or i == 24:
                    cutoff_boundary_tie = True
                    tied_teams_at_cutoff.extend([prev["team_id"], current["team_id"]])
            else:
                current["tie_requires_review"] = False
                current["tie_reason"] = None
        else:
            current["tie_requires_review"] = False
            current["tie_reason"] = None

        current["rank"] = rank

        if is_finalized:
            current["qualification_status"] = "Finalized Qualified" if rank <= 24 else "Finalized Eliminated"
        else:
            if current.get("tie_requires_review") and (rank == 24 or rank == 25):
                current["qualification_status"] = "Tie Review Needed"
            else:
                current["qualification_status"] = "Provisional Qualified" if rank <= 24 else "Provisional Eliminated"

    for inc in incomplete:
        inc["rank"] = None
        inc["tie_requires_review"] = False
        inc["tie_reason"] = None
        inc["qualification_status"] = "Incomplete"

    all_records = completed + incomplete

    can_finalize = True
    issues = []

    if len(all_records) < 32:
        can_finalize = False
        issues.append({
            "code": "INSUFFICIENT_TEAMS",
            "message": f"Tournament has only {len(all_records)} squads registered (expected 32)."
        })
    if len(incomplete) > 0:
        can_finalize = False
        issues.append({
            "code": "INCOMPLETE_RESULTS",
            "message": f"Results incomplete: {len(incomplete)} squad(s) have not completed all three mini-rounds."
        })
    if cutoff_boundary_tie:
        can_finalize = False
        issues.append({
            "code": "CUTOFF_TIE",
            "message": "Unresolved tie exists at the 24th qualification cutoff boundary. Manual marshal review required."
        })

    block_reason = issues[0]["message"] if issues else None
    top24_cutoff_time = completed[23]["adjusted_total_seconds"] if len(completed) >= 24 else None

    return {
        "records": all_records,
        "can_finalize": can_finalize,
        "issues": issues,
        "block_reason": block_reason,
        "ties_count": ties_count,
        "cutoff_boundary_tie": cutoff_boundary_tie,
        "tied_teams_at_cutoff": list(set(tied_teams_at_cutoff)),
        "completed_count": len(completed),
        "incomplete_count": len(incomplete),
        "top24_cutoff_time": top24_cutoff_time
    }
