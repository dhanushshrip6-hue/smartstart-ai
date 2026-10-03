import type { Analysis, HistoryRow } from "./types";

export class ApiError extends Error {
  constructor(message: string, public status: number, public fields?: Record<string, string>, public code?: string) { super(message); }
}

async function req<T>(url: string, init?: RequestInit, timeoutMs = 170000): Promise<T> {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await fetch(url, { ...init, signal: ctl.signal, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
    let body: any = null;
    try { body = await r.json(); } catch { /* non-JSON */ }
    if (!r.ok) throw new ApiError(body?.error || `Request failed (HTTP ${r.status}).`, r.status, body?.fields, body?.code);
    return body as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if ((e as Error).name === "AbortError") throw new ApiError("The request timed out. Try a smaller POI radius.", 0);
    throw new ApiError("Cannot reach the SmartStart server. Is the Flask backend running on port 5000?", 0);
  } finally { clearTimeout(t); }
}

export const api = {
  health: () => req<{ ok: boolean; gemini_configured: boolean }>("/api/health"),
  catalog: () => req<{ categories: string[] }>("/api/catalog"),
  create: (body: unknown) => req<Analysis>("/api/analyses", { method: "POST", body: JSON.stringify(body) }),
  get: (id: string) => req<Analysis>(`/api/analyses/${id}`),
  history: () => req<HistoryRow[]>("/api/analyses"),
  remove: (id: string) => req<{ deleted: boolean }>(`/api/analyses/${id}`, { method: "DELETE" }),
  pdfUrl: (id: string) => `/api/analyses/${id}/report.pdf`,
};
