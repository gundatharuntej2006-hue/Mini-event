from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.team import Team, TeamStatus
from app.models.participant import Participant
from app.models.event_settings import EventSettings
from app.schemas.dashboard import (
    DashboardStatsResponse,
    DashboardOverviewResponse,
    RoundProgressionStepResponse,
    ActivityLogItem,
)
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services import round_service


def get_or_create_settings(db: Session) -> EventSettings:
    settings = db.query(EventSettings).filter(EventSettings.id == 1).first()
    if not settings:
        settings = EventSettings(
            id=1,
            event_name="EVENT HQ · BMSIT 2026",
            current_round_number=1,
            current_round_name="Round 1: Clue Hunt",
            current_round_status="In Progress",
            table_count=32,
            is_mock_enabled=False,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    elif not getattr(settings, "webhook_secret", None) or len(settings.webhook_secret) < 32:
        import secrets
        settings.webhook_secret = f"whsec_{secrets.token_hex(24)}"
        db.commit()
        db.refresh(settings)
    return settings


def get_dashboard_overview(db: Session) -> DashboardOverviewResponse:
    settings = get_or_create_settings(db)
    
    teams = db.query(Team).all()
    participants = db.query(Participant).all()
    
    total_teams = len(teams)
    total_participants = len(participants)
    checked_in_participants = sum(1 for p in participants if p.checked_in)
    
    complete_roster_teams = 0
    incomplete_roster_teams = 0
    checked_in_teams = 0
    active_teams = 0
    
    for t in teams:
        m_count = len(t.members)
        if m_count == 5:
            complete_roster_teams += 1
        else:
            incomplete_roster_teams += 1
            
        if m_count == 5 and all(m.checked_in for m in t.members):
            checked_in_teams += 1
            
        if t.status in [TeamStatus.ACTIVE, TeamStatus.CHECKED_IN, TeamStatus.REGISTERED]:
            active_teams += 1

    stats = DashboardStatsResponse(
        total_teams=total_teams,
        total_participants=total_participants,
        current_round_name=settings.current_round_name,
        current_round_number=settings.current_round_number,
        current_round_status=settings.current_round_status,
        qualified_teams_target=24,
        active_teams_remaining=active_teams,
        event_progress_percentage=20 * settings.current_round_number,
        checked_in_teams=checked_in_teams,
        checked_in_participants=checked_in_participants,
        complete_roster_teams=complete_roster_teams,
        incomplete_roster_teams=incomplete_roster_teams,
        agents_assigned=0,
        fragments_discovered=0,
        total_fragments=0,
    )
    
    # Generate activity logs from recent events
    recent_activities: List[ActivityLogItem] = []
    
    # Check-in activities
    checked_in_parts = [p for p in participants if p.checked_in and p.checked_in_at]
    checked_in_parts.sort(key=lambda x: x.checked_in_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    
    for p in checked_in_parts[:5]:
        recent_activities.append(
            ActivityLogItem(
                id=f"act-checkin-{p.id}",
                timestamp=p.checked_in_at.isoformat() if p.checked_in_at else datetime.now(timezone.utc).isoformat(),
                category="checkin",
                title=f"{p.name} Checked In",
                description=f"USN: {p.usn} verified and marked present.",
                team_tag=p.team.name if p.team else None,
                badge_type="success",
            )
        )
        
    # Retrieve tournament progression steps
    rounds = round_service.get_all_rounds(db)
    progression: List[RoundProgressionStepResponse] = []
    for r in rounds:
        st = "Completed" if r.is_finalized else ("Live" if r.status in ["In Progress", "Live"] else "Scheduled")
        progression.append(
            RoundProgressionStepResponse(
                round_number=r.id,
                name=r.name,
                qualifying_count=r.qualifying_teams_count,
                total_pool=r.initial_teams_count,
                status=st,
            )
        )

    return DashboardOverviewResponse(
        stats=stats,
        progression=progression,
        recent_activities=recent_activities,
    )


def update_event_settings(db: Session, update_in: SettingsUpdate) -> SettingsResponse:
    settings = get_or_create_settings(db)
    
    if update_in.event_name is not None:
        settings.event_name = update_in.event_name
    if update_in.current_round_number is not None:
        settings.current_round_number = update_in.current_round_number
    if update_in.current_round_name is not None:
        settings.current_round_name = update_in.current_round_name
    if update_in.current_round_status is not None:
        settings.current_round_status = update_in.current_round_status
    if update_in.table_count is not None:
        settings.table_count = update_in.table_count
    if update_in.enable_mock_data is not None:
        settings.is_mock_enabled = update_in.enable_mock_data

    db.commit()
    db.refresh(settings)
    
    return SettingsResponse(
        event_name=settings.event_name,
        current_round_number=settings.current_round_number,
        current_round_name=settings.current_round_name,
        current_round_status=settings.current_round_status,
        table_count=settings.table_count,
        enable_mock_data=settings.is_mock_enabled,
    )
