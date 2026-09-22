from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.schemas.common import ApiResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=ApiResponse[dict])
def health_check(db: Session = Depends(get_db)):
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return ApiResponse(
        data={
            "status": "online",
            "database": db_status,
            "version": "1.0.0",
        },
        message="EVENT HQ API service is running"
    )
