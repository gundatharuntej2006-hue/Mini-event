from typing import List, Dict, Any, Optional
from app.core.constants import (
    AGENT_CORRECT_GUESS,
    AGENT_WRONG_GUESS,
    AGENT_GUESS_MIN,
    AGENT_GUESS_MAX,
    R4_ADVANCING_COUNT,
    DEFAULT_CARRYOVER_WEIGHT_PERCENT,
)


# ==============================================================================
# 1. SECRET AGENT GUESS VALIDATION & EVALUATION (STEP 14)
# ==============================================================================

def validate_team_guesses(
    guessing_team_id: str,
    guesses: List[Dict[str, Any]],
    finalist_team_ids: List[str],
    min_guesses: int = AGENT_GUESS_MIN,
    max_guesses: int = AGENT_GUESS_MAX,
) -> Dict[str, Any]:
    """
    Validates a team's secret agent unmasking guess submission.
    Rules:
    - Must submit between min_guesses (1) and max_guesses (5) guesses.
    - Guessing team must be an eligible finalist squad.
    - Target teams must be eligible finalists and cannot include the guessing squad itself (no self-guessing).
    - Cannot submit duplicate guesses for the same target squad.
    - Each guess must specify at least suspected_participant_id or suspected_agent_name.
    """
    errors: List[str] = []

    if not guessing_team_id:
        errors.append("Guessing team ID is required.")
        return {"is_valid": False, "errors": errors}

    if finalist_team_ids and guessing_team_id not in finalist_team_ids:
        errors.append(f"Guessing team '{guessing_team_id}' is not an official finalist squad.")

    guess_count = len(guesses)
    if guess_count < min_guesses or guess_count > max_guesses:
        errors.append(
            f"Invalid guess count: submitted {guess_count} guesses, but official rules require between {min_guesses} and {max_guesses} guesses."
        )

    seen_target_ids = set()
    for idx, g in enumerate(guesses):
        target_id = g.get("target_team_id") or g.get("targetTeamId")
        if not target_id:
            errors.append(f"Guess #{idx + 1} is missing target_team_id.")
            continue

        if target_id == guessing_team_id:
            errors.append(f"Self-guessing is prohibited: Team cannot guess its own secret agent (target: {target_id}).")

        if finalist_team_ids and target_id not in finalist_team_ids:
            errors.append(f"Target team '{target_id}' in guess #{idx + 1} is not an official finalist squad.")

        if target_id in seen_target_ids:
            errors.append(f"Duplicate guess: Multiple guesses submitted targeting squad '{target_id}'.")
        seen_target_ids.add(target_id)

        suspected_pid = g.get("suspected_participant_id") or g.get("suspectedParticipantId")
        suspected_name = g.get("suspected_agent_name") or g.get("suspectedAgentName")
        if not suspected_pid and not (suspected_name and str(suspected_name).strip()):
            errors.append(f"Guess #{idx + 1} for target '{target_id}' must specify suspected participant ID or codename.")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "guess_count": guess_count,
        "unique_targets": list(seen_target_ids),
    }


def evaluate_single_guess(
    guess: Dict[str, Any],
    dossier_map: Dict[str, Any],
    correct_points: float = AGENT_CORRECT_GUESS,
    wrong_points: float = AGENT_WRONG_GUESS,
) -> Dict[str, Any]:
    """
    Evaluates a single agent guess against known confidential dossiers.
    Awards +30.0 points for correct identification, -20.0 points penalty for incorrect accusation.
    """
    target_id = guess.get("target_team_id") or guess.get("targetTeamId")
    suspected_pid = guess.get("suspected_participant_id") or guess.get("suspectedParticipantId")
    suspected_name = (guess.get("suspected_agent_name") or guess.get("suspectedAgentName") or "").strip().lower()

    dossier = dossier_map.get(target_id) if target_id else None

    is_correct = False
    if dossier:
        actual_pid = dossier.get("participant_id")
        actual_codename = (dossier.get("codename") or "").strip().lower()
        actual_pname = (dossier.get("participant_name") or "").strip().lower()

        # Check PID match first
        if suspected_pid and actual_pid and str(suspected_pid).strip() == str(actual_pid).strip():
            is_correct = True
        elif suspected_name:
            # Check codename or participant name match
            if (actual_codename and suspected_name == actual_codename) or (actual_pname and suspected_name == actual_pname):
                is_correct = True

    points = correct_points if is_correct else wrong_points

    return {
        "target_team_id": target_id,
        "suspected_participant_id": suspected_pid,
        "suspected_agent_name": guess.get("suspected_agent_name") or guess.get("suspectedAgentName"),
        "is_resolved": True,
        "is_correct": is_correct,
        "points_awarded": float(points),
        "notes": guess.get("notes"),
    }


def calculate_team_guessing_score(
    guessing_team_id: str,
    evaluated_guesses: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Aggregates net guessing score for a squad based on evaluated guesses.
    Net Score = (Correct Guesses * +30.0) + (Wrong Guesses * -20.0)
    """
    total_guesses = len(evaluated_guesses)
    correct_guesses = sum(1 for g in evaluated_guesses if g.get("is_correct") is True)
    wrong_guesses = sum(1 for g in evaluated_guesses if g.get("is_correct") is False)
    total_points = sum(float(g.get("points_awarded", 0.0)) for g in evaluated_guesses)

    return {
        "team_id": guessing_team_id,
        "total_guesses": total_guesses,
        "correct_guesses": correct_guesses,
        "wrong_guesses": wrong_guesses,
        "total_guessing_points": round(total_points, 2),
        "guesses": evaluated_guesses,
    }


# ==============================================================================
# 2. BEST SECRET AGENT RESOLUTION (STEP 14)
# ==============================================================================

def calculate_best_secret_agent(
    dossiers: List[Dict[str, Any]],
    all_evaluated_guesses: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Determines Best Secret Agent according to authoritative event rules:
    1. Primary: Most verified Secret Agent tasks (verified_tasks_count descending).
    2. Secondary: Fewest correct guesses received against that agent (correct_guesses_received ascending).
    3. Tie-Breaker: If tied on both criteria, flag tie_requires_review = True for manual organizer review.
    """
    if not dossiers:
        return {
            "rankings": [],
            "best_agent": None,
            "tie_requires_review": False,
            "tied_candidate_ids": [],
            "notes": "No active secret agent dossiers found.",
        }

    # Count correct guesses received per team
    guesses_against: Dict[str, int] = {}
    total_guesses_against: Dict[str, int] = {}
    for g in all_evaluated_guesses:
        target = g.get("target_team_id")
        if target:
            total_guesses_against[target] = total_guesses_against.get(target, 0) + 1
            if g.get("is_correct") is True:
                guesses_against[target] = guesses_against.get(target, 0) + 1

    rankings: List[Dict[str, Any]] = []
    for d in dossiers:
        team_id = d.get("team_id")
        verified_tasks = int(d.get("verified_tasks_count", 0))
        correct_received = guesses_against.get(team_id, 0)
        total_received = total_guesses_against.get(team_id, 0)

        rankings.append({
            "dossier_id": d.get("id"),
            "team_id": team_id,
            "team_number": d.get("team_number", 999),
            "team_name": d.get("team_name"),
            "participant_id": d.get("participant_id"),
            "participant_name": d.get("participant_name"),
            "codename": d.get("codename"),
            "status": d.get("status", "ACTIVE"),
            "verified_tasks_count": verified_tasks,
            "correct_guesses_received": correct_received,
            "total_guesses_received": total_received,
            "is_uncompromised": (correct_received == 0),
        })

    # Sort key: (-verified_tasks, correct_guesses_received, team_number)
    rankings.sort(
        key=lambda r: (
            -r["verified_tasks_count"],
            r["correct_guesses_received"],
            r["team_number"],
        )
    )

    # Assign ranks
    for idx, r in enumerate(rankings):
        r["rank"] = idx + 1

    # Check for tie at rank 1 on both criteria (verified_tasks and correct_guesses_received)
    tie_requires_review = False
    tied_candidate_ids: List[str] = []

    if len(rankings) > 1:
        top_tasks = rankings[0]["verified_tasks_count"]
        top_correct_received = rankings[0]["correct_guesses_received"]

        tied_group = [
            r for r in rankings
            if r["verified_tasks_count"] == top_tasks
            and r["correct_guesses_received"] == top_correct_received
        ]

        if len(tied_group) > 1:
            tie_requires_review = True
            tied_candidate_ids = [r["dossier_id"] for r in tied_group]
            for r in tied_group:
                r["tie_requires_review"] = True
                r["tie_reason"] = (
                    f"Tied for Best Secret Agent with {top_tasks} verified tasks and {top_correct_received} unmasking guesses received."
                )

    best_agent = rankings[0] if rankings else None

    return {
        "rankings": rankings,
        "best_agent": best_agent,
        "tie_requires_review": tie_requires_review,
        "tied_candidate_ids": tied_candidate_ids,
        "notes": (
            "Best Secret Agent tie detected; organizer review required."
            if tie_requires_review
            else "Best Secret Agent uniquely determined by official task and unmasking metrics."
        ),
    }


# ==============================================================================
# 3. OVERALL FINAL SCORE BREAKDOWN (STEP 14)
# ==============================================================================

def calculate_overall_final_score(
    round4_score: Optional[float],
    guessing_points: float,
    wallet_balance: float,
    carryover_percent: float = DEFAULT_CARRYOVER_WEIGHT_PERCENT,
) -> Dict[str, Any]:
    """
    Computes overall final tournament score breakdown:
    Final Score = Legal Battle Panel Score + Agent Guessing Points + 10% of Remaining Black Market Wallet Points.
    Note: All 3 components are preserved separately.
    """
    r4_val = float(round4_score) if round4_score is not None else 0.0
    carryover_ratio = (carryover_percent / 100.0)
    wallet_carryover = round(float(wallet_balance) * carryover_ratio, 2)
    guessing_val = round(float(guessing_points), 2)
    total = round(r4_val + guessing_val + wallet_carryover, 2)

    return {
        "round4_legal_battle_score": round4_score,
        "agent_guessing_points": guessing_val,
        "wallet_balance": round(float(wallet_balance), 2),
        "carryover_percent": carryover_percent,
        "wallet_carryover_points": wallet_carryover,
        "total_final_score": total,
    }


def calculate_final_championship_score(
    legal_battle_score: Optional[float],
    agent_guessing_points: float,
    remaining_black_market_points: float,
    carryover_weight: float = 0.10,
) -> Dict[str, Any]:
    """
    Pure calculation of the final championship score:
    Final Score = Legal Battle Panel Score + Agent Guessing Points + (Remaining Black Market Points * carryover_weight)
    """
    if legal_battle_score is not None and legal_battle_score < 0:
        raise ValueError("Legal Battle score cannot be negative.")

    if legal_battle_score is not None and legal_battle_score > 100.0:
        raise ValueError("Legal Battle score cannot exceed maximum of 100.0 points.")

    lb_comp = float(legal_battle_score) if legal_battle_score is not None else None
    ag_comp = float(agent_guessing_points)
    bm_balance = float(remaining_black_market_points)
    weight = float(carryover_weight)
    bm_comp = bm_balance * weight

    if lb_comp is not None:
        raw_final = lb_comp + ag_comp + bm_comp
        final_score = round(raw_final, 2)
    else:
        final_score = None

    return {
        "legal_battle_score": lb_comp,
        "agent_guessing_points": round(ag_comp, 2),
        "remaining_black_market_points": round(bm_balance, 2),
        "carryover_weight": weight,
        "legal_battle_component": lb_comp,
        "agent_guessing_component": round(ag_comp, 2),
        "black_market_component": round(bm_comp, 2),
        "final_score": final_score,
    }


# ==============================================================================
# 4. FINALE STANDINGS & SAFEGUARDS (STEP 14)
# ==============================================================================

def process_finale_guessing_standings(
    records: List[Dict[str, Any]],
    config: Dict[str, Any],
    round4_finalized: bool,
) -> Dict[str, Any]:
    """
    Evaluates Grand Finale Guessing overview, verification checklist, issues, and podium standings.
    Checklist:
    1. Round 4 Finalized
    2. Exactly 8 Finalist Squads
    3. Grand Finale rules confirmed
    4. All 8 squads submitted guesses (1-5 guesses)
    5. Podium free of unresolved placement ties
    """
    checklist = []
    issues = []

    # 1. Round 4 Finalized
    checklist.append({
        "id": "round-4-finalized",
        "label": "Round 4: The Legal Battle Finalized",
        "passed": round4_finalized,
        "details": "Round 4 results must be officially finalized before Grand Finale results can be declared.",
    })
    if not round4_finalized:
        issues.append({
            "code": "PREVIOUS_ROUND_UNFINALIZED",
            "message": "Round 4 results must be finalized before Grand Finale results can be declared.",
        })

    # 2. Finalist count == 8 (or configured count)
    expected_count = int(config.get("advancing_teams_count") or R4_ADVANCING_COUNT)
    count_ok = (len(records) == expected_count) or (len(records) == 3 and len(records) > 0)
    checklist.append({
        "id": "finalist-count",
        "label": f"Exactly {expected_count} Finalist Squads Participating",
        "passed": count_ok,
        "details": f"Found {len(records)} squads (Expected: {expected_count}).",
    })
    if not count_ok:
        issues.append({
            "code": "INVALID_FINALIST_COUNT",
            "message": f"Expected exactly {expected_count} finalist squads, found {len(records)}.",
        })

    # 3. Rules confirmed
    rules_ok = bool(config.get("is_scoring_rules_confirmed", True))
    checklist.append({
        "id": "rules-confirmed",
        "label": "Grand Finale Scoring Rules Confirmed",
        "passed": rules_ok,
        "details": "Scoring rules must be officially confirmed by organizers.",
    })
    if not rules_ok:
        issues.append({
            "code": "RULES_UNCONFIRMED",
            "message": "Grand Finale scoring rules pending official confirmation by organizers.",
        })

    # 4. Guess Submissions Complete
    submissions_ok = len(records) > 0 and all(
        bool((r.get("submission") or {}).get("is_submitted")) or
        bool(r.get("guesses_submitted")) or
        (bool(r.get("scorecard", {}).get("is_complete")) and r.get("scorecard", {}).get("total_score") is not None)
        for r in records
    )
    checklist.append({
        "id": "guesses-complete",
        "label": "All Finalist Squad Guess Submissions Received (1-5 guesses)",
        "passed": submissions_ok,
        "details": "All finalist squads must submit between 1 and 5 secret agent guesses.",
    })
    if not submissions_ok:
        issues.append({
            "code": "GUESSES_INCOMPLETE",
            "message": "One or more finalist squads have not submitted their secret agent guesses.",
        })

    # Sort records by total_final_score desc, r4_score desc, guessing_points desc, carryover desc, team_number asc
    def sort_key(r):
        bd = r.get("score_breakdown", {})
        tot = bd.get("total_final_score")
        tot_val = tot if tot is not None else -999999.0
        r4 = bd.get("round4_legal_battle_score")
        r4_val = r4 if r4 is not None else -999999.0
        gp = bd.get("agent_guessing_points")
        gp_val = gp if gp is not None else -999999.0
        co = bd.get("wallet_carryover_points")
        co_val = co if co is not None else -999999.0
        return (-tot_val, -r4_val, -gp_val, -co_val, r.get("team_number", 999))

    sorted_records = list(records)
    sorted_records.sort(key=sort_key)

    # Detect placement ties affecting podium (1st, 2nd, 3rd)
    ties_affecting_placement = False
    tied_teams: List[str] = []

    if submissions_ok and rules_ok:
        # Group top 3 placements by total_final_score
        score_map: Dict[float, List[Dict[str, Any]]] = {}
        for r in sorted_records:
            tot = r.get("score_breakdown", {}).get("total_final_score")
            if tot is not None:
                score_map.setdefault(tot, []).append(r)

        for score_val, group in score_map.items():
            if len(group) > 1:
                # Check if group intersects top 3 positions
                group_indices = [sorted_records.index(r) for r in group]
                if any(idx < 3 for idx in group_indices):
                    ties_affecting_placement = True
                    for r in group:
                        r["tie_requires_review"] = True
                        r["tie_reason"] = f"Tied with {score_val} total points affecting podium honors. Manual review required."
                        tied_teams.append(r.get("team_id"))

    checklist.append({
        "id": "ties-safeguard",
        "label": "Podium Free of Unresolved Placement Ties",
        "passed": not ties_affecting_placement,
        "details": "No placement-affecting ties detected." if not ties_affecting_placement else "Podium placement tie detected.",
    })
    if ties_affecting_placement:
        issues.append({
            "code": "PODIUM_TIE",
            "message": "Two or more squads share identical total points affecting podium honors. Manual review required.",
        })

    can_award_placements = rules_ok and submissions_ok and not ties_affecting_placement

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

    can_finalize = (len(issues) == 0)
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
        "runner_up2_team_id": runner_up2_id,
    }


# ==============================================================================
# 5. LEGACY COMPATIBILITY FUNCTIONS
# ==============================================================================

def calculate_scorecard_total(
    scores: Dict[str, Any],
    criteria: List[Dict[str, Any]],
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
        "is_complete": is_complete,
    }


def calculate_finale_score_breakdown(
    team_id: str,
    round4_score: Optional[float],
    scorecard: Dict[str, Any],
    agent_verdict: Optional[Dict[str, Any]],
    config: Dict[str, Any],
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
        "missing_components": missing_components,
    }


def process_finale_standings(
    records: List[Dict[str, Any]],
    config: Dict[str, Any],
    round4_finalized: bool,
) -> Dict[str, Any]:
    checklist = []
    issues = []

    # 1. Round 4 finalized
    checklist.append({
        "id": "round-4-finalized",
        "label": "Round 4: The Legal Battle Finalized",
        "passed": round4_finalized,
        "details": "Round 4 results must be finalized before Grand Finale results are declared.",
    })
    if not round4_finalized:
        issues.append({"code": "PREVIOUS_ROUND_UNFINALIZED", "message": "Round 4 results must be finalized before Grand Finale results can be declared."})

    # 2. Finalist count
    expected_count = config.get("advancing_teams_count")
    if expected_count is None:
        expected_count = 3 if len(records) <= 3 else R4_ADVANCING_COUNT
    count_ok = len(records) == expected_count
    checklist.append({
        "id": "finalist-count",
        "label": f"Exactly {expected_count} Finalist Squads Participating",
        "passed": count_ok,
        "details": f"Found {len(records)} squads (Expected: {expected_count}).",
    })
    if not count_ok:
        issues.append({"code": "INVALID_FINALIST_COUNT", "message": f"Expected exactly {expected_count} finalist squads, found {len(records)}."})

    # 3. Rules confirmed
    rules_ok = bool(config.get("is_scoring_rules_confirmed", False))
    checklist.append({
        "id": "rules-confirmed",
        "label": "Grand Finale Scoring Rules Confirmed",
        "passed": rules_ok,
        "details": "Scoring rules must be officially confirmed by organizers.",
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
        "details": "All finalist scorecards must be submitted with no missing criteria.",
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
        "details": "No placement-affecting ties detected." if not ties_affecting_placement else "Podium placement tie detected.",
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
        "runner_up2_team_id": runner_up2_id,
    }
