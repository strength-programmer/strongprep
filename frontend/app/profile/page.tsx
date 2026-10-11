"use client";
import { FormEvent, useEffect, useState } from "react";
import { api, ApiError, useApi } from "@/lib/api";
import { fmtDate, kg, numOrNull } from "@/lib/format";
import { Card, Empty, ErrorBox, Field, Loading } from "@/components/ui";

type Ref = { tasks: any[]; implements: { key: string; label: string }[]; body_areas: string[]; templates: { key: string; name: string }[] };

export default function ProfilePage() {
  const ref = useApi<Ref>("/reference");
  const prof = useApi("/athlete-profile");
  const equip = useApi<any[]>("/equipment");
  const recs = useApi<any[]>("/performance-records");

  if (ref.loading || prof.loading || equip.loading || recs.loading) return <Loading what="Loading profile" />;
  const err = ref.error || prof.error || equip.error || recs.error;
  if (err) return <ErrorBox error={err} onRetry={() => { ref.reload(); prof.reload(); equip.reload(); recs.reload(); }} />;
  if (!ref.data || !prof.data || !equip.data || !recs.data) return null;

  return (
    <>
      <h1>Profile</h1>
      <p className="muted">Everything is stored locally in the demo. Weights are in kg, distances in metres, times in seconds.</p>
      <AthleteForm refData={ref.data} initial={prof.data.profile} completeness={prof.data.completeness.percent} onSaved={prof.reload} />
      <EquipmentForm refData={ref.data} initial={equip.data} onSaved={() => { equip.reload(); prof.reload(); }} />
      <PerformanceSection refData={ref.data} records={recs.data} onChanged={() => { recs.reload(); prof.reload(); }} />
    </>
  );
}

function Notice({ ok, err }: { ok: string | null; err: ApiError | null }) {
  return (
    <>
      {ok && <div className="alert alert-ok" role="status">{ok}</div>}
      <ErrorBox error={err} />
    </>
  );
}

function AthleteForm({ refData, initial, completeness, onSaved }: { refData: Ref; initial: any; completeness: number; onSaved: () => void }) {
  const p = initial ?? {};
  const [f, setF] = useState({
    display_name: p.display_name ?? "", body_weight_kg: p.body_weight_kg?.toString() ?? "", age: p.age?.toString() ?? "",
    division_category: p.division_category ?? "", experience_level: p.experience_level ?? "", competitions_entered: p.competitions_entered?.toString() ?? "",
    city: p.city ?? "", travel_radius_km: p.travel_radius_km?.toString() ?? "", days_per_week: p.days_per_week?.toString() ?? "",
    session_minutes: p.session_minutes?.toString() ?? "", other_commitments: p.other_commitments ?? "", goal: p.goal ?? "",
    avoid_exercises: (p.avoid_exercises ?? []) as string[], pain_flags: (p.pain_flags ?? []) as string[],
  });
  const [ok, setOk] = useState<string | null>(null);
  const [err, setErr] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: string, v: any) => setF((s) => ({ ...s, [k]: v }));
  const toggle = (k: "avoid_exercises" | "pain_flags", v: string) => set(k, f[k].includes(v) ? f[k].filter((x) => x !== v) : [...f[k], v]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setOk(null); setErr(null);
    try {
      await api("/athlete-profile", { method: "PUT", body: {
        display_name: f.display_name || null, body_weight_kg: numOrNull(f.body_weight_kg), age: numOrNull(f.age),
        division_category: f.division_category || null, experience_level: f.experience_level || null,
        competitions_entered: numOrNull(f.competitions_entered), city: f.city || null, travel_radius_km: numOrNull(f.travel_radius_km),
        days_per_week: numOrNull(f.days_per_week), session_minutes: numOrNull(f.session_minutes),
        other_commitments: f.other_commitments || null, goal: f.goal || null,
        avoid_exercises: f.avoid_exercises, pain_flags: f.pain_flags,
      } });
      setOk("Profile saved."); onSaved();
    } catch (x) { setErr(x as ApiError); } finally { setBusy(false); }
  };

  return (
    <Card title={`Athlete (${completeness}% complete)`}>
      <form onSubmit={submit} className="stack">
        <div className="row">
          <Field label="Display name (optional)"><input value={f.display_name} onChange={(e) => set("display_name", e.target.value)} /></Field>
          <Field label="Body weight (kg)"><input type="number" step="0.1" value={f.body_weight_kg} onChange={(e) => set("body_weight_kg", e.target.value)} /></Field>
          <Field label="Age"><input type="number" value={f.age} onChange={(e) => set("age", e.target.value)} /></Field>
          <Field label="Division category">
            <select value={f.division_category} onChange={(e) => set("division_category", e.target.value)}>
              <option value="">Not set</option><option value="men">Men</option><option value="women">Women</option><option value="open">Open</option>
            </select>
          </Field>
        </div>
        <div className="row">
          <Field label="Experience">
            <select value={f.experience_level} onChange={(e) => set("experience_level", e.target.value)}>
              <option value="">Not set</option><option value="novice">Novice</option><option value="intermediate">Intermediate</option>
            </select>
          </Field>
          <Field label="Competitions entered"><input type="number" min="0" value={f.competitions_entered} onChange={(e) => set("competitions_entered", e.target.value)} /></Field>
          <Field label="City (approximate)"><input value={f.city} onChange={(e) => set("city", e.target.value)} /></Field>
          <Field label="Travel radius (km)"><input type="number" min="0" value={f.travel_radius_km} onChange={(e) => set("travel_radius_km", e.target.value)} /></Field>
        </div>
        <div className="row">
          <Field label="Training days per week" hint="1–7"><input type="number" min="1" max="7" value={f.days_per_week} onChange={(e) => set("days_per_week", e.target.value)} /></Field>
          <Field label="Session length (minutes)" hint="15–240"><input type="number" min="15" max="240" value={f.session_minutes} onChange={(e) => set("session_minutes", e.target.value)} /></Field>
          <Field label="Goal">
            <select value={f.goal} onChange={(e) => set("goal", e.target.value)}>
              <option value="">Not set</option><option value="participate">Participate</option><option value="perform">Perform</option>
            </select>
          </Field>
        </div>
        <Field label="Other training commitments (optional)"><textarea rows={2} value={f.other_commitments} onChange={(e) => set("other_commitments", e.target.value)} /></Field>
        <fieldset>
          <legend className="field-label">Current pain flags (affected movements are paused and need professional review; no diagnosis is given)</legend>
          <div className="checks">
            {refData.body_areas.map((a) => (
              <label key={a} className="check"><input type="checkbox" checked={f.pain_flags.includes(a)} onChange={() => toggle("pain_flags", a)} />{a.replace("_", " ")}</label>
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend className="field-label">Exercises to avoid</legend>
          <div className="checks">
            {refData.templates.map((t) => (
              <label key={t.key} className="check"><input type="checkbox" checked={f.avoid_exercises.includes(t.key)} onChange={() => toggle("avoid_exercises", t.key)} />{t.name}</label>
            ))}
          </div>
        </fieldset>
        <Notice ok={ok} err={err} />
        <button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Save athlete"}</button>
      </form>
    </Card>
  );
}

function EquipmentForm({ refData, initial, onSaved }: { refData: Ref; initial: any[]; onSaved: () => void }) {
  const byImpl = Object.fromEntries(initial.map((e) => [e.implement, e]));
  const [rows, setRows] = useState(() =>
    refData.implements.map((i) => ({ implement: i.key, label: i.label, access: byImpl[i.key]?.access ?? "", max: byImpl[i.key]?.max_load_kg?.toString() ?? "", notes: byImpl[i.key]?.notes ?? "" })));
  const [ok, setOk] = useState<string | null>(null);
  const [err, setErr] = useState<ApiError | null>(null);
  const upd = (i: number, k: string, v: string) => setRows((r) => r.map((x, j) => (j === i ? { ...x, [k]: v } : x)));

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setOk(null); setErr(null);
    try {
      await api("/equipment", { method: "PUT", body: rows.filter((r) => r.access).map((r) => ({ implement: r.implement, access: r.access, max_load_kg: numOrNull(r.max), notes: r.notes || null })) });
      setOk("Equipment saved."); onSaved();
    } catch (x) { setErr(x as ApiError); }
  };

  return (
    <Card title="Equipment access">
      <p className="small muted">Leave “Not recorded” if you are unsure. “Occasional” means you have agreed access (e.g. a specialist gym) that the plan may schedule deliberately. “None” means plans will never require it.</p>
      <form onSubmit={submit} className="stack">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Implement</th><th>Access</th><th className="num">Max load (kg)</th><th>Notes</th></tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.implement}>
                  <td>{r.label}</td>
                  <td>
                    <select aria-label={`${r.label} access`} value={r.access} onChange={(e) => upd(i, "access", e.target.value)}>
                      <option value="">Not recorded</option><option value="regular">Regular</option><option value="occasional">Occasional</option><option value="none">None</option>
                    </select>
                  </td>
                  <td><input aria-label={`${r.label} max load`} type="number" min="0" disabled={!r.access || r.access === "none"} value={r.max} onChange={(e) => upd(i, "max", e.target.value)} /></td>
                  <td><input aria-label={`${r.label} notes`} value={r.notes} onChange={(e) => upd(i, "notes", e.target.value)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Notice ok={ok} err={err} />
        <button className="btn btn-primary">Save equipment</button>
      </form>
    </Card>
  );
}

function PerformanceSection({ refData, records, onChanged }: { refData: Ref; records: any[]; onChanged: () => void }) {
  const today = new Date().toISOString().slice(0, 10);
  const blank = { task_key: refData.tasks[0].key, load: "", per_hand: false, reps: "", distance: "", time: "", date: today, rpe: "", source: "self_reported", conditions: "" };
  const [f, setF] = useState(blank);
  const [err, setErr] = useState<ApiError | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const set = (k: string, v: any) => setF((s) => ({ ...s, [k]: v }));
  const label = (k: string) => refData.tasks.find((t) => t.key === k)?.label ?? k;

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setErr(null); setOk(null);
    try {
      await api("/performance-records", { method: "POST", body: {
        task_key: f.task_key, load_kg: numOrNull(f.load), load_per_hand: f.per_hand, reps: numOrNull(f.reps), distance_m: numOrNull(f.distance),
        time_s: numOrNull(f.time), record_date: f.date, effort_rpe: numOrNull(f.rpe), source_type: f.source, conditions: f.conditions || null } });
      setF(blank); setOk("Record added."); onChanged();
    } catch (x) { setErr(x as ApiError); }
  };
  const remove = async (id: number) => { await api(`/performance-records/${id}`, { method: "DELETE" }); onChanged(); };

  return (
    <Card title="Performance records">
      <p className="small muted">A one-rep max, a timed set and a competition result are separate records. Each record keeps its implement/task and whether it was self-reported, verified, or an official result. Records are never converted between implements.</p>
      <form onSubmit={submit} className="stack">
        <div className="row">
          <Field label="Exercise / event">
            <select value={f.task_key} onChange={(e) => set("task_key", e.target.value)}>{refData.tasks.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}</select>
          </Field>
          <Field label="Load (kg)"><input type="number" step="0.5" min="0" value={f.load} onChange={(e) => set("load", e.target.value)} /></Field>
          <Field label="Reps"><input type="number" min="1" value={f.reps} onChange={(e) => set("reps", e.target.value)} /></Field>
          <Field label="Distance (m)"><input type="number" step="0.5" min="0" value={f.distance} onChange={(e) => set("distance", e.target.value)} /></Field>
          <Field label="Time (s)"><input type="number" step="0.1" min="0" value={f.time} onChange={(e) => set("time", e.target.value)} /></Field>
        </div>
        <div className="row">
          <Field label="Date"><input type="date" max={today} value={f.date} onChange={(e) => set("date", e.target.value)} required /></Field>
          <Field label="Effort (RPE 1–10)"><input type="number" min="1" max="10" step="0.5" value={f.rpe} onChange={(e) => set("rpe", e.target.value)} /></Field>
          <Field label="Source">
            <select value={f.source} onChange={(e) => set("source", e.target.value)}>
              <option value="self_reported">Self-reported training</option><option value="verified_training">Verified training</option><option value="official_result">Official competition result</option>
            </select>
          </Field>
          <Field label="Conditions (optional)"><input value={f.conditions} onChange={(e) => set("conditions", e.target.value)} /></Field>
        </div>
        <label className="check"><input type="checkbox" checked={f.per_hand} onChange={(e) => set("per_hand", e.target.checked)} />Load is per hand (carries)</label>
        <Notice ok={ok} err={err} />
        <button className="btn btn-primary">Add record</button>
      </form>
      <h3>History</h3>
      {records.length === 0 ? <Empty title="No performance records yet" /> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Date</th><th>Exercise / event</th><th className="num">Load</th><th className="num">Reps</th><th className="num">Dist.</th><th className="num">Time</th><th>Source</th><th /></tr></thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id}>
                  <td>{fmtDate(r.record_date)}</td><td>{label(r.task_key)}</td><td className="num">{kg(r.load_kg, r.load_per_hand)}</td>
                  <td className="num">{r.reps ?? "—"}</td><td className="num">{r.distance_m ?? "—"}</td><td className="num">{r.time_s ?? "—"}</td>
                  <td>{r.source_type.replace("_", " ")}</td>
                  <td><button className="btn btn-small" onClick={() => remove(r.id)} aria-label={`Delete record ${r.id}`}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
