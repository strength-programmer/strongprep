# Shared contracts: initial build

These are implementation requirements, not already deployed APIs. Extend fields when the named module requires them and record breaking changes here. Generate frontend types from backend OpenAPI where practical.

## Implementation status versus this contract (demo build)

This document is the target. The demo build deviates as below; each row needs a decision (change code, or change the contract) in milestone 05b. Do not assume the contract is already true.

| Contract says | Demo build does |
| --- | --- |
| `/api/v1` prefix | No prefix (`/athlete-profile`, `/competitions`, ...) |
| String UUID ids | Integer ids |
| `/equipment-access` with POST/PATCH/DELETE per record | `GET/PUT /equipment` replaces the whole list |
| `GET/PUT /target-competition` | `PUT /athlete-profile/target` |
| `PATCH /competitions/{id}` | `PUT /events/{id}` (private competitions only) |
| `POST /preparation-plans/{id}/activate`, draft/active | `POST .../save`, draft/saved, no single-active rule |
| Structured errors `{code, message, field errors}` | FastAPI `detail`: string, `{message, errors[]}` or pydantic list |
| Pagination on unbounded lists | None |
| Revision integers on profile/equipment/performance | No revision integers; instead each report stores an evidence fingerprint and goes stale when records, equipment or eligibility fields change and plans additionally go stale when availability, avoid list, pain flags or equipment access change (`PreparationPlan.inputs_hash`) |
| Competition local date + time zone | Done (B1): venue-local `start_time` + IANA `timezone`; `start_at_utc` derived on read; a bare time without a zone is rejected |
| UTC timestamps | `created_at` is UTC; `updated_at` and dates are naive |
| `/jobs` endpoints later | Not present; generation is synchronous |

Extra endpoints in the build: `GET/PUT/DELETE /ai-settings`, `POST /ai-settings/test` (API keys are write-only: never returned), `GET /status`, `GET /reference`, `GET /dashboard`, `GET /export`, `DELETE /my-data`, `GET /assessments` (list), `GET /preparation-plans` (list).

## Common conventions

- String UUID identifiers and UTC creation/update timestamps.
- Explicit integer revision on mutable profile/event records; immutable snapshot references on assessments/plans.
- Private records have server-assigned owner_id. Never use a payload owner_id as access control.
- Normalize known weights to kg, distances/heights to metres, and times to seconds. Preserve original values and units.
- Missing is null/unknown, not zero. Zero may be a valid measured result. Validate finite, physically meaningful numbers and nonnegative counts; do not divide by zero.
- Preserve per-hand versus total loads, repetitions versus maximum loads, completed versus incomplete timed attempts, and full rule/implement context.
- Return structured errors with code, message, and optional field errors. Distinguish validation, missing record, forbidden access, insufficient evidence, and unavailable integration.
- Use demo/synthetic flags and source/review status independently; never turn a mock response into a verified fact.

## Record shapes

| Record | Minimum fields |
| --- | --- |
| AthleteProfile | id, owner_id, revision, body_weight_kg, division/age context, experience, approximate location, travel radius, days/session availability, exercise restrictions |
| EquipmentAccess | id, profile_id, implement, available load with per-hand/total meaning, space, frequency, limits |
| PerformanceRecord | id, profile_id, event/exercise, implement/configuration, load/reps/distance/time, task format/rules, performed_at, effort, verification type, source |
| Competition | id, title, organizer/federation, venue/location, local date/time zone, entry/deadline details, status, source, checked/confirmed times, is_demo |
| CompetitionDivision | id, competition_id, category, weight/age/qualification rules and unknowns |
| EventSpecification | id, division_id, revision, event family, implement, scoring, load sequence, distance/height/time limit, per-hand meaning, assistance rules, evidence |
| SourceEvidence | id, URL/file reference, relevant excerpt, retrieved time, field provenance, verification status |
| Assessment | id, owner_id, profile/evidence snapshot, division/event versions, per-event labels and reasons, eligibility, missing details, optional benchmark, stale flag |
| PreparationPlan | id, owner_id, assessment_id, revision, catalog/template/provider versions, weekly sessions, exercises/effort/progression, access needs, explanations, draft/active state, stale/demo flags |
| TrainingLog | id, owner_id, plan/session reference when applicable, date, completed work, effort/notes, linked performance records |
| HistoricalResult | id, pseudonymous athlete key, division/event version, result/completion status, date, source and synthetic flag |

Equipment and performance records change the athlete evidence revision used by assessments. A report never silently points at a changed record without a snapshot.

## Stable labels

Eligibility: eligible, ineligible, needs_confirmation.
Event evidence: demonstrated, measured_gap, implement_practice_gap, unknown.
Source review: unverified, confirmed, conflicting.
Job lifecycle when introduced: queued, running, succeeded, failed.
Unsupported custom scoring returns unknown unless an explicit validated handler exists.

## Initial API contract

Use /api/v1 as the base prefix.

| Route | Responsibility |
| --- | --- |
| GET/PUT /athlete-profile | Current owner's profile |
| GET/POST /equipment-access | Current owner's available equipment |
| PATCH/DELETE /equipment-access/{id} | Owned record maintenance |
| GET/POST /performance-records | Owned performance evidence |
| PATCH/DELETE /performance-records/{id} | Corrections with snapshot preservation |
| GET /competitions | Filtered catalog |
| POST /competitions | Manual draft entry with ownership/review controls |
| GET /competitions/{id} | Divisions and event details |
| PATCH /competitions/{id} | Authorized edit; create changed event revisions |
| GET/PUT /target-competition | Owned target division |
| POST /assessments | Assess current evidence for selected division |
| GET /assessments/{id} | Owned saved report |
| POST /preparation-plans | Generate validated draft from an assessment |
| GET /preparation-plans/{id} | Owned saved plan |
| POST /preparation-plans/{id}/activate | Athlete-reviewed active plan |
| GET/POST /training-logs | Owned session history and entry |
| GET /health | Basic service availability |

In the first demo use synchronous bounded mock generation. Add /jobs and job-submission endpoints when introducing live long-running processing. Include pagination for unbounded lists, documented filter parameters, and ownership checks for all private IDs.

## Provider contracts

AI: validated assessment + profile constraints + applicable catalog -> structured plan proposal with provider/model/version metadata.
Search: query + optional location/date filters -> candidate URLs/titles/snippets with retrieval times.
Extraction: permitted public URL -> page content/source evidence -> schema-validated event proposal requiring review.
Mocks implement the same interfaces and declare their origin explicitly.
