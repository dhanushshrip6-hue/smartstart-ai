import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api";
import { Banner } from "../components/ui";
import { scoreColor, when } from "../format";
import type { HistoryRow } from "../types";

export default function HistoryPage() {
  const [rows, setRows] = useState<HistoryRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = () => api.history().then(setRows).catch((e: ApiError) => setErr(e.message));
  useEffect(() => { load(); }, []);
  return (
    <div className="main" style={{ margin: "0 auto" }}>
      <div className="page-head"><div><h2>Past analyses</h2><p>Every analysis is stored in your local SQLite database.</p></div><Link className="btn" to="/">New analysis</Link></div>
      {err && <Banner kind="err">{err}</Banner>}
      {!rows && !err && <div className="skeleton" style={{ height: 80 }} />}
      {rows?.length === 0 && <div className="card">No analyses yet. <Link to="/">Describe your first startup</Link>.</div>}
      <div className="hist">{rows?.map((r) => (
        <div className="hrow" key={r.id}>
          <div><Link to={`/analysis/${r.id}/overview`}><b>{r.business_name}</b></Link><div className="small muted">{r.category} · {r.location}</div><div className="small muted">{when(r.created_at)}</div></div>
          <b style={{ color: scoreColor(r.score), fontSize: "1.4rem" }}>{r.score.toFixed(0)}<span className="small muted">/100</span></b>
          <button className="btn ghost sm" onClick={async () => { if (confirm(`Delete "${r.business_name}"?`)) { await api.remove(r.id).catch(() => {}); load(); } }}>Delete</button>
        </div>))}</div>
    </div>
  );
}
