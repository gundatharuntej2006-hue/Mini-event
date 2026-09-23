"""
Core models compatibility adapter for EVENT HQ.
Re-exports Team from app.models.team and provides seed_default_teams().
Preserves single authoritative Team model.
"""
from sqlalchemy.orm import Session
from app.models.team import Team, TeamStatus
from app.models.participant import Participant

__all__ = ["Team", "Participant", "seed_default_teams"]

SAMPLE_SQUAD_NAMES = [
    "Vanguard Titans", "Cipher Syndicate", "Quantum Drift", "Nexus Protocol",
    "Aegis Vanguard", "Shadow Syndicate", "Helix Dynamics", "Apex Sentinels",
    "Binary Phantoms", "Echo Recon", "Solaris Brigade", "Chronos Enclave",
    "Ironclad Ops", "Nova Strike", "Phantom Circuit", "Zero-Day Unit",
    "Spectre Division", "Rogue Matrix", "Vortex Legion", "Omega Collective",
    "Titanium Core", "Aero Blitz", "Cyber Haven", "Pulse Rangers",
    "Delta Horizon", "Obsidian Vanguard", "Aether Sentinels", "Falcon Wing",
    "Hyperion Guild", "Starlight Armada", "Crimson Guard", "Zenith Alliance"
]


def seed_default_teams(db: Session) -> None:
    """Populates the 32 standard registered squads if table has fewer than 32 teams."""
    existing_count = db.query(Team).count()
    if existing_count >= 32:
        return

    for i in range(32):
        team_id = f"team-{i + 1}"
        existing = db.query(Team).filter((Team.id == team_id) | (Team.team_number == i + 1)).first()
        if not existing:
            team_name = SAMPLE_SQUAD_NAMES[i] if i < len(SAMPLE_SQUAD_NAMES) else f"Squad {i + 1}"
            team = Team(
                id=team_id,
                team_number=i + 1,
                name=team_name,
                status=TeamStatus.ACTIVE,
                current_round=1,
                total_score=0.0
            )
            db.add(team)
    db.commit()
