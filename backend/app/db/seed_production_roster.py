"""
Authoritative, idempotent production tournament roster seeder for EVENT HQ.
Populates the exact 32 teams and 160 participants (including Divyansh Singh in Team Mirage).
Works across both SQLite and PostgreSQL (Neon).
"""
import os
import json
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.team import Team, TeamStatus
from app.models.participant import Participant, ParticipantRole
from app.models.round_models import Round1Record

ROSTER_JSON_PATH = os.path.join(os.path.dirname(__file__), "production_roster.json")


def load_production_roster_data() -> list[dict[str, Any]]:
    """Loads and returns the authoritative 32-team roster from production_roster.json."""
    if not os.path.exists(ROSTER_JSON_PATH):
        raise FileNotFoundError(f"Authoritative production roster file not found at {ROSTER_JSON_PATH}")
    with open(ROSTER_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_production_roster(db: Session) -> Tuple[int, int]:
    """
    Idempotently seeds the 32 teams, 160 participants, and baseline Round1 records.
    - If a team exists by ID or team_number, updates name/table/status/round without wiping.
    - If a participant exists by USN or ID, updates attributes without duplicating.
    - If missing, creates the record.
    Returns:
        Tuple[int, int]: (seeded_or_updated_teams_count, seeded_or_updated_participants_count)
    """
    roster_data = load_production_roster_data()

    total_teams = 0
    total_participants = 0

    default_mini_rounds = (
        '[{"roundNumber": 1, "hintsUsed": 0, "hintPenaltySeconds": 0, "isCompleted": false}, '
        '{"roundNumber": 2, "hintsUsed": 0, "hintPenaltySeconds": 0, "isCompleted": false}, '
        '{"roundNumber": 3, "hintsUsed": 0, "hintPenaltySeconds": 0, "isCompleted": false}]'
    )

    for team_dict in roster_data:
        team_id = team_dict["id"]
        team_number = team_dict["team_number"]
        team_name = team_dict["name"]
        assigned_table = team_dict.get("assigned_table")
        status_str = team_dict.get("status", "ACTIVE")
        current_round = team_dict.get("current_round", 1)

        status_enum = TeamStatus.ACTIVE
        for s in TeamStatus:
            if s.value.lower() == status_str.lower() or s.name.lower() == status_str.lower():
                status_enum = s
                break

        team = db.query(Team).filter((Team.id == team_id) | (Team.team_number == team_number)).first()
        if not team:
            team = Team(
                id=team_id,
                team_number=team_number,
                name=team_name,
                assigned_table=assigned_table,
                status=status_enum,
                current_round=current_round,
                total_score=0.0
            )
            db.add(team)
            db.flush()
        else:
            team.name = team_name
            team.assigned_table = assigned_table
            if team.current_round == 1 and team.total_score == 0.0:
                team.status = status_enum
                team.current_round = current_round

        total_teams += 1

        r1_record = db.query(Round1Record).filter(Round1Record.team_id == team.id).first()
        if not r1_record:
            r1_record = Round1Record(
                id=f"r1-{team.id.replace('team-', '')}",
                team_id=team.id,
                mini_rounds_json=default_mini_rounds,
                is_complete=False,
                qualification_status="Incomplete"
            )
            db.add(r1_record)

        for member_dict in team_dict.get("members", []):
            part_id = member_dict["id"]
            part_name = member_dict["name"]
            part_email = member_dict["email"]
            part_usn = member_dict["usn"]
            part_phone = member_dict.get("phone")
            part_role_str = member_dict.get("role", "MEMBER").upper()
            part_role = ParticipantRole.LEADER if "LEAD" in part_role_str else ParticipantRole.MEMBER
            checked_in = bool(member_dict.get("checked_in", False))

            part = db.query(Participant).filter(
                (Participant.id == part_id) | (Participant.usn == part_usn)
            ).first()

            if not part:
                part = Participant(
                    id=part_id,
                    name=part_name,
                    email=part_email,
                    usn=part_usn,
                    phone=part_phone,
                    role=part_role,
                    checked_in=checked_in,
                    team_id=team.id
                )
                db.add(part)
            else:
                part.name = part_name
                part.email = part_email
                part.usn = part_usn
                part.phone = part_phone
                part.role = part_role
                part.team_id = team.id

            total_participants += 1

    db.commit()
    return total_teams, total_participants
