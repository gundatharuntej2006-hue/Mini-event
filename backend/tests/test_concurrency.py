import os
import pytest
import concurrent.futures
from app.core.config import settings
from app.models.participant import Participant

is_postgres = settings.DATABASE_URL.startswith("postgresql") or os.environ.get("DATABASE_URL", "").startswith("postgresql")


@pytest.mark.skipif(
    not is_postgres,
    reason="PostgreSQL Row-Locking Concurrency Test: Requires a running PostgreSQL instance with row-level locking (SELECT ... FOR UPDATE) and multi-connection concurrency. SQLite in-memory is locked at database-level."
)
def test_postgresql_concurrent_simultaneous_participant_creation_squad_cap(client, marshal_headers, db_session):
    """
    PostgreSQL Integration Test:
    Simultaneously executes 10 concurrent requests to add members to a team with only 1 slot remaining.
    Verifies that PostgreSQL row-level locks serialize the requests, exactly 1 succeeds, 9 fail with HTTP 400,
    and the squad count strictly equals 5.
    """
    # 1. Create team and fill 4 slots
    t_res = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Postgres Concurrent Squad"})
    assert t_res.status_code == 201
    team_id = t_res.json()["data"]["id"]

    for i in range(1, 5):
        res = client.post(
            "/api/v1/participants",
            headers=marshal_headers,
            json={
                "name": f"Base Member {i}",
                "email": f"pg_base{i}@bmsit.in",
                "usn": f"1BY22CS70{i}",
                "teamId": team_id,
            }
        )
        assert res.status_code == 201

    # 2. Fire 10 simultaneous concurrent requests to claim the 1 remaining slot
    def attempt_create_member(idx: int):
        return client.post(
            "/api/v1/participants",
            headers=marshal_headers,
            json={
                "name": f"Concurrent Candidate {idx}",
                "email": f"pg_cand{idx}@bmsit.in",
                "usn": f"1BY22CS75{idx:02d}",
                "teamId": team_id,
            }
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(attempt_create_member, i) for i in range(1, 11)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    success_count = sum(1 for r in results if r.status_code == 201)
    rejected_count = sum(1 for r in results if r.status_code == 400)

    assert success_count == 1, f"Expected exactly 1 success, got {success_count}"
    assert rejected_count == 9, f"Expected exactly 9 rejections, got {rejected_count}"

    team_members = db_session.query(Participant).filter(Participant.team_id == team_id).all()
    assert len(team_members) == 5, f"Team member count must strictly equal 5, got {len(team_members)}"


@pytest.mark.skipif(
    not is_postgres,
    reason="PostgreSQL Row-Locking Concurrency Test: Requires PostgreSQL instance for multi-connection transfer locking."
)
def test_postgresql_concurrent_simultaneous_transfers_squad_cap(client, marshal_headers, db_session):
    """
    PostgreSQL Integration Test:
    Simultaneously executes 5 concurrent transfers into a destination team with 4 members.
    Verifies that deterministic multi-team locking prevents deadlocks and enforces the 5-member limit.
    """
    target_res = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Postgres Target Transfer Squad"})
    assert target_res.status_code == 201
    target_team_id = target_res.json()["data"]["id"]

    for i in range(1, 5):
        client.post(
            "/api/v1/participants",
            headers=marshal_headers,
            json={
                "name": f"Target Member {i}",
                "email": f"pg_target{i}@bmsit.in",
                "usn": f"1BY22CS80{i}",
                "teamId": target_team_id,
            }
        )

    candidate_ids = []
    for i in range(1, 6):
        res = client.post(
            "/api/v1/participants",
            headers=marshal_headers,
            json={
                "name": f"Transfer Candidate {i}",
                "email": f"pg_transfer{i}@bmsit.in",
                "usn": f"1BY22CS85{i}",
                "teamId": None,
            }
        )
        assert res.status_code == 201
        candidate_ids.append(res.json()["data"]["id"])

    def attempt_transfer(part_id: str):
        return client.post(
            f"/api/v1/participants/{part_id}/transfer",
            headers=marshal_headers,
            json={"targetTeamId": target_team_id}
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(attempt_transfer, pid) for pid in candidate_ids]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    success_count = sum(1 for r in results if r.status_code == 200)
    rejected_count = sum(1 for r in results if r.status_code == 400)

    assert success_count == 1, f"Expected exactly 1 transfer success, got {success_count}"
    assert rejected_count == 4, f"Expected exactly 4 transfer rejections, got {rejected_count}"

    final_members = db_session.query(Participant).filter(Participant.team_id == target_team_id).all()
    assert len(final_members) == 5, f"Destination team must have exactly 5 members, got {len(final_members)}"