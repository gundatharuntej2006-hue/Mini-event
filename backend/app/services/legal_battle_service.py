"""
Legal Battle (Round 4) Service Layer.
Implements the official Round 4 Moot Court mechanics, case assignments,
resource person questioning, rubric-based faculty judging, panel aggregation,
and NO-ELIMINATION advancement to the Grand Finale.
"""

from app.services.round4_service import (
    get_or_create_round4_config,
    ensure_round4_pairs,
    auto_pair_round4_teams,
    update_round4_config,
    update_pair,
    confirm_pairings,
    unlock_pairings,
    update_pair_case,
    record_resource_person_question,
    update_stage_timing,
    submit_judge_score,
    submit_agent_guess,
    get_round4_overview,
    finalize_round4,
    OFFICIAL_R4_CASES,
    STAGE_IDS,
)

from app.scoring.round4_scoring import (
    validate_rubric_scores,
    calculate_legal_battle_score,
    calculate_panel_score,
    calculate_final_score_breakdown,
    process_round4_standings,
    RUBRIC_CANONICAL_KEYS,
    RUBRIC_KEY_ALIASES,
    DEFAULT_CATEGORY_LIMITS,
)

__all__ = [
    "get_or_create_round4_config",
    "ensure_round4_pairs",
    "auto_pair_round4_teams",
    "update_round4_config",
    "update_pair",
    "confirm_pairings",
    "unlock_pairings",
    "update_pair_case",
    "record_resource_person_question",
    "update_stage_timing",
    "submit_judge_score",
    "submit_agent_guess",
    "get_round4_overview",
    "finalize_round4",
    "validate_rubric_scores",
    "calculate_legal_battle_score",
    "calculate_panel_score",
    "calculate_final_score_breakdown",
    "process_round4_standings",
    "OFFICIAL_R4_CASES",
    "STAGE_IDS",
    "RUBRIC_CANONICAL_KEYS",
    "RUBRIC_KEY_ALIASES",
    "DEFAULT_CATEGORY_LIMITS",
]
