"""
Every tournament constant checked against the Event Documentation, by section.

This exists because test_official_constants.py did not catch the hint-penalty
bug - it asserted 120 seconds and its docstring called that correct, so the
suite certified the error instead of finding it. A test that only says "the
constant equals the constant" cannot fail on a wrong constant.

The difference here is that every assertion quotes the section it comes from,
and wherever the documentation does its own arithmetic - rank 32 earning 52, a
maximum Cabo score of 75, a rubric out of 100, a 40% break-even for guessing -
that worked example is asserted directly. Those pin two constants together, so
neither can drift alone.

If you change a value below, you are changing a rule that was published to the
teams. Take it to the committee, not to this file.
"""

import pytest

from app.core import constants as C
from app.services import wallet as wallet_service


# ---------------------------------------------------------------- Section 2

def test_team_structure():
    """"Each team has exactly 5 members. A maximum of 32 teams are admitted.\""""
    assert C.TEAM_SIZE == 5
    assert C.MAX_TEAMS == 32


# -------------------------------------------------------------- Section 3.1

def test_there_are_exactly_two_code_fragments():
    """"In each of Rounds 1 and 2, a code fragment is hidden." One each, so two."""
    assert C.CODE_FRAGMENT_COUNT == 2
    assert C.DEPRECATED_R3_FRAGMENT_COUNT == 4, "kept only as a marker of the old value"


# -------------------------------------------------------------- Section 3.3

def test_starting_balance_is_one_thousand():
    """"Starting balance 1,000 - given to every team at registration.\""""
    assert C.STARTING_WALLET_BALANCE == 1000.0


def test_round1_rank_one_earns_three_hundred():
    """"Round 1 finishing rank - Rank 1: 300, then -8 per rank.\""""
    assert wallet_service.calculate_r1_reward(1) == 300.0


def test_round1_rank_thirty_two_earns_fifty_two():
    """
    The documentation's own worked example: "Rank 32 earns 52."

    The single most valuable assertion here - it pins the starting value AND
    the step together, so neither can be changed alone without failing.
    """
    assert wallet_service.calculate_r1_reward(32) == 52.0


def test_round1_points_fall_by_eight_per_rank():
    for rank in range(1, C.MAX_TEAMS):
        step = (wallet_service.calculate_r1_reward(rank + 1)
                - wallet_service.calculate_r1_reward(rank))
        assert step == -8.0, f"rank {rank} -> {rank + 1} moved by {step}, not -8"


def test_a_verified_agent_task_pays_fifty():
    """"Secret agent task (verified) +50 per task.\""""
    assert C.AGENT_TASK_REWARD == 50.0


# ---------------------------------------------------------------- Section 4

def test_hint_penalty_is_five_minutes():
    """
    Section 4.3, rule 5: a hint "adds a fixed time penalty (e.g. +5 minutes)".

    This is the one the previous constants test got wrong, asserting 120
    seconds. Round 1 is ranked on adjusted total time, so a three-minute
    shortfall per hint changed which teams reached Round 2.
    """
    assert C.DEFAULT_R1_HINT_PENALTY_SECONDS == 300
    assert C.DEFAULT_R1_HINT_PENALTY_SECONDS == 5 * 60


def test_round1_qualifies_twenty_four():
    """"The slowest 8 teams are eliminated and 24 teams qualify for Round 2.\""""
    assert C.R1_QUALIFIERS == 24
    assert C.MAX_TEAMS - C.R1_QUALIFIERS == 8


# -------------------------------------------------------------- Section 5.3

def test_cabo_placement_points_match_the_published_table():
    """1st = 5, 2nd = 3, 3rd = 2, 4th = 1, 5th = 0."""
    assert dict(C.CABO_PLACEMENT_POINTS) == {1: 5, 2: 3, 3: 2, 4: 1, 5: 0}


def test_a_cabo_table_seats_five():
    assert C.CABO_TABLE_SIZE == 5
    assert len(C.CABO_PLACEMENT_POINTS) == C.CABO_TABLE_SIZE


def test_maximum_team_cabo_score_is_seventy_five():
    """"maximum 5 x 3 x 5 = 75" - the documentation does this sum itself."""
    assert C.CABO_MAX_TEAM_SCORE == 75
    assert C.TEAM_SIZE * C.CABO_GAMES * max(C.CABO_PLACEMENT_POINTS.values()) == 75


def test_cabo_score_converts_to_wallet_points_at_ten_times():
    """"Round 2 Cabo performance - Team Cabo score x 10." (Section 3.3)"""
    assert wallet_service.calculate_r2_cabo_reward(75) == 750.0
    assert wallet_service.calculate_r2_cabo_reward(0) == 0.0


def test_round2_qualifies_twelve():
    assert C.R2_QUALIFIERS == 12


# ---------------------------------------------------------------- Section 6

def test_black_market_prices_match_section_6_2():
    assert C.BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED == 400.0
    assert C.BLACK_MARKET_PREP_PRICE_SUGGESTED == 200.0
    assert C.BLACK_MARKET_WITNESS_PRICE_SUGGESTED == 150.0
    assert C.BLACK_MARKET_AGENT_INTEL_PRICE_SUGGESTED == 250.0


def test_the_fragment_is_the_most_expensive_item():
    """
    It is the only purchase that decides qualification, so it must cost more
    than any pure advantage or the Final Code gate is trivially bought around.
    """
    others = [
        C.BLACK_MARKET_PREP_PRICE_SUGGESTED,
        C.BLACK_MARKET_WITNESS_PRICE_SUGGESTED,
        C.BLACK_MARKET_AGENT_INTEL_PRICE_SUGGESTED,
    ]
    assert C.BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED > max(others)


def test_round3_qualifies_eight():
    """"The top 8 teams qualify for the final round.\""""
    assert C.R3_QUALIFIERS == 8


# -------------------------------------------------------------- Section 7.3

def test_the_judging_rubric_totals_one_hundred():
    """"Judging Rubric (Suggested, per team, out of 100)"."""
    parts = [
        C.R4_RUBRIC_LOGICAL_STRUCTURE_MAX,
        C.R4_RUBRIC_EVIDENCE_MAX,
        C.R4_RUBRIC_REBUTTAL_MAX,
        C.R4_RUBRIC_RESOURCE_PERSON_MAX,
        C.R4_RUBRIC_PRESENTATION_TEAMWORK_MAX,
        C.R4_RUBRIC_TIME_MAX,
    ]
    assert parts == [20.0, 20.0, 20.0, 15.0, 15.0, 10.0]
    assert sum(parts) == C.R4_RUBRIC_TOTAL_MAX == 100.0


def test_questioning_is_worth_fifteen_which_is_why_the_extra_question_is_worth_buying():
    """
    The Black Market sells an extra witness question for 150. That is only a
    rational purchase because questioning carries 15 marks. If either number
    moves, the economy and the rubric stop agreeing.
    """
    assert C.R4_RUBRIC_RESOURCE_PERSON_MAX == 15.0
    assert C.BLACK_MARKET_WITNESS_PRICE_SUGGESTED == 150.0


def test_eight_finalists_in_four_pairs():
    assert C.R4_FINALISTS == 8
    assert C.R4_PAIRS * 2 == C.R4_FINALISTS


def test_all_eight_finalists_advance_to_the_finale():
    """
    Section 9.1 ranks "the 8 finalists", and Section 8.1 has every team guess
    "the other 7 finalist teams" - impossible with a cut to three beforehand.
    """
    assert C.R4_ADVANCING_COUNT == 8
    assert C.PODIUM_SIZE == 3, "the podium falls out of the ranking; it is not a cut"


# ---------------------------------------------------------------- Section 8

def test_agent_guess_scoring():
    """"Correct guess +30 / Wrong guess -20 / Not guessed 0.\""""
    assert C.AGENT_CORRECT_GUESS == 30.0
    assert C.AGENT_WRONG_GUESS == -20.0


def test_break_even_confidence_is_forty_percent():
    """
    The documentation derives this itself: "A guess is worth making only when
    E > 0, that is, when p > 0.4 (40%)."

    This is what catches a regression to +10/-5, which moves the break-even to
    33% and makes a weak hunch profitable - the opposite of what Section 8 is
    written to do.
    """
    correct, wrong = C.AGENT_CORRECT_GUESS, C.AGENT_WRONG_GUESS
    breakeven = -wrong / (correct - wrong)
    assert breakeven == pytest.approx(0.4)


def test_a_random_guess_among_five_members_loses_points():
    """"A random guess among 5 team members has p = 0.2." It must not pay."""
    p = 0.2
    expected = p * C.AGENT_CORRECT_GUESS + (1 - p) * C.AGENT_WRONG_GUESS
    assert expected < 0


def test_guess_counts():
    """"at least 1 guess and may make at most 5 guesses (out of the 7 other)"."""
    assert C.AGENT_GUESS_MIN == 1
    assert C.AGENT_GUESS_MAX == 5
    assert C.AGENT_GUESS_MAX < C.R4_FINALISTS - 1


# -------------------------------------------------------------- Section 9.1

def test_ten_percent_of_the_remaining_balance_carries():
    """"...+ 10% of remaining Black Market points.\""""
    assert C.FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED == pytest.approx(0.10)
    assert C.DEFAULT_CARRYOVER_WEIGHT_PERCENT == pytest.approx(10.0)


def test_the_field_narrows_monotonically():
    """32 -> 24 -> 12 -> 8. Any edit that breaks the funnel fails here."""
    funnel = [C.MAX_TEAMS, C.R1_QUALIFIERS, C.R2_QUALIFIERS, C.R3_QUALIFIERS]
    assert funnel == [32, 24, 12, 8]
    assert all(a > b for a, b in zip(funnel, funnel[1:]))


def test_deprecated_values_are_not_in_use_anywhere():
    """
    The DEPRECATED_* constants exist as markers of what the platform used to
    do. They must never equal the live value, or someone has quietly restored
    one of the original bugs.
    """
    assert C.STARTING_WALLET_BALANCE != C.DEPRECATED_R3_STARTING_BALANCE
    assert C.CODE_FRAGMENT_COUNT != C.DEPRECATED_R3_FRAGMENT_COUNT
    assert C.AGENT_CORRECT_GUESS != C.DEPRECATED_AGENT_CORRECT_BONUS
    assert C.AGENT_WRONG_GUESS != C.DEPRECATED_AGENT_WRONG_PENALTY
    assert C.FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED != C.DEPRECATED_CARRYOVER_WEIGHT
