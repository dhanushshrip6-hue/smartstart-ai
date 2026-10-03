import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Route, Routes, useParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { Banner } from "../components/ui";
import type { Analysis } from "../types";
import { Competition, Location, Market, Overview } from "./sections1";
import { Customers, Expenses, Revenue, Swot } from "./sections2";
import { Alternatives, Feasibility, Summary } from "./sections3";
import ReportPage from "./ReportPage";

export const NAV: [string, string][] = [
  ["overview", "Overview"], ["location", "Location analysis"], ["market", "Nearby market"], ["competition", "Competition"], ["revenue", "Revenue analysis"],
  ["expenses", "Expense & profit"], ["customers", "Customer analysis"], ["swot", "SWOT analysis"], ["feasibility", "Feasibility index"],
  ["alternatives", "Alternative locations"], ["summary", "Final summary"], ["report", "Final report"],
];

export default function Workspace() {
  const { id = "" } = useParams();
  const [a, setA] = useState<Analysis | null>(null);
  const [err, setErr] = useState<ApiError | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => { setA(null); setErr(null); api.get(id).then(setA).catch(setErr); window.scrollTo(0, 0); }, [id]);

  if (err) return <div className="main" style={{ margin: "0 auto" }}><Banner kind="err">{err.message}</Banner><Link className="btn" to="/">Start a new analysis</Link></div>;
  if (!a) return <div className="main"><div className="skeleton" style={{ height: 40, width: 300, marginBottom: 20 }} /><div className="grid g3"><div className="skeleton" style={{ height: 120 }} /><div className="skeleton" style={{ height: 120 }} /><div className="skeleton" style={{ height: 120 }} /></div></div>;

  return (
    <div className="shell">
      <div className="topbar"><b>SmartStart AI</b><button className="btn ghost sm" onClick={() => setOpen(!open)} aria-expanded={open}>Pages</button></div>
      <nav className={`side ${open ? "open" : ""}`} aria-label="Analysis pages" onClick={() => setOpen(false)}>
        <Link to="/" className="brand">SmartStart <b>AI</b></Link>
        <div className="sub">{a.input.business_name}<br />{a.input.category}</div>
        <ol className="route">{NAV.map(([k, l]) => <li key={k}><NavLink to={`/analysis/${id}/${k}`}><i />{l}</NavLink></li>)}</ol>
        <div className="foot"><Link className="btn ghost sm" to="/history">Past analyses</Link><Link className="btn ghost sm" to="/">New analysis</Link></div>
      </nav>
      <main className="main">
        <Routes>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<Overview a={a} />} />
          <Route path="location" element={<Location a={a} />} />
          <Route path="market" element={<Market a={a} />} />
          <Route path="competition" element={<Competition a={a} />} />
          <Route path="revenue" element={<Revenue a={a} />} />
          <Route path="expenses" element={<Expenses a={a} />} />
          <Route path="customers" element={<Customers a={a} />} />
          <Route path="swot" element={<Swot a={a} />} />
          <Route path="feasibility" element={<Feasibility a={a} />} />
          <Route path="alternatives" element={<Alternatives a={a} />} />
          <Route path="summary" element={<Summary a={a} />} />
          <Route path="report" element={<ReportPage a={a} />} />
          <Route path="*" element={<Navigate to="overview" replace />} />
        </Routes>
      </main>
    </div>
  );
}
