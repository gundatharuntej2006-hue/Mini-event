"""
ODDyssey Event Plan conformance: the rules that had no implementation at all.

Three of the plan's rules were specified but never built, so nothing in the
suite could fail when they were ignored:

1. Section 4, Round 1 Scoring - "Total time = time spent at gates + hint
   penalties + RULE penalties". Only the hint half existed. A squad caught
   using a phone or splitting up kept its raw time, and Round 1 decides who
   reaches Round 2.

2. Section 4, Cabo Tie-Breakers 4 and 5 - sudden-death game, then organiser
   draw. The platform computed 1-3 and flagged the rest "unresolved" with no
   way to resolve them, while an unresolved tie blocks finalisation.

3. Section 5, Market Catalogue Quantity column - "4 available", "8 available".
   Stock was published in the catalogue response but never checked at the
   till, so an item could be sold without limit.

Each test below fails if its rule is reverted.
"""

import pytest

from app.core import constants as C
from app.models.team import Team, TeamStatus
from app.scoring.round1_scoring import compute_mini_round, compute_team_totals
from app.services import round1_service
from app.services import cabo_service
from app.services import black_market_service
from app.services import wallet as wallet_service
from app.services.black_market_service import OutOfStockError
from app.services.cabo_service import CaboTieBreakError
from app.services.round_service import ensure_round_states_initialized


class _Actor:
    """Stands in for the authenticated organiser the services expect."""
    id = "organizer-1"
    role = "organizer"
    email = "organizer@example.com"


def _timing_input(mini_round_number, start, end):
    from app.schemas.rounds.round1 import MiniRoundTimingInput

    return MiniRoundTimingInput(
        mini_round_number=mini_round_number,
        start_time=f"2026-01-01T{start}+00:00",
        completion_time=f"2026-01-01T{end}+00:00",
        hints_used=0,
        checkpoints=[],
    )


@pytest.fixture
def r1_team(db_session):
    ensure_round_states_initialized(db_session)
    team = Team(
        id="team-odd-01",
        team_number=1,
        name="Squad ODD",
        status=TeamStatus.ACTIVE,
        current_round=1,
    )
    db_session.add(team)
    db_session.commit()
    wallet_service.get_or_create_wallet(db_session, team.id)
    return team


# ==============================================================================
# 1. ROUND 1 RULE PENALTIES (Section 4)
# ==============================================================================
class TestRound1RulePenaltyConstants:
    def test_penalty_values_match_the_plan(self):
        """
        Section 4 Round 1 Scoring table:
            Using a hint                  +5 minutes
            Unauthorised phone use        +10 minutes
            Team members separating       +5 minutes
            Moving or damaging a clue     -20 points or disqualification
        """
        assert C.R1_PENALTY_HINT_SECONDS == 5 * 60
        assert C.R1_PENALTY_PHONE_USE_SECONDS == 10 * 60
        assert C.R1_PENALTY_TEAM_SEPARATION_SECONDS == 5 * 60
        assert C.R1_CLUE_DAMAGE_POINT_PENALTY == -20.0
        # The hint penalty is the same five minutes in both constants; they
        # drifted apart once before and Round 1 ranking silently changed.
        assert C.R1_PENALTY_HINT_SECONDS == C.DEFAULT_R1_HINT_PENALTY_SECONDS

    def test_all_three_violations_are_nameable(self):
        assert set(C.R1_RULE_VIOLATIONS) == {
            "UNAUTHORISED_PHONE_USE",
            "TEAM_SEPARATION",
            "CLUE_DAMAGE",
        }


class TestRound1RulePenaltyScoring:
    def test_phone_use_adds_ten_minutes_to_adjusted_time(self):
        mr = compute_mini_round(
            {
                "mini_round_number": 1,
                "start_time": "2026-01-01T10:00:00+00:00",
                "completion_time": "2026-01-01T10:20:00+00:00",
                "hints_used": 0,
                "phone_use_count": 1,
            },
            C.DEFAULT_R1_HINT_PENALTY_SECONDS,
        )
        assert mr["duration_seconds"] == 1200
        assert mr["rule_penalty_seconds"] == 600
        assert mr["adjusted_seconds"] == 1800

    def test_separation_adds_five_minutes(self):
        mr = compute_mini_round(
            {
                "mini_round_number": 1,
                "start_time": "2026-01-01T10:00:00+00:00",
                "completion_time": "2026-01-01T10:20:00+00:00",
                "hints_used": 0,
                "separation_count": 1,
            },
            C.DEFAULT_R1_HINT_PENALTY_SECONDS,
        )
        assert mr["adjusted_seconds"] == 1200 + 300

    def test_hint_and_rule_penalties_stack(self):
        """Both terms of "gate time + hint penalties + rule penalties"."""
        mr = compute_mini_round(
            {
                "mini_round_number": 1,
                "start_time": "2026-01-01T10:00:00+00:00",
                "completion_time": "2026-01-01T10:20:00+00:00",
                "hints_used": 2,
                "phone_use_count": 1,
                "separation_count": 1,
            },
            C.DEFAULT_R1_HINT_PENALTY_SECONDS,
        )
        assert mr["hint_penalty_seconds"] == 600      # 2 hints x 5 min
        assert mr["rule_penalty_seconds"] == 900      # 10 min + 5 min
        assert mr["adjusted_seconds"] == 1200 + 600 + 900

    def test_clue_damage_costs_points_not_time(self):
        """
        "-20 points or disqualification" - the only violation scored in points.
        Adding time for it as well would penalise the squad twice.
        """
        mr = compute_mini_round(
            {
                "mini_round_number": 1,
                "start_time": "2026-01-01T10:00:00+00:00",
                "completion_time": "2026-01-01T10:20:00+00:00",
                "hints_used": 0,
                "clue_damage_count": 3,
            },
            C.DEFAULT_R1_HINT_PENALTY_SECONDS,
        )
        assert mr["rule_penalty_seconds"] == 0
        assert mr["adjusted_seconds"] == 1200

    def test_team_total_includes_rule_penalties(self):
        """
        The per-gate penalty is useless if the team total drops it again -
        Round 1 is ranked on adjusted_total_seconds, nothing else.
        """
        record = {
            "team_id": "t1",
            "team_number": 1,
            "team_name": "Squad 1",
            "mini_rounds": [
                {
                    "mini_round_number": n,
                    "start_time": "2026-01-01T10:00:00+00:00",
                    "completion_time": "2026-01-01T10:10:00+00:00",
                    "hints_used": 0,
                    "phone_use_count": 1 if n == 2 else 0,
                }
                for n in (1, 2, 3)
            ],
        }
        totals = compute_team_totals(record, C.DEFAULT_R1_HINT_PENALTY_SECONDS)
        assert totals["raw_total_seconds"] == 1800
        assert totals["total_rule_penalty_seconds"] == 600
        assert totals["total_penalty_seconds"] == 600
        assert totals["adjusted_total_seconds"] == 2400

    def test_clean_squad_outranks_an_identical_squad_that_broke_a_rule(self):
        """The rule that actually matters: penalties must change the order."""
        def record(team_id, number, phone):
            return {
                "team_id": team_id,
                "team_number": number,
                "team_name": f"Squad {number}",
                "mini_rounds": [
                    {
                        "mini_round_number": n,
                        "start_time": "2026-01-01T10:00:00+00:00",
                        "completion_time": "2026-01-01T10:10:00+00:00",
                        "hints_used": 0,
                        "phone_use_count": phone if n == 1 else 0,
                    }
                    for n in (1, 2, 3)
                ],
            }

        clean = compute_team_totals(record("clean", 2, 0), C.DEFAULT_R1_HINT_PENALTY_SECONDS)
        offender = compute_team_totals(record("offender", 1, 1), C.DEFAULT_R1_HINT_PENALTY_SECONDS)
        # Identical raw times, and the offender has the lower team number, so
        # without the penalty it would sort first.
        assert clean["raw_total_seconds"] == offender["raw_total_seconds"]
        assert clean["adjusted_total_seconds"] < offender["adjusted_total_seconds"]


class TestRound1RuleViolationService:
    def test_recording_phone_use_persists_and_adjusts(self, db_session, r1_team):
        round1_service.record_mini_round_timing(
            db_session,
            r1_team.id,
            _timing_input(1, "10:00:00", "10:20:00"),
            _Actor(),
        )
        timing = round1_service.record_rule_violation(
            db=db_session,
            team_id=r1_team.id,
            mini_round_number=1,
            violation="UNAUTHORISED_PHONE_USE",
            count=1,
            actor=_Actor(),
        )
        assert timing.phone_use_count == 1
        assert timing.rule_penalty_seconds == 600
        assert timing.adjusted_seconds == 1200 + 600

    def test_count_is_a_total_not_an_increment(self, db_session, r1_team):
        """A marshal corrects a mis-entry by writing the right number."""
        for value in (3, 1):
            timing = round1_service.record_rule_violation(
                db=db_session,
                team_id=r1_team.id,
                mini_round_number=2,
                violation="TEAM_SEPARATION",
                count=value,
                actor=_Actor(),
            )
        assert timing.separation_count == 1
        assert timing.rule_penalty_seconds == 300

    def test_clue_damage_debits_twenty_points(self, db_session, r1_team):
        before = wallet_service.get_wallet(db_session, r1_team.id).current_balance
        round1_service.record_rule_violation(
            db=db_session,
            team_id=r1_team.id,
            mini_round_number=1,
            violation="CLUE_DAMAGE",
            count=1,
            actor=_Actor(),
        )
        after = wallet_service.get_wallet(db_session, r1_team.id).current_balance
        assert after == before - 20.0

    def test_clue_damage_charges_only_new_incidents(self, db_session, r1_team):
        """Re-saving the same number must not bill the squad twice."""
        before = wallet_service.get_wallet(db_session, r1_team.id).current_balance
        for _ in range(3):
            round1_service.record_rule_violation(
                db=db_session,
                team_id=r1_team.id,
                mini_round_number=1,
                violation="CLUE_DAMAGE",
                count=2,
                actor=_Actor(),
            )
        after = wallet_service.get_wallet(db_session, r1_team.id).current_balance
        assert after == before - 40.0

    def test_clue_damage_can_escalate_to_disqualification(self, db_session, r1_team):
        """Minus 20 points OR disqualification - the marshal chooses."""
        round1_service.record_rule_violation(
            db=db_session,
            team_id=r1_team.id,
            mini_round_number=1,
            violation="CLUE_DAMAGE",
            count=1,
            actor=_Actor(),
            disqualify=True,
        )
        db_session.refresh(r1_team)
        assert r1_team.status == TeamStatus.DISQUALIFIED

    def test_unknown_violation_is_refused(self, db_session, r1_team):
        with pytest.raises(Exception) as exc:
            round1_service.record_rule_violation(
                db=db_session,
                team_id=r1_team.id,
                mini_round_number=1,
                violation="TALKING_LOUDLY",
                count=1,
                actor=_Actor(),
            )
        assert "TALKING_LOUDLY" in str(exc.value) or "400" in str(exc.value)

    def test_retyping_a_finish_time_does_not_refund_the_penalty(self, db_session, r1_team):
        """
        A corrected finish time must not wipe a logged violation. Re-entering
        the timings rebuilds the row, and an earlier version of this path
        dropped the counters on the way through.
        """
        round1_service.record_rule_violation(
            db=db_session,
            team_id=r1_team.id,
            mini_round_number=3,
            violation="UNAUTHORISED_PHONE_USE",
            count=1,
            actor=_Actor(),
        )
        timing = round1_service.record_mini_round_timing(
            db_session,
            r1_team.id,
            _timing_input(3, "11:00:00", "11:15:00"),
            _Actor(),
        )
        assert timing.phone_use_count == 1
        assert timing.rule_penalty_seconds == 600
        assert timing.adjusted_seconds == 900 + 600


# ==============================================================================
# 2. CABO TIE-BREAKERS 4 AND 5 (Section 4)
# ==============================================================================
def _cabo_team(db_session, number):
    ensure_round_states_initialized(db_session)
    team = Team(
        id=f"team-cabo-{number:02d}",
        team_number=number,
        name=f"Cabo Squad {number:02d}",
        status=TeamStatus.ACTIVE,
        current_round=2,
    )
    db_session.add(team)
    db_session.commit()
    return team


class TestCaboTieBreaks:
    def test_only_the_two_documented_methods_are_accepted(self):
        assert cabo_service.CABO_TIE_BREAK_METHODS == ("SUDDEN_DEATH", "ORGANISER_DRAW")

    def test_unknown_method_is_refused(self, db_session):
        team = _cabo_team(db_session, 1)
        with pytest.raises(CaboTieBreakError):
            cabo_service.record_cabo_tie_break(
                db_session, team.id, "COIN_FLIP", 1, actor="org"
            )

    def test_rank_must_be_at_least_one(self, db_session):
        team = _cabo_team(db_session, 2)
        with pytest.raises(CaboTieBreakError):
            cabo_service.record_cabo_tie_break(
                db_session, team.id, "SUDDEN_DEATH", 0, actor="org"
            )

    def test_recording_is_idempotent_per_team(self, db_session):
        """A mis-keyed result is corrected, not duplicated."""
        team = _cabo_team(db_session, 3)
        cabo_service.record_cabo_tie_break(db_session, team.id, "SUDDEN_DEATH", 2, actor="org")
        cabo_service.record_cabo_tie_break(db_session, team.id, "ORGANISER_DRAW", 1, actor="org")
        mine = [r for r in cabo_service.list_cabo_tie_breaks(db_session) if r.team_id == team.id]
        assert len(mine) == 1
        assert mine[0].method == "ORGANISER_DRAW"
        assert mine[0].resolution_rank == 1

    def test_clearing_a_result(self, db_session):
        team = _cabo_team(db_session, 4)
        cabo_service.record_cabo_tie_break(db_session, team.id, "SUDDEN_DEATH", 1, actor="org")
        assert cabo_service.clear_cabo_tie_break(db_session, team.id) is True
        assert cabo_service.clear_cabo_tie_break(db_session, team.id) is False

    def test_sudden_death_orders_two_level_squads(self, db_session):
        """
        Two squads level on all three scored metrics. Before tie-breakers 4
        and 5 existed, both stayed flagged unresolved for good - and an
        unresolved tie blocks Round 2 finalisation.
        """
        first = _cabo_team(db_session, 11)
        second = _cabo_team(db_session, 12)

        before = {s.team_id: s for s in cabo_service.calculate_round2_standings(db_session)}
        assert before[first.id].is_tied_unresolved is True
        assert before[second.id].is_tied_unresolved is True

        # The sudden-death game is played; squad 12 wins it.
        cabo_service.record_cabo_tie_break(db_session, second.id, "SUDDEN_DEATH", 1, actor="org")
        cabo_service.record_cabo_tie_break(db_session, first.id, "SUDDEN_DEATH", 2, actor="org")

        after = {s.team_id: s for s in cabo_service.calculate_round2_standings(db_session)}
        assert after[second.id].rank < after[first.id].rank
        assert after[second.id].is_tied_unresolved is False
        assert after[first.id].is_tied_unresolved is False
        assert after[second.id].tie_break_method == "SUDDEN_DEATH"

    def test_a_half_entered_resolution_stays_unresolved(self, db_session):
        """
        Recording one side of a tie does not separate it. Reporting it as
        resolved would unblock finalisation on a tie nobody had broken.
        """
        first = _cabo_team(db_session, 21)
        second = _cabo_team(db_session, 22)
        cabo_service.record_cabo_tie_break(db_session, first.id, "ORGANISER_DRAW", 1, actor="org")

        standings = {s.team_id: s for s in cabo_service.calculate_round2_standings(db_session)}
        assert standings[first.id].is_tied_unresolved is True
        assert standings[second.id].is_tied_unresolved is True


# ==============================================================================
# 3. BLACK MARKET STOCK LIMITS (Section 5)
# ==============================================================================
@pytest.fixture
def r3_stock_teams(db_session):
    ensure_round_states_initialized(db_session)
    teams = []
    for i in range(1, 9):
        team = Team(
            id=f"team-stock-{i:02d}",
            team_number=i,
            name=f"Stock Squad {i:02d}",
            status=TeamStatus.ACTIVE,
            current_round=3,
        )
        db_session.add(team)
        db_session.flush()
        wallet_service.get_or_create_wallet(db_session, team.id)
        teams.append(team)
    db_session.commit()
    return teams


class TestBlackMarketStock:
    def test_stock_matches_the_market_catalogue(self):
        """
        Section 5 Market Catalogue, Quantity column:
            Missing code fragment   as required
            Extra preparation time  4 available
            Extra witness question  8 available
            Agent clue card         5 available
            Case-theme hint         4 available
        """
        assert C.BLACK_MARKET_STOCK["MISSING_CODE_FRAGMENT"] is None
        assert C.BLACK_MARKET_STOCK["EXTRA_PREP_TIME"] == 4
        assert C.BLACK_MARKET_STOCK["EXTRA_WITNESS_QUESTION"] == 8
        assert C.BLACK_MARKET_STOCK["AGENT_INTEL"] == 5
        assert C.BLACK_MARKET_STOCK["CASE_THEME_HINT"] == 4

    def test_catalog_reports_remaining_stock(self, db_session, r3_stock_teams):
        catalog = {i["asset_type"]: i for i in black_market_service.get_market_catalog(db_session)}
        assert catalog["EXTRA_PREP_TIME"]["remaining_stock"] == 4
        assert catalog["EXTRA_PREP_TIME"]["is_sold_out"] is False
        # "As required" - never sold out.
        assert catalog["MISSING_CODE_FRAGMENT"]["remaining_stock"] is None
        assert catalog["MISSING_CODE_FRAGMENT"]["is_sold_out"] is False

    def test_stock_is_consumed_across_teams_not_per_team(self, db_session, r3_stock_teams):
        """The "4 available" is the whole market's supply, not each squad's."""
        for team in r3_stock_teams[:4]:
            black_market_service.purchase_market_asset(
                db=db_session,
                team_id=team.id,
                asset_type="EXTRA_PREP_TIME",
                quantity=1,
                actor="organizer-1",
            )
        catalog = {i["asset_type"]: i for i in black_market_service.get_market_catalog(db_session)}
        assert catalog["EXTRA_PREP_TIME"]["units_sold"] == 4
        assert catalog["EXTRA_PREP_TIME"]["remaining_stock"] == 0
        assert catalog["EXTRA_PREP_TIME"]["is_sold_out"] is True

        with pytest.raises(OutOfStockError):
            black_market_service.purchase_market_asset(
                db=db_session,
                team_id=r3_stock_teams[4].id,
                asset_type="EXTRA_PREP_TIME",
                quantity=1,
                actor="organizer-1",
            )

    def test_a_bulk_order_cannot_exceed_stock(self, db_session, r3_stock_teams):
        with pytest.raises(OutOfStockError):
            black_market_service.purchase_market_asset(
                db=db_session,
                team_id=r3_stock_teams[0].id,
                asset_type="CASE_THEME_HINT",
                quantity=5,          # only 4 exist
                price=1.0,
                actor="organizer-1",
            )

    def test_a_refused_purchase_costs_nothing(self, db_session, r3_stock_teams):
        """Stock is checked before the wallet is touched."""
        team = r3_stock_teams[0]
        before = wallet_service.get_wallet(db_session, team.id).current_balance
        with pytest.raises(OutOfStockError):
            black_market_service.purchase_market_asset(
                db=db_session,
                team_id=team.id,
                asset_type="AGENT_INTEL",
                quantity=6,          # only 5 exist
                actor="organizer-1",
            )
        after = wallet_service.get_wallet(db_session, team.id).current_balance
        assert after == before

    def test_code_fragments_are_never_out_of_stock(self, db_session, r3_stock_teams):
        """
        "As required" - the fragment is the Round 4 gate, and rationing it
        would eliminate squads the plan intends to let buy their way in.
        """
        assert black_market_service.get_remaining_stock(db_session, "MISSING_CODE_FRAGMENT") is None
        # Never raises, however many are sold.
        black_market_service.assert_in_stock(db_session, "MISSING_CODE_FRAGMENT", 99)


# ==============================================================================
# 4. CROSS-LAYER: THE LEGACY ROUND 1 SCREEN MUST NOT REFUND A PENALTY
# ==============================================================================
class TestRulePenaltiesSurviveTheLegacyBridge:
    """
    Round 1 has two stores: the legacy round1_records the data-entry screen
    writes, and the round1_timings that qualification reads. A bridge mirrors
    one into the other.

    Rule penalties only exist on the timings row, so the bridge originally
    recomputed the adjusted time as "duration + hints x penalty" and silently
    discarded them. Every edit on the Round 1 screen - re-typing a finish time,
    fixing a hint count - would have refunded a phone-use penalty, and the
    screen is edited constantly during the round.
    """

    def _update_legacy(self, db_session, team, durations, hints=0):
        from app.schemas.rounds.legacy import Round1RecordUpdateRequest
        from app.services import round_service

        class _User:
            id = "organizer-1"
            name = "Organizer One"
            role = "organizer"

        payload = Round1RecordUpdateRequest(
            mini_rounds=[
                {
                    "roundNumber": n,
                    "durationSeconds": d,
                    "hintsUsed": hints,
                    "isCompleted": True,
                }
                for n, d in enumerate(durations, start=1)
            ]
        )
        return round_service.update_round1_record(db_session, team.id, payload, _User())

    def test_legacy_edit_keeps_the_rule_penalty(self, db_session, r1_team):
        from app.services import round_service

        self._update_legacy(db_session, r1_team, [600, 600, 600])
        round1_service.record_rule_violation(
            db=db_session,
            team_id=r1_team.id,
            mini_round_number=1,
            violation="UNAUTHORISED_PHONE_USE",
            count=1,
            actor=_Actor(),
        )

        # The marshal corrects gate 2's finish time on the Round 1 screen.
        rec = self._update_legacy(db_session, r1_team, [600, 660, 600])

        assert round_service.get_team_rule_penalty_seconds(db_session, r1_team.id) == 600
        assert rec.raw_total_seconds == 1860
        assert rec.total_penalty_seconds == 600
        assert rec.adjusted_total_seconds == 2460

        # The row itself must be right too, not just the recomputed totals:
        # /rounds/1/teams/{id}/timings serves timing.adjusted_seconds straight
        # to the dashboard, so a stale value here is what a marshal reads back
        # after saving.
        from app.models.round1 import MiniRoundTimingModel

        gate1 = db_session.query(MiniRoundTimingModel).filter(
            MiniRoundTimingModel.id == f"r1-{r1_team.id}-1"
        ).one()
        assert gate1.rule_penalty_seconds == 600
        assert gate1.adjusted_seconds == 600 + 600

    def test_the_store_qualification_reads_agrees_with_the_legacy_record(
        self, db_session, r1_team
    ):
        """
        The two layers must not disagree about the same squad - qualification
        reads one of them and the dashboard shows the other.
        """
        from app.services import round_service

        self._update_legacy(db_session, r1_team, [600, 600, 600])
        round1_service.record_rule_violation(
            db=db_session,
            team_id=r1_team.id,
            mini_round_number=2,
            violation="TEAM_SEPARATION",
            count=1,
            actor=_Actor(),
        )
        rec = self._update_legacy(db_session, r1_team, [600, 600, 600])

        overview = round1_service.get_round1_overview(db_session)
        row = next(r for r in overview["records"] if r["team_id"] == r1_team.id)

        assert row["total_rule_penalty_seconds"] == 300
        assert row["adjusted_total_seconds"] == rec.adjusted_total_seconds == 2100


# ==============================================================================
# 5. TWO ORGANISER SIGNATURES (Section 5, Black Market Rules)
# ==============================================================================
class TestBlackMarketDualSignature:
    """
    "Every transaction requires two organiser signatures." (Final Event Plan
    Section 5; Rulebook Section 5: "Every purchase needs two organisers to
    sign off on it.")

    Only the acting organiser was recorded, so the paper control had no
    counterpart in the ledger: one person could move a squad's points with
    nothing to show who else authorised it, and nothing to check afterwards.
    Enforced at the API, where a real organiser acts.
    """

    def _purchase(self, client, headers, team_id, **extra):
        payload = {
            "team_id": team_id,
            "asset_type": "EXTRA_PREP_TIME",
            "quantity": 1,
        }
        payload.update(extra)
        return client.post("/api/rounds/3/market/purchase", json=payload, headers=headers)

    def test_the_rule_is_switched_on(self):
        assert C.REQUIRE_BLACK_MARKET_DUAL_SIGNATURE is True

    def test_a_purchase_without_a_second_signature_is_refused(
        self, client, organizer_headers, r3_stock_teams
    ):
        res = self._purchase(client, organizer_headers, r3_stock_teams[0].id)
        assert res.status_code == 400
        # The app wraps HTTP errors in {success, data, message, isMockData}.
        assert "two organiser signatures" in res.json()["message"]

    def test_a_refused_purchase_costs_nothing(
        self, client, organizer_headers, db_session, r3_stock_teams
    ):
        team = r3_stock_teams[0]
        before = wallet_service.get_wallet(db_session, team.id).current_balance
        self._purchase(client, organizer_headers, team.id)
        after = wallet_service.get_wallet(db_session, team.id).current_balance
        assert after == before

    def test_signing_your_own_transaction_twice_is_not_two_signatures(
        self, client, organizer_headers, db_session, r3_stock_teams
    ):
        """
        One person entering their own name as the second signature is not a
        second signature - it is the same signature typed twice, and it defeats
        the whole point of the control.
        """
        from app.models.user import User, UserRole

        me = db_session.query(User).filter(User.role == UserRole.ORGANIZER).first()

        for identity in (me.id, me.email, (me.email or "").upper()):
            res = self._purchase(
                client,
                organizer_headers,
                r3_stock_teams[0].id,
                countersigned_by=identity,
            )
            assert res.status_code == 400, f"{identity!r} was accepted: {res.text}"
            assert "second organiser" in res.json()["message"]

    def test_a_countersigned_purchase_completes_and_records_both_names(
        self, client, organizer_headers, db_session, r3_stock_teams
    ):
        team = r3_stock_teams[1]
        before = wallet_service.get_wallet(db_session, team.id).current_balance

        res = self._purchase(
            client, organizer_headers, team.id, countersigned_by="marshal-2"
        )
        assert res.status_code == 200, res.text

        after = wallet_service.get_wallet(db_session, team.id).current_balance
        assert after == before - C.BLACK_MARKET_PREP_PRICE_SUGGESTED

        from app.models.black_market import BlackMarketPurchase

        row = (
            db_session.query(BlackMarketPurchase)
            .filter(BlackMarketPurchase.team_id == team.id)
            .order_by(BlackMarketPurchase.purchased_at.desc())
            .first()
        )
        assert row is not None
        assert row.purchased_by
        assert row.countersigned_by == "marshal-2"
        assert row.countersigned_by != row.purchased_by

    def test_the_fragment_purchase_carries_both_signatures_too(
        self, client, organizer_headers, db_session, r3_stock_teams
    ):
        """
        The fragment is the most expensive item on sale and the one that
        decides Round 4 eligibility, so it is exactly the transaction that
        needs both names on it.
        """
        team = r3_stock_teams[2]
        res = client.post(
            "/api/rounds/3/market/purchase",
            json={
                "team_id": team.id,
                "asset_type": "MISSING_CODE_FRAGMENT",
                "quantity": 1,
                "countersigned_by": "marshal-2",
                "details": {"fragment_number": 1, "recovered_value": "ODD"},
            },
            headers=organizer_headers,
        )
        assert res.status_code == 200, res.text

        from app.models.black_market import BlackMarketPurchase, BlackMarketAssetType

        row = (
            db_session.query(BlackMarketPurchase)
            .filter(
                BlackMarketPurchase.team_id == team.id,
                BlackMarketPurchase.asset_type == BlackMarketAssetType.MISSING_CODE_FRAGMENT,
            )
            .order_by(BlackMarketPurchase.purchased_at.desc())
            .first()
        )
        assert row is not None
        assert row.countersigned_by == "marshal-2"


# ==============================================================================
# 6. FULL BLACK MARKET CARRYOVER (Final Event Plan S1 / Rulebook S8)
# ==============================================================================
class TestFullCarryover:
    """
    "Final Score = Legal Battle score + Agent-guessing score + Points
    remaining after the Black Market."

    The balance carries in FULL. The 10% weight came from the older Event
    Documentation, where it was an explicitly unresolved organiser decision -
    and at 10% a squad finishing on 900 points contributed 90, so the entire
    Black Market economy was worth less than one Legal Battle rubric category.
    """

    def test_the_documented_weight_is_the_whole_balance(self):
        assert C.FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED == 1.0
        assert C.DEFAULT_CARRYOVER_WEIGHT_PERCENT == 100.0
        # The old value survives only as a marker, never as a default.
        assert C.DEPRECATED_CARRYOVER_WEIGHT == 0.10

    def test_the_final_score_is_a_plain_sum_of_the_three_components(self):
        from app.scoring.championship_scoring import calculate_final_championship_score

        result = calculate_final_championship_score(
            legal_battle_score=82.0,
            agent_guessing_points=40.0,
            remaining_black_market_points=900.0,
        )
        assert result["black_market_component"] == 900.0
        assert result["final_score"] == 82.0 + 40.0 + 900.0

    def test_the_wallet_can_decide_the_championship(self):
        """
        The point of the change: a squad that played the market well must be
        able to beat a squad that scored better in the courtroom. At 10% that
        was arithmetically impossible across any realistic balance gap.
        """
        from app.scoring.championship_scoring import calculate_final_championship_score

        courtroom = calculate_final_championship_score(
            legal_battle_score=95.0, agent_guessing_points=0.0,
            remaining_black_market_points=100.0,
        )
        trader = calculate_final_championship_score(
            legal_battle_score=70.0, agent_guessing_points=0.0,
            remaining_black_market_points=800.0,
        )
        assert trader["final_score"] > courtroom["final_score"]

    def test_the_finale_breakdown_carries_the_same_full_balance(self):
        from app.scoring.finale_scoring import calculate_overall_final_score

        breakdown = calculate_overall_final_score(
            round4_score=60.0,
            guessing_points=30.0,
            wallet_balance=450.0,
        )
        assert breakdown["carryover_percent"] == 100.0
        assert breakdown["wallet_carryover_points"] == 450.0
        assert breakdown["total_final_score"] == 60.0 + 30.0 + 450.0
