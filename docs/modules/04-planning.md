# Module 04: preparation planning

## Ownership and boundary
Own versioned plan drafts, validation, athlete review/activation, and plan presentation. Consume an assessment snapshot, availability/equipment, catalog, and typed AI provider. Never let a provider bypass hard validation or ownership.

## Task
Create a deterministic mock plan in the demo and a configurable Claude adapter with the same output schema. Mock output must be explicitly labeled. Use unreviewed sample templates only for demos; require reviewed material for live training advice. Save the assessment/catalog/provider versions and allow an athlete to activate a reviewed draft. Missing live credentials produce unavailable status.

## Required product detail
## Equipment-aware preparation planning

The plan should combine competition demands, preparation time, current performance, training availability, and equipment limits.

Use a curated exercise library reviewed by a strongman coach. The table below illustrates mapping categories; it is not a training prescription or a claim of equivalent performance transfer.

| Competition demand | Possible general preparation | Specificity limitation |
| --- | --- | --- |
| Log clean-and-press | Available pressing and upper-back exercises | Barbell work does not demonstrate log-clean technique |
| Farmer’s carry | Available loaded carries and grip work | Handle height, loading, and course conditions may differ |
| Yoke walk | General leg, trunk, and supported carry work | No direct substitute proves yoke stability or gait competence |
| Stones or loading | Appropriate available loading movements and general strength work | Object shape, grip, loading height, and technique differ |

Each plan includes:

- Weekly session structure and its competition-related purpose.
- Exercises selected from available equipment, with intended effort and progression.
- Event-practice opportunities and unresolved access needs.
- Recovery and pre-competition adjustments drawn from reviewed templates.
- Rules for missed sessions, equipment changes, and reporting pain.
- Explanations linking priorities to the gap report.

The system should not promise that a general-gym substitute fully replaces implement practice. It should help the athlete decide whether occasional access to a specialist gym is necessary and feasible.

For pain or unsupported restrictions, pause the affected recommendation and direct it to appropriate professional review. Do not generate diagnoses or rehabilitation instructions.

## Verify
Plan generation without keys; provider adapter with mocked responses; rejection of invalid schema, unavailable required equipment, disallowed exercises, excessive session count/duration, unsupported facts, and silently substituted implements. Optional access-dependent practice must be a clearly unresolved need, not assumed availability. Verify draft/active states, ownership, stale assessment handling, and provider error messages.
