from datetime import datetime
from typing import List, Dict, Any, Optional

GATE_NAMES = {
    1: "Gate 1 — The Signal Scramble",
    2: "Gate 2 — The Route Riddle",
    3: "Gate 3 — The Logic Lockdown"
}

def compute_mini_round(
    mini_round: Dict[str, Any],
    penalty_per_hint_seconds: int = 300,
    phone_penalty_seconds: int = 600,
    separation_penalty_seconds: int = 300
) -> Dict[str, Any]:
    mr = dict(mini_round)
    mr_num = mr.get("mini_round_number", 1)
    mr["gate_name"] = GATE_NAMES.get(mr_num, f"Gate {mr_num}")

    hints = max(0, mr.get("hints_used", 0) or 0)
    mr["hints_used"] = hints
    hint_penalty = hints * penalty_per_hint_seconds
    mr["hint_penalty_seconds"] = hint_penalty

    phones = max(0, mr.get("phone_penalties_count", 0) or 0)
    mr["phone_penalties_count"] = phones
    phone_pen = phones * phone_penalty_seconds
    mr["phone_penalty_seconds"] = phone_pen

    separations = max(0, mr.get("separation_penalties_count", 0) or 0)
    mr["separation_penalties_count"] = separations
    sep_pen = separations * separation_penalty_seconds
    mr["separation_penalty_seconds"] = sep_pen

    clue_deduction = max(0, mr.get("clue_tampering_deduction", 0) or 0)
    mr["clue_tampering_deduction"] = clue_deduction

    is_dq = bool(mr.get("is_disqualified", False))
    mr["is_disqualified"] = is_dq
    mr["disqualification_reason"] = mr.get("disqualification_reason") if is_dq else None

    total_time_penalty = hint_penalty + phone_pen + sep_pen

    start_str = mr.get("start_time")
    end_str = mr.get("completion_time")

    if start_str and end_str:
        try:
            start_dt = datetime.fromisoformat(str(start_str).replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(str(end_str).replace("Z", "+00:00"))
            if end_dt >= start_dt:
                duration = round((end_dt - start_dt).total_seconds())
                mr["duration_seconds"] = duration
                mr["adjusted_seconds"] = duration + total_time_penalty
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
    penalty_per_hint_seconds: int = 300,
    phone_penalty_seconds: int = 600,
    separation_penalty_seconds: int = 300
) -> Dict[str, Any]:
    updated_mini_rounds = [
        compute_mini_round(
            mr,
            penalty_per_hint_seconds=penalty_per_hint_seconds,
            phone_penalty_seconds=phone_penalty_seconds,
            separation_penalty_seconds=separation_penalty_seconds
        )
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

    total_hint_pen = sum(mr.get("hint_penalty_seconds", 0) or 0 for mr in updated_mini_rounds)
    total_phone_pen = sum(mr.get("phone_penalty_seconds", 0) or 0 for mr in updated_mini_rounds)
    total_sep_pen = sum(mr.get("separation_penalty_seconds", 0) or 0 for mr in updated_mini_rounds)
    total_penalty_seconds = total_hint_pen + total_phone_pen + total_sep_pen

    clue_deduction = sum(mr.get("clue_tampering_deduction", 0) or 0 for mr in updated_mini_rounds)
    is_dq = any(mr.get("is_disqualified", False) for mr in updated_mini_rounds)
    dq_reasons = [mr.get("disqualification_reason") for mr in updated_mini_rounds if mr.get("disqualification_reason")]
    dq_reason = dq_reasons[0] if dq_reasons else ("Disqualified" if is_dq else None)

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
    res["is_disqualified"] = is_dq
    res["disqualification_reason"] = dq_reason
    res["point_deductions"] = clue_deduction
    return res

def process_round1_standings(
    records: List[Dict[str, Any]],
    penalty_per_hint_seconds: int = 300,
    is_finalized: bool = False,
    phone_penalty_seconds: int = 600,
    separation_penalty_seconds: int = 300
) -> Dict[str, Any]:
    processed = [
        compute_team_totals(
            r,
            penalty_per_hint_seconds=penalty_per_hint_seconds,
            phone_penalty_seconds=phone_penalty_seconds,
            separation_penalty_seconds=separation_penalty_seconds
        )
        for r in records
    ]

    disqualified = [r for r in processed if r.get("is_disqualified")]
    completed = [r for r in processed if r.get("is_complete") and not r.get("is_disqualified")]
    incomplete = [r for r in processed if not r.get("is_complete") and not r.get("is_disqualified")]

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
                current["tie_reason"] = f"Tied with {prev['team_name']} (Adj: {current['adjusted_total_seconds']}s, Fastest Gate: {current['fastest_mini_round_seconds']}s)"
                prev["tie_reason"] = f"Tied with {current['team_name']} (Adj: {prev['adjusted_total_seconds']}s, Fastest Gate: {prev['fastest_mini_round_seconds']}s)"
                ties_count += 1

                # Check if straddles 16th cutoff boundary (rank 16 and rank 17)
                if i == 15 or i == 16:
                    cutoff_boundary_tie = True
                    tied_teams_at_cutoff.extend([prev["team_id"], current["team_id"]])
            else:
                current["tie_requires_review"] = False
                current["tie_reason"] = None
        else:
            current["tie_requires_review"] = False
            current["tie_reason"] = None

        current["rank"] = rank

        # Rank Points for Round 1: 1st=16, 2nd=15 ... 16th=1, 17th+=0
        if rank <= 16:
            current["rank_points"] = 17 - rank
        else:
            current["rank_points"] = 0

        deduction = current.get("point_deductions", 0) or 0
        current["net_score_points"] = current["rank_points"] - deduction

        if is_finalized:
            current["qualification_status"] = "Finalized Qualified" if rank <= 16 else "Finalized Eliminated"
        else:
            if current.get("tie_requires_review") and (rank == 16 or rank == 17):
                current["qualification_status"] = "Tie Review Needed"
            else:
                current["qualification_status"] = "Provisional Qualified" if rank <= 16 else "Provisional Eliminated"

    # Handle disqualified teams
    for dq in disqualified:
        dq["rank"] = None
        dq["rank_points"] = 0
        dq["net_score_points"] = -dq.get("point_deductions", 0)
        dq["tie_requires_review"] = False
        dq["tie_reason"] = None
        dq["qualification_status"] = "Disqualified"

    # Handle incomplete teams
    for inc in incomplete:
        inc["rank"] = None
        inc["rank_points"] = None
        inc["net_score_points"] = None
        inc["tie_requires_review"] = False
        inc["tie_reason"] = None
        inc["qualification_status"] = "Incomplete"

    all_records = completed + incomplete + disqualified

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
            "message": f"Results incomplete: {len(incomplete)} squad(s) have not completed all three gates."
        })
    if cutoff_boundary_tie:
        can_finalize = False
        issues.append({
            "code": "CUTOFF_TIE",
            "message": "Unresolved tie exists at the 16th qualification cutoff boundary. Manual marshal review required."
        })

    block_reason = issues[0]["message"] if issues else None
    top16_cutoff_time = completed[15]["adjusted_total_seconds"] if len(completed) >= 16 else None
    top24_cutoff_time = completed[23]["adjusted_total_seconds"] if len(completed) >= 24 else top16_cutoff_time

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
        "disqualified_count": len(disqualified),
        "top16_cutoff_time": top16_cutoff_time,
        "top24_cutoff_time": top24_cutoff_time
    }
