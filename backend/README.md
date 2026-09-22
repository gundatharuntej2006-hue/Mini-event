# EVENT HQ — FastAPI Backend (Part 1)

Production-grade tournament management backend for **EVENT HQ** at BMSIT 2026. Built with FastAPI, SQLAlchemy 2.0, PostgreSQL / SQLite, Alembic migrations, and JWT Role-Based Access Control (RBAC).

---

## 1. Architecture & Security Features

- **FastAPI 0.115+**: Async API framework with automated OpenAPI, Swagger UI (`/docs`), and ReDoc (`/redoc`).
- **Unified API Envelope**: Standard `ApiResponse<T>` response wrapper matching the React frontend client.
- **SQLAlchemy 2.0 & Typed ORM**: Database models with explicit relationship cascades (`cascade="save-update, merge"` preserving participants on team deletion).
- **Alembic Database Migrations**: Reliable, reproducible schema migrations.
- **Explicit Secret Validation**: `SECRET_KEY` must be explicitly provided in `.env` (min 32 characters). Insecure automatic fallback secrets are strictly prohibited.
- **JWT & RBAC Authorization**: Granular role enforcement across `ORGANIZER`, `MARSHAL`, `JUDGE`, and `PUBLIC_PROJECTOR`. Authoritative user status and roles are verified directly against the database on each request.
- **Data Privacy & PII Masking**: Direct participant directories require authenticated staff. Public and Projector views of teams automatically strip participant PII (`email`, `phone`, `usn` set to `null`).
- **5-Person Squad Limit & Concurrency Strategy**:
  - Capacity limit is enforced atomically in all mutation paths (registration, updates, transfers).
  - On PostgreSQL, row-level locks (`SELECT ... FOR UPDATE`) are acquired in deterministic sorted ID order across teams to prevent deadlocks and serialize concurrent assignments.
- **Auditable Check-In Timestamps**: Check-in toggle records exact UTC ISO-8601 timestamps (`checked_in_at`).

---

## 2. Directory Structure

```text
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── auth.py          # /api/v1/auth (login, register, me)
│   │   │   ├── dashboard.py     # /api/v1/dashboard/overview
│   │   │   ├── health.py        # /health, /api/v1/health
│   │   │   ├── participants.py  # /api/v1/participants (CRUD, check-in, transfer)
│   │   │   ├── rounds.py        # /api/v1/rounds (Rounds 1-5 scoring, progression, finalization)
│   │   │   ├── settings.py      # /api/v1/settings (tournament metadata)
│   │   │   └── teams.py         # /api/v1/teams (CRUD & roster management)
│   │   └── router.py            # API v1 route aggregator
│   ├── core/
│   │   ├── config.py            # Pydantic Settings & environment validation
│   │   ├── dependencies.py      # get_db, auth verification, and require_role guards
│   │   └── security.py          # Native Bcrypt hashing & JWT token encode/decode
│   ├── db/
│   │   ├── base.py              # DeclarativeBase and UTC datetime helpers
│   │   └── session.py           # Engine & SessionLocal factory
│   ├── models/                  # SQLAlchemy 2.0 declarative models
│   │   ├── event_settings.py    # EventSettings table
│   │   ├── participant.py       # Participant table
│   │   ├── round_models.py      # Round states, scoring records, transactions, pairs, scorecards
│   │   ├── team.py              # Team table
│   │   └── user.py              # User table & UserRole enum
│   ├── schemas/                 # Pydantic validation & response models
│   │   ├── auth.py
│   │   ├── common.py            # ApiResponse & PaginatedData envelopes
│   │   ├── dashboard.py
│   │   ├── participant.py       # Full & PII-masked public participant schemas
│   │   ├── rounds.py            # Tournament rounds 1-5 scoring, submissions & standings schemas
│   │   ├── settings.py
│   │   ├── team.py
│   │   └── user.py
│   ├── services/                # Isolated business logic layer
│   │   ├── auth_service.py
│   │   ├── dashboard_service.py
│   │   ├── participant_service.py
│   │   ├── round_service.py     # Round 1-5 scoring engines, economy ledger, finalization gates
│   │   └── team_service.py
│   └── main.py                  # FastAPI application entrypoint & CORS middleware
├── alembic/                     # Alembic migration environment and versions
│   ├── versions/
│   │   ├── 3c059318c96d_initial_schema_users_teams_participants.py
│   │   └── 96d9541ddc93_add_rounds_and_scoring_models.py
│   ├── env.py
│   └── script.py.mako
├── tests/                       # Automated pytest suite
│   ├── conftest.py              # In-memory SQLite fixtures & auth token helpers
│   ├── test_auth.py             # Authentication & token verification tests
│   ├── test_concurrency.py      # Multi-session PostgreSQL concurrency tests
│   ├── test_config_security.py  # Secret key validation & configuration tests
│   ├── test_dashboard.py        # Dashboard overview metric tests
│   ├── test_data_integrity.py   # Edge cases, duplicate USN/team names, & validation
│   ├── test_health.py           # Health check endpoints
│   ├── test_participants.py     # Squad limits, transfers, check-ins, unassignments
│   ├── test_rounds_scoring.py   # Complete tournament rounds 1-5 scoring & progression
│   ├── test_security_and_privacy.py # RBAC matrix, PII masking, team deletion
│   └── test_teams.py            # Teams CRUD & duplicate rejection
├── alembic.ini                  # Alembic configuration
├── cli.py                       # Administrative CLI (init-db, create-user, seed-demo)
├── requirements.txt             # Python dependencies
├── .env.example                 # Template environment variables
├── API_CONTRACT.md              # Complete API specification and payloads
└── README.md                    # Setup and operational documentation
```

---

## 3. Quick Start & Local Setup

### Step 1: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure `SECRET_KEY` is set to a secure random string with **at least 32 characters**.

### Step 3: Run Database Migrations
```bash
alembic upgrade head
```

### Step 4: Create Organizer Account
Create the initial administrator account without exposing passwords in source code:
```bash
python cli.py create-user --email organizer@bmsit.in --password "YourStrongPassword123!" --name "Lead Organizer" --role ORGANIZER
```

### Step 5: (Optional) Seed Demo Teams
```bash
python cli.py seed-demo
```

### Step 6: Start Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
- API Base: `http://localhost:8000/api/v1`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc UI: `http://localhost:8000/redoc`
- Health Probe: `http://localhost:8000/health`

---

## 4. Running Automated Tests

Run the complete test suite:
```bash
pytest -v
```

---

## 5. PostgreSQL Verification Instructions

When deploying with PostgreSQL in staging/production:

1. **Start PostgreSQL Database**:
   ```sql
   CREATE DATABASE event_hq;
   ```
2. **Update `.env`**:
   ```ini
   DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/event_hq
   ```
3. **Apply Migrations**:
   ```bash
   alembic upgrade head
   ```
4. **Run Integration & Concurrency Tests**:
   ```bash
   DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/event_hq pytest tests/test_concurrency.py -v
   ```

---

## 6. Organizer Confirmation Checklist (Scoring Engine Configuration)

All tournament scoring parameters are designed with safe defaults and are dynamically configurable by Organizers via `PUT /api/v1/rounds/{round_num}`:

1. **Round 1 Hint Penalty**: Default `120.0s` per hint. Configurable via `configJson.hintPenaltySeconds`.
2. **Round 2 Cabo Point Scale**: Default `100, 80, 65, 55, 45, 35, 25, 20, 15, 10, 5, 0` for 1st–12th. Configurable via `configJson.placementPoints`.
3. **Round 3 Starting Balance & Overdraft**: Default `100.0` points, `allowNegativeBalance: false`. Configurable via `configJson.startingBalance` and `configJson.allowNegativeBalance`.
4. **Round 4 Rubric & Agent Guess Bonus**: Default rubric categories totaling 100 pts, Agent Guess Bonus `10.0` pts. Configurable via `configJson.agentGuessBonus`.
5. **Round 5 (Finale) Carryover Weight & Agent Verdict**: Default `carryoverWeight: 0.0` (can be set to `0.20` / 20%), Agent Correct Bonus `+10.0` pts, Agent Incorrect Penalty `-5.0` pts. Configurable via `configJson.carryoverWeight`, `configJson.agentBonusPoints`, and `configJson.agentPenaltyPoints`.