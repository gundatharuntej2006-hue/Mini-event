"""
Unit and integration tests for authoritative 32-team / 160-participant production roster.
Verifies production_roster.json and seed_production_roster service.
"""
import os
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.team import Team
from app.models.participant import Participant
from app.models.round_models import Round1Record
from app.db.seed_production_roster import load_production_roster_data, seed_production_roster


def test_production_roster_json_integrity():
    roster = load_production_roster_data()
    assert len(roster) == 32, f"Expected 32 teams in production_roster.json, got {len(roster)}"

    team_ids = set()
    team_numbers = set()
    part_ids = set()
    usns = set()
    emails = set()

    total_participants = 0

    for t in roster:
        assert "id" in t and t["id"].startswith("team-")
        assert "team_number" in t and 1 <= t["team_number"] <= 32
        assert "name" in t and len(t["name"]) > 0

        assert t["id"] not in team_ids, f"Duplicate team ID: {t['id']}"
        assert t["team_number"] not in team_numbers, f"Duplicate team number: {t['team_number']}"
        team_ids.add(t["id"])
        team_numbers.add(t["team_number"])

        members = t.get("members", [])
        assert len(members) == 5, f"Team {t['name']} ({t['id']}) must have exactly 5 members, found {len(members)}"
        total_participants += len(members)

        leader_count = 0
        for m in members:
            assert m["id"] not in part_ids, f"Duplicate participant ID: {m['id']}"
            assert m["usn"].lower() not in usns, f"Duplicate USN: {m['usn']}"
            assert m["email"].lower() not in emails, f"Duplicate Email: {m['email']}"

            part_ids.add(m["id"])
            usns.add(m["usn"].lower())
            emails.add(m["email"].lower())

            if "LEAD" in m.get("role", "").upper():
                leader_count += 1

        assert leader_count == 1, f"Team {t['name']} must have exactly 1 leader, found {leader_count}"

    assert total_participants == 160, f"Expected 160 participants, got {total_participants}"

    # Specific check for Team Mirage and Divyansh Singh
    mirage = next(t for t in roster if t["id"] == "team-1032")
    assert mirage["name"] == "Team Mirage"
    assert len(mirage["members"]) == 5
    divyansh = next((m for m in mirage["members"] if m["name"] == "Divyansh Singh"), None)
    assert divyansh is not None, "Divyansh Singh missing from Team Mirage"
    assert divyansh["role"] == "MEMBER"


def test_seed_production_roster_idempotency(tmp_path):
    test_db = tmp_path / "test_roster_idempotent.db"
    engine = create_engine(f"sqlite:///{test_db}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    # First Seed
    with Session() as db:
        teams_count, parts_count = seed_production_roster(db)
        assert teams_count == 32
        assert parts_count == 160

    with Session() as db:
        teams = db.query(Team).all()
        parts = db.query(Participant).all()
        r1_records = db.query(Round1Record).all()
        assert len(teams) == 32
        assert len(parts) == 160
        assert len(r1_records) == 32

        mirage = db.query(Team).filter(Team.id == "team-1032").first()
        assert mirage is not None
        assert len(mirage.members) == 5
        member_names = [m.name for m in mirage.members]
        assert "Divyansh Singh" in member_names

    # Second Seed (Idempotency Check)
    with Session() as db:
        teams_count_2, parts_count_2 = seed_production_roster(db)
        assert teams_count_2 == 32
        assert parts_count_2 == 160

    with Session() as db:
        teams_2 = db.query(Team).all()
        parts_2 = db.query(Participant).all()
        r1_records_2 = db.query(Round1Record).all()
        assert len(teams_2) == 32
        assert len(parts_2) == 160
        assert len(r1_records_2) == 32

    engine.dispose()
