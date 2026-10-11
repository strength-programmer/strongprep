# StrongPrep: project instructions

Equipment-aware strongman competition preparation app.
Journey: athlete profile -> competition/division -> event gaps -> plan -> training log.
The local demo (milestones 00-05, plus synthetic benchmarks) is built. Current state, gaps and next task: `docs/STATUS.md`.
Launch Claude Code from this folder (`strongprep/`) so this file is in scope.

## Stack
- Frontend: Next.js 16 / React 19 / TypeScript in `frontend/` (client-rendered pages, plain CSS).
- Backend: Python 3.11+ / FastAPI / Pydantic / SQLAlchemy / Alembic in `backend/app/{api,schemas,models,services,integrations,data}`.
- SQLite for the demo; Supabase PostgreSQL/Auth for live mode (untested against a real project).
- One backend with feature modules, not services per feature. Claude Code builds the app; the Claude API is the app's runtime AI (`AI_PROVIDER=claude`), mock by default.

## Commands (Windows; backend venv at `backend\.venv`)
- Backend tests: `cd backend && .venv\Scripts\python -m pytest -q`
- Migrate / seed: `alembic upgrade head`, `python -m app.seed --demo-athlete` (run in `backend`)
- Run: `uvicorn app.main:app --host 127.0.0.1 --port 8000` and, in `frontend`, `npm run dev`
- Frontend checks: `npm test`, `npm run typecheck`, `npm run build`
- Never claim a command passed unless you ran it. After a schema change add an Alembic revision and run `alembic check`.

## Rules that apply to every module
- Derive private-record ownership from verified identity, never from payloads. Demo = fixed identity, loopback only, SQLite only. Live auth failures never fall back to demo.
- Calculate eligibility, gaps, unit conversions and benchmarks in ordinary code (`services/assessment.py`, `services/benchmarks.py`), never in a model.
- Keep missing/ambiguous data explicit. Never infer log/yoke/stone performance from barbell lifts; never produce an overall readiness percentage. A task key already encodes the implement, so tasks are never silently equivalent.
- Percentiles need an exactly matched cohort of at least 20 unique athletes; never broaden a cohort to get a number.
- Model output is untrusted: `services/planning.validate_plan` must pass before a plan is saved. Mock/synthetic/unreviewed content stays labeled everywhere it is shown.
- Claude API code: take the model id from `CLAUDE_MODEL` (never hard-code); do not use forced `tool_choice` or `thinking: disabled` on current models; check the `claude-api` skill before changing the adapter.
- Keep keys outside git and server-side only. No deployment, billing, live scraping or competition registration until the user asks.
- Version events, assessments and plans; mark affected outputs stale.

## Load only what the task needs
- Start with `docs/STATUS.md` and `docs/CONTRACTS.md`, then the one module spec in `docs/modules/` named by the task. Module specs: `01-athlete-profile`, `02-competitions`, `03-assessments`, `04-planning`, `05-training-logs`, `06-benchmarks`, `07-integrations`.
- Read `docs/ARCHITECTURE.md` for boundary changes, `docs/SETUP.md` for dependencies/config.
- Do not bulk-read docs. The full product spec is `../strongprep-project-documentation (1).md`: read it only for product/research context, not for startup.
- Read source files that a real dependency requires; saving context must not hide evidence.

## Workflow
- One milestone/task at a time (`docs/ROADMAP.md`). Inspect existing code first; preserve working behavior.
- Verify (tests, typecheck, build) and fix failures in scope. Avoid unrelated features.
- Before ending, update `docs/STATUS.md`: changed paths, verified commands and results, blockers, next task. Update `docs/CONTRACTS.md` and dependent code when a shared API/schema changes.
- Keep `README.md` commands real. Demo must not need Linux, WSL, Docker or paid APIs.
