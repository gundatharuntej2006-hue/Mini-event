from typing import List, Dict, Any, Optional

def calculate_scorecard_total(
    scores: Dict[str, Any],
    criteria: List[Dict[str, Any]]
) -> Dict[str, Any]:
    total = 0.0
    is_complete = True

    for crit in criteria:
        cid = crit["id"]
        val = scores.get(cid)
        if val is None:
            is_complete = False
        else:
            try:
                total += float(val)
            except Exception:
                is_complete = False

    return {
        "total_score": round(total, 2) if is_complete else None,
        "is_complete": is_complete
    }

def calculate_finale_score_breakdown(
    team_id: str,
    round4_score: Optional[float],
    scorecard: Dict[str, Any],
    agent_verdict: Optional[Dict[str, Any]],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    missing_components = []

    if not config.get("is_scoring_rules_confirmed"):
        missing_components.append("Grand Finale scoring rules pending official confirmation")

    if not scorecard.get("is_complete") or scorecard.get("total_score") is None:
        missing_components.append("Grand Finale activity scorecard is incomplete or unsubmitted")

    r4_carried = config.get("round4_score_carried_over", True)
    if r4_carried and round4_score is None:
        missing_components.append("Round 4 carried score is missing")

    r4_weight = float(config.get("round4_score_weight", 0.2))
    finale_weight = float(config.get("finale_activity_weight", 1.0))

    r4_contribution = round(round4_score * r4_weight, 2) if (r4_carried and round4_score is not None) else 0.0
    sc_total = scorecard.get("total_score")
    finale_activity_contribution = round(sc_total * finale_weight, 2) if sc_total is not None else None

    agent_adj = 0.0
    if agent_verdict and agent_verdict.get("is_verified"):
        if agent_verdict.get("is_correct") is True and agent_verdict.get("bonus_points") is not None:
            agent_adj += float(agent_verdict["bonus_points"])
        elif agent_verdict.get("is_correct") is False and agent_verdict.get("penalty_points") is not None:
            agent_adj -= float(agent_verdict["penalty_points"])

    is_complete = (len(missing_components) == 0 and finale_activity_contribution is not None)
    total_score = None
    if is_complete:
        total_score = round(r4_contribution + (finale_activity_contribution or 0.0) + agent_adj, 2)

    return {
        "team_id": team_id,
        "round4_carried_score": round4_score,
        "round4_weight": r4_weight,
        "round4_contribution": r4_contribution,
        "finale_activity_score": sc_total,
        "finale_activity_weight": finale_weight,
        "finale_activity_contribution": finale_activity_contribution,
        "agent_adjustment": agent_adj,
        "total_finale_score": total_score,
        "is_complete": is_complete,
        "missing_components": missing_components
    }

def process_finale_standings(
    records: List[Dict[str, Any]],
    config: Dict[str, Any],
    round4_finalized: bool
) -> Dict[str, Any]:
    checklist = []
    issues = []

    # 1. Round 4 finalized
    checklist.append({
        "id": "round-4-finalized",
        "label": "Round 4: The Legal Battle Finalized",
        "passed": round4_finalized,
        "details": "Round 4 results must be finalized before Grand Finale results are declared."
    })
    if not round4_finalized:
        issues.append({"code": "PREVIOUS_ROUND_UNFINALIZED", "message": "Round 4 results must be finalized before Grand Finale results can be declared."})

    # 2. Finalist count == 3
    count_ok = len(records) == 3
    checklist.append({
        "id": "finalist-count",
        "label": "Exactly 3 Finalist Squads Participating",
        "passed": count_ok,
        "details": f"Found {len(records)} squads (Expected: 3)."
    })
    if not count_ok:
        issues.append({"code": "INVALID_FINALIST_COUNT", "message": f"Expected exactly 3 finalist squads, found {len(records)}."})

    # 3. Rules confirmed
    rules_ok = bool(config.get("is_scoring_rules_confirmed", False))
    checklist.append({
        "id": "rules-confirmed",
        "label": "Grand Finale Scoring Rules Confirmed",
        "passed": rules_ok,
        "details": "Scoring rules must be officially confirmed by organizers."
    })
    if not rules_ok:
        issues.append({"code": "RULES_UNCONFIRMED", "message": "Grand Finale scoring rules pending official confirmation by organizers."})

    # 4. Scorecards complete
    scorecards_ok = len(records) > 0 and all(
        r.get("scorecard", {}).get("is_complete") and
        r.get("score_breakdown", {}).get("total_finale_score") is not None
        for r in records
    )
    checklist.append({
        "id": "scorecards-complete",
        "label": "All Finalist Scorecards Submitted & Complete",
        "passed": scorecards_ok,
        "details": "All finalist scorecards must be submitted with no missing criteria."
    })
    if not scorecards_ok:
        issues.append({"code": "SCORES_INCOMPLETE", "message": "One or more finalist scorecards are missing or incomplete." })

    # Sort records by total_finale_score desc
    scoring_dir = config.get("scoring_direction", "higher_wins")
    is_higher_wins = scoring_dir == "higher_wins"

    def sort_key(r):
        sc = r.get("score_breakdown", {}).get("total_finale_score")
        sc_val = sc if sc is not None else -999999.0
        r4 = r.get("round4_score")
        r4_val = r4 if r4 is not None else -999999.0
        return (-sc_val if is_higher_wins else sc_val, -r4_val, r["team_number"])

    sorted_records = list(records)
    sorted_records.sort(key=sort_key)

    # Detect placement ties affecting podium
    ties_affecting_placement = False
    tied_teams = []

    if scorecards_ok and rules_ok:
        score_map = {}
        for r in sorted_records:
            sc = r.get("score_breakdown", {}).get("total_finale_score")
            if sc is not None:
                score_map.setdefault(sc, []).append(r)

        for sc, group in score_map.items():
            if len(group) > 1:
                ties_affecting_placement = True
                for r in group:
                    r["tie_requires_review"] = True
                    r["tie_reason"] = f"Tied with {sc} pts for podium placement. Manual review required."
                    tied_teams.append(r["team_id"])

    checklist.append({
        "id": "ties-safeguard",
        "label": "Podium Free of Unresolved Placement Ties",
        "passed": not ties_affecting_placement,
        "details": "No placement-affecting ties detected." if not ties_affecting_placement else "Podium placement tie detected."
    })
    if ties_affecting_placement:
        issues.append({"code": "PODIUM_TIE", "message": "Two or more squads share identical total points affecting podium honors. Manual review required."})

    can_award_placements = rules_ok and scorecards_ok and not ties_affecting_placement

    for idx, rec in enumerate(sorted_records):
        if can_award_placements:
            placement = idx + 1
            rec["placement"] = placement
            if placement == 1:
                rec["placement_title"] = "Grand Champion"
            elif placement == 2:
                rec["placement_title"] = "1st Runner Up"
            elif placement == 3:
                rec["placement_title"] = "2nd Runner Up"
            else:
                rec["placement_title"] = None
        else:
            rec["placement"] = None
            rec["placement_title"] = None

    can_finalize = len(issues) == 0
    block_reason = issues[0]["message"] if issues else None

    champion_id = sorted_records[0]["team_id"] if (can_award_placements and len(sorted_records) > 0) else None
    runner_up1_id = sorted_records[1]["team_id"] if (can_award_placements and len(sorted_records) > 1) else None
    runner_up2_id = sorted_records[2]["team_id"] if (can_award_placements and len(sorted_records) > 2) else None

    return {
        "records": sorted_records,
        "can_finalize": can_finalize,
        "issues": issues,
        "block_reason": block_reason,
        "checklist": checklist,
        "ties_affecting_placement": ties_affecting_placement,
        "tied_teams": list(set(tied_teams)),
        "champion_team_id": champion_id,
        "runner_up1_team_id": runner_up1_id,
        "runner_up2_team_id": runner_up2_id
    }
