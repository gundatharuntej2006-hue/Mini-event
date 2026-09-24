"""
Unit tests for EVENT HQ Canonical Tournament Constants and Rules Specification.
Verifies all mandatory tournament rules, placement scales, wallet balance,
advancement cutoffs, agent guessing parameters, and pending decision sentinels
against the authoritative Event Documentation (Reconciled in Step 6B).
"""

import pytest
from app.core.constants import (
    MAX_TEAMS,
    TEAM_SIZE,
    R1_QUALIFIERS,
    R2_QUALIFIERS,
    R3_QUALIFIERS,
    R4_FINALISTS,
    PODIUM_SIZE,
    DEFAULT_R1_HINT_PENALTY_SECONDS,
    DEFAULT_R1_CHECKPOINTS,
    R1_WALLET_POINTS_FORMULA,
    CABO_PLACEMENT_POINTS,
    CABO_GAMES,
    CABO_TABLE_SIZE,
    CABO_MAX_TEAM_SCORE,
    STARTING_WALLET_BALANCE,
    BLACK_MARKET_SUGGESTED_PRICES,
    BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED,
    BLACK_MARKET_PREP_PRICE_SUGGESTED,
    BLACK_MARKET_WITNESS_PRICE_SUGGESTED,
    BLACK_MARKET_AGENT_INTEL_PRICE_SUGGESTED,
    CODE_FRAGMENT_COUNT,
    FINAL_CODE_REQUIRED_FOR_R4,
    AGENT_TASK_REWARD,
    PENALTY_MIN,
    PENALTY_MAX,
    AGENT_GUESS_MIN,
    AGENT_GUESS_MAX,
    AGENT_CORRECT_GUESS,
    AGENT_WRONG_GUESS,
    FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED,
    DEFAULT_CARRYOVER_WEIGHT_PERCENT,
)


class TestTournamentStructureConstants:
    def test_team_capacity_and_size(self):
        """Mandatory: Maximum 32 teams, 5 members per team."""
        assert MAX_TEAMS == 32
        assert TEAM_SIZE == 5

    def test_progression_advancement_cutoffs(self):
        """Mandatory: 32 -> 24 (R1) -> 12 (R2) -> 8 (R3) -> 8 (R4 finalists)."""
        assert R1_QUALIFIERS == 24
        assert R2_QUALIFIERS == 12
        assert R3_QUALIFIERS == 8
        assert R4_FINALISTS == 8
        assert PODIUM_SIZE == 3


class TestRound1ExpeditionConstants:
    def test_default_hint_penalty(self):
        """Default hint penalty is 120 seconds (2 minutes)."""
        assert DEFAULT_R1_HINT_PENALTY_SECONDS == 120

    def test_checkpoints_list(self):
        """Default checkpoint configuration has 3 mystery stations."""
        assert len(DEFAULT_R1_CHECKPOINTS) == 3

    def test_r1_time_to_points_formula_is_pending(self):
        """Unresolved decision #1: conversion formula must be flagged pending."""
        assert R1_WALLET_POINTS_FORMULA == "PENDING_ORGANIZER_DECISION"


class TestRound2CaboConstants:
    def test_cabo_table_placement_points(self):
        """Mandatory: Cabo table scoring is strictly 5, 3, 2, 1, 0 for 1st-5th."""
        assert CABO_PLACEMENT_POINTS == {
            1: 5,
            2: 3,
            3: 2,
            4: 1,
            5: 0,
        }

    def test_cabo_structure_and_max_score(self):
        """
        Mandatory: 3 games, 5 players per table (1 per squad).
        Maximum possible team score = 5 players * 5 points (1st) * 3 games = 75 points.
        """
        assert CABO_GAMES == 3
        assert CABO_TABLE_SIZE == 5
        assert CABO_MAX_TEAM_SCORE == 75
        assert CABO_MAX_TEAM_SCORE == (CABO_TABLE_SIZE * CABO_PLACEMENT_POINTS[1] * CABO_GAMES)


class TestRound3BlackMarketAndWalletConstants:
    def test_starting_wallet_balance(self):
        """Mandatory: Unified tournament wallet starting balance is 1000 points."""
        assert STARTING_WALLET_BALANCE == 1000.0

    def test_black_market_suggested_prices(self):
        """Unresolved decision #2: Black Market prices are suggested guidelines."""
        assert BLACK_MARKET_SUGGESTED_PRICES["missing_code_fragment"] == 400.0
        assert BLACK_MARKET_SUGGESTED_PRICES["extra_prep_time"] == 200.0
        assert BLACK_MARKET_SUGGESTED_PRICES["extra_witness_question"] == 150.0
        assert BLACK_MARKET_SUGGESTED_PRICES["agent_intel"] == 250.0

        assert BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED == 400.0
        assert BLACK_MARKET_PREP_PRICE_SUGGESTED == 200.0
        assert BLACK_MARKET_WITNESS_PRICE_SUGGESTED == 150.0
        assert BLACK_MARKET_AGENT_INTEL_PRICE_SUGGESTED == 250.0


class TestCodeFragmentsAndFinalCodeGateConstants:
    def test_code_fragment_count(self):
        """Mandatory: Exactly 2 fragments (Fragment 1 in R1, Fragment 2 in R2)."""
        assert CODE_FRAGMENT_COUNT == 2

    def test_final_code_gate_mandatory_for_r4(self):
        """Mandatory: Final Code gate is required for Round 4 access."""
        assert FINAL_CODE_REQUIRED_FOR_R4 is True


class TestSecretAgentTrackConstants:
    def test_agent_task_reward(self):
        """Mandatory: Undercover agent task/sabotage reward is +50 points."""
        assert AGENT_TASK_REWARD == 50.0

    def test_penalty_range(self):
        """Mandatory: Misconduct/infraction penalty range is -50 to -200 points."""
        assert PENALTY_MIN == -50.0
        assert PENALTY_MAX == -200.0
        assert PENALTY_MIN > PENALTY_MAX  # Note: -50 is larger than -200 in value, minimum severity


class TestFinaleAgentUnmaskingAndCarryoverConstants:
    def test_agent_guessing_counts_and_points(self):
        """
        Mandatory:
        - 1 to 5 guesses allowed
        - Each correct guess: +30 points
        - Each wrong guess: -20 points
        """
        assert AGENT_GUESS_MIN == 1
        assert AGENT_GUESS_MAX == 5
        assert AGENT_CORRECT_GUESS == 30.0
        assert AGENT_WRONG_GUESS == -20.0

    def test_black_market_carryover_weight(self):
        """Unresolved decision #3: Suggested 10% carryover into Finale."""
        assert FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED == 0.10
        assert DEFAULT_CARRYOVER_WEIGHT_PERCENT == 10.0
