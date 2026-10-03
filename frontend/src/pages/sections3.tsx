import { useState } from "react";
import { Link } from "react-router-dom";
import { BarChart, Banner, Card, C, Legend2, MapView, PageHead, RadarChart, ScoreRing, Tag } from "../components/ui";
import { dist, money, scoreColor, when } from "../format";
import type { Analysis } from "../types";

export function Feasibility({ a }: { a: Analysis }) {
  const f = a.feasibility;
  return (
    <div className="grid fade">
      <PageHead title="Feasibility index" intro="A 0–100 screening score from six weighted components." />
      <div className="grid g2">
        <Card title="Score" tag="Calculated estimate"><ScoreRing score={f.score} color={scoreColor(f.score)} size={210} />
          <p style={{ textAlign: "center", fontWeight: 600, marginBottom: 0 }}>{f.band} (70+ strong · 50–69 mixed · below 50 weak)</p><p className="small muted" style={{ textAlign: "center" }}>{f.note}</p></Card>
        <Card title="Component profile" tag="Calculated estimate"><RadarChart data={{ labels: f.components.map((c) => c.label), datasets: [{ data: f.components.map((c) => c.score), backgroundColor: "rgba(31,95,168,.18)", borderColor: C.blue, pointBackgroundColor: C.blue }] }} /></Card>
      </div>
    </div>
  );
}

export function Alternatives({ a }: { a: Analysis }) {
  const al = a.alternatives, cur = a.input.currency, rows = al.rows || [];
  const [pick, setPick] = useState<string | null>(null);
  if (al.status !== "ok") return (
    <div className="grid fade"><PageHead title="Alternative locations" intro="Nearby candidate areas from OpenStreetMap." />
      <Banner kind="warn">{al.error || "Alternative locations are not available for this analysis."}</Banner></div>);
  const others = rows.filter((r) => !r.selected);
  const pts = others.map((r) => ({ lat: r.lat!, lon: r.lon!, color: pick === r.name ? C.orange : C.blue, label: `${r.name} · ${r.distance_km} km away`, radius: 9 }));
  return (
    <div className="grid fade">
      <PageHead title="Alternative locations" intro={`Named areas within ${al.radius_km} km of your site, compared on the same measures. They are listed by distance and are not ranked.`} />
      <Card title="Candidate areas" tag="Retrieved fact"><MapView center={[a.location.lat, a.location.lon]} radiusM={(al.radius_km || 10) * 1000} points={pts} />
        <Legend2 items={[["Candidate area (OSM place)", C.blue]]} /></Card>
      <Card title="Side-by-side comparison" tag="Calculated estimate"><div className="tbl"><table><thead><tr><th>Location</th><th className="num">Distance</th><th className="num">Competitors (≤1 km)</th><th className="num">Customer places (weighted)</th><th className="num">Transit ≤1 km</th><th className="num">Revenue/mo (medium)</th><th className="num">Risk score</th><th className="num">Index</th></tr></thead><tbody>
        {rows.map((r) => <tr key={r.name} onMouseEnter={() => setPick(r.name)} onMouseLeave={() => setPick(null)} style={r.selected ? { background: "#f1f5f2" } : undefined}>
          <td><b>{r.selected ? "Your selected location" : r.name}</b>{r.place_type && <div className="small muted">{r.place_type}</div>}</td><td className="num">{r.selected ? "—" : `${r.distance_km} km`}</td>
          <td className="num">{r.competitors_radius} ({r.competitors_1km})</td><td className="num">{r.customer_poi_weighted}</td><td className="num">{r.transit_1km}</td><td className="num">{money(cur, r.revenue_medium, true)}</td><td className="num">{r.scores.risk}</td><td className="num"><b style={{ color: scoreColor(r.feasibility) }}>{r.feasibility.toFixed(1)}</b></td></tr>)}</tbody></table></div></Card>
      <div className="grid g2">
        <Card title="Mapped competitors" tag="Retrieved fact"><BarChart data={{ labels: rows.map((r) => (r.selected ? "Selected" : r.name)), datasets: [{ label: `within ${al.poi_radius_km} km`, data: rows.map((r) => r.competitors_radius), backgroundColor: rows.map((r) => (r.selected ? C.ink : C.orange)) }] }} options={{ plugins: { legend: { display: false } } }} /></Card>
        <Card title="Customer-place indicator" tag="Retrieved fact"><BarChart data={{ labels: rows.map((r) => (r.selected ? "Selected" : r.name)), datasets: [{ label: "weighted", data: rows.map((r) => r.customer_poi_weighted), backgroundColor: rows.map((r) => (r.selected ? C.ink : C.green)) }] }} options={{ plugins: { legend: { display: false } } }} /></Card>
      </div>
      <Banner kind="info"><b>How to read this.</b> {al.method} {al.caveats}</Banner>
    </div>
  );
}

export function Summary({ a }: { a: Analysis }) {
  return (
    <div className="grid fade">
      <PageHead title="Final summary" intro="The main findings and the limits of the data behind them.">
        <Link className="btn" to={`/analysis/${a.id}/report`}>Open final report</Link>
      </PageHead>
      <div className="grid g2">
        <Card title="Important findings"><ul style={{ paddingLeft: 18, display: "grid", gap: 10, margin: 0 }}>{a.highlights.map((h, i) => <li key={i}>{h.text} <Tag kind={h.basis} /></li>)}</ul></Card>
        <Card title="Data limitations"><ul style={{ paddingLeft: 18, display: "grid", gap: 8, margin: 0 }} className="small">{a.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul></Card>
      </div>
      <Card title="Data retrieved"><dl className="dl"><dt>Retrieved at</dt><dd>{when(a.retrieval.retrieved_at)}</dd><dt>Sources</dt><dd>{a.retrieval.sources.join(", ")}</dd><dt>Elements returned</dt><dd>{a.retrieval.elements_returned}{a.retrieval.truncated ? " (cap reached)" : ""}</dd></dl>
        <p className="small muted">Map data © OpenStreetMap contributors (ODbL).</p></Card>
    </div>
  );
}
