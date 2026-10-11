"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, apiFull, ApiError, useApi } from "@/lib/api";
import { fmtDate, fmtVenueTime, numOrNull } from "@/lib/format";
import { Card, CompStatusBadge, DemoBadge, Badge, Empty, ErrorBox, Field, Loading } from "@/components/ui";

export default function Competitions() {
  const [filters, setFilters] = useState({ q: "", city: "", date_from: "", date_to: "", status: "", nearby: "" });
  const [applied, setApplied] = useState(filters);
  const me = useApi<any>("/athlete-profile");
  const radius: number | null = me.data?.profile?.travel_radius_km ?? null;
  const hasLocation = me.data?.profile?.approx_lat != null;
  const { nearby, ...plain } = applied;
  const qs = new URLSearchParams({ ...Object.fromEntries(Object.entries(plain).filter(([, v]) => v)), ...(nearby && radius ? { within_km: String(radius) } : {}) }).toString();
  const [data, setData] = useState<any[] | null>(null);
  const [hidden, setHidden] = useState<number | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const r = await apiFull<any[]>(`/competitions${qs ? `?${qs}` : ""}`);
      setData(r.data);
      const h = r.headers.get("X-Unknown-Distance-Count");
      setHidden(h == null ? null : Number(h));
    } catch (e) { setError(e as ApiError); } finally { setLoading(false); }
  }, [qs]);
  useEffect(() => { reload(); }, [reload]);
  const set = (k: string, v: string) => setFilters((f) => ({ ...f, [k]: v }));

  return (
    <>
      <div className="page-head">
        <h1>Competitions</h1>
        <p>Pick the show you are preparing for. The seeded catalog is entirely fictional; add your own competition below to work with real requirements.</p>
      </div>
      <details open={Boolean(qs)}>
        <summary>Filter competitions{qs ? " (active)" : ""}</summary>
        <form className="row" style={{ marginTop: ".6rem" }} onSubmit={(e) => { e.preventDefault(); setApplied(filters); }}>
          <Field label="Name contains"><input value={filters.q} onChange={(e) => set("q", e.target.value)} /></Field>
          <Field label="City"><input value={filters.city} onChange={(e) => set("city", e.target.value)} /></Field>
          <Field label="From"><input type="date" value={filters.date_from} onChange={(e) => set("date_from", e.target.value)} /></Field>
          <Field label="To"><input type="date" value={filters.date_to} onChange={(e) => set("date_to", e.target.value)} /></Field>
          <Field label="Status">
            <select value={filters.status} onChange={(e) => set("status", e.target.value)}>
              <option value="">Any</option><option value="upcoming">Upcoming</option><option value="canceled">Canceled</option><option value="completed">Completed</option>
            </select>
          </Field>
          <label className="check" style={{ flexBasis: "100%" }}>
            <input type="checkbox" checked={Boolean(filters.nearby)} disabled={!radius} onChange={(e) => set("nearby", e.target.checked ? "1" : "")} />
            Only within my travel radius{radius ? ` (${radius} km, straight-line)` : " (set a travel radius in your profile first)"}
          </label>
          <button className="btn btn-primary">Apply</button>
          <button type="button" className="btn" onClick={() => { const empty = { q: "", city: "", date_from: "", date_to: "", status: "", nearby: "" }; setFilters(empty); setApplied(empty); }}>Clear</button>
        </form>
        <p className="small muted">Distances are straight-line estimates from your approximate location, not driving or travel time. {hasLocation ? "" : <>Add an approximate location in <Link href="/profile">your profile</Link> to see them.</>}</p>
      </details>

      {hidden != null && hidden > 0 && (
        <div className="alert alert-info" role="status">
          {hidden} competition{hidden === 1 ? " has" : "s have"} no recorded location, so the distance filter cannot judge {hidden === 1 ? "it" : "them"} and {hidden === 1 ? "it is" : "they are"} hidden. Clear the filter to see {hidden === 1 ? "it" : "them"}.
        </div>
      )}
      {loading && !data ? <Loading what="Loading competitions" /> : error ? <ErrorBox error={error} onRetry={reload} /> : !data || data.length === 0 ? (
        <Empty title="No competitions match these filters">Clear the filters or add one manually below.</Empty>
      ) : (
        <div className="list" style={{ marginTop: "1rem" }}>
          {[...data].sort((a, b) => (a.status === "upcoming" ? 0 : 1) - (b.status === "upcoming" ? 0 : 1) || a.start_date.localeCompare(b.start_date)).map((c) => {
            const [y, m, dd] = c.start_date.split("-").map(Number);
            const dt = new Date(y, m - 1, dd);
            const days = Math.round((dt.getTime() - new Date().setHours(0, 0, 0, 0)) / 86400000);
            return (
              <article key={c.id} className="comp" style={c.status !== "upcoming" ? { opacity: 0.75 } : undefined}>
                <div className="datebox" aria-hidden>
                  <span className="d">{dd}</span>
                  <span className="m">{dt.toLocaleString(undefined, { month: "short" })} {y}</span>
                </div>
                <div>
                  <Link href={`/competitions/${c.id}`} className="title">{c.title}</Link>
                  <div className="small muted">{[c.city, c.country].filter(Boolean).join(", ") || "Location unknown"} · {fmtVenueTime(c.start_time, c.timezone)} · {c.divisions.map((d: any) => d.name).join(" · ")}</div>
                  <div>
                    <CompStatusBadge status={c.status} />
                    {c.status === "upcoming" && days >= 0 && <Badge tone="info">{days} days away</Badge>}
                    {c.approx_distance_km != null && <Badge tone="neutral">~{c.approx_distance_km} km straight-line, not driving time</Badge>}
                    {c.is_demo && <DemoBadge label={c.demo_label} />}
                    {!c.is_shared_catalog && <Badge tone="info">Your entry</Badge>}
                    {c.verification_status !== "verified" && <Badge tone="warn">{c.verification_status === "fixture" ? "Fixture data" : "Unverified"}</Badge>}
                    <span className="small muted"> Fee: {c.entry_fee != null ? `${c.entry_fee} ${c.fee_currency ?? ""}` : "unknown"}</span>
                  </div>
                </div>
                <Link href={`/competitions/${c.id}`} className="btn btn-primary">View events</Link>
              </article>
            );
          })}
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
  const [f, setF] = useState({ title: "", organizer: "", city: "", start_date: "", start_time: "", timezone: "", latitude: "", longitude: "", source_url: "", div_name: "Open", category: "open", wmin: "", wmax: "", amin: "", amax: "", notes: "" });
  const [events, setEvents] = useState([{ name: "", task_key: "deadlift_barbell", scoring_type: "max_load", load: "", per_hand: false, unit: "kg", time: "", dist: "", rules: "" }]);
  const [err, setErr] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  // Filled after mount: Node and the browser list different zones, so computing this during render
  // would not match the server-rendered HTML (React hydration error).
  const [zones, setZones] = useState<string[]>([]);
  useEffect(() => {
    try { setZones((Intl as any).supportedValuesOf("timeZone") as string[]); } catch { setZones(["Asia/Manila", "UTC"]); }
  }, []);
  const set = (k: string, v: string) => setF((s) => ({ ...s, [k]: v }));
  const setEv = (i: number, k: string, v: any) => setEvents((e) => e.map((x, j) => (j === i ? { ...x, [k]: v } : x)));

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try {
      const c = await api("/competitions", { method: "POST", body: {
        title: f.title, organizer: f.organizer || null, city: f.city || null, start_date: f.start_date, start_time: f.start_time || null, timezone: f.timezone || null, latitude: numOrNull(f.latitude), longitude: numOrNull(f.longitude), source_url: f.source_url || null,
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
            <Field label="Date (venue local)"><input required type="date" value={f.start_date} onChange={(e) => set("start_date", e.target.value)} /></Field>
            <Field label="Start time (optional)" hint="Leave blank if not published."><input type="time" value={f.start_time} onChange={(e) => set("start_time", e.target.value)} /></Field>
            <Field label="Time zone" hint="Required with a start time, e.g. Asia/Manila.">
              <input list="tz-list" value={f.timezone} onChange={(e) => set("timezone", e.target.value)} placeholder="Asia/Manila" required={Boolean(f.start_time)} />
              <datalist id="tz-list">{zones.map((z) => <option key={z} value={z} />)}</datalist>
            </Field>
            <Field label="City"><input value={f.city} onChange={(e) => set("city", e.target.value)} /></Field>
            <Field label="Organizer"><input value={f.organizer} onChange={(e) => set("organizer", e.target.value)} /></Field>
          </div>
          <div className="row">
            <Field label="Venue latitude (optional)" hint="Approximate is fine. Enter both or neither."><input type="number" step="0.01" min="-90" max="90" value={f.latitude} onChange={(e) => set("latitude", e.target.value)} /></Field>
            <Field label="Venue longitude (optional)"><input type="number" step="0.01" min="-180" max="180" value={f.longitude} onChange={(e) => set("longitude", e.target.value)} /></Field>
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
