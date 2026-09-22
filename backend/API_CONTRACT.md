# EVENT HQ — Backend Part 1 API Contract & Integration Specification

## 1. Architectural Overview
- **Base URL**: `http://localhost:8000/api/v1`
- **Swagger Interactive Docs**: `http://localhost:8000/docs`
- **ReDoc Interactive Docs**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`
- **Root Health Check**: `http://localhost:8000/health`

---

## 2. Universal API Envelope Format
All successful responses are returned within a standard JSON envelope matching the frontend `ApiResponse<T>`:

```json
{
  "success": true,
  "data": {},
  "message": "Human readable status description",
  "isMockData": false,
  "timestamp": "2026-09-19T18:15:30.000000Z"
}
```

Error responses follow a structured format:
```json
{
  "success": false,
  "data": null,
  "message": "Specific error description",
  "isMockData": false
}
```

---

## 3. Role-Based Access Control (RBAC) & Privacy Matrix

Authentication uses standard **JWT Bearer** tokens in the `Authorization: Bearer <token>` header.

| Role | Permissions & Data Privacy Level |
| :--- | :--- |
| **`ORGANIZER`** | Full administrative rights: manage global settings, delete teams/participants, register official accounts. Full PII access. |
| **`MARSHAL`** | Operations rights: register teams & participants, toggle check-ins, execute squad transfers. Full PII access. |
| **`JUDGE`** | Evaluation rights (Part 2 scoring). Read-only roster access. Full PII access. |
| **`PUBLIC_PROJECTOR` / Anonymous** | Public displays only: leaderboard, table assignments, and roster overview. **PII Masked**: `email`, `phone`, and `usn` are stripped (`null`). |

---

## 4. Endpoints Specification

### A. Health Check
- **`GET /health`** & **`GET /api/v1/health`**
  - **Auth**: None (Public)
  - **Response**:
    ```json
    {
      "success": true,
      "data": {
        "status": "online",
        "database": "healthy",
        "version": "1.0.0"
      },
      "message": "EVENT HQ API service is running"
    }
    ```

---

### B. Authentication
- **`POST /api/v1/auth/login`**
  - **Body**: `{"email": "organizer@bmsit.in", "password": "YourSecurePassword"}`
  - **Response**:
    ```json
    {
      "success": true,
      "data": {
        "accessToken": "eyJhbGciOi...",
        "tokenType": "bearer",
        "user": {
          "id": "usr-8a21fbc40912",
          "email": "organizer@bmsit.in",
          "name": "Lead Organizer",
          "role": "ORGANIZER",
          "isActive": true,
          "createdAt": "2026-09-19T18:00:00.000Z"
        }
      },
      "message": "Authentication successful"
    }
    ```

- **`GET /api/v1/auth/me`**
  - **Auth**: Bearer Token
  - **Response**: Current `UserResponse`

- **`POST /api/v1/auth/register`**
  - **Auth**: Required role `ORGANIZER`
  - **Body**: `{"email": "...", "name": "...", "password": "...", "role": "MARSHAL"}`

---

### C. Teams Management
- **`GET /api/v1/teams`**
  - **Auth**: Public / Staff
  - **Privacy**: If unauthenticated or `PUBLIC_PROJECTOR`, member PII (`email`, `phone`, `usn`) is stripped to `null`.
  - **Response**: Array of `TeamResponse` objects with embedded `members` list.

- **`GET /api/v1/teams/{team_id}`**
  - **Auth**: Public / Staff (PII stripped for non-staff)
  - **Response**: Detailed `TeamResponse`

- **`POST /api/v1/teams`**
  - **Auth**: `ORGANIZER`, `MARSHAL`
  - **Body**: `{"name": "Vanguard Unit 01", "assignedTable": "Table 1"}`
  - **Status Code**: `201 Created`

- **`PUT /api/v1/teams/{team_id}`**
  - **Auth**: `ORGANIZER`, `MARSHAL`
  - **Body**: `{"name": "New Name", "assignedTable": "Table 4", "status": "Checked In"}`

- **`DELETE /api/v1/teams/{team_id}`**
  - **Auth**: `ORGANIZER`
  - **Action**: Safely unassigns all member participants (`team_id = null`, `role = Member`) and deletes the team record.

---

### D. Participants Management
- **`GET /api/v1/participants`**
  - **Auth**: Required role `ORGANIZER`, `MARSHAL`, `JUDGE`
  - **Query Params**:
    - `teamId` (string, optional)
    - `checkedIn` (boolean, optional)
    - `search` (string, optional — searches name, USN, or email)
  - **Response**: Array of `ParticipantResponse`

- **`GET /api/v1/participants/{participant_id}`**
  - **Auth**: Required role `ORGANIZER`, `MARSHAL`, `JUDGE`
  - **Response**: `ParticipantResponse`

- **`POST /api/v1/participants`**
  - **Auth**: `ORGANIZER`, `MARSHAL`
  - **Validation Rules**:
    1. **USN Normalization & Uniqueness**: USN is trimmed and uppercased (e.g. `1BY22CS001`). Must be unique across tournament.
    2. **5-Person Squad Limit**: If `teamId` is provided, target team must have < 5 existing members. Throws `400 Bad Request` if full.
  - **Body**:
    ```json
    {
      "name": "Jane Doe",
      "email": "jane@bmsit.in",
      "usn": "1BY22CS099",
      "phone": "+91 98765 43210",
      "role": "Leader",
      "teamId": "team-01",
      "checkedIn": true
    }
    ```

- **`PATCH /api/v1/participants/{participant_id}/check-in`**
  - **Auth**: `ORGANIZER`, `MARSHAL`
  - **Body**: `{"checkedIn": true}`
  - **Behavior**: Sets `checked_in_at` to current UTC timestamp on check-in; clears timestamp on undo.

- **`POST /api/v1/participants/{participant_id}/transfer`**
  - **Auth**: `ORGANIZER`, `MARSHAL`
  - **Body**: `{"targetTeamId": "team-02"}` (or `null` to move to unassigned pool)
  - **Validation**: Enforces 5-member limit on target squad.

- **`DELETE /api/v1/participants/{participant_id}`**
  - **Auth**: `ORGANIZER`

---

### E. Overview Dashboard & Metrics
- **`GET /api/v1/dashboard/overview`**
  - **Auth**: Public / Projector / Staff
  - **Response**:
    ```json
    {
      "success": true,
      "data": {
        "stats": {
          "totalTeams": 32,
          "totalParticipants": 160,
          "currentRoundName": "Round 1: Clue Hunt",
          "currentRoundNumber": 1,
          "currentRoundStatus": "In Progress",
          "qualifiedTeamsTarget": 24,
          "activeTeamsRemaining": 32,
          "eventProgressPercentage": 20,
          "checkedInTeams": 28,
          "checkedInParticipants": 152,
          "completeRosterTeams": 30,
          "incompleteRosterTeams": 2,
          "agentsAssigned": 0,
          "fragmentsDiscovered": 0,
          "totalFragments": 0
        },
        "recentActivities": []
      },
      "message": "Dashboard overview metrics computed"
    }
    ```

---

### F. Event Settings
- **`GET /api/v1/settings`**
  - **Auth**: Public / Projector / Staff
  - **Response**: `SettingsResponse`
- **`PATCH /api/v1/settings`**
  - **Auth**: `ORGANIZER`
  - **Body**: `{"eventName": "EVENT HQ · BMSIT 2026 FINALS", "tableCount": 36}`

---

## 5. Tournament Rounds & Scoring APIs (Part 2)

### A. Generic Round State & Progression
- **`GET /api/v1/rounds`**
  - **Auth**: Public / Staff
  - **Response**: Array of all 5 `RoundSummary` objects.
- **`GET /api/v1/rounds/{round_num}`**
  - **Auth**: Public / Staff
  - **Response**: Detailed `RoundSummary` for round `round_num` (1 to 5).
- **`PUT /api/v1/rounds/{round_num}`**
  - **Auth**: `ORGANIZER`
  - **Body**: `{"status": "In Progress", "location": "Auditorium Annex", "configJson": {...}}`
- **`POST /api/v1/rounds/{round_num}/finalize`**
  - **Auth**: `ORGANIZER`
  - **Gating**: Requires Round $N-1$ to be finalized before Round $N$ can finalize.
  - **Idempotency**: Safely callable repeatedly without duplicating or corrupting state.
  - **Discrepancy Override & Audit**: When qualifying count deviates from target, requires `overrideDiscrepancy: true`. Stored with organizer ref, timestamp, and audit notes.
  - **Body**: `{"finalizedBy": "Lead Organizer", "overrideDiscrepancy": false, "notes": "Optional audit note"}`
  - **Response**: `FinalizeRoundResponse` with `qualifiedTeamIds`, `totalEligible`, and `success`.
- **`IMMUTABILITY LOCK`**:
  - Once a round is finalized (`isFinalized: true`), all mutations on that round (`PUT /records`, `POST /placements`, `POST /transactions`, `POST /transfer`, `PUT /codes/fragment`, `PUT /pairs`, `POST /scores`, `POST /agent-guess`, `POST /scorecards`, `POST /agent-verdict`) immediately return `400 Bad Request` ("Round is finalized and sealed. Modifications are not allowed.").

---

### B. Round 1: Clue Hunt / Expedition
- **`GET /api/v1/rounds/1/records`**
  - **Auth**: Public / Staff
  - **Response**: List of `Round1RecordResponse` with raw total, hint penalties (120s/hint default), adjusted totals, and Top 24 qualification ranks.
- **`PUT /api/v1/rounds/1/records/{team_id}`**
  - **Auth**: `ORGANIZER`, `MARSHAL`
  - **Body**: `{"miniRounds": [...], "hiddenCodeRecovered": true, "hiddenCodeNotes": "Found in Archives"}`
- **`POST /api/v1/rounds/1/records/batch`**
  - **Auth**: `ORGANIZER`, `MARSHAL`
  - **Body**: `{"records": [{"teamId": "...", "miniRounds": [...]}, ...]}`

---

### C. Round 2: Cabo Tournament
- **`GET /api/v1/rounds/2/placements`**
  - **Query**: `gameNumber` (optional, 1..3)
- **`POST /api/v1/rounds/2/placements`**
  - **Auth**: `ORGANIZER`, `MARSHAL`
  - **Body**: `{"gameNumber": 1, "teamId": "...", "placement": 1, "points": 100}`
- **`POST /api/v1/rounds/2/game/submit`**
  - **Auth**: `ORGANIZER`, `MARSHAL`
  - **Body**: `{"gameNumber": 1, "placements": [{"teamId": "...", "placement": 1, "points": 100}]}`
- **`GET /api/v1/rounds/2/standings`**
  - **Auth**: Public / Staff
  - **Response**: Aggregated points table across 3 games, Top 12 qualified.

---

### D. Round 3: The Black Market Economy
- **`GET /api/v1/rounds/3/transactions`**
  - **Query**: `teamId` (optional)
- **`POST /api/v1/rounds/3/transactions`**
  - **Auth**: `ORGANIZER`, `MARSHAL`
  - **Body**: `{"teamId": "...", "amount": 50.0, "type": "earn", "reason": "Station Bounty"}`
- **`POST /api/v1/rounds/3/transactions/{tx_id}/reverse`**
  - **Auth**: `ORGANIZER`
  - **Action**: Generates compensating reversal ledger transaction and marks original reversed.
- **`POST /api/v1/rounds/3/transfer`**
  - **Auth**: `ORGANIZER`, `MARSHAL`
  - **Body**: `{"fromTeamId": "...", "toTeamId": "...", "amount": 30.0, "reason": "Clue Trade"}`
- **`GET /api/v1/rounds/3/codes`** & **`PUT /api/v1/rounds/3/codes/fragment`**
  - **Auth**: `ORGANIZER`, `MARSHAL`
  - **Body**: `{"teamId": "...", "fragmentIndex": 0, "code": "SIGMA-9", "isDiscovered": true}`
- **`GET /api/v1/rounds/3/standings`**
  - **Response**: Sorted by balance & fragments discovered, Top 8 qualified.

---

### E. Round 4: The Legal Battle
- **`GET /api/v1/rounds/4/pairs`**
  - **Response**: 4 Matchup pairs with case assignments, case file flags, and resource person Q&A logs.
- **`PUT /api/v1/rounds/4/pairs/{pair_number}`**
  - **Auth**: `ORGANIZER`, `MARSHAL`
  - **Body**: `{"caseId": "...", "teamAHasCaseFile": true, "resourcePersonQuestions": [...]}`
- **`POST /api/v1/rounds/4/pairs/auto`**
  - **Auth**: `ORGANIZER`
  - **Action**: Auto-pairs top 8 qualified teams into 4 fictional legal cases.
- **`POST /api/v1/rounds/4/scores`**
  - **Auth**: `ORGANIZER`, `MARSHAL`, `JUDGE`
  - **Body**: `{"judgeId": "...", "judgeName": "...", "teamId": "...", "scores": {"arguments": 28, "crossExam": 24}}`
- **`POST /api/v1/rounds/4/agent-guess`**
  - **Auth**: `ORGANIZER`, `MARSHAL`, `JUDGE`
  - **Body**: `{"teamId": "...", "outcome": "correct", "pointsAwarded": 10.0}`
- **`GET /api/v1/rounds/4/standings`**
  - **Response**: Jury score average + Agent Guess points, Top 3 qualified for Grand Finale.

---

### F. Grand Finale (Round 5)
- **`GET /api/v1/rounds/5/scorecards`**
- **`POST /api/v1/rounds/5/scorecards`**
  - **Auth**: `ORGANIZER`, `MARSHAL`, `JUDGE`
  - **Body**: `{"teamId": "...", "judgeName": "Grand Jury", "scores": {"opening": 20, "debate": 39, "rebuttal": 25, "poise": 15}}`
- **`POST /api/v1/rounds/5/agent-verdict`**
  - **Auth**: `ORGANIZER`, `MARSHAL`, `JUDGE`
  - **Body**: `{"teamId": "...", "suspectedAgent": "Agent Cobalt", "actualAgent": "Agent Cobalt", "isCorrect": true, "bonusPoints": 10.0}`
- **`GET /api/v1/rounds/5/standings`**
  - **Response**: Final tournament podium (Champion, 1st Runner Up, 2nd Runner Up) with carryover weighting and agent verdicts.