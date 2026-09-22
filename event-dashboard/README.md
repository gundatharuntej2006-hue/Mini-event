# EVENT HQ — BMSIT Operations & Live Control Dashboard

A multi-round college competition event management and live operations dashboard built for **BMSIT**. Orchestrates 32 teams (5 participants per team = 160 participants) through progressive elimination rounds, hidden code hunts, secret agent activities, and the grand finale.

---

## 1. Project Overview

EVENT HQ serves as the mission-control console for event organizers, marshals, and judges. 

### Event Tournament Structure
* **Field**: 32 registered teams, 5 participants each (160 participants total).
* **Round 1 — The Great Expedition**: Physical checkpoint problem solving & outdoor navigation ($32 \rightarrow 24$ teams qualify).
* **Round 2 — Cabo**: Tactical card memory and risk deduction ($24 \rightarrow 12$ teams qualify).
* **Round 3 — The Black Market**: Dynamic resource trading and token asset economy ($12 \rightarrow 8$ teams qualify).
* **Round 4 — The Legal Battle**: Moot court adversarial debating and judges rubric scoring ($8 \rightarrow$ Finalist teams).
* **Finale**: Secret agent deduction unmasking, point verification, and Top 3 podium championship awards.
* **Passive Track**: Campus-wide hidden QR code fragments and undercover secret agent assignments running throughout all rounds.

---

## 2. Technology Stack

### Current Frontend Stack (Prompt 00 Foundation)
* **Framework**: [React 18](https://react.dev/) + [Vite 5](https://vitejs.dev/)
* **Language**: [TypeScript](https://www.typescriptlang.org/) (Strict mode enabled)
* **Styling**: [Tailwind CSS v3](https://tailwindcss.com/) with custom navy palette
* **Routing**: [React Router DOM v6](https://reactrouter.com/)
* **Icons**: [Lucide React](https://lucide.dev/)

### Future Backend Stack (Later Phases)
* **API**: Python 3.14 + FastAPI
* **Database**: PostgreSQL with SQLAlchemy ORM (SQLite fallback for local dev)
* **Live Telemetry**: WebSockets live stream

---

## 3. Prerequisites

* **Node.js**: v18.0.0 or later (Tested on v22.20.0)
* **npm**: v9.0.0 or later (Tested on 10.9.3)

---

## 4. Installation & Setup

Navigate into the `event-dashboard` directory:

```bash
cd event-dashboard
```

Install all required frontend dependencies:

```bash
npm install
```

### Environment Variable Setup

Copy the template `.env.example` to `.env`:

```bash
cp .env.example .env
```

Default configuration variables in `.env`:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_EVENT_NAME="EVENT HQ · BMSIT 2026"
VITE_ENABLE_MOCK_DATA=true
```

---

## 5. Running the Application

### Development Server
Start the local Vite dev server:

```bash
npm run dev
```

Open your browser at: `http://localhost:5173`

### Production Build & Type-Check
Verify compilation and produce optimized assets:

```bash
npm run build
```

Preview the production build locally:

```bash
npm run preview
```

---

## 6. Project Folder Structure

```text
event-dashboard/
├── public/
├── src/
│   ├── assets/               # Static assets
│   ├── components/
│   │   ├── layout/           # Persistent layout wrappers
│   │   │   ├── MainLayout.tsx
│   │   │   ├── Sidebar.tsx   # Dark navy responsive sidebar (11 routes)
│   │   │   └── TopNavbar.tsx # Header with search, status, profile, alerts
│   │   ├── ui/               # Reusable atomic UI components
│   │   │   ├── Badge.tsx     # Standardized status badges
│   │   │   ├── Banner.tsx    # Demo mode indicator banner
│   │   │   ├── Button.tsx    # Accessible multi-variant buttons
│   │   │   ├── Card.tsx      # Clean rounded cards with subtle borders
│   │   │   ├── EmptyState.tsx
│   │   │   └── LoadingSkeleton.tsx # Shimmer skeleton states
│   │   └── dashboard/        # Dashboard widgets
│   │       ├── MetricCard.tsx
│   │       ├── QuickActionsPanel.tsx
│   │       ├── RecentActivityFeed.tsx
│   │       └── RoundProgressCard.tsx
│   ├── pages/                # Navigable application pages
│   │   ├── OverviewPage.tsx  # Mission control overview & KPIs
│   │   ├── TeamsPage.tsx     # 32 teams table & check-in search
│   │   ├── ParticipantsPage.tsx # 160 participants directory
│   │   ├── RoundsPage.tsx    # 5 rounds progression breakdown
│   │   ├── ScoreboardPage.tsx # Live leaderboard & cutoff tracker
│   │   ├── SecretAgentsPage.tsx # Confidential agent security console
│   │   ├── CodeFragmentsPage.tsx # QR code hunt checkpoint ledger
│   │   ├── BlackMarketPage.tsx # Round 3 trading floor preview
│   │   ├── JudgesPage.tsx    # Round 4 moot court portal preview
│   │   ├── FinalePage.tsx    # Awards podium & unmasking preview
│   │   ├── SettingsPage.tsx  # API connection & event parameters
│   │   └── NotFoundPage.tsx  # 404 fallback page
│   ├── routes/               # Centralized React Router configuration
│   │   └── index.tsx
│   ├── services/             # Service abstraction layer
│   │   ├── apiConfig.ts      # Base URL & environment configuration
│   │   ├── apiClient.ts      # HTTP fetch client with error handling
│   │   └── eventService.ts   # Centralized data service with mock switch
│   ├── types/                # Strict domain TypeScript models
│   │   ├── api.ts            # ApiResponse, PaginatedResponse, ApiError
│   │   ├── dashboard.ts      # Metric and activity log types
│   │   ├── round.ts          # RoundInfo, progression steps
│   │   ├── team.ts           # Team, Participant, statuses
│   │   └── index.ts
│   ├── data/
│   │   └── mockData.ts       # 32 teams, 160 students, 5 rounds mock data
│   ├── utils/
│   │   ├── cn.ts             # Tailwind classnames merge utility
│   │   └── formatters.ts     # Timestamps, USN formatting, ordinals
│   ├── App.tsx               # Root app router
│   ├── main.tsx              # React DOM entry
│   └── index.css             # Tailwind base & Inter typography
├── .env.example
├── .gitignore
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
└── README.md
```

---

## 7. Current Implementation Status (Prompt 00)

* [x] Complete React + Vite + TypeScript project initialized.
* [x] Tailwind CSS configured with dark navy sidebar palette (`#0A1128`) and clean neutral canvas.
* [x] Persistent responsive sidebar with 11 navigation links and mobile drawer.
* [x] Top navigation bar with BMSIT event branding, live badge, search placeholder, notification center dropdown, and operator profile.
* [x] Operations overview page with 4 KPI cards, secondary metrics, visual round progression stepper, live activity log, and quick action panel.
* [x] 10 navigable pages populated with clearly labeled demo data and mock indicators.
* [x] Centralized service layer (`eventService`, `apiClient`, `apiConfig`) configured for seamless future FastAPI integration.
* [x] Loading shimmer skeletons and error handling states implemented.
* [x] Strict confidentiality guardrails on Secret Agent information.

---

## 8. Features Intentionally Deferred to Later Prompts

Per Prompt 00 requirements, the following features are scheduled for subsequent prompts:
* **Official Event Documentation Rules Ingestion**: Precise formulas and rubrics once uploaded.
* **Backend Database & Models**: FastAPI backend, PostgreSQL schemas, and SQLAlchemy ORM models.
* **Authentication & RBAC**: JWT tokens, organizer roles, judge logins, and participant views.
* **Live Scoring Engine**: Round 1 checkpoint grading, Cabo card tabulation, Black Market automated market-maker formulas, and Judges scorecard submission.
* **Automated Bracket Progression**: Automated qualification cutoff calculation and elimination dispatch.
* **WebSockets**: Real-time push updates for live scoreboard and broadcast alerts.
