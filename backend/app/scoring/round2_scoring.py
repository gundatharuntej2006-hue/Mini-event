from typing import List, Dict, Any, Optional

def is_point_table_valid(point_table: Dict[Any, Any]) -> bool:
    if not isinstance(point_table, dict):
        return False
    for i in range(1, 25):
        val = point_table.get(i)
        if val is None:
            val = point_table.get(str(i))
        if val is None or not isinstance(val, (int, float)) or val < 0:
            return False
    return True

def get_points_for_placement(point_table: Dict[Any, Any], placement: Optional[int]) -> Optional[float]:
    if placement is None:
        return None
    val = point_table.get(placement)
    if val is None:
        val = point_table.get(str(placement))
    return float(val) if val is not None else None

def compute_team_round2_points(
    team_id: str,
    team_number: int,
    team_name: str,
    round1_qualified: bool,
    games_placements: List[Optional[int]],  # 3 placements
    point_table: Dict[Any, Any]
) -> Dict[str, Any]:
    g1_p = games_placements[0] if len(games_placements) > 0 else None
    g2_p = games_placements[1] if len(games_placements) > 1 else None
    g3_p = games_placements[2] if len(games_placements) > 2 else None

    g1_pts = get_points_for_placement(point_table, g1_p)
    g2_pts = get_points_for_placement(point_table, g2_p)
    g3_pts = get_points_for_placement(point_table, g3_p)

    games_completed = sum(1 for p in [g1_p, g2_p, g3_p] if p is not None)
    is_complete = games_completed == 3

    # NEVER treat missing results as zero
    total_points = None
    if is_complete and g1_pts is not None and g2_pts is not None and g3_pts is not None:
        total_points = g1_pts + g2_pts + g3_pts

    return {
        "team_id": team_id,
        "team_number": team_number,
        "team_name": team_name,
        "round1_qualified": round1_qualified,
        "game1_placement": g1_p,
        "game1_points": g1_pts,
        "game2_placement": g2_p,
        "game2_points": g2_pts,
        "game3_placement": g3_p,
        "game3_points": g3_pts,
        "total_points": total_points,
        "games_completed_count": games_completed,
        "is_complete": is_complete,
        "rank": None,
        "tie_requires_review": False,
        "tie_reason": None,
        "qualification_status": "Provisional Cutoff" if is_complete else "Incomplete"
    }

def process_round2_standings(
    records: List[Dict[str, Any]],
    config: Dict[str, Any],
    round1_finalized: bool
) -> Dict[str, Any]:
    scoring_direction = config.get("scoring_direction", "higher_is_better")
    is_higher_better = scoring_direction == "higher_is_better"
    point_table = config.get("point_table", {})
    is_finalized = config.get("is_finalized", False)

    complete_records = [r for r in records if r.get("is_complete") and r.get("total_points") is not None]
    incomplete_records = [r for r in records if not (r.get("is_complete") and r.get("total_points") is not None)]

    # Sort complete records
    def sort_key(r):
        pts = r["total_points"]
        return (-pts if is_higher_better else pts, r["team_number"])
    complete_records.sort(key=sort_key)

    # Group by score to detect ties
    score_groups = {}
    for r in complete_records:
        pts = r["total_points"]
        score_groups.setdefault(pts, []).append(r)

    current_rank = 1
    for r in complete_records:
        r["rank"] = current_rank
        current_rank += 1

    ties_affecting_cutoff = False
    tied_teams_at_cutoff = []

    # Cutoff is between Rank 12 (qualifying) and Rank 13 (eliminated)
    for pts, group in score_groups.items():
        if len(group) > 1:
            ranks = [r["rank"] for r in group]
            min_rank = min(ranks)
            max_rank = max(ranks)
            spans_cutoff = (min_rank <= 12 and max_rank >= 13)

            for r in group:
                if spans_cutoff:
                    r["tie_requires_review"] = True
                    r["tie_reason"] = f"Tied on {pts} total points spanning the 12th-place cutoff (Ranks #{min_rank}-#{max_rank}). Manual review required."
                    ties_affecting_cutoff = True
                    tied_teams_at_cutoff.append(r["team_id"])
                elif max_rank <= 12:
                    r["tie_reason"] = f"Tied on {pts} total points inside Top 12."
                else:
                    r["tie_reason"] = f"Tied on {pts} total points in elimination zone."

    for r in complete_records:
        if not round1_finalized:
            r["qualification_status"] = "Round 1 Pending"
        elif is_finalized:
            r["qualification_status"] = "Finalized Qualified" if r["rank"] <= 12 else "Finalized Eliminated"
        elif r.get("tie_requires_review"):
            r["qualification_status"] = "Tie Review Needed"
        elif r["rank"] <= 12:
            r["qualification_status"] = "Provisional Top 12"
        else:
            r["qualification_status"] = "Provisional Cutoff"

    for inc in incomplete_records:
        inc["rank"] = None
        inc["tie_requires_review"] = False
        inc["tie_reason"] = None
        inc["qualification_status"] = "Round 1 Pending" if not round1_finalized else "Incomplete"

    all_records = complete_records + incomplete_records

    can_finalize = True
    issues = []

    if not round1_finalized:
        can_finalize = False
        issues.append({
            "code": "PREVIOUS_ROUND_UNFINALIZED",
            "message": "Round 1 results are not yet officially finalized. Finalize Round 1 first."
        })
    if len(records) != 24:
        can_finalize = False
        issues.append({
            "code": "INVALID_TEAM_COUNT",
            "message": f"Expected exactly 24 qualified teams from Round 1, but found {len(records)}."
        })
    if len(incomplete_records) > 0:
        can_finalize = False
        issues.append({
            "code": "INCOMPLETE_RESULTS",
            "message": f"{len(incomplete_records)} squad(s) have incomplete Cabo game results. All 3 games must be recorded."
        })
    if not is_point_table_valid(point_table):
        can_finalize = False
        issues.append({
            "code": "INVALID_CONFIG",
            "message": "Placement points table is incomplete or invalid. All 24 placements must have valid non-negative points."
        })
    if ties_affecting_cutoff:
        can_finalize = False
        issues.append({
            "code": "CUTOFF_TIE",
            "message": "An unresolved tie affects the 12th-place qualification cutoff boundary. Manual marshal review required."
        })

    block_reason = issues[0]["message"] if issues else None

    top12_team_ids = [r["team_id"] for r in complete_records if r.get("rank") and r["rank"] <= 12]
    eliminated_team_ids = [r["team_id"] for r in complete_records if r.get("rank") and r["rank"] > 12]

    return {
        "records": all_records,
        "can_finalize": can_finalize,
        "issues": issues,
        "block_reason": block_reason,
        "ties_affecting_cutoff": ties_affecting_cutoff,
        "tied_teams_at_cutoff": list(set(tied_teams_at_cutoff)),
        "top12_team_ids": top12_team_ids,
        "eliminated_team_ids": eliminated_team_ids,
        "complete_count": len(complete_records),
        "incomplete_count": len(incomplete_records)
    }
