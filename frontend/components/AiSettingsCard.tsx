"use client";
import { FormEvent, useState } from "react";
import { api, ApiError, useApi } from "@/lib/api";
import { Badge, Card, ErrorBox, Field, Loading } from "@/components/ui";

type View = { insecure_http: boolean; source: string; provider: string; base_url: string | null; model: string | null; key_configured: boolean; key_last4: string | null; available: boolean; detail: string | null };

const PROVIDERS = [
  { id: "mock", label: "Mock AI (no key, deterministic demo output)" },
  { id: "claude", label: "Claude (Anthropic API key)" },
  { id: "openai_compatible", label: "Qwen / other OpenAI-compatible endpoint" },
];

type Msg = { ok: boolean; text: string } | null;

export default function AiSettingsCard({ onChanged }: { onChanged?: () => void }) {
  const { data, error, loading, reload } = useApi<View>("/ai-settings");
  // Held here (not in Form) because Form remounts after every save/reload, which would wipe the message.
  const [msg, setMsg] = useState<Msg>(null);
  if (loading && !data) return <Loading what="Loading AI settings" />;
  if (error && !data) return <ErrorBox error={error} onRetry={reload} />;
  if (!data) return null;
  return <Form key={`${data.provider}-${data.key_last4}-${data.model}-${data.base_url}`} view={data} msg={msg} setMsg={setMsg} reload={() => { reload(); onChanged?.(); }} />;
}

function Form({ view, reload, msg, setMsg }: { view: View; reload: () => void; msg: Msg; setMsg: (m: Msg) => void }) {
  const [provider, setProvider] = useState(view.provider);
  const [baseUrl, setBaseUrl] = useState(view.base_url ?? "");
  const [model, setModel] = useState(view.model ?? "");
  const [apiKey, setApiKey] = useState("");
  const [allowInsecure, setAllowInsecure] = useState(view.insecure_http);
  const insecureUrl = provider === "openai_compatible" && /^http:\/\//i.test(baseUrl.trim()) && !/^http:\/\/(localhost|127\.0\.0\.1|\[::1\])([:/]|$)/i.test(baseUrl.trim());
  const [err, setErr] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const sameProvider = provider === view.provider;
  const keyStored = view.key_configured && sameProvider && view.source === "app";

  const save = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null); setMsg(null);
    try {
      await api("/ai-settings", { method: "PUT", body: {
        provider, base_url: provider === "openai_compatible" ? baseUrl : null, model: provider === "mock" ? null : model, api_key: apiKey || null,
        allow_insecure_http: insecureUrl && allowInsecure } });
      setApiKey(""); setMsg({ ok: true, text: "Saved. Your key is stored encrypted on the backend and is never shown again." }); reload();
    } catch (x) { setErr(x as ApiError); } finally { setBusy(false); }
  };
  const test = async () => {
    setBusy(true); setErr(null); setMsg(null);
    try { const r = await api("/ai-settings/test", { method: "POST" }); setMsg({ ok: r.ok, text: r.message }); } catch (x) { setErr(x as ApiError); } finally { setBusy(false); }
  };
  const remove = async () => {
    if (!confirm("Remove your saved AI settings and key? The app will go back to the default.")) return;
    setBusy(true); setErr(null); setMsg(null);
    try { await api("/ai-settings", { method: "DELETE" }); setMsg({ ok: true, text: "Saved AI settings removed. The app is back to its default." }); reload(); } catch (x) { setErr(x as ApiError); } finally { setBusy(false); }
  };

  return (
    <Card title="AI assistant" actions={
      view.available ? <Badge tone={view.provider === "mock" ? "demo" : "good"}>{view.provider === "mock" ? "Mock AI active" : "Key saved (use Test connection)"}</Badge> : <Badge tone="bad">Unavailable</Badge>}>
      <p className="small muted">
        The AI writes your preparation plan. The app still checks every plan against your equipment, schedule and safety rules before showing it, so a model cannot slip in unavailable equipment.
        {view.source === "env" && " Currently using the backend's environment settings."}
      </p>
      {view.insecure_http && <p><Badge tone="warn">unencrypted http</Badge></p>}
      {view.detail && !view.available && <div className="alert alert-warn">{view.detail}</div>}
      <form className="stack" onSubmit={save} autoComplete="off">
        <Field label="Provider">
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            {PROVIDERS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
        </Field>
        {provider !== "mock" && (
          <>
            {provider === "openai_compatible" && (
              <Field label="Base URL" hint="For Qwen on Alibaba DashScope this ends in /compatible-mode/v1. Use https where you can. Plain http is allowed in the demo only with your explicit opt-in (localhost needs none).">
                <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://…/compatible-mode/v1" required />
              </Field>
            )}
            {insecureUrl && (
              <div className="alert alert-warn" role="note">
                <strong>This address uses plain http.</strong> Your API key would be sent unencrypted to this server, so only use it on a network you trust (for example your own proxy).
                <label className="check"><input type="checkbox" checked={allowInsecure} onChange={(e) => setAllowInsecure(e.target.checked)} />Allow unencrypted http for this provider</label>
              </div>
            )}
            <Field label="Model name" hint="Use the exact model id from your provider's docs.">
              <input value={model} onChange={(e) => setModel(e.target.value)} required />
            </Field>
            <Field label="API key" hint={keyStored ? `A key ending in …${view.key_last4} is saved. Leave blank to keep it, or paste a new one to replace it.` : "Stored encrypted on the backend. It is sent only to the provider, never back to this page."}>
              <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} autoComplete="new-password" spellCheck={false}
                placeholder={keyStored ? `•••• ${view.key_last4}` : "paste key"} required={!keyStored} />
            </Field>
          </>
        )}
        {msg && <div className={`alert ${msg.ok ? "alert-ok" : "alert-error"}`} role="status">{msg.text}</div>}
        <ErrorBox error={err} />
        <div className="row">
          <button className="btn btn-primary" disabled={busy}>{busy ? "Working…" : "Save"}</button>
          <button type="button" className="btn" onClick={test} disabled={busy}>Test connection</button>
          {view.source === "app" && <button type="button" className="btn" onClick={remove} disabled={busy}>Remove saved key</button>}
        </div>
        <p className="small muted">“Test connection” makes one tiny request to your provider, which may use a few tokens.</p>
      </form>
    </Card>
  );
}
