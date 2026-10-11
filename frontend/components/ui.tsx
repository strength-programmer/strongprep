"use client";
import { ReactNode } from "react";
import { ApiError } from "@/lib/api";
import { STATUS_TEXT } from "@/lib/format";

export function Loading({ what = "Loading" }: { what?: string }) {
  return (
    <div className="state" role="status" aria-live="polite">
      <span className="spinner" aria-hidden /> {what}…
    </div>
  );
}

export function ErrorBox({ error, onRetry }: { error: ApiError | string | null; onRetry?: () => void }) {
  if (!error) return null;
  const lines = typeof error === "string" ? [error] : error.lines;
  return (
    <div className="alert alert-error" role="alert">
      <strong>{lines[0]}</strong>
      {lines.length > 1 && (
        <ul>
          {lines.slice(1).map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      )}
      {onRetry && (
        <button className="btn btn-small" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="state empty">
      <p>
        <strong>{title}</strong>
      </p>
      {children}
    </div>
  );
}

export function Badge({ tone = "neutral", children }: { tone?: "neutral" | "demo" | "good" | "warn" | "bad" | "info"; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

const STATUS_TONE: Record<string, "good" | "bad" | "warn" | "neutral"> = {
  demonstrated: "good",
  measured_gap: "bad",
  implement_practice_gap: "warn",
  unknown: "neutral",
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONE[status] ?? "neutral"}>{STATUS_TEXT[status] ?? status}</Badge>;
}

export function CompStatusBadge({ status }: { status: string }) {
  if (status === "upcoming") return <Badge tone="info">Upcoming</Badge>;
  if (status === "canceled") return <Badge tone="bad">Canceled</Badge>;
  return <Badge>Completed</Badge>;
}

export function DemoBadge({ label }: { label?: string | null }) {
  return <Badge tone="demo">{label ? "Fictional / demo" : "Demo"}</Badge>;
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="hint">{hint}</span>}
    </label>
  );
}

export function Card({ title, children, actions }: { title?: ReactNode; children: ReactNode; actions?: ReactNode }) {
  return (
    <section className="card">
      {(title || actions) && (
        <header className="card-head">
          {title && <h2>{title}</h2>}
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}
