# EVENT HQ — Going Live

Written for whoever deploys and runs the platform on event day.

Two pieces ship separately:

| Piece | What it is | Where it goes |
|---|---|---|
| `backend/` | FastAPI + PostgreSQL | A web service (always-on process) |
| `event-dashboard/` | Vite + React, builds to static files | A static site / CDN |

---

## 1. Platform

**Recommended: Render.** Backend as a Web Service, database as Render
PostgreSQL, dashboard as a Static Site. All three in one dashboard, and we
already run other things there.

**One thing that will bite you on the free tier:** free web services sleep
after a period of inactivity and take roughly a minute to wake. On event day
that is a marshal staring at a spinner while a squad waits at a gate. Either
upgrade the backend instance for the month of the event, or keep it warm by
pinging `GET /api/v1/health` every 10 minutes from an uptime monitor. Free
managed Postgres instances also expire after a fixed window — check the current
limit when you create it, and if the event is further out than that window,
create the database close to the event or take the paid tier.

The dashboard is static files, so it can sit on the free tier without any of
this. Cloudflare Pages or Netlify work just as well for it.

**Alternative worth knowing about:** for a single-day campus event, running the
backend on a laptop behind a Cloudflare Tunnel costs nothing, never cold-starts,
and keeps traffic on campus. The trade is that the laptop becomes a single point
of failure. Use it as a fallback plan, not the primary.

---

## 2. Backend environment variables

Set these on the web service. Never commit them.

| Variable | Value | Notes |
|---|---|---|
| `ENVIRONMENT` | `production` | |
| `SECRET_KEY` | *(48+ random chars)* | **The app refuses to start without it.** Minimum 32 characters, no fallback. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | `postgresql+psycopg://...` | **See the gotcha below.** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | 8 hours — one event day, so nobody is logged out mid-round |
| `CORS_ORIGINS` | `https://<your-dashboard-url>` | Comma-separated. The dashboard cannot talk to the API unless its exact origin is listed |
| `EVENT_NAME` | `ODDyssey · BMSIT 2026` | |
| `DEFAULT_TABLE_COUNT` | `32` | |
| `INITIAL_ORGANIZER_EMAIL` | *(your email)* | Seeds the first organiser account on `init-db` |
| `INITIAL_ORGANIZER_PASSWORD` | *(strong password)* | Change it after first login |
| `INITIAL_ORGANIZER_NAME` | `Lead Organizer` | |
| `GOOGLE_FORMS_WEBHOOK_SECRET` | *(random)* | Only if you use the Google Forms registration intake |

### The DATABASE_URL gotcha

Hosts hand you a URL starting `postgres://` or `postgresql://`. This app uses
psycopg 3, which needs the driver named explicitly:

```
postgresql+psycopg://user:password@host:5432/dbname
```

Copy the host's URL and change the scheme to `postgresql+psycopg://`. Leaving
it as `postgres://` fails at startup with a driver error, and the message does
not make the cause obvious.

---

## 3. Backend build and start

```
Build command:  pip install -r requirements.txt
Pre-deploy:     alembic upgrade head
Start command:  uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Root directory: `backend`

Run `alembic upgrade head` as a pre-deploy/release step, not inside the start
command — otherwise every restart re-runs it and two instances starting at once
can race.

The app also calls `Base.metadata.create_all` at startup, which creates the
handful of tables Alembic does not own. Running the migrations first and letting
startup fill in the rest is the supported order, and it has been verified
against both a fresh database and one that already has the tables.

---

## 4. Dashboard build

```
Build command:   npm ci && npm run build
Publish dir:     dist
Root directory:  event-dashboard
```

Environment variables:

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://<your-backend-url>` — no trailing slash, no `/api/v1` |
| `VITE_ENABLE_MOCK_DATA` | `false` |
| `VITE_EVENT_NAME` | `ODDyssey · BMSIT 2026` |

**These are read at build time, not run time.** Vite bakes them into the
bundle. Changing one in the host's dashboard does nothing until you trigger a
rebuild. If the dashboard shows invented teams and scores after deploying,
`VITE_ENABLE_MOCK_DATA` was not `false` when it was built.

**Add an SPA rewrite:** `/*` → `/index.html` (rewrite, not redirect). Without
it, every route except the home page 404s on refresh, which people will do.

---

## 5. Accounts to create

After the first deploy, from a shell on the backend:

```bash
python cli.py init-db                       # tables + the seed organiser
python cli.py create-user --email marshal1@bmsit.in --name "Gate 1 Marshal"  --role MARSHAL
python cli.py create-user --email judge1@bmsit.in   --name "Courtroom 1 Judge" --role JUDGE
python cli.py create-user --email screen@bmsit.in   --name "Hall Projector"    --role PUBLIC_PROJECTOR
```

Omit `--password` and it prompts without echoing.

The four roles and what each can reach:

| Role | Can do |
|---|---|
| `ORGANIZER` | Everything, including finalising rounds and the Black Market |
| `MARSHAL` | Enter timings, hints, rule violations, Cabo scorecards |
| `JUDGE` | Submit Round 4 scorecards |
| `PUBLIC_PROJECTOR` | Read-only scoreboard for the hall screen |

How many to make, from the event structure:

- **3 marshals minimum** — one per Round 1 gate. They log timings and the rule
  violations (phone use, separation, clue damage).
- **1 marshal at the Black Market desk.** Purchases need two organiser
  signatures, so this person plus an organiser.
- **4 judges** — one per courtroom pairing.
- **1 projector account** for the hall screen.

---

## 6. Data to load before the event

| What | How much | Where |
|---|---|---|
| Teams | 32, five members each (160 people) | Participants screen, or the Google Forms intake |
| Round 1 checkpoints | 3 real campus locations | Round 1 → Parameters. Defaults are placeholders — replace them |
| Hint penalty | 300 seconds | Already correct; the screen lets you confirm it |
| Cabo seating | 24 tables × 3 games | Generated by the platform — teammates are never seated together |
| Round 4 cases | 4 | The case files live in the event plan, not the platform |
| Secret agents | 1 per team, 2 tasks each | Secret Agents screen. A third task is refused unless you tick the override |

Rehearse with `python scripts/rehearsal.py` against a **scratch** database. It
drives 32 teams and 160 players through every round and prints a pass/fail line
per rule. Never point it at the live database — it writes.

---

## 7. Event-day checklist

- [ ] `GET /api/v1/health` returns healthy, and says the database is healthy too
- [ ] Log in as the organiser and change the seeded password
- [ ] Dashboard shows the real 32 teams, not demo data (if it shows demo data, rebuild with `VITE_ENABLE_MOCK_DATA=false`)
- [ ] Round 1 checkpoint names are the real locations
- [ ] Every marshal, judge and the projector can log in **on their own device**
- [ ] The projector screen loads on the hall display
- [ ] Backend is either on a paid instance or being pinged, so it cannot fall asleep
- [ ] Take a database backup before Round 1 starts, and again after each round is finalised

---

## 8. Things that will look like bugs and are not

**A purchase is refused with "requires two organiser signatures."** That is the
rule. Fill in the second organiser's name. It must be a different person from
the one recording it.

**An item shows "Sold out."** Stock is market-wide, not per squad: 4 extra prep
times, 8 extra witness questions, 5 agent clue cards, 4 case-theme hints. Code
fragments never sell out.

**Round 2 will not finalise: "Cutoff Tie."** Two squads are level on all three
scored metrics across the 12th-place cutoff. Play the sudden-death game or hold
the draw, then record it under Record Tie-Break Result. Both squads need a
position — recording one side does not separate them.

**A squad's Round 1 time jumped by ten minutes.** Someone logged a phone-use
violation. Round 1 ranks on gate time + hint penalties + rule penalties.

**A squad's balance dropped by 20 with no purchase.** Clue damage. It is scored
in points, not time.

**A team with all four fragments still fails the Round 4 gate.** The gate checks
a *verified* code, not four stored fragments. Verify it on the Code Fragments
screen.

---

## 9. Finalising a round is one-way — read this before event day

**There is no unfinalize.** Once a round is finalised it refuses every edit,
and the platform has no route to reopen it. That is deliberate: it stops a late
edit silently changing who qualified. It also means a mistake finalised is a
mistake you live with, unless you restore the database.

So, in order:

1. **Back up the database immediately before finalising each round**, not after.
   A backup taken after the mistake is sealed does not help you.
2. Check the standings screen before you press finalise. The platform already
   blocks finalisation on unresolved ties and incomplete results, but it cannot
   know that a marshal typed 10:35 instead of 10:53.
3. If you do finalise something wrong, the fix is a database restore to the
   pre-finalise backup, then re-enter the corrections. Budget ten minutes for
   this and decide who is allowed to make that call before the day starts.

Everything else — timings, hints, rule violations, purchases, scorecards —
stays editable while its round is open, and every change carries the actor in
the audit log.
