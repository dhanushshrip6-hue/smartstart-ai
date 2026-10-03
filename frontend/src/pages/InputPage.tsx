import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api";
import { Banner } from "../components/ui";

const EXP = ["rent", "salaries", "utilities", "marketing", "other"] as const;
const blank = {
  business_name: "", category: "Cafe / Coffee Shop", competitor_tag: "", description: "", target_customers: "", location: "", budget: "", avg_price: "",
  customers_per_day: "", working_days: "26", variable_cost_pct: "35", currency: "INR", poi_radius_km: 3, alt_radius_km: 10,
  expenses: { rent: "", salaries: "", utilities: "", marketing: "", other: "" } as Record<string, string>,
};
const example = {
  ...blank, business_name: "Brew & Bloom", description: "Specialty coffee and light snacks for people studying and working nearby.", target_customers: "College students and office workers aged 18-35",
  location: "T Nagar, Chennai", budget: "1500000", avg_price: "180", customers_per_day: "120",
  expenses: { rent: "60000", salaries: "90000", utilities: "15000", marketing: "10000", other: "8000" },
};
const STAGES = ["Geocoding the location with Nominatim", "Retrieving nearby places from Overpass", "Finding alternative locations", "Calculating revenue, break-even and the feasibility index"];

function Topo() {
  return (
    <svg className="topo" viewBox="0 0 600 300" fill="none" stroke="#5e7585" strokeWidth="1" aria-hidden="true">
      {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => <path key={i} d={`M-20 ${250 - i * 26} C 120 ${210 - i * 30}, 200 ${290 - i * 22}, 320 ${230 - i * 26} S 520 ${180 - i * 24}, 640 ${220 - i * 28}`} />)}
    </svg>
  );
}

function Field({ k, label, hint, type = "text", full, f, set, errs }: any) {
  return (
    <label className={`f ${full ? "full" : ""}`}>{label}{hint && <small>{hint}</small>}
      <input className={errs[k] ? "bad" : ""} type={type} value={f[k]} onChange={(e) => set(k, e.target.value)} inputMode={type === "number" ? "decimal" : undefined} />
      {errs[k] && <span className="ferr" role="alert">{errs[k]}</span>}</label>
  );
}

export default function InputPage() {
  const nav = useNavigate();
  const [f, setF] = useState<typeof blank>(blank);
  const [cats, setCats] = useState<string[]>(["Cafe / Coffee Shop"]);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [top, setTop] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState(0);
  const timer = useRef<number>();

  useEffect(() => { api.catalog().then((c) => setCats(c.categories)).catch(() => {}); }, []);
  useEffect(() => () => clearInterval(timer.current), []);

  const set = (k: string, v: any) => { setF((p) => ({ ...p, [k]: v })); setErrs((e) => { const n = { ...e }; delete n[k]; return n; }); };
  const setEx = (k: string, v: string) => { setF((p) => ({ ...p, expenses: { ...p.expenses, [k]: v } })); setErrs((e) => { const n = { ...e }; delete n["expenses." + k]; return n; }); };
  const E = (k: string) => errs[k] ? <span className="ferr" role="alert">{errs[k]}</span> : null;

  function clientCheck() {
    const e: Record<string, string> = {};
    const req = (k: string, v: string, m: string) => { if (!String(v).trim()) e[k] = m; };
    req("business_name", f.business_name, "Enter the business name."); req("description", f.description, "Describe the business in a sentence or two.");
    req("target_customers", f.target_customers, "Say who you want to serve."); req("location", f.location, "Enter an area, street or landmark with the city.");
    ["budget", "avg_price", "customers_per_day", "working_days"].forEach((k) => { const v = Number((f as any)[k]); if (!(v > 0)) e[k] = "Enter a number above 0."; });
    EXP.forEach((k) => { const raw = f.expenses[k]; if (raw !== "" && !(Number(raw) >= 0)) e["expenses." + k] = "Enter 0 or more."; });
    if (f.category.startsWith("Other") && !/^[a-z0-9_:]+=[a-z0-9_]+$/i.test(f.competitor_tag)) e.competitor_tag = "Use an OSM tag such as shop=florist.";
    return e;
  }

  async function submit(ev: React.FormEvent) {
    ev.preventDefault();
    setTop(null);
    const e = clientCheck();
    if (Object.keys(e).length) { setErrs(e); setTop("Fix the highlighted fields to continue."); document.querySelector(".bad")?.scrollIntoView({ block: "center" }); return; }
    const body = {
      ...f, budget: Number(f.budget), avg_price: Number(f.avg_price), customers_per_day: Number(f.customers_per_day), working_days: Number(f.working_days),
      variable_cost_pct: Number(f.variable_cost_pct || 0), expenses: Object.fromEntries(EXP.map((k) => [k, Number(f.expenses[k] || 0)])),
    };
    setBusy(true); setStage(0);
    timer.current = window.setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 5000);
    try {
      const r = await api.create(body);
      nav(`/analysis/${r.id}/overview`);
    } catch (x) {
      const ex = x as ApiError;
      setErrs(ex.fields || {}); setTop(ex.message);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally { clearInterval(timer.current); setBusy(false); }
  }

  const bad = (k: string) => (errs[k] ? "bad" : "");
  const Pick = ({ k, opts, suffix }: { k: "poi_radius_km" | "alt_radius_km"; opts: number[]; suffix: string }) => (
    <div className="seg-pick" role="group">{opts.map((o) => <button type="button" key={o} aria-pressed={f[k] === o} onClick={() => set(k, o)}>{o} {suffix}</button>)}</div>
  );

  return (
    <div className="landing">
      <aside className="hero">
        <div style={{ position: "relative" }}>
          <div style={{ fontWeight: 800, fontSize: "1.1rem", marginBottom: 40 }}>SmartStart <span style={{ color: "var(--orange)" }}>AI</span></div>
          <h1>Check a location before you sign the lease.</h1>
          <p style={{ marginTop: 16 }}>Enter your business plan. SmartStart AI geocodes the site, reads nearby places from OpenStreetMap, calculates revenue and break-even, and scores feasibility with a fixed formula.</p>
        </div>
        <div className="flow" style={{ zIndex: 1 }}><b>Input</b>→<span>Analysis workspace (12 pages)</span>→<span>Final report</span>→<span>PDF</span></div>
        <Topo />
      </aside>
      <main className="formwrap">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 18 }}>
          <h2>Describe your startup</h2>
          <span style={{ display: "flex", gap: 8 }}><button type="button" className="btn ghost sm" onClick={() => { setF(example); setErrs({}); }}>Fill example inputs</button><Link className="btn ghost sm" to="/history">Past analyses</Link></span>
        </div>
        {top && <Banner kind="err">{top}</Banner>}
        <form onSubmit={submit} noValidate>
          <fieldset><legend>The business</legend><div className="fields">
            <Field f={f} set={set} errs={errs} k="business_name" label="Business name" />
            <label className="f">Category<select value={f.category} onChange={(e) => set("category", e.target.value)}>{cats.map((c) => <option key={c}>{c}</option>)}</select></label>
            {f.category.startsWith("Other") && <Field f={f} set={set} errs={errs} k="competitor_tag" label="Competitor OSM tag" hint="Places with this tag count as competitors, e.g. shop=florist" full />}
            <label className={`f full`}>Description<textarea className={bad("description")} rows={3} value={f.description} onChange={(e) => set("description", e.target.value)} />{E("description")}</label>
            <Field f={f} set={set} errs={errs} k="target_customers" label="Target customers" hint="Who you want to serve" full />
          </div></fieldset>
          <fieldset><legend>Where</legend><div className="fields">
            <Field f={f} set={set} errs={errs} k="location" label="Location" hint="Area, street or landmark, plus city" full />
            <div className="f"><span>Nearby POI radius</span><Pick k="poi_radius_km" opts={[1, 3, 5, 10]} suffix="km" /><small className="muted">Places and competitors are counted inside this radius.</small></div>
            <div className="f"><span>Alternative-location radius</span><Pick k="alt_radius_km" opts={[5, 10, 15]} suffix="km" /><small className="muted">Where to look for other candidate areas.</small></div>
          </div></fieldset>
          <fieldset><legend>Money and customers (your assumptions)</legend><div className="fields">
            <label className="f">Currency<select value={f.currency} onChange={(e) => set("currency", e.target.value)}>{["INR", "USD", "EUR", "GBP", "AED", "SGD"].map((c) => <option key={c}>{c}</option>)}</select></label>
            <Field f={f} set={set} errs={errs} k="budget" label="Initial budget" type="number" hint="Total money to set up" />
            <Field f={f} set={set} errs={errs} k="avg_price" label="Average price per customer" type="number" />
            <Field f={f} set={set} errs={errs} k="customers_per_day" label="Expected customers per day" type="number" />
            <Field f={f} set={set} errs={errs} k="working_days" label="Working days per month" type="number" />
            <Field f={f} set={set} errs={errs} k="variable_cost_pct" label="Variable cost, % of revenue" type="number" hint="Ingredients, stock, payment fees" />
          </div></fieldset>
          <fieldset><legend>Monthly fixed expenses</legend><div className="fields">
            {EXP.map((k) => <label key={k} className="f" style={{ textTransform: "capitalize" }}>{k}<input className={bad("expenses." + k)} inputMode="decimal" value={f.expenses[k]} onChange={(e) => setEx(k, e.target.value)} placeholder="0" />{E("expenses." + k)}</label>)}
          </div></fieldset>
          <button className="btn" disabled={busy} style={{ padding: "13px 26px", fontSize: "1.02rem" }}>Start analysis</button>
          <p className="small muted" style={{ marginTop: 10 }}>Analysis uses live OpenStreetMap services and can take up to a minute for larger radii.</p>
        </form>
      </main>
      {busy && (
        <div className="overlay" role="status" aria-live="polite"><div>
          <div className="radar" /><h2>Analysing {f.location}</h2>
          <ul className="stages" style={{ textAlign: "left", display: "inline-grid" }}>
            {STAGES.map((s, i) => <li key={s} className={i < stage ? "done" : i === stage ? "now" : ""}><span>{i < stage ? "✓" : i === stage ? "●" : "○"}</span>{s}</li>)}
          </ul>
        </div></div>
      )}
    </div>
  );
}
