"use client";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { api, ApiError, useApi } from "@/lib/api";
import { fmtDate, kg, numOrNull } from "@/lib/format";
import { Card, Empty, ErrorBox, Field, Loading } from "@/components/ui";

export default function TrainingPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Training />
    </Suspense>
  );
}

function Training() {
  const params = useSearchParams();
  const logs = useApi<any[]>("/training-logs");
  const plans = useApi<any[]>("/preparation-plans");
  const ref = useApi<any>("/reference");
  const [planId, setPlanId] = useState(params.get("plan") ?? "");
  const detail = useApi<any>(planId ? `/preparation-plans/${planId}` : null);

  if (logs.loading || plans.loading || ref.loading) return <Loading what="Loading training" />;
  const err = logs.error || plans.error || ref.error;
  if (err) return <ErrorBox error={err} onRetry={() => { logs.reload(); plans.reload(); ref.reload(); }} />;

  const sessions: { id: string; name: string; exercises: any[] }[] = detail.data ? detail.data.content.weeks.flatMap((w: any) => w.sessions.map((s: any) => ({ id: s.id, name: s.name, exercises: s.exercises }))) : [];

  return (
    <>
      <div className="page-head"><h1>Training</h1></div>
      <p className="muted">Log sessions and any new performance. New records feed the next gap report, so re-run the assessment afterward.</p>
      <LogForm
        key={`${planId}-${params.get("session") ?? ""}-${sessions.length}`}
        tasks={ref.data.tasks} plans={plans.data ?? []} planId={planId} setPlanId={setPlanId} sessions={sessions}
        initialSession={params.get("session") ?? ""} onSaved={logs.reload}
      />
      <Card title="Recent sessions">
        {!logs.data || logs.data.length === 0 ? <Empty title="No sessions logged yet" /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Session</th><th>Done</th><th className="num">RPE</th><th>Work</th><th>Notes</th><th /></tr></thead>
              <tbody>
                {logs.data.map((l) => (
                  <tr key={l.id}>
                    <td>{fmtDate(l.session_date)}</td><td>{l.planned_session ?? "Unplanned"}</td><td>{l.completed ? "Yes" : "Skipped"}</td><td className="num">{l.effort_rpe ?? "—"}</td>
                    <td className="small">{l.exercises.map((x: any) => `${x.name}${x.sets ? ` ${x.sets}×${x.reps ?? "?"}` : ""}${x.load_kg != null ? ` @ ${kg(x.load_kg)}` : ""}`).join("; ") || "—"}</td>
                    <td className="small">{l.notes ?? ""}</td>
                    <td><button className="btn btn-small" aria-label={`Delete log ${l.id}`} onClick={async () => { await api(`/training-logs/${l.id}`, { method: "DELETE" }); logs.reload(); }}>Delete</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}

function LogForm({ tasks, plans, planId, setPlanId, sessions, initialSession, onSaved }: any) {
  const today = new Date().toISOString().slice(0, 10);
  const [f, setF] = useState({ session: initialSession, date: today, completed: true, rpe: "", notes: "" });
  type Row = { name: string; sets: string; reps: string; load: string };
  const [exs, setExs] = useState<Row[]>((): Row[] => {
    const sess = sessions.find((x: any) => x.id === initialSession);
    return sess ? sess.exercises.map((x: any) => ({ name: x.name, sets: String(x.sets), reps: /^\d+$/.test(String(x.reps)) ? String(x.reps) : "", load: "" })) : [{ name: "", sets: "", reps: "", load: "" }];
  });
  const [perfs, setPerfs] = useState<any[]>([]);
  const [err, setErr] = useState<ApiError | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const pickSession = (id: string) => {
    setF((v) => ({ ...v, session: id }));
    const sess = sessions.find((x: any) => x.id === id);
    if (sess) setExs(sess.exercises.map((x: any) => ({ name: x.name, sets: String(x.sets), reps: String(x.reps).match(/^\d+$/) ? String(x.reps) : "", load: "" })));
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null); setOk(null);
    try {
      await api("/training-logs", { method: "POST", body: {
        plan_id: planId ? Number(planId) : null, planned_session: f.session || null, session_date: f.date, completed: f.completed,
        effort_rpe: numOrNull(f.rpe), notes: f.notes || null,
        exercises: exs.filter((x) => x.name).map((x) => ({ name: x.name, sets: numOrNull(x.sets), reps: numOrNull(x.reps), load_kg: numOrNull(x.load) })),
        new_performance: perfs.map((p) => ({ task_key: p.task_key, load_kg: numOrNull(p.load), load_per_hand: p.per_hand, reps: numOrNull(p.reps), distance_m: numOrNull(p.dist),
          time_s: numOrNull(p.time), record_date: f.date, source_type: "self_reported" })),
      } });
      setOk("Session logged."); setExs([{ name: "", sets: "", reps: "", load: "" }]); setPerfs([]); setF({ ...f, notes: "", rpe: "" }); onSaved();
    } catch (x) { setErr(x as ApiError); } finally { setBusy(false); }
  };
  const setEx = (i: number, k: string, v: string) => setExs((a) => a.map((x, j) => (j === i ? { ...x, [k]: v } : x)));
  const setPf = (i: number, k: string, v: any) => setPerfs((a) => a.map((x, j) => (j === i ? { ...x, [k]: v } : x)));

  return (
    <Card title="Log a session">
      <form className="stack" onSubmit={submit}>
        <div className="row">
          <Field label="Plan (optional)">
            <select value={planId} onChange={(e) => setPlanId(e.target.value)}>
              <option value="">No plan</option>
              {plans.map((p: any) => <option key={p.id} value={p.id}>{p.competition_title} · v{p.version} · {p.review_state}</option>)}
            </select>
          </Field>
          <Field label="Planned session">
            <select value={f.session} onChange={(e) => pickSession(e.target.value)} disabled={!planId}>
              <option value="">Unplanned</option>
              {sessions.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="Date"><input type="date" max={today} value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} required /></Field>
          <Field label="Effort (RPE 1–10)"><input type="number" min="1" max="10" step="0.5" value={f.rpe} onChange={(e) => setF({ ...f, rpe: e.target.value })} /></Field>
        </div>
        <label className="check"><input type="checkbox" checked={f.completed} onChange={(e) => setF({ ...f, completed: e.target.checked })} />Session completed (untick if skipped)</label>
        <h3>Work done</h3>
        {exs.map((x, i) => (
          <div className="row" key={i}>
            <Field label="Exercise"><input value={x.name} onChange={(e) => setEx(i, "name", e.target.value)} /></Field>
            <Field label="Sets"><input type="number" min="1" value={x.sets} onChange={(e) => setEx(i, "sets", e.target.value)} /></Field>
            <Field label="Reps"><input type="number" min="1" value={x.reps} onChange={(e) => setEx(i, "reps", e.target.value)} /></Field>
            <Field label="Load (kg)"><input type="number" min="0" step="0.5" value={x.load} onChange={(e) => setEx(i, "load", e.target.value)} /></Field>
          </div>
        ))}
        <button type="button" className="btn btn-small" onClick={() => setExs([...exs, { name: "", sets: "", reps: "", load: "" }])}>Add exercise</button>
        <h3>New performance records (optional)</h3>
        {perfs.map((p, i) => (
          <div className="row" key={i}>
            <Field label="Task"><select value={p.task_key} onChange={(e) => setPf(i, "task_key", e.target.value)}>{tasks.map((t: any) => <option key={t.key} value={t.key}>{t.label}</option>)}</select></Field>
            <Field label="Load (kg)"><input type="number" step="0.5" value={p.load} onChange={(e) => setPf(i, "load", e.target.value)} /></Field>
            <Field label="Reps"><input type="number" value={p.reps} onChange={(e) => setPf(i, "reps", e.target.value)} /></Field>
            <Field label="Distance (m)"><input type="number" value={p.dist} onChange={(e) => setPf(i, "dist", e.target.value)} /></Field>
            <Field label="Time (s)"><input type="number" step="0.1" value={p.time} onChange={(e) => setPf(i, "time", e.target.value)} /></Field>
            <label className="check"><input type="checkbox" checked={p.per_hand} onChange={(e) => setPf(i, "per_hand", e.target.checked)} />per hand</label>
            <button type="button" className="btn btn-small" onClick={() => setPerfs(perfs.filter((_, j) => j !== i))}>Remove</button>
          </div>
        ))}
        <button type="button" className="btn btn-small" onClick={() => setPerfs([...perfs, { task_key: tasks[0].key, load: "", reps: "", dist: "", time: "", per_hand: false }])}>Add performance record</button>
        <Field label="Notes (do not include medical details)"><textarea rows={2} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
        <p className="small muted">If any movement caused pain, stop it and seek review by a qualified professional; set a pain flag in your profile so affected exercises are paused.</p>
        {ok && <div className="alert alert-ok" role="status">{ok}</div>}
        <ErrorBox error={err} />
        <button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Save session"}</button>
      </form>
    </Card>
  );
}
