"""
Pure Championship Scoring Engine for Step 15.
Source of Truth: Reconciled Official Event Documentation.

Official Final Championship Score Formula:
    Final Score = Legal Battle Panel Score + Agent Guessing Points + (Remaining Black Market Wallet Points * carryover_weight)

Rules & Safeguards:
1. Exactly 8 finalists enter the Championship.
2. Legal Battle score is strictly from finalized Round 4 (0.0 to 100.0).
3. Agent Guessing Points come from Step 14:
   - Correct = +30.0
   - Wrong = -20.0
   - Unguessed = 0.0
4. Remaining Black Market points are the team's wallet balance after Round 3.
5. Default carryover weight is 10% (0.10) and is configurable.
6. All 3 components are preserved separately.
7. Under-the-hood scores (R4, Guessing, Wallet) are never modified when calculating composites.
8. Cutoff & Podium Ties:
   - Top 4: If rank 4 and rank 5 are tied, flag requires_organizer_review = True.
   - Top 3 / Podium: If ranks 1-3 are tied or rank 3 ties rank 4, flag requires_organizer_review = True.
   - No arbitrary mathematical tie-breakers are invented.
9. Best Secret Agent:
   - Tier 1: Most verified tasks (descending).
   - Tier 2: Fewest correct unmasking guesses received (ascending).
   - Tie: Flag tie_requires_review = True for organizer review.
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal, ROUND_HALF_UP

from app.core.constants import (
    DEFAULT_CARRYOVER_WEIGHT_PERCENT,
    AGENT_CORRECT_GUESS,
    AGENT_WRONG_GUESS,
    R4_ADVANCING_COUNT,
    PODIUM_SIZE,
)


def calculate_final_championship_score(
    legal_battle_score: Optional[float],
    agent_guessing_points: float,
    remaining_black_market_points: float,
    carryover_weight: float = 0.10,
) -> Dict[str, Any]:
    """
    Pure calculation of a squad's composite final championship score.

    Formula:
        Final Score = Legal Battle Panel Score + Agent Guessing Points + (Remaining Black Market Points * carryover_weight)

    Components are preserved separately.
    No premature rounding; values rounded to 2 decimal places for storage/display.
    """
    if legal_battle_score is not None and legal_battle_score < 0:
        raise ValueError("Legal Battle score cannot be negative.")

    if legal_battle_score is not None and legal_battle_score > 100.0:
        raise ValueError("Legal Battle score cannot exceed maximum of 100.0 points.")

    lb_comp = float(legal_battle_score) if legal_battle_score is not None else None
    ag_comp = float(agent_guessing_points)
    bm_balance = float(remaining_black_market_points)
    weight = float(carryover_weight)

    # Black market component = remaining_balance * carryover_weight
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


def calculate_championship_standings(
    finalist_records: List[Dict[str, Any]],
    carryover_weight: float = 0.10,
    expected_finalists: int = 8,
    round4_finalized: bool = True,
    guessing_finalized: bool = True,
) -> Dict[str, Any]:
    """
    Generates deterministic Grand Finale Championship standings for all 8 finalist squads.

    Evaluates:
    - 8 Finalist Count validation (fewer/more rejected).
    - Top 4 determination (ranks 1-4).
    - Top 4 cutoff tie detection (ranks 4 vs 5).
    - Top 3 / Podium placement determination ("Grand Champion", "1st Runner Up", "2nd Runner Up").
    - Podium tie detection.
    - Component preservation and audit checklist.
    """
    checklist: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []

    # 1. Check Round 4 Finalization
    checklist.append({
        "id": "round-4-finalized",
        "label": "Round 4: The Legal Battle Finalized",
        "passed": round4_finalized,
        "details": "Round 4 results must be officially finalized before championship standings can be sealed.",
    })
    if not round4_finalized:
        issues.append({
            "code": "PREVIOUS_ROUND_UNFINALIZED",
            "message": "Round 4: The Legal Battle must be finalized before championship standings can be sealed.",
        })

    # 2. Check Guessing Finalized
    checklist.append({
        "id": "guessing-finalized",
        "label": "Grand Finale Agent Guessing Completed",
        "passed": guessing_finalized,
        "details": "Secret Agent guessing must be finalized across all finalist squads.",
    })
    if not guessing_finalized:
        issues.append({
            "code": "GUESSING_UNFINALIZED",
            "message": "Secret Agent guessing must be completed before championship finalization.",
        })

    # 3. Finalist Count Validation (Must be exactly 8)
    actual_count = len(finalist_records)
    count_ok = (actual_count == expected_finalists)
    checklist.append({
        "id": "finalist-count",
        "label": f"Exactly {expected_finalists} Finalist Squads Participating",
        "passed": count_ok,
        "details": f"Found {actual_count} finalist squads (Expected: {expected_finalists}).",
    })
    if actual_count < expected_finalists:
        issues.append({
            "code": "FEWER_THAN_8_FINALISTS",
            "message": f"Expected exactly {expected_finalists} finalist squads, but found {actual_count} (fewer than 8).",
        })
    elif actual_count > expected_finalists:
        issues.append({
            "code": "MORE_THAN_8_FINALISTS",
            "message": f"Expected exactly {expected_finalists} finalist squads, but found {actual_count} (more than 8).",
        })

    # Calculate final scores for each record
    processed_records: List[Dict[str, Any]] = []
    all_scores_complete = True

    for r in finalist_records:
        r4_score = r.get("legal_battle_score")
        ag_points = float(r.get("agent_guessing_points", 0.0))
        wallet_bal = float(r.get("remaining_black_market_points", r.get("wallet_balance", 0.0)))

        breakdown = calculate_final_championship_score(
            legal_battle_score=r4_score,
            agent_guessing_points=ag_points,
            remaining_black_market_points=wallet_bal,
            carryover_weight=carryover_weight,
        )

        if breakdown["final_score"] is None:
            all_scores_complete = False

        record_copy = dict(r)
        record_copy["score_breakdown"] = breakdown
        record_copy["final_score"] = breakdown["final_score"]
        record_copy["legal_battle_score"] = breakdown["legal_battle_score"]
        record_copy["agent_guessing_points"] = breakdown["agent_guessing_points"]
        record_copy["remaining_black_market_points"] = breakdown["remaining_black_market_points"]
        record_copy["black_market_carryover_points"] = breakdown["black_market_component"]
        processed_records.append(record_copy)

    # Check score completeness
    checklist.append({
        "id": "scores-complete",
        "label": "All 8 Composite Scores Calculated",
        "passed": all_scores_complete and len(processed_records) > 0,
        "details": "All finalist squads have complete composite championship scores.",
    })
    if not all_scores_complete and len(processed_records) > 0:
        issues.append({
            "code": "INCOMPLETE_FINAL_SCORES",
            "message": "One or more finalist squads are missing Legal Battle scores or wallet balances.",
        })

    # Sort records deterministically by final_score descending, then team_number ascending
    def sort_key(rec):
        fs = rec.get("final_score")
        fs_val = fs if fs is not None else -999999.0
        return (-fs_val, rec.get("team_number", 999))

    processed_records.sort(key=sort_key)

    # Assign ranks and initial placement titles
    for idx, rec in enumerate(processed_records):
        rank = idx + 1
        rec["rank"] = rank
        rec["is_top_four"] = (rank <= 4)

        if rank == 1:
            rec["podium_position"] = 1
            rec["placement_title"] = "Grand Champion"
        elif rank == 2:
            rec["podium_position"] = 2
            rec["placement_title"] = "1st Runner Up"
        elif rank == 3:
            rec["podium_position"] = 3
            rec["placement_title"] = "2nd Runner Up"
        else:
            rec["podium_position"] = None
            rec["placement_title"] = "Finalist"

        rec["tie_requires_review"] = False
        rec["tie_reason"] = None

    # Detect Top 4 Cutoff Ties (Rank 4 vs Rank 5)
    top_four_tie_requires_review = False
    tied_top_four_teams: List[str] = []

    if len(processed_records) >= 5 and all_scores_complete:
        r4_score = processed_records[3].get("final_score")
        r5_score = processed_records[4].get("final_score")

        if r4_score is not None and r5_score is not None and r4_score == r5_score:
            top_four_tie_requires_review = True
            # Find all teams tied with rank 4 score
            tied_group = [
                rec for rec in processed_records
                if rec.get("final_score") == r4_score
            ]
            tied_top_four_teams = [rec["team_id"] for rec in tied_group]
            for rec in tied_group:
                rec["tie_requires_review"] = True
                rec["tie_reason"] = f"Tied at Top-4 cutoff position with score {r4_score}."

            issues.append({
                "code": "TOP_FOUR_CUTOFF_TIE",
                "message": f"Tie detected at Top-4 cutoff position between {len(tied_group)} squads ({', '.join(tied_top_four_teams)}). Organizer review required.",
                "tied_teams": tied_top_four_teams,
            })

    # Detect Podium Ties (Ranks 1, 2, 3)
    podium_tie_requires_review = False
    tied_podium_teams: List[str] = []

    if len(processed_records) >= 3 and all_scores_complete:
        scores = [rec.get("final_score") for rec in processed_records[:4] if rec.get("final_score") is not None]
        # Check if 1==2, 2==3, or 3==4
        if len(scores) >= 2 and scores[0] == scores[1]:
            podium_tie_requires_review = True
        if len(scores) >= 3 and scores[1] == scores[2]:
            podium_tie_requires_review = True
        if len(scores) >= 4 and scores[2] == scores[3]:
            podium_tie_requires_review = True

        if podium_tie_requires_review:
            # Group tied podium teams
            seen_scores = set()
            for rec in processed_records[:4]:
                sc = rec.get("final_score")
                if sc is not None:
                    count = sum(1 for r in processed_records if r.get("final_score") == sc)
                    if count > 1:
                        seen_scores.add(sc)

            tied_recs = [rec for rec in processed_records if rec.get("final_score") in seen_scores and rec.get("rank", 999) <= 4]
            tied_podium_teams = [rec["team_id"] for rec in tied_recs]
            for rec in tied_recs:
                rec["tie_requires_review"] = True
                rec["tie_reason"] = f"Tied for championship podium honors with score {rec.get('final_score')}."

            issues.append({
                "code": "PODIUM_TIE",
                "message": f"Podium placement tie detected between {len(tied_recs)} squads ({', '.join(tied_podium_teams)}). Organizer review required.",
                "tied_teams": tied_podium_teams,
            })

    # Overall tie review flag
    requires_organizer_review = top_four_tie_requires_review or podium_tie_requires_review

    # Can finalize gate
    can_finalize = (
        round4_finalized and
        guessing_finalized and
        count_ok and
        all_scores_complete and
        not top_four_tie_requires_review and
        not podium_tie_requires_review
    )

    top_four = processed_records[:4] if len(processed_records) >= 4 else processed_records
    top_three = processed_records[:3] if len(processed_records) >= 3 else processed_records

    champion_team_id = top_three[0]["team_id"] if len(top_three) > 0 and not podium_tie_requires_review else None
    runner_up1_team_id = top_three[1]["team_id"] if len(top_three) > 1 and not podium_tie_requires_review else None
    runner_up2_team_id = top_three[2]["team_id"] if len(top_three) > 2 and not podium_tie_requires_review else None

    return {
        "records": processed_records,
        "top_four": top_four,
        "top_three": top_three,
        "can_finalize": can_finalize,
        "issues": issues,
        "checklist": checklist,
        "requires_organizer_review": requires_organizer_review,
        "top_four_tie_requires_review": top_four_tie_requires_review,
        "tied_top_four_teams": tied_top_four_teams,
        "podium_tie_requires_review": podium_tie_requires_review,
        "tied_podium_teams": tied_podium_teams,
        "champion_team_id": champion_team_id,
        "runner_up1_team_id": runner_up1_team_id,
        "runner_up2_team_id": runner_up2_team_id,
    }


def calculate_best_secret_agent(
    dossiers: List[Dict[str, Any]],
    all_evaluated_guesses: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Calculates Best Secret Agent standings according to authoritative event rules:
    1. Primary: Most verified Secret Agent tasks (verified_tasks_count descending).
    2. Secondary: Fewest correct guesses received against that agent (correct_guesses_received ascending).
    3. Tie: If tied on both criteria, flags tie_requires_review = True.
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
        r["tie_requires_review"] = False
        r["tie_reason"] = None

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