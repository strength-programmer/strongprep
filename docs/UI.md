# Athlete-facing interface

### Screens to implement

| Route | Main behavior |
| --- | --- |
| `/` | Dashboard showing profile completeness, target competition, gaps, and current plan |
| `/profile` | Profile, equipment, availability, and performance forms |
| `/competitions` | Competition list with date/location filters and clear demo labels |
| `/competitions/[id]` | Division selector, event requirements, sources, and target selection |
| `/assessments/[id]` | Event-level evidence, gaps, unknowns, and any supported benchmark |
| `/plans/[id]` | Weekly sessions, explanations, practice needs, and save/review action |
| `/training` | Session logging and recent records |

Use a clean, responsive dashboard with readable tables, consistent units, helpful validation, and loading/empty/error states. Keep implementation details out of normal athlete screens; show only necessary integration status in settings or development diagnostics.

## Behavior and integration
- Use the backend contract for data. Do not duplicate assessment logic or call paid providers from the browser.
- Distinguish fictional data, self-reported evidence, confirmed facts, unknown values, stale outputs, and provider errors.
- Use units consistently and show original units where interpreting a source. A location filter cannot claim driving time from straight-line distance.
- Dashboard shows the saved target, latest report and its staleness, active plan, and recent completed sessions.
- Plan review/activation is a visible user action. Logging a session does not silently prescribe new loads.
- Integration configuration belongs in settings/development diagnostics, not ordinary athlete decisions.
- Prefer accessible labels, keyboard navigation, readable mobile layouts, and usable empty states.
- Read only the backend module contract needed for the screen being implemented.
