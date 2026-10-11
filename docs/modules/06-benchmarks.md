# Module 06: historical performance benchmarks

## Ownership and boundary
Own reference-cohort selection, compatible result matching, and numerical comparisons. Results come from a permitted dataset or labeled synthetic fixtures, not model guesses. Add optional evidence to assessments without blocking the core journey.

## Required product detail
## Historical benchmarking

Benchmark against a clearly defined reference cohort, not “all strongmen.”

### Matching criteria

Require compatible division and performance category, then inspect event family, implement, load, distance, time limit, assistance rules, and scoring. Do not merge novice and elite athletes into a single default comparison. Document any differences that remain.

Do not combine results with incompatible scoring. A points-based deadlift is not directly comparable with a maximum-load deadlift. Incomplete timed events need their own result handling rather than invented finish times.

### Percentile calculation

For an external reference sample where larger values are better:

```text
percentile = 100 × (number_below + 0.5 × number_equal) / sample_size
```

For comparable completed timed events, smaller values are better; use the number of slower results in place of `number_below`. State the tie convention and whether results represent unique athletes or repeated performances.

Display cohort filters, sample size, date range, source, and missing-data limitations. A percentile within collected records is not a percentile of the whole sport.

**Proposed MVP rule:** Suppress percentile labels below 20 unique matched athletes. This is a conservative interface choice, not a guarantee of statistical reliability. Smaller samples may still be shown as individual historical results with an explicit limited-sample label.

Keep the MVP benchmark descriptive. Do not present a probability of winning, or broaden mismatched cohorts just to produce a number.

## Task and verification
Store provenance and pseudonymous athlete identity. Use one documented result-selection rule per athlete for a given cohort, such as the latest compatible result; do not count repeated entries as extra athletes. Select the reference cohort independently of the user result. Label synthetic comparisons at every display point.
Verify higher/lower-is-better direction, ties, 19 versus 20 unique-athlete boundary, duplicates, incompatible divisions/implements/rules, missing metadata, and incomplete timed results. Show no percentile when any required matching evidence is unavailable. Report selected cohort rules, dates, and sample size.
