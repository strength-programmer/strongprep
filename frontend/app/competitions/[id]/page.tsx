"use client";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError, useApi } from "@/lib/api";
import { fmtDate, fmtVenueTime, kg, metres, numOrNull, seconds } from "@/lib/format";
import { Badge, Card, CompStatusBadge, DemoBadge, ErrorBox, Loading } from "@/components/ui";

export default function CompetitionDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: c, error, loading, reload } = useApi(`/competitions/${id}`);
  const router = useRouter();
  const [divId, setDivId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<ApiError | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  if (loading) return <Loading what="Loading competition" />;
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!c) return null;

  const div = c.divisions.find((d: any) => d.id === divId) ?? c.divisions[0];
  const editable = !c.is_shared_catalog;

  const setTarget = async () => {
    setBusy(true); setActionError(null); setMsg(null);
    try {
      await api("/athlete-profile/target", { method: "PUT", body: { competition_id: c.id, division_id: div.id } });
      setMsg(`Target set: ${c.title}, ${div.name}.`);
    } catch (e) { setActionError(e as ApiError); } finally { setBusy(false); }
  };
  const generate = async () => {
    setBusy(true); setActionError(null); setMsg(null);
    try {
      await api("/athlete-profile/target", { method: "PUT", body: { competition_id: c.id, division_id: div.id } });
      const a = await api("/assessments", { method: "POST", body: { competition_id: c.id, division_id: div.id } });
      router.push(`/assessments/${a.id}`);
    } catch (e) { setActionError(e as ApiError); setBusy(false); }
  };

  return (
    <>
      <h1>{c.title}</h1>
      <p>
        {c.is_demo && <DemoBadge label={c.demo_label} />} <CompStatusBadge status={c.status} />{" "}
        <Badge tone={c.verification_status === "verified" ? "good" : "warn"}>{c.verification_status === "fixture" ? "fixture data" : c.verification_status}</Badge>
      </p>
      {c.is_demo && <div className="alert alert-info">{c.demo_label}. Loads and rules below are invented for demonstration.</div>}
      {c.status !== "upcoming" && <div className="alert alert-warn">This competition is {c.status}; plans can only be generated for upcoming competitions.</div>}

      <Card title="Details">
        <div className="grid">
          <div><div className="field-label">Date</div>{fmtDate(c.start_date)}</div>
          <div><div className="field-label">Start time</div>{fmtVenueTime(c.start_time, c.timezone)}</div>
          <div><div className="field-label">Registration deadline</div>{fmtDate(c.registration_deadline)}</div>
          <div><div className="field-label">Venue / city</div>{[c.venue, c.city, c.country].filter(Boolean).join(", ") || "Unknown"}</div>
          <div><div className="field-label">Organizer</div>{c.organizer ?? "Unknown"}</div>
          <div><div className="field-label">Entry fee</div>{c.entry_fee != null ? `${c.entry_fee} ${c.fee_currency ?? ""}` : "Unknown"}</div>
          <div><div className="field-label">Last checked</div>{fmtDate(c.last_checked_at)} <span className="muted small">(last confirmed: {c.last_confirmed_at ? fmtDate(c.last_confirmed_at) : "never"})</span></div>
          <div><div className="field-label">Source</div>{c.source_url ?? "None"}</div>
        </div>
      </Card>

      <Card title="Division">
        <div className="tabs" role="tablist">
          {c.divisions.map((d: any) => (
            <button key={d.id} role="tab" aria-selected={d.id === div.id} className="tab" onClick={() => setDivId(d.id)}>{d.name}</button>
          ))}
        </div>
        <p className="small">
          Category: <strong>{div.category}</strong> · Body weight: {div.weight_min_kg != null || div.weight_max_kg != null ? `${div.weight_min_kg ?? "any"}–${div.weight_max_kg ?? "any"} kg (bounds inclusive)` : "no limit listed"} ·
          Age: {div.age_min != null || div.age_max != null ? `${div.age_min ?? "any"}–${div.age_max ?? "any"}` : "no limit listed"} · Spec version {div.spec_version}
        </p>
        {div.eligibility_notes && <div className="alert alert-warn">Entry requirement to confirm: {div.eligibility_notes}</div>}

        <h3>Event requirements</h3>
        {div.events.length === 0 ? <p className="muted">No events recorded for this division.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>#</th><th>Event</th><th>Implement / task</th><th>Scoring</th><th className="num">Load</th><th className="num">Time limit</th><th className="num">Distance</th><th>Status</th>{editable && <th />}</tr></thead>
              <tbody>
                {div.events.map((e: any, i: number) => <EventRow key={`${e.id}-${e.version}`} i={i} e={e} editable={editable} onSaved={reload} />)}
              </tbody>
            </table>
          </div>
        )}
        <h3>Sources</h3>
        {[...div.events.flatMap((e: any) => e.evidence.map((x: any) => ({ ...x, event: e.name }))), ...c.evidence.map((x: any) => ({ ...x, event: "Competition" }))].map((x: any) => (
          <p key={`${x.entity_type}-${x.id}`} className="small"><strong>{x.event}</strong> ({x.field_name}) · <Badge>{x.review_status}</Badge> · {x.url ?? "no URL"}<br /><span className="muted">“{x.excerpt}”</span></p>
        ))}
        <ErrorBox error={actionError} />
        {msg && <div className="alert alert-ok" role="status">{msg}</div>}
        <div className="row" style={{ marginTop: "1rem" }}>
          <button className="btn" disabled={busy} onClick={setTarget}>Set as target</button>
          <button className="btn btn-primary" disabled={busy} onClick={generate}>{busy ? "Working…" : "Set target and generate gap report"}</button>
        </div>
      </Card>
    </>
  );
}

function EventRow({ e, i, editable, onSaved }: { e: any; i: number; editable: boolean; onSaved: () => void }) {
  const [editing, setEditing] = useState(false);
  const [f, setF] = useState({ load: e.load_kg?.toString() ?? "", time: e.time_limit_s?.toString() ?? "", dist: e.distance_m?.toString() ?? "" });
  const [err, setErr] = useState<ApiError | null>(null);

  const save = async () => {
    setErr(null);
    try {
      await api(`/events/${e.id}`, { method: "PUT", body: {
        name: e.name, task_key: e.task_key, scoring_type: e.scoring_type, load_kg: numOrNull(f.load), load_per_hand: e.load_per_hand,
        original_load_text: e.original_load_text, original_unit: e.original_unit, time_limit_s: numOrNull(f.time), distance_m: numOrNull(f.dist), rules_text: e.rules_text } });
      setEditing(false); onSaved();
    } catch (x) { setErr(x as ApiError); }
  };

  return (
    <>
      <tr>
        <td>{i + 1}</td>
        <td><strong>{e.name}</strong>{e.rules_text && <div className="small muted">{e.rules_text}</div>}</td>
        <td>{e.task_label}</td>
        <td>{e.scoring_type.replace("_", " ")}</td>
        <td className="num">
          {editing ? <input aria-label="Load kg" type="number" value={f.load} onChange={(x) => setF({ ...f, load: x.target.value })} /> : (
            <>{kg(e.load_kg, e.load_per_hand)}{e.original_load_text && <div className="small muted">as published: {e.original_load_text}</div>}{e.load_kg == null && <Badge tone="warn">load unknown</Badge>}</>
          )}
        </td>
        <td className="num">{editing ? <input aria-label="Time limit s" type="number" value={f.time} onChange={(x) => setF({ ...f, time: x.target.value })} /> : seconds(e.time_limit_s)}</td>
        <td className="num">{editing ? <input aria-label="Distance m" type="number" value={f.dist} onChange={(x) => setF({ ...f, dist: x.target.value })} /> : metres(e.distance_m)}</td>
        <td><Badge tone={e.verification_status === "verified" ? "good" : "warn"}>{e.verification_status.replace("_", " ")}</Badge> <span className="small muted">v{e.version}</span></td>
        {editable && (
          <td>
            {editing ? (<><button className="btn btn-small btn-primary" onClick={save}>Save</button> <button className="btn btn-small" onClick={() => setEditing(false)}>Cancel</button></>) : (
              <button className="btn btn-small" onClick={() => setEditing(true)}>Edit</button>)}
          </td>
        )}
      </tr>
      {err && <tr><td colSpan={9}><ErrorBox error={err} /></td></tr>}
    </>
  );
}
