from typing import Optional
from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    event_name: str = Field(serialization_alias="eventName")
    current_round_number: int = Field(serialization_alias="currentRoundNumber")
    current_round_name: str = Field(serialization_alias="currentRoundName")
    current_round_status: str = Field(serialization_alias="currentRoundStatus")
    table_count: int = Field(serialization_alias="tableCount")
    enable_mock_data: bool = Field(serialization_alias="enableMockData")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class SettingsUpdate(BaseModel):
    event_name: Optional[str] = Field(default=None, alias="eventName")
    current_round_number: Optional[int] = Field(default=None, alias="currentRoundNumber")
    current_round_name: Optional[str] = Field(default=None, alias="currentRoundName")
    current_round_status: Optional[str] = Field(default=None, alias="currentRoundStatus")
    table_count: Optional[int] = Field(default=None, alias="tableCount")
    enable_mock_data: Optional[bool] = Field(default=None, alias="enableMockData")

    model_config = {
        "populate_by_name": True,
    }
