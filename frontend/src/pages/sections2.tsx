import { BarChart, Banner, Card, C, DonutChart, LineChart, PageHead, PolarChart, SEG_COLORS, Stat, Tag } from "../components/ui";
import { dist, money, num, poiName } from "../format";
import type { Analysis, SwotItem } from "../types";

const SC = { low: C.amber, medium: C.blue, high: C.green } as const;

export function Revenue({ a }: { a: Analysis }) {
  const cur = a.input.currency, s = a.financials.scenarios, names = ["low", "medium", "high"] as const;
  return (
    <div className="grid fade">
      <PageHead title="Revenue analysis" intro="Three scenarios built from your expected customers per day. Low is 60% and High is 130% of your expectation. These are not forecasts." />
      <div className="grid g3">{names.map((n) => (
        <div key={n} className="card scen" style={{ ["--c" as any]: SC[n] }}>
          <header><h3 style={{ textTransform: "capitalize" }}>{n} · {s[n].multiplier * 100}%</h3><Tag kind="Calculated estimate" /></header>
          <div className="stat"><div className="v">{money(cur, s[n].revenue, true)}</div><div className="l">revenue per month</div></div>
          <dl className="dl" style={{ marginTop: 10 }}><dt>Customers/day</dt><dd>{num(s[n].customers_per_day, 1)}</dd><dt>Profit</dt><dd>{money(cur, s[n].profit)}</dd><dt>Margin</dt><dd>{(s[n].margin * 100).toFixed(1)}%</dd>
            <dt>Payback</dt><dd>{s[n].payback_months ? `${s[n].payback_months!.toFixed(1)} months` : "not reached"}</dd></dl>
        </div>))}</div>
      <div className="grid g2">
        <Card title="Monthly revenue, costs and profit" tag="Calculated estimate">
          <BarChart data={{ labels: names.map((n) => n[0].toUpperCase() + n.slice(1)), datasets: [
            { label: "Revenue", data: names.map((n) => s[n].revenue), backgroundColor: C.blue },
            { label: "Total costs", data: names.map((n) => s[n].variable_costs + s[n].fixed_costs), backgroundColor: C.grey },
            { label: "Profit", data: names.map((n) => s[n].profit), backgroundColor: names.map((n) => (s[n].profit >= 0 ? C.green : C.orange)) }] }}
            options={{ plugins: { legend: { position: "bottom" } } }} /></Card>
        <Card title="Cumulative cash over 24 months" tag="Calculated estimate">
          <LineChart data={{ labels: Array.from({ length: 25 }, (_, i) => i), datasets: names.map((n) => ({ label: n, data: s[n].cash_curve, borderColor: SC[n], backgroundColor: SC[n], pointRadius: 0, tension: 0.1 })) }}
            options={{ plugins: { legend: { position: "bottom" } }, scales: { x: { title: { display: true, text: "Month" } }, y: { title: { display: true, text: `${cur}, after initial budget` } } } }} />
          <p className="small muted">Starts at minus your initial budget. The line crosses zero when profit has repaid it.</p></Card>
      </div>
    </div>
  );
}

export function Expenses({ a }: { a: Analysis }) {
  const cur = a.input.currency, f = a.financials, m = f.scenarios.medium, ex = a.input.expenses;
  const be = f.breakeven_customers_per_day;
  const labels = [...Object.keys(ex).map((k) => k[0].toUpperCase() + k.slice(1)), "Variable costs"];
  return (
    <div className="grid fade">
      <PageHead title="Expense & profit" intro="Where the money goes each month and how many customers you need to cover it." />
      <div className="grid g4">
        <Stat label="Fixed costs / month" value={money(cur, f.fixed_monthly, true)} tag="User assumption" />
        <Stat label="Variable cost" value={`${f.variable_pct}%`} sub="of revenue" tag="User assumption" />
        <Stat label="Break-even customers/day" value={be == null ? "n/a" : be.toFixed(1)} sub={be != null ? `vs ${a.input.customers_per_day} expected` : "price below variable cost"} tag="Calculated estimate" />
        <Stat label="Break-even revenue" value={money(cur, f.breakeven_revenue_monthly, true)} sub="per month" tag="Calculated estimate" />
      </div>
      <div className="grid g2">
        <Card title="Cost structure, medium scenario" tag="Calculated estimate">
          <DonutChart data={{ labels, datasets: [{ data: [...Object.values(ex), m.variable_costs], backgroundColor: [C.blue, C.green, C.amber, C.purple, C.grey, C.orange], borderWidth: 0 }] }} />
          <div className="tbl"><table><tbody>{Object.entries(ex).map(([k, v]) => <tr key={k}><td style={{ textTransform: "capitalize" }}>{k}</td><td className="num">{money(cur, v)}</td></tr>)}
            <tr><td>Variable costs (medium)</td><td className="num">{money(cur, m.variable_costs)}</td></tr><tr><td><b>Profit (medium)</b></td><td className="num"><b>{money(cur, m.profit)}</b></td></tr></tbody></table></div>
        </Card>
        <Card title="Break-even point" tag="Calculated estimate">
          <LineChart data={{ labels: f.breakeven_curve.map((p) => p.customers_per_day.toFixed(0)), datasets: [
            { label: "Revenue", data: f.breakeven_curve.map((p) => p.revenue), borderColor: C.green, pointRadius: 0 },
            { label: "Total cost", data: f.breakeven_curve.map((p) => p.total_cost), borderColor: C.orange, pointRadius: 0 }] }}
            options={{ plugins: { legend: { position: "bottom" } }, scales: { x: { title: { display: true, text: "Customers per day" } }, y: { title: { display: true, text: `${cur} per month` } } } }} />
          <p className="small muted">Where revenue crosses total cost is break-even. Your expected {a.input.customers_per_day} customers/day is {be != null && a.input.customers_per_day >= be ? "above" : "below"} that point.</p>
        </Card>
      </div>
    </div>
  );
}

export function Customers({ a }: { a: Analysis }) {
  const segs = a.customers.segments;
  return (
    <div className="grid fade">
      <PageHead title="Customer analysis" intro={`You target: ${a.customers.target_text}. Here are the real places near the site that bring those groups together.`} />
      {!a.customers.dominant_segment && <Banner kind="info">No customer-generating places are mapped in this radius. Try a larger radius.</Banner>}
      <div className="grid g2">
        <Card title="Weighted opportunity by group" tag="Calculated estimate"><PolarChart data={{ labels: segs.map((s) => s.segment), datasets: [{ data: segs.map((s) => s.weighted), backgroundColor: SEG_COLORS.map((c) => c + "cc") }] }} /></Card>
        <Card title="Reading this chart"><p>Bigger slices mean more mapped places that draw that group, after applying the group weight.</p>
          <p className="muted">{a.customers.note}</p>{a.customers.dominant_segment && <p>Largest weighted group: <b>{a.customers.dominant_segment}</b>.</p>}</Card>
      </div>
      <div className="grid g3">{segs.map((s, i) => (
        <Card key={s.segment} title={s.segment} tag="Retrieved fact">
          <div className="stat"><div className="v" style={{ color: SEG_COLORS[i % 6] }}>{s.count}</div><div className="l">places in {a.market.radius_km} km · {s.within_500m} within 500 m · nearest {dist(s.nearest_m)}</div></div>
          <div className="seg"><ul>{s.top.slice(0, 5).map((p) => <li key={p.id}>{poiName(p)} · {dist(p.distance_m)}</li>)}{s.top.length === 0 && <li>None mapped</li>}</ul></div>
        </Card>))}</div>
    </div>
  );
}

function Quad({ cls, title, items }: { cls: string; title: string; items: SwotItem[] }) {
  return <div className={`q ${cls}`}><h3>{title}</h3><ul>{items.length ? items.map((s, i) => <li key={i}><span>{s.text}</span><span><Tag kind={s.basis} /></span></li>) : <li className="muted">Nothing flagged by the rules.</li>}</ul></div>;
}
export function Swot({ a }: { a: Analysis }) {
  const s = a.swot;
  return (
    <div className="grid fade">
      <PageHead title="SWOT analysis" intro="Built by fixed rules from this location's retrieved data and your financial inputs. Each point shows what kind of evidence backs it." />
      <div className="swot"><Quad cls="s" title="Strengths" items={s.strengths} /><Quad cls="w" title="Weaknesses" items={s.weaknesses} /><Quad cls="o" title="Opportunities" items={s.opportunities} /><Quad cls="t" title="Threats" items={s.threats} /></div>
    </div>
  );
}
