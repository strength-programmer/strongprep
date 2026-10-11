"use client";
import { useState } from "react";
import { api, API_BASE, ApiError, useApi } from "@/lib/api";
import { Badge, Card, ErrorBox, Loading } from "@/components/ui";

export default function Settings() {
  const { data, error, loading, reload } = useApi("/status");
  const [err, setErr] = useState<ApiError | null>(null);
  const [done, setDone] = useState<string | null>(null);

  if (loading) return <Loading />;
  if (error) return <ErrorBox error={error} onRetry={reload} />;

  const exportData = async () => {
    setErr(null);
    try {
      const d = await api("/export");
      const url = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: "application/json" }));
      const a = document.createElement("a");
      a.href = url; a.download = "strongprep-export.json"; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { setErr(e as ApiError); }
  };
  const wipe = async () => {
    if (!confirm("Delete your profile, equipment, records, assessments, plans, logs and manually added competitions? This cannot be undone.")) return;
    setErr(null);
    try { await api("/my-data", { method: "DELETE" }); setDone("Your private data was deleted."); } catch (e) { setErr(e as ApiError); }
  };

  return (
    <>
      <h1>Settings and diagnostics</h1>
      <Card title="Integration status">
        <table>
          <tbody>
            <tr><th>Mode</th><td><Badge tone={data.mode === "demo" ? "demo" : "info"}>{data.mode}</Badge></td></tr>
            <tr><th>Backend</th><td>{API_BASE}</td></tr>
            <tr><th>AI provider</th><td>{data.ai.provider} — {data.ai.available ? <Badge tone="good">available</Badge> : <Badge tone="bad">unavailable</Badge>} <span className="small muted">{data.ai.detail ?? data.ai.model ?? ""}</span></td></tr>
            <tr><th>Tavily search</th><td>mock only (live adapter is a later milestone){data.integrations.tavily.configured && " · key present but unused"}</td></tr>
            <tr><th>Firecrawl extraction</th><td>mock only (live adapter is a later milestone){data.integrations.firecrawl.configured && " · key present but unused"}</td></tr>
          </tbody>
        </table>
      </Card>
      <Card title="Your data">
        <p className="small muted">Export or delete everything private to your account.</p>
        <ErrorBox error={err} />
        {done && <div className="alert alert-ok" role="status">{done}</div>}
        <div className="row">
          <button className="btn" onClick={exportData}>Export my data (JSON)</button>
          <button className="btn" onClick={wipe}>Delete my data</button>
        </div>
      </Card>
    </>
  );
}
