# StrongPrep (local demo build)

Strongman competition preparation assistant: **profile → competition → gap report → preparation plan → training log**.

> **Demo content is not real.** The competitions are *fictional*, historical results are *synthetic*, exercise templates are *unreviewed samples*, and in demo mode the planner is a *mock AI*, not Claude. None of it is research or coaching advice.

## Prerequisites (Windows)

- **Python 3.11+** (tested on 3.13) — `python --version`
- **Node.js 20.9+** (tested on 22) with npm — `node --version`
- No Docker, WSL, cloud account, or API key is needed for the demo.

## First-time setup (Windows CMD)

Open **two** terminals. From the `strongprep` folder:

**Terminal 1: backend**

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-lock.txt
copy .env.example .env
alembic upgrade head
python -m app.seed --demo-athlete
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`python -m app.seed` loads the fictional competitions, synthetic history and sample templates. `--demo-athlete` also adds a fictional athlete (98 kg, 180 kg deadlift single, 65 kg strict press, 4 days/week). Omit it to start with an empty profile and enter your own. The seed is idempotent.

**Terminal 2: frontend**

```bat
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Open <http://127.0.0.1:3000> (both servers listen on this machine only). API docs are at <http://127.0.0.1:8000/docs>.

Restarting: re-run only the last command in each terminal (activate the venv first). Data lives in `backend\strongprep-demo.db` and survives restarts.

## Try the journey

1. **Profile** — edit athlete, equipment (try making *Log* “occasional” and *Sandbag* “none”) and performance records.
2. **Competitions** → *Harbor Strongman Open* → pick *Novice Men -105 kg* → **Set target and generate gap report**.
3. **Gap report** — eligibility, event-by-event conclusions (observed/inferred/unavailable), benchmarks (percentile only for cohorts of ≥ 20 unique athletes), data gaps.
4. **Generate preparation plan** → review → **save**.
5. **Training** — log a session and a new performance record (e.g. a 60 s deadlift set at 160 kg), then re-run the assessment and watch the deadlift event change.
6. To see stale handling: add your own competition (manual form), generate a report and plan, edit an event load on its page, and reopen the report/plan (both flagged stale; new plans are blocked until you reassess). Seeded fixtures are read-only.

## Design rules enforced in code

- Gap labels (*demonstrated / measured gap / implement-practice gap / unknown*) come from deterministic functions in `backend/app/services/assessment.py`. A record is comparable only when the task key (implement included) and per-hand flag match; a barbell press is never treated as log ability. No overall readiness score exists.
- Missing values stay missing; units are never assumed (lb must be chosen explicitly and is converted with the original text kept).
- Plans are hard-validated (`services/planning.py`) before saving: only available-equipment templates (occasional access only in a flagged access session, ≤ 1 per week), sessions ≤ days/week and ≤ minutes, avoid-list and pain-flag exclusions, every gap explained, banned claims rejected. Invalid model output is rejected, never patched up.
- Event spec edits bump a version, keep history, and mark dependent reports/plans stale.

## Modes and configuration

Backend `.env` (see `backend/.env.example`):

| Variable | Notes |
| --- | --- |
| `APP_MODE` | `demo` (default) or `live` |
| `DATABASE_URL` | demo: SQLite only (startup refuses anything else); live: Supabase Postgres `postgresql+psycopg://…` |
| `AI_PROVIDER` | `mock` (default) or `claude` |
| `ANTHROPIC_API_KEY`, `CLAUDE_MODEL` | required for `claude`; set a current model id from the Claude API docs. Missing → the app reports “unavailable” (HTTP 503) and never fabricates Claude output |
| `TAVILY_API_KEY`, `FIRECRAWL_API_KEY` | reserved; live adapters are not implemented yet (mock only) |
| `SUPABASE_URL`, `SUPABASE_JWT_SECRET` | live mode. With no secret, tokens are verified against the project's JWKS endpoint |
| `CORS_ALLOWED_ORIGINS` | defaults to `http://localhost:3000,http://127.0.0.1:3000` |

Frontend `.env.local`: `NEXT_PUBLIC_API_BASE_URL` (default `http://127.0.0.1:8000`), and for live mode `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`.

**Demo mode** uses one fixed identity, accepts loopback clients only (non-local requests get 403), and refuses to start against a non-SQLite database. **Live mode** requires a valid Supabase-issued bearer token on every private route; there is no fallback to the demo identity. The owner always comes from the verified token `sub`, never from the request body, and every private query filters by it.

### Adding an AI key in the app

Open **Settings → AI assistant**, choose Claude or a Qwen/OpenAI-compatible endpoint, enter the model name (and base URL for Qwen), paste the key, **Save**, then **Test connection**. The backend stores the key encrypted (Fernet) per account and never sends it back to the browser (only "…last4" is shown); it is sent only to the provider you chose. Demo mode creates `backend\.strongprep-secret` automatically (gitignored; deleting it makes saved keys unreadable, so just re-enter them). Live mode requires `APP_SECRET_KEY` in the backend environment and enforces https plus a block on private/loopback base URLs. App-saved settings override the `.env` AI settings; "Remove saved key" reverts to them. After pulling this change run `alembic upgrade head` once (adds the `ai_settings` table).

### Live-mode checklist (not required for the demo)

1. Create a Supabase project; use its Postgres connection string as `DATABASE_URL` (run `pip install "psycopg[binary]"` — already in the lock file) and run `alembic upgrade head`, then `python -m app.seed`.
2. Set `APP_MODE=live`, `SUPABASE_URL`, optionally `SUPABASE_JWT_SECRET`; set the two `NEXT_PUBLIC_SUPABASE_*` values in the frontend.
3. The API server reaches Postgres directly with the server's credentials, so ownership is enforced in the API. If you ever expose tables through Supabase's own API, add row-level-security policies first (none are included).
4. For Claude: set `AI_PROVIDER=claude`, `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`.

## Tests

```bat
cd backend && .venv\Scripts\activate && pytest
cd frontend && npm test && npm run typecheck && npm run build
```

Backend tests cover: gap rules (including the spec §15 example), eligibility boundaries, percentile ties/direction/suppression/de-duplication/cohort mismatch, the full journey with persistence across an app restart, plan constraints, stale handling, input validation, Claude-adapter behavior with a fake client, and live-mode auth (missing/invalid/expired/wrong-audience/wrong-issuer tokens, cross-account isolation) using mocked HS256 credentials.

## Layout

```
backend/app/{api,schemas,models,services,integrations,data}   migrations/   tests/
frontend/app (routes)  components/  lib/
```

## Known limitations

- The UI was rendered and screenshotted in headless Chromium (desktop, mobile, light/dark; no console errors) after the redesign, but forms were not click-tested end to end; expect small polish issues.
- The Claude adapter is tested only against a fake client; it has not been run against the live API. Tavily/Firecrawl are interfaces plus mocks only; competition input is manual.
- Live Supabase auth/Postgres was **not** tested against a real project (only mocked tokens on SQLite). Migrations were generated against SQLite.
- Exercise templates are unreviewed demo content; the gap-label rules and the 20-athlete threshold await coach review.
- Equipment `max load` is compared to event loads directly (no per-hand/total conversion). Distances are straight-line estimates from an approximate (about 1 km rounded) location, never driving time; competitions without coordinates are hidden by the radius filter and counted.
- Plans are synchronous (no job queue), one plan per click; no LangGraph.
