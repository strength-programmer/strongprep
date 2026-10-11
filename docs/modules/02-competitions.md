# Module 02: competition catalog and event rules

## Ownership and boundary
Own competition listings, divisions, event specifications, source evidence, and saved target selection. Live search/extraction belongs to module 07. Depend on CONTRACTS; serve /competitions and /competitions/[id].

## Task
Seed several visibly fictional competitions with multiple divisions. Support manual draft entry and correction, date/location filters, source/review displays, division selection, and persistent target selection. Keep unverified submissions separate from confirmed catalog facts. Changes to event requirements create revisions and invalidate dependent outputs without destroying history.

## Required product detail
## Competition and event data

### Competition record

Store title, organizer, federation where applicable, venue, location, local date/time, registration deadline, source URL, registration link, entry fee when known, last checked time, status, and available divisions.

Unknown fees, coordinates, or eligibility requirements remain unknown. Approximate distance must be labeled; do not display straight-line distance as driving time.

### Event specification

Each event belongs to a competition division and should contain:

- Event family and exact name.
- Implement and relevant configuration.
- Load or load sequence, including whether a carry load is per hand or total.
- Time limit, distance, height, and course details where relevant.
- Scoring type: maximum load, repetitions, time, distance, or custom scoring.
- Performance rules and permitted equipment.
- Source evidence and verification status.

For example, one organizer listing describes a points-based deadlift with multiple bars and a separate log event where a heavy-log repetition outranks light-log repetitions [S5]. These examples show why the app must support event-specific scoring instead of assuming every event is a simple maximum or repetition count.

**Extraction rule:** Preserve original units and text, normalize verified values, and request review for ambiguity. Never assume an unlabeled weight is kilograms or pounds.

## Verify
Correct division-specific weights, original units, per-hand/total meaning, unknown fees/rules, date/time zones, missing coordinates, draft ownership, and revisions. Ambiguous values stay unknown pending confirmation. Canceled/past events remain clearly identified. Distance filters only operate where coordinates are available and do not imply travel time.
