import { Link } from "react-router-dom";
import { BarChart, Banner, Card, C, DonutChart, Legend2, MapView, Meter, PageHead, ScoreRing, SEG_COLORS, Stat, Tag } from "../components/ui";
import { dist, money, num, poiName, scoreColor } from "../format";
import type { Analysis } from "../types";

export function Overview({ a }: { a: Analysis }) {
  const i = a.input, med = a.financials.scenarios.medium, f = a.feasibility, be = a.financials.breakeven_customers_per_day;
  const cur = i.currency;
  return (
    <div className="grid fade">
      <PageHead title={i.business_name} intro={`${i.category} · ${a.location.display_name}`}>
        <Link className="btn" to={`/analysis/${a.id}/location`}>Start with the location</Link>
      </PageHead>
      {a.retrieval.truncated && <Banner kind="warn">Overpass results reached the retrieval cap, so counts are lower bounds. Use a smaller radius for complete data.</Banner>}
      <div className="grid" style={{ gridTemplateColumns: "minmax(220px,300px) 1fr" }}>
        <Card title="Feasibility index" tag="Calculated estimate">
          <ScoreRing score={f.score} color={scoreColor(f.score)} />
          <p style={{ textAlign: "center", fontWeight: 600, margin: "10px 0 0" }}>{f.band}</p>
          <p className="small muted" style={{ textAlign: "center" }}>{f.note}</p>
        </Card>
        <div className="grid g3" style={{ alignContent: "start" }}>
          <Stat label="Revenue / month (medium)" value={money(cur, med.revenue, true)} sub={`${num(med.customers_per_day, 0)} customers/day`} tag="Calculated estimate" />
          <Stat label="Profit / month (medium)" value={money(cur, med.profit, true)} sub={`${(med.margin * 100).toFixed(1)}% margin`} tag="Calculated estimate" />
          <Stat label="Break-even" value={be == null ? "n/a" : `${be.toFixed(1)}/day`} sub="customers per day" tag="Calculated estimate" />
          <Stat label={`Competitors in ${a.market.radius_km} km`} value={a.competition.total} sub={`nearest ${dist(a.competition.nearest_m)}`} tag="Retrieved fact" />
          <Stat label="Customer-generating places" value={a.market.segments.reduce((s, x) => s + x.count, 0)} sub={`${a.market.transit.total} transit stops`} tag="Retrieved fact" />
          <Stat label="Initial budget" value={money(cur, i.budget, true)} sub={med.payback_months ? `payback ${med.payback_months.toFixed(1)} mo (medium)` : "no payback in medium case"} tag="User assumption" />
        </div>
      </div>
      <div className="grid g2">
        <Card title="Business summary" tag="User assumption">
          <dl className="dl"><dt>Description</dt><dd>{i.description}</dd><dt>Target customers</dt><dd>{i.target_customers}</dd><dt>Price / customer</dt><dd>{money(cur, i.avg_price)}</dd>
            <dt>Customers per day</dt><dd>{i.customers_per_day}</dd><dt>Working days</dt><dd>{i.working_days} per month</dd><dt>Radii</dt><dd>{i.poi_radius_km} km nearby · {i.alt_radius_km} km alternatives</dd></dl>
        </Card>
        <Card title="Where each number comes from">
          <div className="grid" style={{ gap: 10 }}>
            {([["Retrieved fact", "Places and distances from OpenStreetMap via Nominatim and Overpass."], ["User assumption", "Your price, customers, expenses, budget and radii."],
              ["Calculated estimate", "Deterministic formulas on the two groups above, including the score."]] as const)
              .map(([k, d]) => <div key={k}><Tag kind={k} /> <span className="small muted">{d}</span></div>)}
          </div>
        </Card>
      </div>
    </div>
  );
}

export function Location({ a }: { a: Analysis }) {
  const c: [number, number] = [a.location.lat, a.location.lon];
  const addr = Object.entries(a.location.address || {}).filter(([k]) => !["ISO3166-2-lvl4", "country_code"].includes(k)).slice(0, 8);
  const R = a.market.radius_km * 1000;
  return (
    <div className="grid fade">
      <PageHead title="Location analysis" intro="The address you entered, geocoded by Nominatim, with the analysis radius drawn on OpenStreetMap." />
      <Card title="Map" tag="Retrieved fact">
        <MapView center={c} radiusM={R} rings={[500, 1000].filter((r) => r < R)} />
        <p className="small muted">Dashed circle: {a.market.radius_km} km analysis radius. Grey rings: 500 m and 1 km.</p>
      </Card>
      <div className="grid g2">
        <Card title="Geocoding result" tag="Retrieved fact">
          <dl className="dl"><dt>You entered</dt><dd>{a.input.location}</dd><dt>Matched to</dt><dd>{a.location.display_name}</dd><dt>Coordinates</dt><dd className="mono">{a.location.lat.toFixed(5)}, {a.location.lon.toFixed(5)}</dd>
            <dt>OSM object</dt><dd>{a.location.osm_type} {a.location.osm_id}</dd><dt>Source</dt><dd>{a.location.source}</dd>
            {addr.map(([k, v]) => [<dt key={k + "k"}>{k.replace(/_/g, " ")}</dt>, <dd key={k}>{v}</dd>])}</dl>
          <p className="small muted">Nominatim returns the best single match. If this is the wrong place, add more detail and run again.</p>
        </Card>
        <Card title="What surrounds the site" tag="Retrieved fact">
          <BarChart data={{ labels: a.competition.rings.map((r) => r.label), datasets: [
            { label: "Customer-generating places", data: a.competition.rings.map((r) => r.customer_pois), backgroundColor: C.green },
            { label: "Competitors", data: a.competition.rings.map((r) => r.competitors), backgroundColor: C.orange }] }} options={{ plugins: { legend: { position: "bottom" } } }} />
          <p className="small muted">Counts by straight-line distance ring from the geocoded point.</p>
        </Card>
      </div>
    </div>
  );
}

export function Market({ a }: { a: Analysis }) {
  const m = a.market, segs = m.segments;
  const col = (s: string) => SEG_COLORS[segs.findIndex((x) => x.segment === s) % SEG_COLORS.length];
  const pts = m.pois.map((p) => ({ lat: p.lat, lon: p.lon, color: col(p.segment!), label: `${poiName(p)} (${p.segment}, ${dist(p.distance_m)})` }));
  const mx = Math.max(1, ...segs.map((s) => s.weighted));
  return (
    <div className="grid fade">
      <PageHead title="Nearby market" intro={`Places within ${m.radius_km} km that attract your customer groups, plus public transport access.`} />
      <div className="grid g4">
        <Stat label="Weighted customer indicator" value={num(m.weighted_total, 1)} sub="places × group weight" tag="Calculated estimate" />
        <Stat label="Density" value={`${m.weighted_density_per_km2}/km²`} sub={`${m.area_km2} km² searched`} tag="Calculated estimate" />
        <Stat label="Within 1 km" value={num(m.weighted_within_1km, 1)} sub="weighted indicator" tag="Calculated estimate" />
        <Stat label="Transit stops" value={m.transit.total} sub={`${m.transit.within_1km} within 1 km · nearest ${dist(m.transit.nearest_m)}`} tag="Retrieved fact" />
      </div>
      <div className="grid g2">
        <Card title="Customer-generating places" tag="Retrieved fact"><MapView center={[a.location.lat, a.location.lon]} radiusM={m.radius_km * 1000} points={pts} />
          <Legend2 items={segs.map((s) => [s.segment, col(s.segment)])} /></Card>
        <div className="grid" style={{ alignContent: "start" }}>
          <Card title="Indicator by customer group" tag="Retrieved fact">
            <div className="seg">{segs.map((s) => (
              <div key={s.segment}><div style={{ display: "flex", justifyContent: "space-between" }}><b>{s.segment}</b><span className="mono small">{s.count} places · weight {s.weight}</span></div>
                <Meter value={s.weighted} max={mx} color={col(s.segment)} /></div>))}</div>
          </Card>
          <Card title="Most common place types" tag="Retrieved fact">
            {m.poi_types.length ? <BarChart data={{ labels: m.poi_types.map((t) => t.type.replace(/_/g, " ")), datasets: [{ data: m.poi_types.map((t) => t.count), backgroundColor: m.poi_types.map((t) => col(t.segment)) }] }}
              options={{ indexAxis: "y", plugins: { legend: { display: false } } }} tall /> : <p className="muted">No matching places were mapped in this radius.</p>}
          </Card>
        </div>
      </div>
    </div>
  );
}

export function Competition({ a }: { a: Analysis }) {
  const cp = a.competition, c: [number, number] = [a.location.lat, a.location.lon];
  const pts = [...a.market.pois.slice(0, 120).map((p) => ({ lat: p.lat, lon: p.lon, color: "#9fb8a9", label: `${poiName(p)} (customer place)`, radius: 3 })),
    ...cp.list.map((p) => ({ lat: p.lat, lon: p.lon, color: C.orange, label: `${poiName(p)} · ${dist(p.distance_m)}`, radius: 7 }))];
  return (
    <div className="grid fade">
      <PageHead title="Competition" intro={`Mapped ${a.input.category.toLowerCase()} competitors within ${a.market.radius_km} km, using tags ${a.category_spec.competitor_filters.join(", ")}.`} />
      {cp.total === 0 && <Banner kind="info">No competitors are mapped in this radius. OpenStreetMap can be incomplete, so verify on the ground.</Banner>}
      <div className="grid g4">
        <Stat label="Competitors" value={cp.total} sub={`${cp.named} named · ${cp.unnamed} unnamed`} tag="Retrieved fact" />
        <Stat label="Density" value={`${cp.density_per_km2}/km²`} tag="Calculated estimate" />
        <Stat label="Within 500 m / 1 km" value={`${cp.within_500m} / ${cp.within_1km}`} tag="Retrieved fact" />
        <Stat label="Nearest" value={dist(cp.nearest_m)} tag="Retrieved fact" />
      </div>
      <div className="grid g2">
        <Card title="Competitor map" tag="Retrieved fact"><MapView center={c} radiusM={a.market.radius_km * 1000} points={pts} />
          <Legend2 items={[["Competitor", C.orange], ["Customer-generating place", "#9fb8a9"]]} /></Card>
        <div className="grid" style={{ alignContent: "start" }}>
          <Card title="Competitors by distance" tag="Retrieved fact"><BarChart data={{ labels: cp.rings.map((r) => r.label), datasets: [{ data: cp.rings.map((r) => r.competitors), backgroundColor: C.orange }] }} options={{ plugins: { legend: { display: false } } }} /></Card>
          <Card title="Competition pressure" tag="Calculated estimate">
            <Meter value={Math.min(cp.pressure, 16)} max={16} color={C.orange} />
            <p className="small muted">Pressure = competitors within 1 km + 0.25 × competitors beyond. Value: <b>{cp.pressure}</b>. The score formula is on the Feasibility page.</p>
          </Card>
        </div>
      </div>
      <Card title="Nearest competitors" tag="Retrieved fact"><div className="tbl"><table><thead><tr><th>Name</th><th>Type</th><th className="num">Distance</th><th>OSM</th></tr></thead><tbody>
        {cp.list.slice(0, 20).map((p) => <tr key={p.id}><td>{poiName(p)}</td><td>{p.kind.replace(/_/g, " ")}</td><td className="num">{dist(p.distance_m)}</td><td><a href={`https://www.openstreetmap.org/${p.id}`} target="_blank" rel="noreferrer">{p.id}</a></td></tr>)}</tbody></table></div>
        <p className="small muted">Ratings and reviews are not part of OpenStreetMap, so none are shown. Showing {Math.min(20, cp.list.length)} of {cp.total}.</p></Card>
    </div>
  );
}
