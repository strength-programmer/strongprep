"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { getAccessToken, getSupabase, supabaseConfigured } from "@/lib/supabase";

const ICONS: Record<string, ReactNode> = {
  home: <path d="M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10" />,
  user: <path d="M12 12a4 4 0 100-8 4 4 0 000 8zM4 21c0-4 4-6 8-6s8 2 8 6" />,
  trophy: <path d="M8 4h8v5a4 4 0 01-8 0V4zM8 6H4v1a4 4 0 004 4M16 6h4v1a4 4 0 01-4 4M12 13v4M8 21h8M10 17h4" />,
  dumbbell: <path d="M3 9v6M6 6v12M18 6v12M21 9v6M6 12h12" />,
  gear: <path d="M12 15a3 3 0 100-6 3 3 0 000 6zM19 12a7 7 0 00-.1-1.3l2-1.5-2-3.4-2.3 1a7 7 0 00-2.3-1.3L14 3h-4l-.3 2.5a7 7 0 00-2.3 1.3l-2.3-1-2 3.4 2 1.5A7 7 0 005 12c0 .4 0 .9.1 1.3l-2 1.5 2 3.4 2.3-1a7 7 0 002.3 1.3L10 21h4l.3-2.5a7 7 0 002.3-1.3l2.3 1 2-3.4-2-1.5c.1-.4.1-.9.1-1.3z" />,
};

const NAV = [
  { href: "/", label: "Home", icon: "home" },
  { href: "/profile", label: "Profile", icon: "user" },
  { href: "/competitions", label: "Compete", icon: "trophy" },
  { href: "/training", label: "Train", icon: "dumbbell" },
  { href: "/settings", label: "Settings", icon: "gear" },
];

export default function Shell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [mode, setMode] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [ai, setAi] = useState<string>("");
  const [backendDown, setBackendDown] = useState(false);
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    api("/status")
      .then((s) => {
        setMode(s.mode);
        setNotice(s.demo_notice);
        setAi(s.ai.provider === "mock" ? "Mock AI" : s.ai.available ? `AI: ${s.ai.provider}` : "AI unavailable");
      })
      .catch(() => setBackendDown(true));
    getAccessToken().then((t) => setAuthed(Boolean(t)));
  }, []);

  // Live mode: no session means no access. Never fall back to anything else.
  useEffect(() => {
    if (mode === "live" && authed === false && path !== "/login") router.replace("/login");
  }, [mode, authed, path, router]);

  const isActive = (href: string) => (href === "/" ? path === "/" : path === href || path.startsWith(href + "/") || (href === "/competitions" && path.startsWith("/assessments")) || (href === "/competitions" && path.startsWith("/plans")));

  const signOut = async () => {
    await getSupabase()?.auth.signOut();
    router.replace("/login");
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <Link href="/" className="brand">Strong<span>Prep</span></Link>
        <nav className="nav" aria-label="Main">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} aria-current={isActive(n.href) ? "page" : undefined}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>{ICONS[n.icon]}</svg>
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="side-foot">
          <span>{mode === "demo" ? "Local demo" : mode === "live" ? "Live" : ""} · <Link href="/settings" style={{ color: "inherit" }}>{ai || "AI"}</Link></span>
          {mode === "live" && supabaseConfigured && authed && <button className="btn btn-small" onClick={signOut}>Sign out</button>}
        </div>
      </aside>
      <div className="main">
        {notice && <div className="demo-banner" role="note"><strong>Demo:</strong> {notice}</div>}
        <main className="container">
          {backendDown && (
            <div className="alert alert-error" role="alert">
              <strong>The backend is not reachable.</strong> Start it in a separate terminal (see README), then reload this page.
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}
