"use client";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { getSupabase, supabaseConfigured } from "@/lib/supabase";
import { Card, ErrorBox } from "@/components/ui";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!supabaseConfigured) {
    return (
      <Card title="Sign in">
        <p>Sign-in is only used in live mode. In the local demo, the app uses a fixed demo identity and needs no account.</p>
        <p className="small muted">To enable live mode, set the Supabase values in <code>frontend/.env.local</code> and <code>APP_MODE=live</code> on the backend.</p>
      </Card>
    );
  }

  const submit = async (e: FormEvent, mode: "in" | "up") => {
    e.preventDefault();
    setBusy(true); setErr(null);
    const sb = getSupabase()!;
    const { error } = mode === "in" ? await sb.auth.signInWithPassword({ email, password }) : await sb.auth.signUp({ email, password });
    setBusy(false);
    if (error) return setErr(error.message);
    router.replace("/");
    router.refresh();
  };

  return (
    <Card title="Sign in to StrongPrep">
      <form className="stack" onSubmit={(e) => submit(e, "in")}>
        <label className="field"><span className="field-label">Email</span><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
        <label className="field"><span className="field-label">Password</span><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} /></label>
        <ErrorBox error={err} />
        <div className="row">
          <button className="btn btn-primary" disabled={busy}>Sign in</button>
          <button type="button" className="btn" disabled={busy} onClick={(e) => submit(e as any, "up")}>Create account</button>
        </div>
      </form>
    </Card>
  );
}
