from fastapi import APIRouter
from app.api.routes import health, auth, teams, participants, dashboard, settings, rounds, integrations, wallet, code_hunt, secret_agents
from app.api.rounds.round1 import router as r1_router
from app.api.rounds.round2 import router as r2_router
from app.api.rounds.round3 import router as r3_router
from app.api.rounds.round4 import router as r4_router
from app.api.rounds.finale import router as finale_router
from app.api.rounds.progression import router as progression_router

api_router = APIRouter()

# Core tournament management & administration routes
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(teams.router)
api_router.include_router(wallet.router)
api_router.include_router(code_hunt.router)
api_router.include_router(secret_agents.router)
api_router.include_router(participants.router)
api_router.include_router(dashboard.router)
api_router.include_router(settings.router)
# Modular tournament round mechanics & progression routes (specific prefixes evaluated first)
api_router.include_router(r1_router)
api_router.include_router(r2_router)
api_router.include_router(r3_router)
api_router.include_router(r4_router)
api_router.include_router(finale_router, prefix="/rounds/finale")
api_router.include_router(finale_router, prefix="/finale")
api_router.include_router(progression_router)

# Unified tournament rounds & generic round-state routes
api_router.include_router(rounds.router)
api_router.include_router(integrations.router)
