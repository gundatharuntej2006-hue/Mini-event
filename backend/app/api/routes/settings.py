from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import require_role, get_optional_user
from app.models.user import User, UserRole
from app.schemas.common import ApiResponse
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services.dashboard_service import get_or_create_settings, update_event_settings

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=ApiResponse[SettingsResponse])
def get_settings(
    db: Session = Depends(get_db),
    user: User = Depends(get_optional_user)
):
    settings = get_or_create_settings(db)
    return ApiResponse(
        data=SettingsResponse(
            event_name=settings.event_name,
            current_round_number=settings.current_round_number,
            current_round_name=settings.current_round_name,
            current_round_status=settings.current_round_status,
            table_count=settings.table_count,
            enable_mock_data=settings.is_mock_enabled,
        ),
        message="Event settings retrieved"
    )


@router.patch("", response_model=ApiResponse[SettingsResponse])
@router.put("", response_model=ApiResponse[SettingsResponse])
def update_settings(
    settings_in: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER]))
):
    updated = update_event_settings(db, settings_in)
    return ApiResponse(
        data=updated,
        message="Event settings updated successfully"
    )

