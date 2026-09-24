"""
PROBE: does Round 3 money and code state written by the dashboard reach the
services that spend it and gate on it?

Round 3 is served by two router layers at once. api/router.py mounts the new
r3_router (prefix /rounds/3) before the legacy rounds.router, so for any path
they both define, the new one wins - and for paths only the legacy one defines,
the legacy one serves it. The frontend calls a mix:

    /rounds/3/transactions          only legacy defines it  -> round3_transactions
    /rounds/3/transfer              only legacy             -> round3_transactions
    /rounds/3/standings             only legacy             -> round3_transactions
    /rounds/3/codes/fragment        only legacy             -> round3_code_records
    /rounds/3/purchase              new                     -> team_wallets
    /teams/{id}/wallet              new                     -> team_wallets
    /code-hunt/{id}/fragment/N      new                     -> code_hunt tables

These tests are written to FAIL if the stores are disconnected. Each one writes
through the endpoint the dashboard actually uses and reads through the service
that actually decides something.
"""

from fastapi.testclient import TestClient

from app.core import constants as C


def _team(client, headers, name):
    return client.post("/api/v1/teams", json={"name": name}, headers=headers).json()["data"]["id"]


def test_points_awarded_by_the_dashboard_are_spendable(
    client: TestClient, organizer_headers: dict, marshal_headers: dict
):
    """
    A marshal awards points through /rounds/3/transactions, which is what the
    dashboard calls. Those points must show in the wallet, because the wallet
    is what purchases and qualification read.
    """
    team = _team(client, organizer_headers, "Money Squad")

    r = client.post(
        "/api/v1/rounds/3/transactions",
        json={"teamId": team, "amount": 500.0, "type": "earn", "reason": "Round 2 bonus"},
        headers=marshal_headers,
    )
    assert r.status_code == 200, r.text

    w = client.get(f"/api/teams/{team}/wallet", headers=organizer_headers)
    assert w.status_code == 200, w.text
    balance = w.json()["data"]["currentBalance"]
    assert balance == C.STARTING_WALLET_BALANCE + 500, (
        f"awarded 500 through the dashboard, wallet shows {balance} - "
        "the two Round 3 stores are not connected"
    )


def test_a_fragment_logged_by_the_dashboard_opens_the_round4_gate(
    client: TestClient, organizer_headers: dict, marshal_headers: dict
):
    """
    A code verifier logs both fragments through /rounds/3/codes/fragment, which
    is what the dashboard calls. The Round 4 eligibility check reads the
    code-hunt store, so it has to see them.
    """
    team = _team(client, organizer_headers, "Code Squad")

    for idx in range(C.CODE_FRAGMENT_COUNT):
        r = client.put(
            "/api/v1/rounds/3/codes/fragment",
            json={"teamId": team, "fragmentIndex": idx, "isDiscovered": True, "code": f"F{idx}"},
            headers=marshal_headers,
        )
        assert r.status_code == 200, r.text

    e = client.get(f"/api/code-hunt/eligibility/r4/{team}", headers=organizer_headers)
    assert e.status_code == 200, e.text
    assert e.json()["data"].get("isEligible") is True, (
        "both fragments logged through the dashboard, but the Round 4 gate "
        "still says the team has no Final Code"
    )


def test_a_transfer_made_by_the_dashboard_moves_real_money(
    client: TestClient, organizer_headers: dict, marshal_headers: dict
):
    """/rounds/3/transfer is legacy-only; the wallets are what get spent."""
    a = _team(client, organizer_headers, "Sender Squad")
    b = _team(client, organizer_headers, "Receiver Squad")

    r = client.post(
        "/api/v1/rounds/3/transfer",
        json={"fromTeamId": a, "toTeamId": b, "amount": 200.0, "reason": "Alliance"},
        headers=marshal_headers,
    )
    assert r.status_code == 200, r.text

    wa = client.get(f"/api/teams/{a}/wallet", headers=organizer_headers).json()["data"]
    wb = client.get(f"/api/teams/{b}/wallet", headers=organizer_headers).json()["data"]
    assert wa["currentBalance"] == C.STARTING_WALLET_BALANCE - 200
    assert wb["currentBalance"] == C.STARTING_WALLET_BALANCE + 200
