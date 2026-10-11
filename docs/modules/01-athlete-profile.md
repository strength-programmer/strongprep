# Module 01: athlete profile and performance

## Ownership and boundary
Own profile, equipment access, performance records, and evidence revisions. No competition extraction or plan generation. Depend on shared identity/persistence and docs/CONTRACTS.md. Serve /profile and profile completeness on the dashboard.

## Task
Create, read, edit, and validate the current athlete's information. Support equipment and performance corrections. Save across restarts. Prefer explicit unknowns over guessed measurements. Update the evidence revision when inputs used by reports change; preserve past assessment snapshots.

## Required product detail
## Athlete inputs

Collect information that changes the competition assessment or plan. Keep optional fields optional.

| Category | Fields | Use |
| --- | --- | --- |
| Profile | Body weight, relevant division/age information, competition experience | Division checks and reference-cohort selection |
| Location | City or approximate coordinates, travel radius | Competition filtering without requiring an exact home address |
| Performance | Exercise/event, load, reps, distance, time, date, effort, and conditions | Establish what the athlete has actually demonstrated |
| Equipment | Available implements, maximum loads, carry space, occasional access | Choose feasible training and identify practice limitations |
| Availability | Days per week, session duration, other training commitments | Fit the plan to the athlete’s schedule |
| Constraints | Movement restrictions, exercises to avoid, current pain flags | Apply supported restrictions or request coach review |
| Goal | Target competition, division, participation or performance objective | Determine priorities and preparation timeline |

Height may be recorded for context, but it should not produce unsupported performance predictions. Do not require a large collection of physical measurements just because they are available.

Every performance record should distinguish **self-reported training**, **verified training**, and **official competition result**. A one-repetition maximum, a timed set, and a competition result must remain separate records.

## Verify
Exercise create/update/read and persistence, missing optional fields, invalid units/values, per-hand versus total loads, dated evidence, and ownership checks. Self-reported entries must retain that label. Updating equipment or performance must make dependent saved reports/plans visibly stale.
