"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api, ApiError, useApi } from "@/lib/api";
import { fmtDate, numOrNull } from "@/lib/format";
import { Card, CompStatusBadge, DemoBadge, Badge, Empty, ErrorBox, Field, Loading } from "@/components/ui";

export default function Competitions() {
  const [filters, setFilters] = useState({ q: "", city: "", date_from: "", date_to: "", status: "" });
  const [applied, setApplied] = useState(filters);
  const qs = new URLSearchParams(Object.entries(applied).filter(([, v]) => v)).toString();
  const { data, error, loading, reload } = useApi<any[]>(`/competitions${qs ? `?${qs}` : ""}`);
  const set = (k: string, v: string) => setFilters((f) => ({ ...f, [k]: v }));

  return (
    <>
      <h1>Competitions</h1>
      <p className="muted">The seeded catalog is entirely fictional. Add your own competition manually to work with real requirements.</p>
      <Card title="Filter">
        <form className="row" onSubmit={(e) => { e.preventDefault(); setApplied(filters); }}>
          <Field label="Name contains"><input value={filters.q} onChange={(e) => set("q", e.target.value)} /></Field>
          <Field label="City"><input value={filters.city} onChange={(e) => set("city", e.target.value)} /></Field>
          <Field label="From"><input type="date" value={filters.date_from} onChange={(e) => set("date_from", e.target.value)} /></Field>
          <Field label="To"><input type="date" value={filters.date_to} onChange={(e) => set("date_to", e.target.value)} /></Field>
          <Field label="Status">
            <select value={filters.status} onChange={(e) => set("status", e.target.value)}>
              <option value="">Any</option><option value="upcoming">Upcoming</option><option value="canceled">Canceled</option><option value="completed">Completed</option>
            </select>
          </Field>
          <button className="btn btn-primary">Apply</button>
        </form>
        <p className="small muted">Distance is not calculated: location filtering is by city text only, and travel time is not estimated.</p>
      </Card>

      {loading ? <Loading what="Loading competitions" /> : error ? <ErrorBox error={error} onRetry={reload} /> : !data || data.length === 0 ? (
        <Empty title="No competitions match these filters">Clear the filters or add one manually below.</Empty>
      ) : (
        <div className="table-wrap card">
          <table>
            <thead><tr><th>Competition</th><th>Date</th><th>Location</th><th>Status</th><th>Divisions</th><th>Entry fee</th></tr></thead>
            <tbody>
              {data.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link href={`/competitions/${c.id}`}><strong>{c.title}</strong></Link><br />
                    {c.is_demo && <DemoBadge label={c.demo_label} />}
                    {!c.is_shared_catalog && <Badge tone="info">Your entry</Badge>}
                    {c.verification_status !== "verified" && <Badge tone="warn">{c.verification_status === "fixture" ? "Fixture" : "Unverified"}</Badge>}
                  </td>
                  <td>{fmtDate(c.start_date)}</td>
                  <td>{[c.city, c.country].filter(Boolean).join(", ") || "—"}</td>
                  <td><CompStatusBadge status={c.status} /></td>
                  <td>{c.divisions.map((d: any) => d.name).join("; ")}</td>
                  <td>{c.entry_fee != null ? `${c.entry_fee} ${c.fee_currency ?? ""}` : "Unknown"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <ManualEntry onCreated={reload} />
    </>
  );
}

const SCORING = ["max_load", "reps", "time", "distance", "custom"];

function ManualEntry({ onCreated }: { onCreated: () => void }) {
  const ref = useApi<any>("/reference");
  const router = useRouter();
  const [f, setF] = useState({ title: "", organizer: "", city: "", start_date: "", source_url: "", div_name: "Open", category: "open", wmin: "", wmax: "", amin: "", amax: "", notes: "" });
  const [events, setEvents] = useState([{ name: "", task_key: "deadlift_barbell", scoring_type: "max_load", load: "", per_hand: false, unit: "kg", time: "", dist: "", rules: "" }]);
  const [err, setErr] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: string, v: string) => setF((s) => ({ ...s, [k]: v }));
  const setEv = (i: number, k: string, v: any) => setEvents((e) => e.map((x, j) => (j === i ? { ...x, [k]: v } : x)));

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try {
      const c = await api("/competitions", { method: "POST", body: {
        title: f.title, organizer: f.organizer || null, city: f.city || null, start_date: f.start_date, source_url: f.source_url || null,
        divisions: [{
          name: f.div_name, category: f.category, weight_min_kg: numOrNull(f.wmin), weight_max_kg: numOrNull(f.wmax), age_min: numOrNull(f.amin), age_max: numOrNull(f.amax),
          eligibility_notes: f.notes || null, needs_manual_confirmation: Boolean(f.notes),
          events: events.filter((x) => x.name).map((x) => {
            const raw = numOrNull(x.load);
            // Never guess units: pounds are converted explicitly and the original text is preserved.
            const loadKg = raw == null ? null : x.unit === "lb" ? Math.round((raw / 2.20462262185) * 10) / 10 : raw;
            return { name: x.name, task_key: x.task_key, scoring_type: x.scoring_type, load_kg: loadKg, load_per_hand: x.per_hand,
              original_load_text: raw == null ? null : `${raw} ${x.unit}${x.per_hand ? " per hand" : ""}`, original_unit: raw == null ? null : x.unit,
              time_limit_s: numOrNull(x.time), distance_m: numOrNull(x.dist), rules_text: x.rules || null };
          }),
        }],
      } });
      onCreated(); router.push(`/competitions/${c.id}`);
    } catch (x) { setErr(x as ApiError); setBusy(false); }
  };

  return (
    <Card title="Add a competition manually">
      <details>
        <summary>Open the entry form</summary>
        <form className="stack" onSubmit={submit}>
          <div className="row">
            <Field label="Title"><input required value={f.title} onChange={(e) => set("title", e.target.value)} /></Field>
            <Field label="Date"><input required type="date" value={f.start_date} onChange={(e) => set("start_date", e.target.value)} /></Field>
            <Field label="City"><input value={f.city} onChange={(e) => set("city", e.target.value)} /></Field>
            <Field label="Organizer"><input value={f.organizer} onChange={(e) => set("organizer", e.target.value)} /></Field>
          </div>
          <Field label="Source URL (where you found these rules)"><input value={f.source_url} onChange={(e) => set("source_url", e.target.value)} /></Field>
          <h3>Division</h3>
          <div className="row">
            <Field label="Division name"><input required value={f.div_name} onChange={(e) => set("div_name", e.target.value)} /></Field>
            <Field label="Category">
              <select value={f.category} onChange={(e) => set("category", e.target.value)}><option value="open">Open</option><option value="men">Men</option><option value="women">Women</option></select>
            </Field>
            <Field label="Min body weight (kg)"><input type="number" value={f.wmin} onChange={(e) => set("wmin", e.target.value)} /></Field>
            <Field label="Max body weight (kg)"><input type="number" value={f.wmax} onChange={(e) => set("wmax", e.target.value)} /></Field>
            <Field label="Min age"><input type="number" value={f.amin} onChange={(e) => set("amin", e.target.value)} /></Field>
            <Field label="Max age"><input type="number" value={f.amax} onChange={(e) => set("amax", e.target.value)} /></Field>
          </div>
          <Field label="Other entry requirements (flags the division as 'needs confirmation')"><input value={f.notes} onChange={(e) => set("notes", e.target.value)} /></Field>
          <h3>Events</h3>
          {events.map((x, i) => (
            <div key={i} className="card">
              <div className="row">
                <Field label="Event name"><input value={x.name} onChange={(e) => setEv(i, "name", e.target.value)} /></Field>
                <Field label="Task / implement">
                  <select value={x.task_key} onChange={(e) => setEv(i, "task_key", e.target.value)}>{ref.data?.tasks.map((t: any) => <option key={t.key} value={t.key}>{t.label}</option>)}</select>
                </Field>
                <Field label="Scoring"><select value={x.scoring_type} onChange={(e) => setEv(i, "scoring_type", e.target.value)}>{SCORING.map((s) => <option key={s}>{s}</option>)}</select></Field>
              </div>
              <div className="row">
                <Field label="Load as published"><input type="number" step="0.5" value={x.load} onChange={(e) => setEv(i, "load", e.target.value)} /></Field>
                <Field label="Unit" hint="Pick explicitly. Unlabeled weights are never assumed."><select value={x.unit} onChange={(e) => setEv(i, "unit", e.target.value)}><option value="kg">kg</option><option value="lb">lb (converted)</option></select></Field>
                <Field label="Time limit (s)"><input type="number" value={x.time} onChange={(e) => setEv(i, "time", e.target.value)} /></Field>
                <Field label="Distance (m)"><input type="number" value={x.dist} onChange={(e) => setEv(i, "dist", e.target.value)} /></Field>
              </div>
              <label className="check"><input type="checkbox" checked={x.per_hand} onChange={(e) => setEv(i, "per_hand", e.target.checked)} />Load is per hand</label>
              <Field label="Rules (as written)"><input value={x.rules} onChange={(e) => setEv(i, "rules", e.target.value)} /></Field>
            </div>
          ))}
          <button type="button" className="btn btn-small" onClick={() => setEvents((e) => [...e, { ...e[0], name: "", load: "", time: "", dist: "", rules: "" }])}>Add another event</button>
          <ErrorBox error={err} />
          <div><button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Save competition"}</button></div>
        </form>
      </details>
    </Card>
  );
}
