from typing import List, Dict, Any, Optional
from app.core.constants import (
    R4_FINALISTS,
    R4_ADVANCING_COUNT,
    R4_RUBRIC_LOGICAL_STRUCTURE_MAX,
    R4_RUBRIC_EVIDENCE_MAX,
    R4_RUBRIC_REBUTTAL_MAX,
    R4_RUBRIC_RESOURCE_PERSON_MAX,
    R4_RUBRIC_PRESENTATION_TEAMWORK_MAX,
    R4_RUBRIC_TIME_MAX,
    R4_RUBRIC_TOTAL_MAX,
    R4_RUBRIC_LIMITS,
)

# Canonical rubric criteria keys
RUBRIC_CANONICAL_KEYS = [
    "logical_structure",
    "evidence",
    "rebuttal",
    "resource_person_questioning",
    "presentation_teamwork",
    "time",
]

RUBRIC_KEY_ALIASES = {
    "logical_structure": "logical_structure",
    "evidence": "evidence",
    "evidence_use": "evidence",
    "rebuttal": "rebuttal",
    "resource_person_questioning": "resource_person_questioning",
    "resource_questioning": "resource_person_questioning",
    "presentation_teamwork": "presentation_teamwork",
    "time": "time",
    "time_management": "time",
}

DEFAULT_CATEGORY_LIMITS = {
    "logical_structure": R4_RUBRIC_LOGICAL_STRUCTURE_MAX,  # 20.0
    "evidence": R4_RUBRIC_EVIDENCE_MAX,                    # 20.0
    "evidence_use": R4_RUBRIC_EVIDENCE_MAX,                # 20.0
    "rebuttal": R4_RUBRIC_REBUTTAL_MAX,                    # 20.0
    "resource_person_questioning": R4_RUBRIC_RESOURCE_PERSON_MAX,  # 15.0
    "resource_questioning": R4_RUBRIC_RESOURCE_PERSON_MAX,          # 15.0
    "presentation_teamwork": R4_RUBRIC_PRESENTATION_TEAMWORK_MAX,  # 15.0
    "time": R4_RUBRIC_TIME_MAX,                            # 10.0
    "time_management": R4_RUBRIC_TIME_MAX,                 # 10.0
}

LEGACY_CATEGORY_LIMITS = {
    "arguments": 30.0,
    "crossExam": 25.0,
    "cross_exam": 25.0,
    "evidence": 25.0,
    "demeanor": 20.0,
}


def normalize_rubric_key(key: str) -> str:
    """Normalize alias keys to canonical rubric keys."""
    return RUBRIC_KEY_ALIASES.get(key, key)


def validate_rubric_scores(
    scores: Dict[str, float],
    rubric_categories: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, float]:
    """
    Validates that:
    1. Score values are non-negative.
    2. Category marks do not exceed defined maximums for defined criteria.
    3. Total score does not exceed 100.0 (or custom rubric maximum).
    """
    if not scores:
        raise ValueError("Judge scorecard scores cannot be empty.")

    is_legacy_format = any(k in ("arguments", "crossExam", "cross_exam", "demeanor") for k in scores)

    known_limits: Dict[str, float] = {}
    if is_legacy_format:
        known_limits.update(LEGACY_CATEGORY_LIMITS)
    elif rubric_categories:
        for cat in rubric_categories:
            cat_id = cat.get("id")
            if cat_id:
                max_m = float(cat.get("maxMarks", 20.0))
                known_limits[cat_id] = max_m
                norm_k = normalize_rubric_key(cat_id)
                known_limits[norm_k] = max_m
    else:
        for k, v in DEFAULT_CATEGORY_LIMITS.items():
            known_limits[k] = v

    normalized: Dict[str, float] = {}
    total = 0.0

    for raw_key, raw_val in scores.items():
        try:
            val = float(raw_val)
        except (TypeError, ValueError):
            raise ValueError(f"Score for '{raw_key}' must be a numeric value, got '{raw_val}'.")

        if val < 0.0:
            raise ValueError(f"Score for '{raw_key}' cannot be negative (got {val}).")

        # Check limit if key is in known_limits
        max_allowed = known_limits.get(raw_key)
        if max_allowed is None:
            norm_k = normalize_rubric_key(raw_key)
            if norm_k in known_limits:
                max_allowed = known_limits[norm_k]

        if max_allowed is not None and val > max_allowed:
            raise ValueError(
                f"Score {val} for '{raw_key}' exceeds maximum allowed marks of {max_allowed}."
            )
        elif max_allowed is None and val > R4_RUBRIC_TOTAL_MAX:
            raise ValueError(
                f"Score {val} for '{raw_key}' exceeds maximum rubric limit of {R4_RUBRIC_TOTAL_MAX}."
            )

        normalized[raw_key] = val
        total += val

    max_total = R4_RUBRIC_TOTAL_MAX
    if total > max_total:
        raise ValueError(f"Total score {round(total, 2)} exceeds maximum rubric limit of {max_total}.")

    return normalized


def calculate_legal_battle_score(
    logical_structure: float,
    evidence: float,
    rebuttal: float,
    resource_person_questioning: float,
    presentation_teamwork: float,
    time: float
) -> float:
    """
    Direct calculation function accepting the 6 official rubric criteria out of 100.
    """
    scores = {
        "logical_structure": logical_structure,
        "evidence": evidence,
        "rebuttal": rebuttal,
        "resource_person_questioning": resource_person_questioning,
        "presentation_teamwork": presentation_teamwork,
        "time": time,
    }
    validated = validate_rubric_scores(scores)
    return round(sum(validated.values()), 2)


def calculate_panel_score(
    judge_scores: List[Dict[str, Any]],
    aggregation: str = "average"
) -> Dict[str, Any]:
    """
    Aggregates multi-judge scorecards for a squad.
    """
    submitted = [s for s in judge_scores if s.get("is_submitted")]
    if not submitted:
        return {"panel_score": None, "is_complete": False, "submitted_count": 0}

    scores = [float(s["total_score"]) for s in submitted]

    if aggregation == "single_judge":
        return {"panel_score": scores[0], "is_complete": True, "submitted_count": len(scores)}
    elif aggregation == "sum":
        return {"panel_score": round(sum(scores), 2), "is_complete": True, "submitted_count": len(scores)}
    elif aggregation == "median":
        sorted_s = sorted(scores)
        n = len(sorted_s)
        med = sorted_s[n // 2] if n % 2 != 0 else (sorted_s[n // 2 - 1] + sorted_s[n // 2]) / 2.0
        return {"panel_score": round(med, 2), "is_complete": True, "submitted_count": len(scores)}
    else:  # default: average
        avg = round(sum(scores) / len(scores), 2)
        return {"panel_score": avg, "is_complete": True, "submitted_count": len(scores)}


def calculate_final_score_breakdown(
    team_id: str,
    panel_score: Optional[float],
    agent_record: Optional[Dict[str, Any]] = None,
    black_market_balance: float = 0.0,
    formula: Optional[Dict[str, Any]] = None,
    is_guessing_configured: bool = False
) -> Dict[str, Any]:
    """
    Calculates the team's official Round 4 Legal Battle score breakdown.

    OFFICIAL EVENT RULES:
    1. The Round 4 Legal Battle score is STRICTLY based on the official 100-point Legal Battle rubric:
       - Logical Structure: 20 max
       - Evidence: 20 max
       - Rebuttal: 20 max
       - Resource Person Questioning: 15 max
       - Presentation / Teamwork: 15 max
       - Time: 10 max
       - TOTAL: 100 max
    2. Secret Agent guessing bonuses/penalties and Black Market balances are NOT included in the
       Round 4 Legal Battle score (Secret Agent guessing is officially scored in the Finale / Step 14).
    3. The team's score equals their pure panel score out of 100.
    """
    missing_components = []
    if panel_score is None:
        missing_components.append("Faculty judging panel score missing")

    is_complete = (panel_score is not None)
    final_score = round(panel_score, 2) if panel_score is not None else None

    return {
        "team_id": team_id,
        "raw_panel_score": panel_score,
        "weighted_panel_score": panel_score,
        "agent_guessing_points": None,  # Not part of Round 4 Legal Battle score
        "black_market_balance": black_market_balance,
        "black_market_contribution": 0.0,  # Not added to Round 4 Legal Battle score
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
        issues.append({"code": "JUDGING_INCOMPLETE", "message": "Faculty judging scorecards are missing or incomplete."})

    # 7. Rubric confirmation
    rubric_confirmed = bool(config.get("is_rubric_confirmed", True))
    checklist.append({
        "id": "rubric-confirmed",
        "label": "Legal Battle Rubric Confirmed",
        "passed": rubric_confirmed,
        "details": "Official 100-point Legal Battle rubric confirmed."
    })

    # Sort records strictly by pure panel_score descending, then team_number
    def sort_key(r):
        ps = r.get("panel_score")
        ps_val = ps if ps is not None else -999999.0
        return (-ps_val, r.get("team_number", 999))

    sorted_records = list(records)
    sorted_records.sort(key=sort_key)

    current_rank = 1
    for r in sorted_records:
        if r.get("final_score_breakdown", {}).get("final_score") is not None:
            r["rank"] = current_rank
            current_rank += 1
        else:
            r["rank"] = None

    # CRITICAL: Under official rules, advancing_teams_count defaults to 8 (NO ELIMINATION)
    advancing_count = config.get("advancing_teams_count", R4_ADVANCING_COUNT)
    if advancing_count is None:
        advancing_count = R4_ADVANCING_COUNT

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

    # Mark advancing status for each record
    for r in sorted_records:
        r["is_advancing"] = bool(r.get("rank") and r["rank"] <= advancing_count)

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
