"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError, useApi } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { Badge, Card, CompStatusBadge, DemoBadge, Empty, ErrorBox, Loading } from "@/components/ui";

const MISSING_TEXT: Record<string, string> = {
  body_weight_kg: "Body weight", age: "Age", division_category: "Division category", experience_level: "Experience level",
  availability: "Training days and session length", equipment: "Equipment access", performance_records: "At least one performance record",
  target_competition: "Target competition and division",
};

export default function Dashboard() {
  const { data, error, loading, reload } = useApi("/dashboard");
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<ApiError | null>(null);

  if (loading) return <Loading what="Loading dashboard" />;
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!data) return null;

  const { completeness, target, assessment, plan, recent_logs } = data;

  const reassess = async () => {
    setBusy(true);
    setActionError(null);
    try {
      const a = await api("/assessments", { method: "POST", body: { competition_id: target.competition_id, division_id: target.division_id } });
      router.push(`/assessments/${a.id}`);
    } catch (e) {
      setActionError(e as ApiError);
      setBusy(false);
    }
  };

  return (
    <>
      <h1>Dashboard</h1>
      <p className="muted">Given a competition, your current performance and the equipment you can access: what should you work on next?</p>
      <ErrorBox error={actionError} />
      <div className="grid">
        <Card title="Profile completeness" actions={<Link href="/profile" className="btn btn-small">Edit profile</Link>}>
          <div className="progress" role="progressbar" aria-valuenow={completeness.percent} aria-valuemin={0} aria-valuemax={100}>
            <div style={{ width: `${completeness.percent}%` }} />
          </div>
          <p><strong>{completeness.percent}%</strong> complete</p>
          {completeness.missing.length > 0 && (
            <ul className="small">
              {completeness.missing.map((m: string) => <li key={m}>{MISSING_TEXT[m] ?? m}</li>)}
            </ul>
          )}
        </Card>

        <Card title="Target competition">
          {!target ? (
            <Empty title="No target selected yet">
              <Link className="btn btn-primary" href="/competitions">Browse competitions</Link>
            </Empty>
          ) : (
            <>
              <p>
                <Link href={`/competitions/${target.competition_id}`}><strong>{target.title}</strong></Link>{" "}
                {target.is_demo && <DemoBadge label="fictional" />} <CompStatusBadge status={target.status} />
              </p>
              <p className="small">{target.division_name} · {fmtDate(target.date)}{target.status === "upcoming" && target.days_left >= 0 ? ` · ${target.days_left} days away` : ""}</p>
            </>
          )}
        </Card>

        <Card title="Event gaps">
          {!target ? <p className="muted">Select a target to generate a gap report.</p> : !assessment ? (
            <>
              <p className="muted">No gap report yet.</p>
              <button className="btn btn-primary" onClick={reassess} disabled={busy}>{busy ? "Generating…" : "Generate gap report"}</button>
            </>
          ) : (
            <>
              {assessment.stale && (
                <div className="alert alert-warn">
                  This report is stale: {assessment.stale_reasons.join(" ")}{" "}
                  <button className="btn btn-small" onClick={reassess} disabled={busy}>Reassess</button>
                </div>
              )}
              <p className="small">Eligibility: <Badge tone={assessment.eligibility === "eligible" ? "good" : assessment.eligibility === "ineligible" ? "bad" : "warn"}>{assessment.eligibility.replace("_", " ")}</Badge></p>
              <p className="small">
                {assessment.summary_counts.measured_gap} measured gap · {assessment.summary_counts.implement_practice_gap} implement-practice gap · {assessment.summary_counts.unknown} unknown · {assessment.summary_counts.demonstrated} demonstrated
              </p>
              {assessment.top_priorities.length > 0 && (
                <ol className="small">
                  {assessment.top_priorities.map((p: any) => <li key={p.event}><strong>{p.event}</strong> — {p.status_label}</li>)}
                </ol>
              )}
              <Link className="btn btn-small" href={`/assessments/${assessment.id}`}>Open report</Link>
            </>
          )}
        </Card>

        <Card title="Current plan">
          {!plan ? <p className="muted">{assessment ? "No plan yet. Open the gap report to generate one." : "A plan comes after a gap report."}</p> : (
            <>
              <p>
                Plan v{plan.version} · <Badge tone={plan.review_state === "saved" ? "good" : "warn"}>{plan.review_state}</Badge>{" "}
                {plan.provider === "mock" && <Badge tone="demo">mock AI</Badge>} {plan.stale && <Badge tone="bad">stale</Badge>}
              </p>
              <Link className="btn btn-small" href={`/plans/${plan.id}`}>Open plan</Link>
            </>
          )}
        </Card>
      </div>

      <Card title="Recent training" actions={<Link href="/training" className="btn btn-small">Log a session</Link>}>
        {recent_logs.length === 0 ? <Empty title="No sessions logged yet" /> : (
          <ul>
            {recent_logs.map((l: any) => (
              <li key={l.id}>{fmtDate(l.session_date)} — {l.completed ? "completed" : "skipped"}{l.effort_rpe ? `, RPE ${l.effort_rpe}` : ""}{l.planned_session ? ` (${l.planned_session})` : ""}</li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
