from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar, List
from pydantic import BaseModel, Field

T = TypeVar("T")


def utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: Optional[str] = None
    isMockData: bool = Field(default=False, serialization_alias="isMockData")
    timestamp: str = Field(default_factory=utc_iso_now)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class PaginatedData(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    pageSize: int = Field(serialization_alias="pageSize")
    totalPages: int = Field(serialization_alias="totalPages")

    model_config = {
        "populate_by_name": True,
    }
