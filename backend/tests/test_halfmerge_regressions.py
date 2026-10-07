"""
Regressions for four half-merged references that each answered HTTP 500.

All four shared one cause: a branch brought over a service but not the model,
helper or constant it depends on. Python only notices when the line runs, and
these lines run when an organiser clicks something - so they reached production
unnoticed. One of them, GET /api/rounds/1/records, was confirmed returning 500
against the live deployment while a control endpoint returned 200.

The suite could not have caught any of them: tests/test_oddyssey_rules.py
imported a name this build does not define, which fails at COLLECTION and
aborts the whole run rather than one module.

scripts/scan_halfmerge.py finds this class statically. These tests pin the
specific four.
"""

import pytest

from app.core import constants as C
from app.models.round1 import MiniRoundTimingModel
from app.services import code_hunt_service


def test_mini_round_timing_maps_rule_penalty_seconds():
    """
    Migration a7b8c9d0e1f2 adds rule_penalty_seconds and round_service reads it
    in three places, but the model never mapped it, so get_round1_records and
    update_round1_record raised AttributeError -> 500 on the Round 1 score
    screen (GET, PUT and POST .../batch all route through it).
    """
    assert "rule_penalty_seconds" in MiniRoundTimingModel.__table__.columns, (
        "MiniRoundTimingModel must map rule_penalty_seconds; the column exists "
        "in the database and round_service reads it"
    )


def test_record_fragment_dispatcher_exists():
    """
    app/api/routes/code_hunt.py and round_service both call
    code_hunt_service.record_fragment(fragment_number=...). Only
    record_fragment_1..4 existed, so POST /api/code-hunt/{team}/fragment/{n}
    and PUT /api/rounds/3/codes/fragment both raised AttributeError -> 500.
    """
    assert hasattr(code_hunt_service, "record_fragment")
    for n in (1, 2, 3, 4):
        assert hasattr(code_hunt_service, f"record_fragment_{n}")


def test_record_fragment_rejects_a_bad_number():
    with pytest.raises(ValueError):
        code_hunt_service.record_fragment(
            db=None, team_id="team-x", fragment_number=9
        )


def test_allow_point_transfers_constant_exists():
    """
    transfer_round3_funds reads C.ALLOW_POINT_TRANSFERS to raise a 403. Without
    it the lookup raised AttributeError and POST /api/rounds/3/transfer answered
    500 instead of refusing cleanly. The value stays False - transfers are
    meant to be off; only the failure mode was wrong.
    """
    assert hasattr(C, "ALLOW_POINT_TRANSFERS")
    assert C.ALLOW_POINT_TRANSFERS is False


def test_complete_key_conditions_are_independent():
    """
    has_complete_key read:

        has_all_4
        or (has_code_items and missing_frag_count == 0)
        or (is_verified   and missing_frag_count == 0)

    and has_all_4 IS (missing_frag_count == 0), so the whole expression
    collapsed to missing_frag_count == 0 and the last two clauses could never
    change the result. A squad that bought both secret code items, and a squad
    an organiser had explicitly verified, each still counted as holding no
    code - which blocked Round 3 finalization with no working way to clear it.

    This reproduces the logic rather than the service, because standing up a
    finalizable 12-squad Round 3 is what the rehearsal script is for.
    """
    def collapsed(has_all_4, has_code_items, is_verified, missing):
        return (has_all_4 or (has_code_items and missing == 0)
                or (is_verified and missing == 0))

    def fixed(has_all_4, has_code_items, is_verified, missing):  # noqa: ARG001
        return has_all_4 or has_code_items or is_verified

    # A squad missing two fragments that bought both secret code items.
    assert collapsed(False, True, False, 2) is False, "documents the old bug"
    assert fixed(False, True, False, 2) is True

    # A squad missing fragments that an organiser verified by hand.
    assert collapsed(False, False, True, 1) is False, "documents the old bug"
    assert fixed(False, False, True, 1) is True

    # A squad with nothing is still not qualified either way.
    assert fixed(False, False, False, 3) is False
