from fastapi import APIRouter
from app.api.routes import health, auth, teams, participants, dashboard, settings, rounds, integrations

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(teams.router)
api_router.include_router(participants.router)
api_router.include_router(dashboard.router)
api_router.include_router(settings.router)
api_router.include_router(rounds.router)
api_router.include_router(integrations.router)

