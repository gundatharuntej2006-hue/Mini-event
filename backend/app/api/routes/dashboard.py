from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import get_optional_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.dashboard import DashboardOverviewResponse
from app.services.dashboard_service import get_dashboard_overview

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=ApiResponse[DashboardOverviewResponse])
def get_overview(
    db: Session = Depends(get_db),
    user: User = Depends(get_optional_user)
):
    overview = get_dashboard_overview(db)
    return ApiResponse(
        data=overview,
        message="Dashboard overview metrics computed"
    )
