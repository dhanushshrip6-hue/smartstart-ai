export const money = (cur: string, v: number | null | undefined, compact = false) =>
  v == null ? "—" : new Intl.NumberFormat("en-IN", { style: "currency", currency: cur, maximumFractionDigits: 0, notation: compact ? "compact" : "standard" }).format(v);
export const num = (v: number | null | undefined, d = 0) => (v == null ? "—" : v.toLocaleString("en-IN", { maximumFractionDigits: d }));
export const dist = (m: number | null | undefined) => (m == null ? "—" : m >= 1000 ? `${(m / 1000).toFixed(2)} km` : `${m} m`);
export const poiName = (p: { name: string | null; kind: string }) => p.name || `Unnamed ${p.kind.replace(/_/g, " ")}`;
export const when = (iso: string) => new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
export const scoreColor = (s: number) => (s >= 70 ? "var(--green)" : s >= 50 ? "var(--amber)" : "var(--orange)");
