from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.api.router import api_router
from app.api.routes.health import health_check
from app.services.auth_service import ensure_default_organizer
from app.services.dashboard_service import get_or_create_settings
from app.db.seed_production_roster import seed_production_roster


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema
    Base.metadata.create_all(bind=engine)
    # Seed default organizer, settings, and authoritative tournament roster
    with SessionLocal() as db:
        ensure_default_organizer(db)
        get_or_create_settings(db)
        seed_production_roster(db)
        # Ensure pre-start test scans and dry run state are cleanly reset
        from app.services.round1_service import reset_round1_live_state, get_or_create_round1_config
        cfg = get_or_create_round1_config(db)
        # A restart during the live event must never erase scans or answers.
        # Only clean dry-run data while Round 1 has not started yet.
        if not cfg.is_finalized and not cfg.started_at:
            # Clean up dry-run scans and reset initial state for real event
            reset_round1_live_state(db)
    yield


is_production = settings.ENVIRONMENT.lower() == "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Production-ready FastAPI backend for EVENT HQ tournament management platform.",
    # Interactive API documentation is useful locally, but must not advertise
    # operational endpoints during the live event.
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root-level health check endpoint
@app.get("/health", tags=["Health"])
def root_health():
    with SessionLocal() as db:
        return health_check(db)

# Include API Routers (/api and /api/v1 for compatibility)
app.include_router(api_router, prefix="/api")
app.include_router(api_router, prefix=settings.API_V1_STR)


# Custom exception handlers for unified JSON envelope
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "message": exc.detail,
            "isMockData": False,
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0]["msg"] if errors else "Validation error"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "data": errors,
            "message": f"Validation Error: {first_error}",
            "isMockData": False,
        }
    )
