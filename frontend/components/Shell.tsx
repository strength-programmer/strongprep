"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { getAccessToken, getSupabase, supabaseConfigured } from "@/lib/supabase";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/profile", label: "Profile" },
  { href: "/competitions", label: "Competitions" },
  { href: "/training", label: "Training" },
  { href: "/settings", label: "Settings" },
];

export default function Shell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [mode, setMode] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [backendDown, setBackendDown] = useState(false);
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    api("/status")
      .then((s) => {
        setMode(s.mode);
        setNotice(s.demo_notice);
      })
      .catch(() => setBackendDown(true));
    getAccessToken().then((t) => setAuthed(Boolean(t)));
  }, []);

  // Live mode: no session means no access. Never fall back to anything else.
  useEffect(() => {
    if (mode === "live" && authed === false && path !== "/login") router.replace("/login");
  }, [mode, authed, path, router]);

  const signOut = async () => {
    await getSupabase()?.auth.signOut();
    router.replace("/login");
  };

  return (
    <>
      {notice && (
        <div className="demo-banner" role="note">
          <strong>Local demo.</strong> {notice}
        </div>
      )}
      <header className="topbar">
        <Link href="/" className="brand">
          StrongPrep
        </Link>
        <nav aria-label="Main">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className={path === n.href || (n.href !== "/" && path.startsWith(n.href)) ? "active" : ""}>
              {n.label}
            </Link>
          ))}
        </nav>
        {mode === "live" && supabaseConfigured && authed && (
          <button className="btn btn-small" onClick={signOut}>
            Sign out
          </button>
        )}
      </header>
      <main className="container">
        {backendDown && (
          <div className="alert alert-error" role="alert">
            <strong>The backend is not reachable.</strong> Start it in a separate terminal (see README), then reload this page.
          </div>
        )}
        {children}
      </main>
    </>
  );
}
