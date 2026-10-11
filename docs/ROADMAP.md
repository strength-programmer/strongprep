# Build roadmap

One milestone per task/session is the default. Load STATUS and CONTRACTS plus only the listed specs and relevant code. Resolve necessary dependencies rather than implementing unrelated future features.

| Milestone | Read next | Deliverable and completion gate |
| --- | --- | --- |
| 00 Foundation | ARCHITECTURE, SETUP, UI | Next.js/FastAPI scaffold, persistent demo database/migrations, seed command, localhost/demo boundaries, mock provider interfaces, Windows run instructions; health endpoint and migration/seed verification |
| 01 Athlete | modules/01-athlete-profile, UI | Persist profile/equipment/performance, validate forms, edit records; data survives restart and private ownership rules pass tests |
| 02 Competitions | modules/02-competitions, UI | Seed catalog, manual draft entry, detail/division/target selection, provenance and revisions; unknown units/conflicting data stay explicit |
| 03 Assessments | modules/03-assessments | Event gaps and eligibility from snapshots; missing/incompatible data and rule changes pass tests; benchmarks may be unavailable |
| 04 Planning | modules/04-planning, relevant portions of modules/07-integrations | Constrained mock plan and Claude adapter with mocked API tests, review/activate UI; schedule/equipment checks pass without a paid call |
| 05 Training and full journey | modules/05-training-logs, UI | Session logs, linked performance, stale-output handling, persisted dashboard; exercise complete profile-to-log journey |
| 06 Benchmarks | modules/06-benchmarks | Synthetic or permitted matching results, cohort/tie/direction calculations, insufficient-data handling |
| 07 Live integrations and accounts | modules/07-integrations, SETUP | Supabase live auth/database, permitted Tavily/Firecrawl adapters, bounded/durable work as needed; fail closed with missing credentials and verify authorization |
| 08 Pilot refinement | Relevant module + research context if needed | Coach-reviewed catalog, verified events/data, athlete feedback and corrections; deployment only if separately requested |

## Progress (see STATUS for evidence)

| Milestone | State |
| --- | --- |
| 00 Foundation | Done and verified |
| 01 Athlete | Done; no evidence revisions yet |
| 02 Competitions | Done; no time zones, no PATCH on competitions |
| 03 Assessments | Done; **evidence-change staleness missing** |
| 04 Planning | Done; save instead of activate |
| 05 Training / full journey | Done; stale-after-new-evidence missing |
| **05b Alignment (next)** | Evidence staleness + fingerprint, then decide each CONTRACTS deviation, split `routes.py` by feature, browser-test the UI |
| 06 Benchmarks | Done with synthetic data only; permitted real dataset still open |
| 07 Live integrations | Not started (Claude adapter exists but is untested live) |
| 08 Pilot refinement | Not started |

## Completion for every milestone
Implement behavior, verify appropriate domain/API/UI checks, fix relevant failures, update STATUS and actual README commands, and report limitations. Do not mark the task complete because a folder or stub exists.

Initial usable demo is milestones 00–05. Implement live-service interfaces early where necessary, but live setup and source access must not block those milestones. A stubbed future integration must be described as deferred, not complete.
