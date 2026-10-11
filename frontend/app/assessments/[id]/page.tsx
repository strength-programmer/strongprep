"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError, useApi } from "@/lib/api";
import { fmtDate, kg, metres, ratioText, seconds } from "@/lib/format";
import { Badge, Card, DemoBadge, ErrorBox, Loading, StatusBadge } from "@/components/ui";

const BASIS_TEXT: Record<string, string> = { observed: "Observed", inferred: "Inferred", unavailable: "Unavailable" };
const ELIG_TONE: Record<string, "good" | "bad" | "warn"> = { eligible: "good", ineligible: "bad", needs_confirmation: "warn" };

export default function AssessmentPage() {
  const { id } = useParams<{ id: string }>();
  const { data: a, error, loading, reload } = useApi(`/assessments/${id}`);
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError | null>(null);

  if (loading) return <Loading what="Loading gap report" />;
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!a) return null;
  const r = a.result;

  const rerun = async () => {
    setBusy(true); setErr(null);
    try {
      const n = await api("/assessments", { method: "POST", body: { competition_id: a.competition_id, division_id: a.division_id } });
      router.push(`/assessments/${n.id}`);
    } catch (e) { setErr(e as ApiError); setBusy(false); }
  };
  const makePlan = async () => {
    setBusy(true); setErr(null);
    try {
      const p = await api("/preparation-plans", { method: "POST", body: { assessment_id: a.id } });
      router.push(`/plans/${p.id}`);
    } catch (e) { setErr(e as ApiError); setBusy(false); }
  };

  return (
    <>
      <h1>Gap report</h1>
      <p>
        <Link href={`/competitions/${a.competition_id}`}><strong>{r.competition.title}</strong></Link> · {r.division.name} · {fmtDate(r.competition.date)}{" "}
        {r.competition.is_demo && <DemoBadge label={r.competition.demo_label} />} <span className="small muted">Report made {fmtDate(a.created_at)} · rules {r.calculation_version}</span>
      </p>
      {a.stale && (
        <div className="alert alert-warn" role="alert">
          <strong>This report is stale.</strong> {a.stale_reasons.join(" ")} It is kept for reference; run a new assessment to update it.{" "}
          <button className="btn btn-small" onClick={rerun} disabled={busy}>Reassess now</button>
        </div>
      )}
      <ErrorBox error={err} />

      <Card title="1 · Can I enter this division?">
        <p><Badge tone={ELIG_TONE[r.eligibility.status]}>{r.eligibility.status.replace("_", " ")}</Badge></p>
        <ul>
          {r.eligibility.checks.map((c: any, i: number) => (
            <li key={i}><Badge tone={c.result === "pass" ? "good" : c.result === "fail" ? "bad" : "warn"}>{c.result === "unknown" ? "confirm" : c.result}</Badge> {c.detail}</li>
          ))}
          {r.eligibility.checks.length === 0 && <li>No machine-checkable entry rules were recorded for this division.</li>}
        </ul>
        <p className="small muted">{r.eligibility.note}</p>
      </Card>

      <Card title="2 · Event-level preparation gaps">
        <p className="small muted">{r.disclaimer} Labels are product rules awaiting coach review, not validated readiness categories. Load ratio compares only the same task on the same implement; 1.10 does not mean “110% ready”.</p>
        <div className="table-wrap">
          <table>
            <thead><tr><th className="num">Priority</th><th>Event</th><th>Requirement</th><th>Conclusion</th><th className="num">Load ratio</th><th>Basis</th><th>Next step</th></tr></thead>
            <tbody>
              {[...r.events].sort((x: any, y: any) => x.priority - y.priority).map((e: any) => (
                <tr key={e.event_id}>
                  <td className="num">{e.priority}</td>
                  <td><strong>{e.event_name}</strong><div className="small muted">{e.scoring_type.replace("_", " ")}</div></td>
                  <td className="small">
                    {kg(e.requirement.load_kg, e.requirement.load_per_hand)}
                    {e.requirement.time_limit_s != null && <> · limit {seconds(e.requirement.time_limit_s)}</>}
                    {e.requirement.distance_m != null && <> · {metres(e.requirement.distance_m)}</>}
                  </td>
                  <td><StatusBadge status={e.status} /><div className="small">{e.detail}</div></td>
                  <td className="num">{ratioText(e.load_ratio)}</td>
                  <td>{BASIS_TEXT[e.basis]}</td>
                  <td className="small">{e.next_step}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="small">
          Totals (counts only, not a score): {r.summary_counts.measured_gap} measured gap · {r.summary_counts.implement_practice_gap} implement-practice gap · {r.summary_counts.unknown} unknown · {r.summary_counts.demonstrated} demonstrated
        </p>
        {r.events.some((e: any) => e.equipment.flags.length > 0) && (
          <details>
            <summary>Equipment notes</summary>
            <ul>
              {r.events.filter((e: any) => e.equipment.flags.length).map((e: any) => (
                <li key={e.event_id}><strong>{e.event_name}</strong>: access {e.equipment.access}; {e.equipment.flags.map((f: string) => f.replace(/_/g, " ")).join(", ")}</li>
              ))}
            </ul>
          </details>
        )}
        <details>
          <summary>Evidence used for each event</summary>
          {r.events.map((e: any) => (
            <div key={e.event_id}>
              <h3>{e.event_name}</h3>
              {e.evidence.length === 0 ? <p className="small muted">No performance records on this task or related tasks.</p> : (
                <ul className="small">
                  {e.evidence.map((x: any) => (
                    <li key={x.record_id}>
                      <Badge tone={x.comparable ? "good" : "neutral"}>{x.comparable ? "comparable" : "not comparable"}</Badge> {fmtDate(x.date)} · {x.task_key.replace(/_/g, " ")} ·{" "}
                      {kg(x.load_kg, x.load_per_hand)}{x.reps ? ` × ${x.reps}` : ""}{x.distance_m ? ` · ${x.distance_m} m` : ""}{x.time_s ? ` · ${x.time_s} s` : ""} · {x.source_type.replace("_", " ")}
                      {x.note && <span className="muted"> — {x.note}</span>}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </details>
      </Card>

      <Card title="3 · Historical benchmarks">
        <p className="small muted">Benchmarks use only exactly matched cohorts. Percentiles appear only with at least 20 unique matched athletes; they describe the collected records, not the whole sport.</p>
        {r.events.map((e: any) => <Benchmark key={e.event_id} e={e} />)}
      </Card>

      {r.data_gaps.length > 0 && (
        <Card title="Data gaps and unknowns">
          <ul>{r.data_gaps.map((g: string, i: number) => <li key={i}>{g}</li>)}</ul>
        </Card>
      )}

      <div className="row">
        <button className="btn btn-primary" onClick={makePlan} disabled={busy || a.stale}>{busy ? "Working…" : "Generate preparation plan"}</button>
        <button className="btn" onClick={rerun} disabled={busy}>Re-run assessment with current data</button>
      </div>
    </>
  );
}

function Benchmark({ e }: { e: any }) {
  const b = e.benchmark;
  return (
    <details>
      <summary>{e.event_name} — {labelFor(b)}</summary>
      {b.cohort && (
        <p className="small">
          <strong>Cohort:</strong> {b.cohort.division_category} · {b.cohort.task.replace(/_/g, " ")} · {b.cohort.scoring.replace("_", " ")}
          {b.cohort.load_kg != null && <> · {kg(b.cohort.load_kg, b.cohort.load_per_hand)}</>}{b.cohort.time_limit_s != null && <> · {b.cohort.time_limit_s} s limit</>}{b.cohort.distance_m != null && <> · {b.cohort.distance_m} m</>}
          <br /><span className="muted">{b.cohort.criteria}</span>
        </p>
      )}
      {b.sample_size != null && b.sample_size > 0 && (
        <p className="small">
          <strong>Sample:</strong> {b.sample_size} unique athletes · {b.date_range?.[0]} to {b.date_range?.[1]} · min {b.min}, median {b.median}, max {b.max} {b.unit}<br />
          <strong>Source:</strong> {b.sources?.join("; ")} {b.synthetic && <Badge tone="demo">synthetic</Badge>}
        </p>
      )}
      {b.status === "percentile" && <p><strong>Your result: {b.athlete_value} {b.unit} → {b.percentile}th percentile</strong> within this cohort. <span className="small muted">{b.tie_convention}</span></p>}
      {b.status === "limited_sample" && <><p className="alert alert-warn">{b.reason}</p><p className="small">Your comparable result: {b.athlete_value} {b.unit}. Individual historical results (limited sample):</p></>}
      {b.status === "no_athlete_value" && <p className="alert alert-info">{b.reason}</p>}
      {(b.status === "no_cohort" || b.status === "unsupported") && <p className="alert alert-info">{b.reason}</p>}
      {b.results && (
        <ul className="small">{b.results.map((r: any, i: number) => <li key={i}>{r.athlete}: {r.value} {b.unit} ({fmtDate(r.date)})</li>)}</ul>
      )}
      {b.limitations && <p className="small muted">{b.limitations.join(" ")}</p>}
    </details>
  );
}

function labelFor(b: any) {
  switch (b.status) {
    case "percentile": return `${b.percentile}th percentile (n=${b.sample_size})`;
    case "limited_sample": return `limited sample (n=${b.sample_size}), percentile hidden`;
    case "no_athlete_value": return `cohort exists (n=${b.sample_size}), no comparable record from you`;
    case "no_cohort": return "no compatible cohort";
    default: return "not supported";
  }
}
