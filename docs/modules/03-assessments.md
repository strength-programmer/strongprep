# Module 03: event-gap assessments

## Ownership and boundary
Own deterministic eligibility and preparation-gap calculations and saved evidence snapshots. Consume athlete and selected division/event data. No web scraping or invented lift conversions. Benchmarks are optional enrichment from module 06. Serve /assessments/[id].

## Task
Generate and persist one report per selected division with per-event evidence, labels, reasons, missing details, and source/version references. Show unassessable cases usefully. Until benchmarking is implemented, return unavailable rather than fabricated statistics.

## Required product detail
## Preparation assessment

Separate three questions:

| Question | Evidence required | Output |
| --- | --- | --- |
| Can I enter this division? | Published age, weight, qualification, and entry rules | Eligible, ineligible, or needs confirmation |
| What preparation gaps do I have? | Event requirements, recent comparable training, implement experience, and access | Event-level evidence and priorities |
| How do I compare with historical competitors? | Matched results with compatible conditions | Cohort comparison or insufficient data |

Eligibility does not establish safety, expected placing, or event competence.

### Event-level labels

- **Demonstrated under recorded conditions:** Relevant recent performance meets the specified task under sufficiently similar rules.
- **Measured performance gap:** A comparable record falls below a defined task requirement.
- **Implement-practice gap:** General strength evidence exists, but relevant implement practice is missing.
- **Unknown:** Required event details or athlete evidence are missing.

These labels are product rules to develop with a qualified strongman coach. They are not validated scientific readiness categories.

### Numerical comparisons

Where conditions match, a load ratio can describe a gap:

```text
load_ratio = demonstrated_load / specified_load
```

Use this only for a comparable load task. A ratio of 1.10 does not mean “110% ready.” It does not predict repetitions at the event load or performance on another implement.

For timed repetition events, prefer a recorded set at the target load under comparable rules. For carries, include load, course distance, time, turns, and implement. Do not infer yoke speed from squat strength or log performance from a strict barbell press.

Start with an event table rather than an overall readiness percentage. Report which conclusions are observed, inferred, or unavailable. Overall ranking predictions should wait for suitable data and validation.

## Verify
Use cases: comparable max-load record, timed-rep requirement with only a single available, different implement, unsupported scoring, absent load, incomplete rule evidence, equipment-practice gap, and eligibility boundary. Keep eligibility independent of preparation labels. Test ratios and zero denominators, ownership, snapshot history, and stale state after changed requirements.
