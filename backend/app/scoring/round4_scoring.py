from typing import List, Dict, Any, Optional

def calculate_panel_score(
    judge_scores: List[Dict[str, Any]],
    aggregation: str = "average"
) -> Dict[str, Any]:
    submitted = [s for s in judge_scores if s.get("is_submitted")]
    if not submitted:
        return {"panel_score": None, "is_complete": False}

    scores = [float(s["total_score"]) for s in submitted]

    if aggregation == "single_judge":
        return {"panel_score": scores[0], "is_complete": True}
    elif aggregation == "sum":
        return {"panel_score": round(sum(scores), 2), "is_complete": True}
    else:  # average
        avg = round(sum(scores) / len(scores), 2)
        return {"panel_score": avg, "is_complete": True}

def calculate_final_score_breakdown(
    team_id: str,
    panel_score: Optional[float],
    agent_record: Optional[Dict[str, Any]],
    black_market_balance: float,
    formula: Dict[str, Any],
    is_guessing_configured: bool
) -> Dict[str, Any]:
    missing_components = []

    if not formula.get("isFormulaConfirmed"):
        missing_components.append("Final score formula unconfirmed by organizers")

    if panel_score is None:
        missing_components.append("Faculty judging panel score missing")

    agent_points = None
    if is_guessing_configured:
        if not agent_record or not agent_record.get("is_verified") or agent_record.get("points_awarded") is None:
            missing_components.append("Secret agent guessing score unverified")
        else:
            agent_points = float(agent_record["points_awarded"])
    else:
        agent_points = float(agent_record["points_awarded"]) if agent_record and agent_record.get("points_awarded") is not None else None

    panel_weight = float(formula.get("panelScoreWeight", 1.0))
    agent_weight = float(formula.get("agentGuessingWeight", 1.0))
    bm_weight_pct = float(formula.get("blackMarketWeightPercent", 10.0))

    weighted_panel = round(panel_score * panel_weight, 2) if panel_score is not None else None
    bm_contribution = round(max(0.0, float(black_market_balance)) * bm_weight_pct / 100.0, 2)

    is_complete = (len(missing_components) == 0 and panel_score is not None)
    final_score = None

    if is_complete:
        total = (weighted_panel or 0.0) + bm_contribution
        if agent_points is not None:
            total += agent_points * agent_weight
        final_score = round(total, 2)

    return {
        "team_id": team_id,
        "raw_panel_score": panel_score,
        "weighted_panel_score": weighted_panel,
        "agent_guessing_points": agent_points,
        "black_market_balance": black_market_balance,
        "black_market_contribution": bm_contribution,
        "final_score": final_score,
        "is_complete": is_complete,
        "missing_components": missing_components
    }

def process_round4_standings(
    records: List[Dict[str, Any]],
    pairs: List[Dict[str, Any]],
    config: Dict[str, Any],
    round3_finalized: bool
) -> Dict[str, Any]:
    checklist = []
    issues = []

    # 1. Round 3 finalized
    checklist.append({
        "id": "round-3-finalized",
        "label": "Round 3 Finalized",
        "passed": round3_finalized,
        "details": "Round 3 results must be finalized before Round 4 proceeds."
    })
    if not round3_finalized:
        issues.append({"code": "PREVIOUS_ROUND_UNFINALIZED", "message": "Round 3 results must be finalized before Round 4 proceeds."})

    # 2. Squad count == 8
    count_ok = len(records) == 8
    checklist.append({
        "id": "squad-count",
        "label": "Exactly 8 Finalist Squads Participating",
        "passed": count_ok,
        "details": f"Found {len(records)} squads (Expected: 8)."
    })
    if not count_ok:
        issues.append({"code": "INVALID_TEAM_COUNT", "message": f"Expected exactly 8 participating squads, found {len(records)}."})

    # 3. Pairings confirmed (4 pairs)
    pairs_ok = len(pairs) == 4 and all(p.get("team_a_id") and p.get("team_b_id") and p.get("is_confirmed") for p in pairs)
    checklist.append({
        "id": "pairings-confirmed",
        "label": "4 Team Matchup Pairings Confirmed",
        "passed": pairs_ok,
        "details": "All 4 head-to-head pairings must be confirmed."
    })
    if not pairs_ok:
        issues.append({"code": "PAIRINGS_UNCONFIRMED", "message": "All 4 head-to-head pairings must be created and confirmed by organizers."})

    # 4. Cases assigned
    cases_ok = len(pairs) == 4 and all(
        p.get("case_name") and
        p.get("team_a_side", "Unassigned") != "Unassigned" and
        p.get("team_b_side", "Unassigned") != "Unassigned"
        for p in pairs
    )
    checklist.append({
        "id": "cases-assigned",
        "label": "Fictional Legal Cases & Sides Assigned",
        "passed": cases_ok,
        "details": "Case names and team sides must be assigned for all pairs."
    })
    if not cases_ok:
        issues.append({"code": "CASES_UNASSIGNED", "message": "Case names and team sides must be assigned for all 4 pairs."})

    # 5. Stages completed
    def stages_done(p):
        stages = p.get("stages", {})
        h1 = stages.get("hearing_1", {}).get("status") == "completed"
        fe = stages.get("file_exchange", {}).get("status") == "completed"
        h2 = stages.get("hearing_2", {}).get("status") == "completed"
        return h1 and fe and h2

    hearings_ok = len(pairs) == 4 and all(stages_done(p) for p in pairs)
    checklist.append({
        "id": "hearings-completed",
        "label": "Hearing Stages & File Exchange Completed",
        "passed": hearings_ok,
        "details": "Hearings and file exchange must be logged as completed."
    })
    if not hearings_ok:
        issues.append({"code": "HEARINGS_INCOMPLETE", "message": "Hearing stages and file exchanges must be completed for all matchups."})

    # 6. Faculty judging complete
    judging_ok = len(records) == 8 and all(r.get("is_judge_panel_complete") and r.get("panel_score") is not None for r in records)
    checklist.append({
        "id": "judging-scores",
        "label": "Faculty Panel Scorecards Submitted",
        "passed": judging_ok,
        "details": "All finalist squads must have submitted judging scores."
    })
    if not judging_ok:
        issues.append({"code": "JUDGING_INCOMPLETE", "message": "Faculty judging scorecards are missing or incomplete." })

    # 7. Final score formula confirmed
    formula_confirmed = bool(config.get("final_score_formula", {}).get("isFormulaConfirmed", False))
    checklist.append({
        "id": "formula-confirmed",
        "label": "Final-Score Formula Confirmed",
        "passed": formula_confirmed,
        "details": "Scoring formula must be reviewed and confirmed by organizers."
    })
    if not formula_confirmed:
        issues.append({"code": "FORMULA_UNCONFIRMED", "message": "Final-score formula has not been confirmed by organizers." })

    # Sort records
    def sort_key(r):
        fs = r.get("final_score_breakdown", {}).get("final_score")
        ps = r.get("panel_score")
        fs_val = fs if fs is not None else -999999.0
        ps_val = ps if ps is not None else -999999.0
        return (-fs_val, -ps_val, r["team_number"])

    sorted_records = list(records)
    sorted_records.sort(key=sort_key)

    current_rank = 1
    for r in sorted_records:
        if r.get("final_score_breakdown", {}).get("final_score") is not None:
            r["rank"] = current_rank
            current_rank += 1
        else:
            r["rank"] = None

    # Check ties across advancing cutoff
    advancing_count = config.get("advancing_teams_count", 3) or 3
    ties_affecting_cutoff = False
    tied_teams_at_cutoff = []

    if 0 < advancing_count < len(sorted_records):
        score_groups = {}
        for r in sorted_records:
            fs = r.get("final_score_breakdown", {}).get("final_score")
            if fs is not None:
                score_groups.setdefault(fs, []).append(r)

        for fs, group in score_groups.items():
            if len(group) > 1:
                ranks = [r["rank"] for r in group if r.get("rank") is not None]
                if ranks:
                    min_rank = min(ranks)
                    max_rank = max(ranks)
                    if min_rank <= advancing_count and max_rank > advancing_count:
                        ties_affecting_cutoff = True
                        for r in group:
                            r["tie_requires_review"] = True
                            r["tie_reason"] = f"Tied on {fs} pts across advancing cutoff #{advancing_count}. Manual review required."
                            tied_teams_at_cutoff.append(r["team_id"])

    checklist.append({
        "id": "tie-safeguard",
        "label": "Advancement Cutoff Free of Unresolved Ties",
        "passed": not ties_affecting_cutoff,
        "details": "No cutoff-affecting ties detected." if not ties_affecting_cutoff else "Cutoff tie detected."
    })
    if ties_affecting_cutoff:
        issues.append({"code": "CUTOFF_TIE", "message": f"An unresolved tie spans across advancing cutoff #{advancing_count}. Manual review required."})

    can_finalize = len(issues) == 0
    block_reason = issues[0]["message"] if issues else None

    advancing_team_ids = [r["team_id"] for r in sorted_records if r.get("rank") and r["rank"] <= advancing_count]
    eliminated_team_ids = [r["team_id"] for r in sorted_records if r.get("rank") and r["rank"] > advancing_count]

    return {
        "records": sorted_records,
        "can_finalize": can_finalize,
        "issues": issues,
        "block_reason": block_reason,
        "checklist": checklist,
        "ties_affecting_cutoff": ties_affecting_cutoff,
        "tied_teams_at_cutoff": list(set(tied_teams_at_cutoff)),
        "advancing_team_ids": advancing_team_ids,
        "eliminated_team_ids": eliminated_team_ids
    }
