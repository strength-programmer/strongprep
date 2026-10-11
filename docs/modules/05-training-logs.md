# Module 05: training logs and reassessment

## Ownership and boundary
Own session completion records and link measured performances to the athlete module. Consume plan/session IDs; do not put coaching calculations into the log endpoint. Serve /training and recent activity on the dashboard.

## Task
- Record date, completed work, load/reps/time/distance, effort, and notes.
- Support a session linked to a plan or a standalone training entry.
- Validate ownership of every referenced plan and performance record.
- Let the athlete explicitly record completed work as new performance evidence; keep its task and rule details. Link records rather than duplicating the same effort twice.
- Update evidence revisions and mark dependent assessments/plans stale.
- Provide an explicit reassess action using current athlete evidence and selected event versions. Preserve older reports/plans and let the athlete review a replacement plan.
- Return persisted history after restart and reflect saved sessions on the dashboard.
- Do not automatically increase prescribed loads merely because a session was logged.

## Verify
Create/list a log, reject cross-owner links, persist across restarts, preserve legitimate zero results and unknowns, avoid duplicated performance records, and show stale status after new evidence. Check the complete profile -> target -> assessment -> reviewed plan -> session log -> reassessment journey with demo fixtures.

No wearables, video analysis, or medical tracking are required.
