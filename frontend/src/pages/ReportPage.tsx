import { useState } from "react";
import { api } from "../api";
import { Banner, Tag } from "../components/ui";
import { dist, money, poiName, scoreColor, when } from "../format";
import type { Analysis } from "../types";

export default function ReportPage({ a }: { a: Analysis }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const i = a.input, cur = i.currency, f = a.financials, s = f.scenarios;

  async function download() {
    setBusy(true); setErr(null);
    try {
      const r = await fetch(api.pdfUrl(a.id));
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `PDF failed (HTTP ${r.status}).`);
      const url = URL.createObjectURL(await r.blob());
      const l = document.createElement("a");
      l.href = url; l.download = `SmartStart_${i.business_name.replace(/[^A-Za-z0-9_-]+/g, "_")}.pdf`; l.click();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <div className="fade">
      <div className="page-head noprint"><div><h2>Final report</h2><p>Everything from the analysis in one document. Download the PDF, or print this page.</p></div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="btn" onClick={download} disabled={busy}>{busy ? "Preparing PDF…" : "Download Complete Report"}</button>
          <button className="btn ghost" onClick={() => window.print()}>Print / Save as PDF</button></div></div>
      {err && <Banner kind="err">{err}</Banner>}
      <article className="doc">
        <h1>{i.business_name}</h1><p className="muted">Startup location &amp; feasibility report · {i.category} · generated {when(a.created_at)}</p>
        <p style={{ fontSize: "1.1rem" }}>Feasibility index <b style={{ color: scoreColor(a.feasibility.score), fontSize: "1.6rem" }}>{a.feasibility.score.toFixed(1)}</b> / 100 · {a.feasibility.band}</p>

        <h2>1. Startup details</h2><Tag kind="User assumption" />
        <p>{i.description}</p><p>Target customers: {i.target_customers}. Budget {money(cur, i.budget)}; average price {money(cur, i.avg_price)}; {i.customers_per_day} customers/day; {i.working_days} working days/month.</p>
        <h2>2. Location and map</h2><Tag kind="Retrieved fact" />
        <p>{a.location.display_name} ({a.location.lat.toFixed(5)}, {a.location.lon.toFixed(5)}). The full interactive map is on the Location page; the PDF includes a plotted map of the retrieved points.</p>
        <h2>3. Market analysis</h2><Tag kind="Retrieved fact" />
        <p>Within {a.market.radius_km} km: {a.market.segments.reduce((n, x) => n + x.count, 0)} customer-generating places (weighted {a.market.weighted_total}) and {a.market.transit.total} transit stops.</p>
        <ul>{a.market.segments.map((x) => <li key={x.segment}>{x.segment}: {x.count} places, nearest {dist(x.nearest_m)}</li>)}</ul>
        <h2>4. Competition</h2><Tag kind="Retrieved fact" />
        <p>{a.competition.total} mapped competitors, {a.competition.within_1km} within 1 km, nearest {dist(a.competition.nearest_m)}. Density {a.competition.density_per_km2}/km².</p>
        <ul>{a.competition.list.slice(0, 8).map((c) => <li key={c.id}>{poiName(c)} · {dist(c.distance_m)}</li>)}</ul>
        <h2>5. Customer analysis</h2><Tag kind="Retrieved fact" /><p>{a.customers.note}{a.customers.dominant_segment ? ` Largest weighted group: ${a.customers.dominant_segment}.` : ""}</p>
        <h2>6. Revenue</h2><Tag kind="Calculated estimate" />
        <div className="tbl"><table><thead><tr><th>Scenario</th><th className="num">Customers/day</th><th className="num">Revenue/month</th><th className="num">Profit/month</th></tr></thead><tbody>
          {(["low", "medium", "high"] as const).map((n) => <tr key={n}><td style={{ textTransform: "capitalize" }}>{n}</td><td className="num">{s[n].customers_per_day.toFixed(1)}</td><td className="num">{money(cur, s[n].revenue)}</td><td className="num">{money(cur, s[n].profit)}</td></tr>)}</tbody></table></div>
        <h2>7. Expenses and profit</h2><Tag kind="User assumption" />
        <p>Fixed {money(cur, f.fixed_monthly)} per month plus {f.variable_pct}% variable cost. Medium-scenario profit {money(cur, s.medium.profit)}.</p>
        <h2>8. Break-even</h2><Tag kind="Calculated estimate" />
        <p>{f.breakeven_customers_per_day != null ? `${f.breakeven_customers_per_day.toFixed(1)} customers per day (${money(cur, f.breakeven_revenue_monthly)} revenue per month).` : "Not reachable at this price and variable cost."}</p>
        <h2>9. SWOT</h2>
        {(["strengths", "weaknesses", "opportunities", "threats"] as const).map((k) => <div key={k}><b style={{ textTransform: "capitalize" }}>{k}</b><ul>{a.swot[k].map((x, n) => <li key={n}>{x.text} <Tag kind={x.basis} /></li>)}</ul></div>)}
        <h2>10. Feasibility score</h2><Tag kind="Calculated estimate" />
        <div className="tbl"><table><tbody>{a.feasibility.components.map((c) => <tr key={c.key}><td>{c.label}</td><td className="num">{(c.weight * 100).toFixed(0)}%</td><td className="num">{c.score.toFixed(1)}</td></tr>)}</tbody></table></div>
        <h2>11. Alternative locations</h2><Tag kind="Calculated estimate" />
        {a.alternatives.status === "ok" ? <div className="tbl"><table><thead><tr><th>Location</th><th className="num">Dist.</th><th className="num">Competitors</th><th className="num">Index</th></tr></thead><tbody>
          {a.alternatives.rows.map((r) => <tr key={r.name}><td>{r.selected ? "Selected location" : r.name}</td><td className="num">{r.selected ? "—" : `${r.distance_km} km`}</td><td className="num">{r.competitors_radius}</td><td className="num">{r.feasibility.toFixed(1)}</td></tr>)}</tbody></table></div>
          : <p>{a.alternatives.error || "Not available."}</p>}
        <p className="small muted">Map data © OpenStreetMap contributors. Generated by SmartStart AI.</p>
      </article>
    </div>
  );
}
