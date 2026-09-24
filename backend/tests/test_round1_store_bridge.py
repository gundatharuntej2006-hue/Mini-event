"""
Round 1 data entered through the dashboard must reach Round 1 qualification.

THE DEFECT THIS COVERS

Round 1 has two stores, and they were never connected:

    the dashboard writes to  /rounds/1/records      -> round1_records
    qualification reads      MiniRoundTimingModel   -> round1_timings

backendApiService.ts calls /rounds/1/records and nothing in the frontend ever
calls the endpoint that writes round1_timings. So on the day, every checkpoint
time a marshal entered would land in round1_records, and
process_round1_standings would compute qualification from an empty table -
on the first round of the event.

Round 2 is not affected: the dashboard uses /rounds/2/cabo/*, which is the
same layer its scoring reads.

These tests assert the bridge holds. They are deliberately written against the
TWO SEPARATE APIS - write through the one the dashboard uses, read through the
one qualification uses - because a test that stays inside one layer passes
happily while the two stores disagree, which is exactly how this survived.
"""

from fastapi.testclient import TestClient

from app.core import constants as C


def _team(client, headers, name):
    return client.post("/api/v1/teams", json={"name": name}, headers=headers).json()["data"]["id"]


def _write_via_dashboard(client, marshal_headers, team_id, durations, hints=(0, 0, 0)):
    """Exactly what backendApiService.updateRound1Record sends."""
    return client.put(
        f"/api/v1/rounds/1/records/{team_id}",
        json={
            "miniRounds": [
                {
                    "roundNumber": n,
                    "durationSeconds": durations[n - 1],
                    "hintsUsed": hints[n - 1],
                    "isCompleted": True,
                }
                for n in (1, 2, 3)
            ]
        },
        headers=marshal_headers,
    )


def _read_via_qualification_layer(client, headers):
    """The store Round 1 standings and progression actually read."""
    return client.get("/api/rounds/1/teams", headers=headers)


def test_dashboard_writes_reach_the_qualification_store(
    client: TestClient, organizer_headers: dict, marshal_headers: dict
):
    """
    The headline case. Write through the dashboard's endpoint, then read
    through the layer that decides who qualifies.
    """
    team = _team(client, organizer_headers, "Bridge Squad")
    assert _write_via_dashboard(client, marshal_headers, team, (100, 120, 80)).status_code == 200

    r = _read_via_qualification_layer(client, organizer_headers)
    assert r.status_code == 200, r.text
    rows = {row["team_id"]: row for row in r.json()["data"]}
    assert team in rows, "the qualification layer cannot see the dashboard's data"


def test_the_times_carry_across_not_just_the_row(
    client: TestClient, organizer_headers: dict, marshal_headers: dict
):
    """An empty row would still fail qualification; the seconds have to arrive."""
    team = _team(client, organizer_headers, "Timing Squad")
    _write_via_dashboard(client, marshal_headers, team, (100, 120, 80))

    rows = {r["team_id"]: r for r in _read_via_qualification_layer(client, organizer_headers).json()["data"]}
    row = rows[team]
    assert row["raw_total_seconds"] == 300
    assert row["adjusted_total_seconds"] == 300


def test_a_hint_costs_five_minutes_through_the_bridge(
    client: TestClient, organizer_headers: dict, marshal_headers: dict
):
    """
    Section 4.3 rule 5, checked end to end rather than as a constant: one hint
    entered on the dashboard must cost 300 seconds in the qualification store.
    """
    team = _team(client, organizer_headers, "Hint Squad")
    _write_via_dashboard(client, marshal_headers, team, (100, 120, 80), hints=(1, 0, 0))

    rows = {r["team_id"]: r for r in _read_via_qualification_layer(client, organizer_headers).json()["data"]}
    row = rows[team]
    assert row["raw_total_seconds"] == 300
    assert row["total_penalty_seconds"] == C.DEFAULT_R1_HINT_PENALTY_SECONDS == 300
    assert row["adjusted_total_seconds"] == 600


def test_ranking_across_the_bridge_matches_adjusted_time(
    client: TestClient, organizer_headers: dict, marshal_headers: dict
):
    """
    The thing that actually decides Round 2 entry. Three teams entered through
    the dashboard must rank correctly in the qualification layer, including the
    hint penalty demoting a team that was faster on raw time.
    """
    fast_with_hint = _team(client, organizer_headers, "Fast But Hinted")
    steady = _team(client, organizer_headers, "Steady")
    slow = _team(client, organizer_headers, "Slow")

    _write_via_dashboard(client, marshal_headers, fast_with_hint, (100, 100, 100), hints=(1, 0, 0))
    _write_via_dashboard(client, marshal_headers, steady, (140, 140, 140))
    _write_via_dashboard(client, marshal_headers, slow, (300, 300, 300))

    rows = {r["team_id"]: r for r in _read_via_qualification_layer(client, organizer_headers).json()["data"]}

    # 300 raw + 300 penalty = 600, against 420 and 900.
    assert rows[fast_with_hint]["adjusted_total_seconds"] == 600
    assert rows[steady]["adjusted_total_seconds"] == 420
    assert rows[slow]["adjusted_total_seconds"] == 900
    assert rows[steady]["rank"] < rows[fast_with_hint]["rank"] < rows[slow]["rank"]


def test_a_correction_updates_rather_than_duplicates(
    client: TestClient, organizer_headers: dict, marshal_headers: dict
):
    """
    A marshal fixing a mistyped time must not leave the old value behind in the
    qualification store.
    """
    team = _team(client, organizer_headers, "Corrected Squad")
    _write_via_dashboard(client, marshal_headers, team, (500, 500, 500))
    _write_via_dashboard(client, marshal_headers, team, (100, 100, 100))

    rows = {r["team_id"]: r for r in _read_via_qualification_layer(client, organizer_headers).json()["data"]}
    assert rows[team]["raw_total_seconds"] == 300


def test_the_batch_endpoint_bridges_too(
    client: TestClient, organizer_headers: dict, marshal_headers: dict
):
    """
    The dashboard offers a batch save. It must feed the qualification store as
    well, or a bulk entry silently goes nowhere.
    """
    a = _team(client, organizer_headers, "Batch A")
    b = _team(client, organizer_headers, "Batch B")
    payload = {
        "records": [
            {"teamId": t, "miniRounds": [
                {"roundNumber": n, "durationSeconds": 110, "hintsUsed": 0, "isCompleted": True}
                for n in (1, 2, 3)
            ]}
            for t in (a, b)
        ]
    }
    r = client.post("/api/v1/rounds/1/records/batch", json=payload, headers=marshal_headers)
    assert r.status_code == 200, r.text

    rows = {row["team_id"]: row for row in _read_via_qualification_layer(client, organizer_headers).json()["data"]}
    assert rows[a]["raw_total_seconds"] == 330
    assert rows[b]["raw_total_seconds"] == 330


def test_the_penalty_config_is_kept_in_step(
    client: TestClient, organizer_headers: dict, marshal_headers: dict
):
    """
    Standings read the penalty from the new layer's own config row, not from
    the legacy round state, so the bridge has to keep that row correct too.
    """
    team = _team(client, organizer_headers, "Config Squad")
    _write_via_dashboard(client, marshal_headers, team, (100, 100, 100))

    cfg = client.get("/api/rounds/1/config", headers=organizer_headers).json()["data"]
    assert cfg["penalty_per_hint_seconds"] == 300
