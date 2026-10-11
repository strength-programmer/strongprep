"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { api, ApiError, useApi } from "@/lib/api";
import { Badge, Card, ErrorBox, Loading, StatusBadge } from "@/components/ui";

export default function PlanPage() {
  const { id } = useParams<{ id: string }>();
  const { data: p, error, loading, reload, setData } = useApi(`/preparation-plans/${id}`);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ApiError | null>(null);

  if (loading) return <Loading what="Loading plan" />;
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!p) return null;
  const c = p.content;

  const save = async () => {
    setBusy(true); setErr(null);
    try { setData(await api(`/preparation-plans/${p.id}/save`, { method: "POST" })); } catch (e) { setErr(e as ApiError); } finally { setBusy(false); }
  };

  return (
    <>
      <h1>{c.title}</h1>
      <p>
        <Badge tone={p.review_state === "saved" ? "good" : "warn"}>{p.review_state === "saved" ? "Saved" : "Draft: review before saving"}</Badge>{" "}
        <Badge tone={p.provider === "mock" ? "demo" : "info"}>{c.ai_label}</Badge> <span className="small muted">Plan v{p.version} · {p.template_versions.length} templates used</span>
      </p>
      <div className="alert alert-info">{c.demo_notice} {c.template_notice}</div>
      {p.stale && <div className="alert alert-warn" role="alert"><strong>This plan is stale.</strong> {p.stale_reasons.join(" ")} Run a new assessment and generate a new plan. <Link href={`/assessments/${p.assessment_id}`}>Open the original report</Link></div>}
      <ErrorBox error={err} />

      <Card title="Why this plan (from your gap report)" actions={<Link className="btn btn-small" href={`/assessments/${p.assessment_id}`}>Gap report</Link>}>
        {c.explanations.length === 0 ? <p>All events are demonstrated under recorded conditions; the plan maintains them.</p> : (
          <ol>
            {[...c.explanations].sort((a: any, b: any) => a.priority - b.priority).map((x: any) => (
              <li key={x.event_id}><StatusBadge status={x.status} /> {x.text}</li>
            ))}
          </ol>
        )}
      </Card>

      <Card title="Practice needs and unresolved access">
        {c.practice_needs.length === 0 ? <p className="muted">No access issues were identified.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Event</th><th>Implement</th><th>Your access</th><th>Status</th><th>Action</th></tr></thead>
              <tbody>
                {c.practice_needs.map((n: any) => (
                  <tr key={n.event_id}>
                    <td>{n.event_name}</td><td>{n.implement}</td><td>{n.access}</td>
                    <td><Badge tone={n.status === "unresolved" ? "bad" : "info"}>{n.status}</Badge></td><td className="small">{n.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="small muted">General-gym substitutes do not replace practice on the competition implement.</p>
      </Card>

      <Card title="Weekly sessions">
        {c.weeks.map((w: any) => (
          <details key={w.week} open={w.week === 1}>
            <summary>Week {w.week} · {w.phase} · {w.sessions.length} sessions</summary>
            {w.sessions.map((s: any) => (
              <div className="session" key={s.id}>
                <strong>{s.name}</strong> {s.access_session && <Badge tone="warn">needs agreed access</Badge>} <span className="small muted">~{s.estimated_minutes} min</span>
                <div className="small">{s.purpose}</div>
                <div className="table-wrap">
                  <table>
                    <thead><tr><th>Exercise</th><th className="num">Sets</th><th>Reps</th><th>Intensity</th></tr></thead>
                    <tbody>{s.exercises.map((x: any, i: number) => <tr key={i}><td>{x.name}</td><td className="num">{x.sets}</td><td>{x.reps}</td><td>{x.intensity}</td></tr>)}</tbody>
                  </table>
                </div>
                <Link className="small" href={`/training?plan=${p.id}&session=${s.id}`}>Log this session</Link>
              </div>
            ))}
          </details>
        ))}
      </Card>

      <Card title="Rules">
        <ul>
          <li><strong>Missed sessions:</strong> {c.rules.missed_sessions}</li>
          <li><strong>Equipment changes:</strong> {c.rules.equipment_changes}</li>
          <li><strong>Pain:</strong> {c.rules.pain}</li>
        </ul>
        {c.paused.length > 0 && (
          <>
            <h3>Paused or excluded exercises</h3>
            <ul className="small">{c.paused.map((x: any, i: number) => <li key={i}><strong>{x.item}</strong>: {x.reason}</li>)}</ul>
          </>
        )}
        <p className="small muted">Checks passed before this plan was shown: {c.validation.checked.join(", ")}.</p>
      </Card>

      <div className="row">
        <button className="btn btn-primary" onClick={save} disabled={busy || p.review_state === "saved" || p.stale}>{p.review_state === "saved" ? "Saved" : busy ? "Saving…" : "Review done, save plan"}</button>
        <Link className="btn" href="/training">Go to training log</Link>
      </div>
    </>
  );
}
