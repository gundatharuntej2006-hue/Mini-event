# EVENT HQ — BMSIT 2026 Tournament Operations Platform

Production-grade tournament management and operations dashboard built for **EVENT HQ** at BMSIT 2026. This full-stack repository combines a responsive React/Vite/TypeScript frontend, a FastAPI asynchronous backend, tournament scoring engines across all 5 competition rounds, and automated Google Forms team registration integration.

---

## 1. Monorepo Architecture

```text
sihnew/
├── event-dashboard/     # React 18, Vite, TypeScript, Tailwind CSS, Lucide icons, Three.js 3D
│   ├── src/
│   │   ├── components/  # Cyberpunk UI, modals, metrics, settings, layout
│   │   ├── pages/       # Overview, Teams, Participants, Rounds 1-5, Grand Finale, Settings, Register
│   │   ├── routes/      # React Router route definitions
│   │   ├── services/    # apiClient, backendApiService, authService, eventService
│   │   └── types/       # TypeScript contracts, interfaces, and scoring models
│   └── package.json
│
├── backend/             # FastAPI, Python 3.11+, SQLAlchemy 2.0, Pydantic v2, Alembic
│   ├── app/
│   │   ├── api/routes/  # auth, dashboard, health, integrations, participants, rounds, settings, teams
│   │   ├── core/        # config, dependencies, security (bcrypt & JWT)
│   │   ├── db/          # engine, session factory, declarative base
│   │   ├── models/      # User, Team, Participant, EventSettings, RegistrationSubmission, RoundModels
│   │   ├── schemas/     # Pydantic request/response schemas & ApiResponse envelope
│   │   └── services/    # Business logic: team, participant, round, integration, dashboard
│   ├── alembic/         # Database migrations
│   └── requirements.txt
│
└── scripts/             # External integration utilities
    └── google_forms_webhook.js  # Production-ready Google Apps Script for form submissions
```

---

## 2. Key Capabilities

* **Tournament Operations & Live Dashboard**: Real-time operations overview with squad status, round progress, dynamic check-ins, and projector views.
* **Combined Team & Participant Registration**: Register a squad with all 5 members (1 Leader, 4 Members) atomically with intra-form collision checks, duplicate USN/email safeguards, and a 32-squad tournament limit.
* **Google Forms & External Webhook Integration**:
  * External teams submit Google Forms or public web registration (`/register`).
  * **Manual Review Default**: Submissions are queued with status `PENDING` in the Submissions Audit Queue for Organizer inspection and 1-click approval.
  * **Security**: Webhook endpoint protected by constant-time secret verification (`hmac.compare_digest`), timing-safe authentication, and idempotency deduplication.
* **5 Tournament Competition Rounds**:
  1. **Round 1 — Expedition**: Clue hunt tracking, hint penalties, and qualifying leaderboards.
  2. **Round 2 — Cabo**: Card elimination, placement tracking, and score penalties.
  3. **Round 3 — Black Market**: Cyber economy, transaction ledger, and code fragments trading.
  4. **Round 4 — Legal Battle**: Head-to-head debate matchmaking, secret agent deduction, and judge scoring.
  5. **Grand Finale / Championship**: Multi-criteria weighted judging matrix, agent verdicts, and tiebreak resolution.
* **Role-Based Access Control (RBAC)**: Distinct permissions for `ORGANIZER`, `MARSHAL`, `JUDGE`, and `PUBLIC_PROJECTOR` with automatic PII masking for unauthenticated viewers.

---

## 3. Quick Start

### Backend (FastAPI on Port 8001)

```bash
cd backend
python -m venv .venv
# Windows:
..\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

* API Health Check: `http://127.0.0.1:8001/api/v1/health`
* Interactive API Documentation: `http://127.0.0.1:8001/docs`

### Frontend (React/Vite on Port 5173)

```bash
cd event-dashboard
npm install
npm run dev
```

* Dashboard UI: `http://localhost:5173/`
* Public Squad Registration: `http://localhost:5173/register`

---

## 4. Google Forms Setup

1. In your Google Form / Google Sheet, navigate to **Extensions > Apps Script**.
2. Paste the script from [`scripts/google_forms_webhook.js`](scripts/google_forms_webhook.js).
3. Set `WEBHOOK_URL` to your live public HTTPS endpoint.
4. Copy your private secret from **Event Settings > Google Forms Integration** in Event HQ and paste it into `WEBHOOK_SECRET`.
5. Add an `onFormSubmit` trigger in Google Apps Script.

---

## 5. Verification & Testing

* **Backend Tests**: `pytest` (62 passing tests covering auth, RBAC, rounds scoring, webhook security, and database integrity).
* **Frontend Production Build**: `npm run build` (Clean Vite build with chunk separation).
* **End-to-End Test Suites**: Dedicated TypeScript test runners in `event-dashboard/src/` testing full-stack workflows against live backend APIs.

---

## 6. License & Organization

Developed for **EVENT HQ · BMSIT 2026**. All rights reserved.
