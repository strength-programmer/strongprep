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
  const profileMissing = completeness.missing.filter((m: string) => m !== "target_competition");

  const reassess = async () => {
    setBusy(true); setActionError(null);
    try {
      const a = await api("/assessments", { method: "POST", body: { competition_id: target.competition_id, division_id: target.division_id } });
      router.push(`/assessments/${a.id}`);
    } catch (e) { setActionError(e as ApiError); setBusy(false); }
  };

  const steps = [
    { key: "profile", label: "Profile", sub: profileMissing.length ? `${profileMissing.length} to fill` : "Complete", done: profileMissing.length === 0, href: "/profile" },
    { key: "target", label: "Competition", sub: target ? target.title : "Pick a target", done: !!target, href: "/competitions" },
    { key: "report", label: "Gap report", sub: assessment ? (assessment.stale ? "Out of date" : "Ready") : "Not made", done: !!assessment && !assessment.stale, href: assessment ? `/assessments/${assessment.id}` : "/competitions" },
    { key: "plan", label: "Plan", sub: plan ? (plan.stale ? "Out of date" : plan.review_state) : "Not made", done: !!plan && plan.review_state === "saved" && !plan.stale, href: plan ? `/plans/${plan.id}` : "/competitions" },
    { key: "train", label: "Training", sub: recent_logs.length ? `${recent_logs.length}+ logged` : "None yet", done: recent_logs.length > 0, href: "/training" },
  ];
  const current = steps.findIndex((s) => !s.done);

  // One obvious next action, derived from state.
  let hero: { kicker: string; title: string; text: string; cta: React.ReactNode };
  if (profileMissing.length > 0) {
    hero = { kicker: "Next step", title: "Complete your profile", text: `Still needed: ${profileMissing.map((m: string) => MISSING_TEXT[m]).join(", ")}. This is what your gap report and plan are built from.`, cta: <Link href="/profile" className="btn btn-primary btn-lg">Open profile</Link> };
  } else if (!target) {
    hero = { kicker: "Next step", title: "Choose a competition", text: "Pick the show and division you are preparing for. We will compare each event to what you have actually demonstrated.", cta: <Link href="/competitions" className="btn btn-primary btn-lg">Browse competitions</Link> };
  } else if (!assessment || assessment.stale) {
    hero = { kicker: "Next step", title: assessment ? "Update your gap report" : "See where your gaps are", text: assessment ? `The last report is out of date: ${assessment.stale_reasons.join(" ")}` : `Compare your records and equipment with each event in ${target.title}.`, cta: <button className="btn btn-primary btn-lg" onClick={reassess} disabled={busy}>{busy ? "Working…" : assessment ? "Reassess now" : "Generate gap report"}</button> };
  } else if (!plan || plan.stale) {
    hero = { kicker: "Next step", title: "Build your preparation plan", text: "Your gap report is ready. Generate a weekly plan that fits your days, session length and equipment.", cta: <Link href={`/assessments/${assessment.id}`} className="btn btn-primary btn-lg">Open report and make plan</Link> };
  } else if (plan.review_state !== "saved") {
    hero = { kicker: "Next step", title: "Review and save your plan", text: "Your draft plan is waiting. Read why each session is there, then save it.", cta: <Link href={`/plans/${plan.id}`} className="btn btn-primary btn-lg">Review plan</Link> };
  } else {
    hero = { kicker: "Today", title: "Log your next session", text: "Record what you did and any new performance. New records feed the next gap report.", cta: <Link href={`/training?plan=${plan.id}`} className="btn btn-primary btn-lg">Log a session</Link> };
  }

  return (
    <>
      <div className="page-head">
        <h1>Dashboard</h1>
        <p>What should you work on next, given the competition, what you have shown, and the equipment you can reach?</p>
      </div>
      <ErrorBox error={actionError} />

      <section className="hero" aria-label="Next step">
        <div className="kicker">{hero.kicker}</div>
        <h2>{hero.title}</h2>
        <p>{hero.text}</p>
        <div className="row" style={{ marginTop: ".8rem" }}>{hero.cta}</div>
      </section>

      <ol className="stepper" aria-label="Your journey">
        {steps.map((s, i) => (
          <li key={s.key}>
            <Link href={s.href} className={`step ${s.done ? "done" : i === current ? "current" : ""}`} aria-current={i === current ? "step" : undefined}>
              <span className="num">{s.done ? "✓" : i + 1}</span>
              <span className="lbl">{s.label}</span>
              <span className="sub">{s.sub}</span>
            </Link>
          </li>
        ))}
      </ol>

      <div className="grid">
        <Card title="Target">
          {!target ? <Empty title="No target yet" /> : (
            <>
              <p><Link href={`/competitions/${target.competition_id}`}><strong>{target.title}</strong></Link></p>
              <p className="small">{target.division_name} · {fmtDate(target.date)}</p>
              <p>{target.is_demo && <DemoBadge label="fictional" />} <CompStatusBadge status={target.status} />{target.status === "upcoming" && target.days_left >= 0 && <Badge tone="info">{target.days_left} days to go</Badge>}</p>
            </>
          )}
        </Card>
        <Card title="Top priorities">
          {!assessment ? <p className="muted">Appears after your gap report.</p> : assessment.top_priorities.length === 0 ? <p>Every event is demonstrated under recorded conditions.</p> : (
            <ol className="small" style={{ paddingLeft: "1.1rem", margin: 0 }}>
              {assessment.top_priorities.map((p: any) => <li key={p.event}><strong>{p.event}</strong><br /><span className="muted">{p.status_label}</span></li>)}
            </ol>
          )}
          {assessment && <p><Link className="btn btn-small" href={`/assessments/${assessment.id}`}>Open report</Link></p>}
        </Card>
        <Card title="Recent training" actions={<Link href="/training" className="btn btn-small">Log</Link>}>
          {recent_logs.length === 0 ? <p className="muted">Nothing logged yet.</p> : (
            <ul className="small" style={{ paddingLeft: "1.1rem", margin: 0 }}>
              {recent_logs.slice(0, 4).map((l: any) => <li key={l.id}>{fmtDate(l.session_date)} · {l.completed ? "done" : "skipped"}{l.effort_rpe ? ` · RPE ${l.effort_rpe}` : ""}</li>)}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}
