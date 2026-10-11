export const STATUS_TEXT: Record<string, string> = {
  demonstrated: "Demonstrated under recorded conditions",
  measured_gap: "Measured performance gap",
  implement_practice_gap: "Implement-practice gap",
  unknown: "Unknown",
};

/** Turn FastAPI error bodies (string, {message, errors}, or pydantic list) into readable lines. */
export function errorLines(detail: unknown): string[] {
  if (detail == null) return ["Something went wrong."];
  if (typeof detail === "string") return [detail];
  if (Array.isArray(detail)) {
    return detail.map((d: any) => {
      const where = Array.isArray(d?.loc) ? d.loc.filter((x: any) => x !== "body").join(".") : "";
      return where ? `${where}: ${d?.msg ?? "invalid"}` : String(d?.msg ?? JSON.stringify(d));
    });
  }
  if (typeof detail === "object") {
    const o = detail as { message?: string; errors?: string[] };
    return [o.message ?? "Request failed.", ...(o.errors ?? [])];
  }
  return [String(detail)];
}

export function kg(v: number | null | undefined, perHand = false): string {
  if (v == null) return "—";
  return `${Number.isInteger(v) ? v : v.toFixed(1)} kg${perHand ? " per hand" : ""}`;
}

export function seconds(v: number | null | undefined): string {
  return v == null ? "—" : `${v} s`;
}

export function metres(v: number | null | undefined): string {
  return v == null ? "—" : `${v} m`;
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function numOrNull(s: string): number | null {
  if (s.trim() === "") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

export function ratioText(r: number | null | undefined): string {
  return r == null ? "—" : r.toFixed(2);
}
