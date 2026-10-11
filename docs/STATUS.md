# Implementation checkpoint

Updated: October 11, 2026.
Milestones 00-05 and a synthetic-data version of 06 are implemented. Next: **05b contract alignment and evidence staleness** (see ROADMAP).

## Implemented and verified
Verified by running: backend `pytest` (63 passing), frontend `vitest` (4), `tsc --noEmit`, `next build`, `alembic upgrade head` + `alembic check` (no drift), `python -m app.seed --demo-athlete` (idempotent), both servers started and every route returned 200, CORS preflight from `http://localhost:3000` OK.

| Area | Where | Notes |
| --- | --- | --- |
| Config / modes / auth | `backend/app/config.py`, `api/auth.py`, `main.py` | Demo: fixed identity, loopback only, SQLite only (startup refuses otherwise). Live: Supabase JWT (HS256 secret or JWKS), no demo fallback. Live tested with **mocked** tokens only |
| Athlete, equipment, performance | `api/routes.py`, `models`, `schemas` | Single `PUT /athlete-profile`; equipment replaced as a list; records CRUD |
| Competitions | `api/routes.py`, `data/fixtures.py` | 5 fictional competitions, manual entry, event edit bumps version + keeps `EventSpecRevision`; shared catalog read-only |
| Assessments | `services/assessment.py`, `services/evidence.py` | Eligibility + event labels; stale on spec-version, status, or athlete-evidence change |
| Benchmarks | `services/benchmarks.py`, `HistoricalResult` | Synthetic cohorts only; exact-match cohort; percentile at n>=20 |
| Planning | `services/planning.py`, `integrations/ai.py` | Mock planner + Claude adapter (fake-client tested only) + OpenAI-compatible adapter for Qwen/proxies (`AI_PROVIDER=openai_compatible`, mocked-transport tested only, never run against a real endpoint); hard validator; draft -> saved |
| Training logs | `api/routes.py` | Log + optional new performance records linked via `training_log_id` |
| UI | `frontend/app/*` | Dashboard, profile, competitions, detail, assessment, plan, training, settings, login |
| In-app AI key | `models.AiSetting`, `services/{secrets,ai_settings}.py`, `api/routes.py`, `frontend/components/AiSettingsCard.tsx` | Per-owner provider/model/base URL + Fernet-encrypted key; masked in every response; URL guard (https; no private/loopback in live); connection test. Click-tested in headless Chromium with a fake key; never run against a real provider |
| Tavily / Firecrawl | `integrations/search_extract.py` | Interfaces + mocks; live adapters deliberately raise "not implemented" |
| Export / delete | `GET /export`, `DELETE /my-data` | Covered by tests |

## Known gaps versus these docs (highest priority first)
1. **Plan-input staleness is not done yet (step A3).** Reports now go stale when records, equipment or eligibility fields (body weight, age, category) change (A2, fingerprint on `Assessment.evidence_hash`; reports made before migration 0003 are 'unknown', not stale). Plans are stale when their report is, but not yet when availability, avoid list or pain flags change.
2. **Contract drift** (see the table at the top of CONTRACTS): integer ids, no `/api/v1` prefix, `/equipment` + `/target`, "saved" instead of "active", plain FastAPI errors, no pagination, no revision fields on profile/equipment.
3. No `repositories` layer: routes call ORM directly (`api/routes.py` is one large file). Split by feature when it next changes.
4. Competition times are dates only (no time zone). No `PATCH /competitions/{id}`; only events are editable, and only private ones.
5. Plan "activation" is a plain save; there is no single-active-plan rule.
6. UI redesigned (sidebar/bottom-tab shell, next-step hero + journey tracker, event cards with a 3-fact evidence tracker, plan week tabs, pre-filled training log) and screenshot-checked in headless Chromium, but form interactions were not click-tested. Claude adapter never run against the real API. Supabase never tried live. No RLS policies.
7. Equipment max load is compared to event load without per-hand/total conversion.

## Decisions
- Task keys encode the implement (`log_clean_press` vs `press_barbell_strict`), so comparability is exact-key plus per-hand match; same-family records are "related" only.
- Records older than 365 days are excluded from comparison (shown with a note).
- Reps events need a timed set (>= 2 reps, within the time limit) at or above the event load to count as demonstrated; a single is "unknown" with the load ratio shown as context.
- Plan estimates: 5 min warm-up + 3 min per set; no absolute loads are prescribed.

## Next task
Milestone 05b: implement evidence-based staleness (store an evidence fingerprint on each assessment; compare on read; surface in dashboard/assessment/plan), add tests, then reconcile the contract drift above (decide per row: change code or change CONTRACTS).

## Checkpoint format for later updates
Record completed milestone, changed source paths, working behavior, exact verification commands/results, failures or blockers, schema decisions, and next task. Distinguish implemented, tested, mocked, and deferred functionality. No long logs here.
