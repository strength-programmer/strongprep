# Architecture and module boundaries

Use a modular monolith: one FastAPI backend with separate feature packages and one Next.js frontend. Modules are units of responsibility; they do not need independent servers or autonomous agents.

| Feature | Owns | Depends on |
| --- | --- | --- |
| Athlete | Profile, equipment access, performance evidence | Persistence, identity |
| Competitions | Listings, divisions, event rules, source evidence | Persistence |
| Assessments | Eligibility, event gaps, evidence explanations | Athlete and competition snapshots |
| Planning | Constrained versioned plans | Assessments, exercise/template catalog, AI adapter |
| Training | Completed sessions and new performance evidence | Athlete records, plans |
| Benchmarks | Matched cohorts and descriptive percentiles | Event rules, permitted historical results |
| Integrations | Provider requests and validated proposals | Typed contracts and source policies |

Routes validate inputs and call services. Services contain domain logic and use repositories. Provider adapters perform external I/O and return typed data; they do not decide ownership or write approved competition facts automatically. Avoid making backend routes call one another through HTTP.

## Code organization

Within backend/app, separate api, schemas, models, services, repositories, integrations, and data. Each layer may have feature-named files/packages such as athlete, competitions, assessments, planning, training, and benchmarks. The frontend may organize feature components similarly. Keep shared primitives small; avoid one enormous utils file.

Frontend -> FastAPI -> domain service -> repository/provider adapter.
(Current build: the assessment, benchmark and planning logic follows this; there is no repositories layer yet and `api/routes.py` holds all routes and some orchestration. Split it by feature when next touched.)
All sensitive provider calls and private-record authorization are backend responsibilities. Cross-feature APIs and records are documented in CONTRACTS.

## Runtime modes

Demo: localhost only, fixed isolated identity, persistent SQLite, deterministic mock AI/search/extraction, clearly labeled fictional data.
Live: Supabase PostgreSQL/Auth, verified identity and ownership, explicit integration configuration. Missing live credentials give unavailable errors; never change identity or return disguised demo content.

Use SQLAlchemy-compatible field types and migrations across SQLite/PostgreSQL. Save UTC timestamps and competition time-zone information; display venue-local dates. Reset/seed operations target the demo database explicitly and must not erase user data by default.

## Workflow and versions

Initial workflow is ordinary Python functions plus structured model calls. Long imports/research later need durable workers and persisted job status. LangGraph remains optional. Keep scheduling separate from domain calculations.

An assessment snapshots athlete evidence and event versions. A plan refers to an assessment and catalog/provider versions. Updated rules or evidence mark affected outputs stale; old versions remain readable. Generation previews require review before becoming an active plan.

The project is a locally runnable app first. Deployment and external integration activation are later milestones.
