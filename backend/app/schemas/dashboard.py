from typing import List, Optional
from pydantic import BaseModel, Field


class DashboardStatsResponse(BaseModel):
    total_teams: int = Field(serialization_alias="totalTeams")
    total_participants: int = Field(serialization_alias="totalParticipants")
    current_round_name: str = Field(serialization_alias="currentRoundName")
    current_round_number: int = Field(serialization_alias="currentRoundNumber")
    current_round_status: str = Field(serialization_alias="currentRoundStatus")
    qualified_teams_target: int = Field(default=24, serialization_alias="qualifiedTeamsTarget")
    active_teams_remaining: int = Field(serialization_alias="activeTeamsRemaining")
    event_progress_percentage: int = Field(default=20, serialization_alias="eventProgressPercentage")
    checked_in_teams: int = Field(serialization_alias="checkedInTeams")
    checked_in_participants: int = Field(serialization_alias="checkedInParticipants")
    complete_roster_teams: int = Field(serialization_alias="completeRosterTeams")
    incomplete_roster_teams: int = Field(serialization_alias="incompleteRosterTeams")
    agents_assigned: int = Field(default=0, serialization_alias="agentsAssigned")
    fragments_discovered: int = Field(default=0, serialization_alias="fragmentsDiscovered")
    total_fragments: int = Field(default=0, serialization_alias="totalFragments")

    model_config = {
        "populate_by_name": True,
    }


class ActivityLogItem(BaseModel):
    id: str
    timestamp: str
    category: str
    title: str
    description: str
    team_tag: Optional[str] = Field(default=None, serialization_alias="teamTag")
    badge_type: str = Field(default="default", serialization_alias="badgeType")

    model_config = {
        "populate_by_name": True,
    }


class RoundProgressionStepResponse(BaseModel):
    round_number: int = Field(serialization_alias="roundNumber")
    name: str
    qualifying_count: int = Field(serialization_alias="qualifyingCount")
    total_pool: int = Field(serialization_alias="totalPool")
    status: str

    model_config = {
        "populate_by_name": True,
    }


class DashboardOverviewResponse(BaseModel):
    stats: DashboardStatsResponse
    progression: List[RoundProgressionStepResponse] = Field(default_factory=list)
    recent_activities: List[ActivityLogItem] = Field(default_factory=list, serialization_alias="recentActivities")

    model_config = {
        "populate_by_name": True,
    }
