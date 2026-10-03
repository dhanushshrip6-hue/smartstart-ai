"""Deterministic analysis engine. No network, no AI. Every number is reproducible from inputs + retrieved OSM data."""
import math
from collections import Counter

WEIGHTS = {"market": 0.25, "location_fit": 0.20, "competition": 0.15, "accessibility": 0.15, "revenue": 0.20, "risk": 0.05}
LABELS = {"market": "Market", "location_fit": "Location Fit", "competition": "Competition",
          "accessibility": "Customer Accessibility", "revenue": "Revenue", "risk": "Risk"}
SCENARIOS = {"low": 0.6, "medium": 1.0, "high": 1.3}
RINGS = [(0, 0.5), (0.5, 1), (1, 2), (2, 3), (3, 5), (5, 10)]


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def sat(x, k):
    return 100 * (1 - math.exp(-max(x, 0) / k))


def haversine_m(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(d - b) / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


def _match(tags, filters):
    for k, v in filters:
        if k in tags and (v is None or tags[k] in v):
            return k if (v is None and tags[k] in ("yes", "")) else (tags[k] if tags[k] != "yes" else k)
    return None


# ---------------- financials ----------------
def financials(inp, mult=1.0):
    fixed = sum(inp["expenses"].values())
    v = inp["variable_cost_pct"] / 100
    scen = {}
    for name, m in SCENARIOS.items():
        cpd = inp["customers_per_day"] * m * mult
        rev = inp["avg_price"] * cpd * inp["working_days"]
        profit = rev * (1 - v) - fixed
        scen[name] = {
            "multiplier": m, "customers_per_day": cpd, "revenue": rev, "variable_costs": rev * v,
            "fixed_costs": fixed, "profit": profit, "margin": profit / rev if rev else 0.0,
            "payback_months": inp["budget"] / profit if profit > 0 else None,
            "cash_curve": [-inp["budget"] + profit * mth for mth in range(0, 25)],
        }
    contrib = inp["avg_price"] * (1 - v) * inp["working_days"]
    be_cpd = fixed / contrib if contrib > 0 else None
    return {
        "scenarios": scen, "fixed_monthly": fixed, "variable_pct": inp["variable_cost_pct"],
        "breakeven_customers_per_day": be_cpd,
        "breakeven_revenue_monthly": fixed / (1 - v) if v < 1 else None,
        "breakeven_curve": [
            {"customers_per_day": x, "revenue": inp["avg_price"] * x * inp["working_days"],
             "total_cost": fixed + inp["avg_price"] * x * inp["working_days"] * v}
            for x in [inp["customers_per_day"] * 1.6 * i / 16 for i in range(17)]],
    }


# ---------------- scoring ----------------
def demand_index(m):
    return (sat(m["wR"] / (math.pi * m["radius_km"] ** 2), 10) + sat(m["w1k"], 8)) / 2


def evaluate(inp, m, ratio=1.0):
    """Feasibility components for one location from count-based metrics `m`."""
    fin = financials(inp, ratio)
    med = fin["scenarios"]["medium"]
    area = math.pi * m["radius_km"] ** 2
    dens = m["wR"] / area
    pressure = m["c1k"] + 0.25 * max(m["cR"] - m["c1k"], 0)
    margin_s = 100 * clamp(med["margin"] / 0.30)
    pay = med["payback_months"]
    pay_s = 100 * clamp(1 - pay / 36) if pay else 0.0
    be = fin["breakeven_customers_per_day"]
    be_ratio = (be / med["customers_per_day"]) if (be is not None and med["customers_per_day"]) else None
    risk_s = 100 * clamp((1 - be_ratio) / 0.5) if be_ratio is not None else 0.0
    raw = {
        "market": (sat(dens, 10), f"100·(1−e^(−d/10)) where d = weighted customer-POI density = {dens:.2f} per km² "
                   f"({m['wR']:.1f} weighted POIs over {area:.1f} km²)"),
        "location_fit": (sat(m["w1k"], 8), f"100·(1−e^(−w/8)) where w = weighted customer POIs within 1 km = {m['w1k']:.1f}"),
        "competition": (100 * math.exp(-pressure / 8), f"100·e^(−p/8) where p = competitors within 1 km ({m['c1k']}) + 0.25 × competitors beyond 1 km "
                        f"({max(m['cR'] - m['c1k'], 0)}) = {pressure:.2f}. Higher score = less mapped competition."),
        "accessibility": (sat(m["t1k"], 5), f"100·(1−e^(−t/5)) where t = public-transport stops/stations within 1 km = {m['t1k']}"),
        "revenue": (0.5 * margin_s + 0.5 * pay_s, f"50% margin score ({margin_s:.0f}; medium margin {med['margin'] * 100:.1f}%, 30% = 100) + "
                    f"50% payback score ({pay_s:.0f}; payback {'n/a' if not pay else f'{pay:.1f} months'}, 36 months = 0)"),
        "risk": (risk_s, "100 × clamp((1 − break-even/expected customers per day) / 0.5). "
                 + ("Break-even cannot be reached at this price." if be_ratio is None else f"Break-even/expected = {be_ratio:.2f}.")),
    }
    comps, total = [], 0.0
    for k, w in WEIGHTS.items():
        s, expl = raw[k]
        comps.append({"key": k, "label": LABELS[k], "weight": w, "score": round(s, 1), "contribution": round(s * w, 2), "explanation": expl})
        total += s * w
    return {"score": round(total, 1), "components": comps, "financials": fin}


def band(score):
    if score >= 70:
        return "Strong indicators"
    if score >= 50:
        return "Mixed indicators"
    return "Weak indicators"


# ---------------- primary-location processing ----------------
def process_elements(elements, center, radius_m, spec):
    lat0, lon0 = center
    comps, segs, transit = [], {s: [] for s in spec["segments"]}, []
    for e in elements:
        t = e.get("tags", {})
        lat, lon = (e.get("lat"), e.get("lon")) if "lat" in e else ((e.get("center") or {}).get("lat"), (e.get("center") or {}).get("lon"))
        if lat is None:
            continue
        d = haversine_m(lat0, lon0, lat, lon)
        if d > radius_m:
            continue
        base = {"id": f"{e['type']}/{e['id']}", "name": t.get("name"), "lat": lat, "lon": lon, "distance_m": round(d)}
        k = _match(t, spec["competitor"])
        if k:
            comps.append({**base, "kind": k, "brand": t.get("brand"), "opening_hours": t.get("opening_hours"), "website": t.get("website")})
        for s, sd in spec["segments"].items():
            k = _match(t, sd["filters"])
            if k:
                segs[s].append({**base, "kind": k, "segment": s})
        k = _match(t, spec["transit"])
        if k:
            transit.append({**base, "kind": k})
    for lst in [comps, transit, *segs.values()]:
        lst.sort(key=lambda x: x["distance_m"])
    return comps, segs, transit


def build_result(inp, geo, elements, truncated, spec, alt_block, retrieved_at):
    R = inp["poi_radius_km"] * 1000
    comps, segs, transit = process_elements(elements, (geo["lat"], geo["lon"]), R, spec)
    area = math.pi * inp["poi_radius_km"] ** 2
    wR = sum(len(v) * spec["segments"][s]["weight"] for s, v in segs.items())
    w1k = sum(sum(1 for x in v if x["distance_m"] <= 1000) * spec["segments"][s]["weight"] for s, v in segs.items())
    c1k = sum(1 for c in comps if c["distance_m"] <= 1000)
    t1k = sum(1 for t in transit if t["distance_m"] <= 1000)
    m = {"radius_km": inp["poi_radius_km"], "wR": wR, "w1k": w1k, "cR": len(comps), "c1k": c1k, "t1k": t1k}
    ev = evaluate(inp, m)

    seg_rows = []
    for s, v in segs.items():
        w = spec["segments"][s]["weight"]
        seg_rows.append({
            "segment": s, "weight": w, "count": len(v), "within_500m": sum(1 for x in v if x["distance_m"] <= 500),
            "within_1km": sum(1 for x in v if x["distance_m"] <= 1000), "weighted": round(len(v) * w, 1),
            "nearest_m": v[0]["distance_m"] if v else None, "top": v[:8]})
    kinds = Counter((x["segment"], x["kind"]) for v in segs.values() for x in v)
    poi_types = [{"segment": s, "type": k, "count": n} for (s, k), n in kinds.most_common(14)]
    all_pois = sorted((x for v in segs.values() for x in v), key=lambda x: x["distance_m"])[:350]
    rings = []
    for lo, hi in RINGS:
        if lo * 1000 >= R:
            break
        hi = min(hi, inp["poi_radius_km"])
        rings.append({"label": f"{lo:g}–{hi:g} km",
                      "competitors": sum(1 for c in comps if lo * 1000 < c["distance_m"] <= hi * 1000 or (lo == 0 and c["distance_m"] == 0)),
                      "customer_pois": sum(1 for x in all_pois_full(segs) if lo * 1000 < x["distance_m"] <= hi * 1000 or (lo == 0 and x["distance_m"] == 0))})
    named = sum(1 for c in comps if c["name"])
    competition = {
        "total": len(comps), "named": named, "unnamed": len(comps) - named, "density_per_km2": round(len(comps) / area, 3),
        "within_500m": sum(1 for c in comps if c["distance_m"] <= 500), "within_1km": c1k,
        "within_3km": sum(1 for c in comps if c["distance_m"] <= 3000), "nearest_m": comps[0]["distance_m"] if comps else None,
        "pressure": round(m["c1k"] + 0.25 * max(m["cR"] - m["c1k"], 0), 2), "rings": rings, "list": comps[:300],
        "ratings_available": False,
    }
    market = {
        "radius_km": inp["poi_radius_km"], "area_km2": round(area, 2), "weighted_total": round(wR, 1),
        "weighted_density_per_km2": round(wR / area, 2), "weighted_within_1km": round(w1k, 1),
        "segments": seg_rows, "poi_types": poi_types, "pois": all_pois,
        "transit": {"within_1km": t1k, "total": len(transit), "nearest_m": transit[0]["distance_m"] if transit else None, "list": transit[:60]},
    }
    top = sorted(seg_rows, key=lambda r: r["weighted"], reverse=True)
    customers = {"target_text": inp["target_customers"], "segments": seg_rows, "dominant_segment": top[0]["segment"] if top and top[0]["count"] else None,
                 "note": "Counts show mapped places that attract each customer group. They do not measure footfall, population or spending."}

    result = {
        "input": inp,
        "location": {k: geo[k] for k in ("lat", "lon", "display_name", "address", "osm_type", "osm_id", "source")},
        "category_spec": {"competitor_filters": [f"{k}={'|'.join(v) if v else '*'}" for k, v in spec["competitor"]],
                          "segments": {s: {"weight": d["weight"], "filters": [f"{k}={'|'.join(v) if v else '*'}" for k, v in d["filters"]]} for s, d in spec["segments"].items()}},
        "retrieval": {"retrieved_at": retrieved_at, "elements_returned": len(elements), "truncated": truncated,
                      "sources": ["Nominatim (geocoding)", "Overpass API (OpenStreetMap POIs)"]},
        "metrics": m, "market": market, "competition": competition, "customers": customers,
        "financials": ev["financials"],
        "feasibility": {"score": ev["score"], "band": band(ev["score"]), "components": ev["components"],
                        "note": "Indicative screening score computed from fixed formulas. It is not a prediction of success."},
        "alternatives": alt_block(m, ev) if alt_block else {"status": "unavailable"},
    }
    result["swot"] = swot(result)
    result["highlights"] = highlights(result)
    result["limitations"] = limitations(result)
    return result


def all_pois_full(segs):
    return [x for v in segs.values() for x in v]


# ---------------- alternatives ----------------
def pick_candidates(raw, center, radius_m, limit=6):
    min_sep = max(1500, radius_m * 0.12)
    rows = []
    for c in raw:
        d = haversine_m(center[0], center[1], c["lat"], c["lon"])
        if min_sep <= d <= radius_m:
            rows.append({**c, "distance_km": round(d / 1000, 2)})
    from categories import SEGMENTS  # noqa: F401  (keeps import graph simple)
    rank = {"town": 0, "suburb": 1, "neighbourhood": 2, "quarter": 2, "village": 3, "city": 4}
    rows.sort(key=lambda r: (rank.get(r["place_type"], 9), r["distance_km"]))
    chosen, names = [], set()
    for r in rows:
        if r["name"].lower() in names:
            continue
        if all(haversine_m(r["lat"], r["lon"], c["lat"], c["lon"]) >= min_sep for c in chosen):
            chosen.append(r)
            names.add(r["name"].lower())
        if len(chosen) >= limit:
            break
    return chosen


def make_alt_block(inp, spec, cands, counts):
    def block(m_primary, ev_primary):
        di0 = demand_index(m_primary)
        rows = [{"name": "Selected location", "selected": True, "place_type": None, "distance_km": 0, "lat": None, "lon": None,
                 "competitors_radius": m_primary["cR"], "competitors_1km": m_primary["c1k"], "customer_poi_weighted": round(m_primary["wR"], 1),
                 "customer_poi_weighted_1km": round(m_primary["w1k"], 1), "transit_1km": m_primary["t1k"],
                 "scores": {c["key"]: c["score"] for c in ev_primary["components"]}, "feasibility": ev_primary["score"],
                 "revenue_medium": ev_primary["financials"]["scenarios"]["medium"]["revenue"],
                 "profit_medium": ev_primary["financials"]["scenarios"]["medium"]["profit"], "demand_ratio": 1.0}]
        for c, k in zip(cands, counts):
            wR = sum(k["seg_R"][s] * d["weight"] for s, d in spec["segments"].items())
            w1 = sum(k["seg_1k"][s] * d["weight"] for s, d in spec["segments"].items())
            m = {"radius_km": inp["poi_radius_km"], "wR": wR, "w1k": w1, "cR": k["cR"], "c1k": k["c1k"], "t1k": k["t1k"]}
            ratio = clamp((demand_index(m) + 20) / (di0 + 20), 0.75, 1.25)
            ev = evaluate(inp, m, ratio)
            med = ev["financials"]["scenarios"]["medium"]
            rows.append({"name": c["name"], "selected": False, "place_type": c["place_type"], "distance_km": c["distance_km"],
                         "lat": c["lat"], "lon": c["lon"], "osm_id": c["osm_id"], "competitors_radius": k["cR"], "competitors_1km": k["c1k"],
                         "customer_poi_weighted": round(wR, 1), "customer_poi_weighted_1km": round(w1, 1), "transit_1km": k["t1k"],
                         "segments_radius": k["seg_R"], "scores": {x["key"]: x["score"] for x in ev["components"]}, "feasibility": ev["score"],
                         "revenue_medium": med["revenue"], "profit_medium": med["profit"], "demand_ratio": round(ratio, 2)})
        return {"status": "ok", "radius_km": inp["alt_radius_km"], "poi_radius_km": inp["poi_radius_km"], "rows": rows,
                "method": ("Candidates are named OpenStreetMap place nodes (suburb, neighbourhood, town, village) inside the alternative radius, "
                           "spaced apart. Each candidate point is scored with the same count-based formulas as the selected location, using exact "
                           "Overpass counts within the POI radius. Revenue potential scales your customers/day by the ratio of a demand index "
                           "(market + location fit) versus the selected location, limited to 0.75×–1.25×. Rows are not ranked."),
                "caveats": "Candidate availability, rent and zoning are unknown. Straight-line distances only."}
    return block


# ---------------- text blocks ----------------
def swot(r):
    comp = {c["key"]: c for c in r["feasibility"]["components"]}
    m, mk, cp, fin = r["metrics"], r["market"], r["competition"], r["financials"]
    med = fin["scenarios"]["medium"]
    S, W, O, T = [], [], [], []
    R = "Retrieved fact"
    C = "Calculated estimate"
    U = "User assumption"
    top = sorted(mk["segments"], key=lambda x: x["count"], reverse=True)
    if top and top[0]["count"]:
        (S if top[0]["count"] >= 5 else O).append({"text": f"{top[0]['count']} mapped '{top[0]['segment']}' places within {mk['radius_km']} km (nearest {top[0]['nearest_m']} m).", "basis": R})
    if comp["market"]["score"] >= 60:
        S.append({"text": f"Customer-POI density is {mk['weighted_density_per_km2']} weighted places/km² (market score {comp['market']['score']}).", "basis": C})
    elif comp["market"]["score"] < 35:
        W.append({"text": f"Few customer-generating places are mapped nearby ({mk['weighted_density_per_km2']} weighted/km²).", "basis": R})
    if m["w1k"] >= 8:
        S.append({"text": f"Dense customer-generating surroundings within 1 km (weighted {m['w1k']:.1f}).", "basis": R})
    elif m["w1k"] < 3:
        W.append({"text": f"Few customer-generating places within walking range of the site (weighted {m['w1k']:.1f} within 1 km).", "basis": R})
    if cp["total"] == 0:
        S.append({"text": f"No mapped {r['input']['category']} competitors within {mk['radius_km']} km. OSM may be incomplete.", "basis": R})
    elif cp["within_500m"] == 0:
        O.append({"text": f"No mapped direct competitor within 500 m (nearest {cp['nearest_m']} m).", "basis": R})
    if cp["within_500m"] >= 3:
        T.append({"text": f"{cp['within_500m']} mapped competitors within 500 m.", "basis": R})
    elif cp["within_1km"] >= 6:
        T.append({"text": f"{cp['within_1km']} mapped competitors within 1 km.", "basis": R})
    if cp["total"] and comp["competition"]["score"] >= 60:
        S.append({"text": f"Limited mapped competition pressure (competition score {comp['competition']['score']}).", "basis": C})
    if m["t1k"] >= 5:
        S.append({"text": f"{m['t1k']} public-transport stops/stations within 1 km.", "basis": R})
    elif m["t1k"] == 0:
        W.append({"text": "No mapped public-transport stop within 1 km.", "basis": R})
    if med["profit"] > 0:
        S.append({"text": f"Medium scenario is profitable at your inputs (margin {med['margin'] * 100:.1f}%).", "basis": C})
    else:
        W.append({"text": "Medium scenario does not cover your stated expenses.", "basis": C})
    be = fin["breakeven_customers_per_day"]
    if be is not None and be > r["input"]["customers_per_day"] * 0.8:
        T.append({"text": f"Break-even needs {be:.1f} customers/day versus your expectation of {r['input']['customers_per_day']:g}.", "basis": C})
    low = fin["scenarios"]["low"]
    if low["profit"] < 0:
        T.append({"text": "Low scenario (60% of expected customers) produces a monthly loss.", "basis": C})
    pb = med["payback_months"]
    if pb:
        (S if pb <= 18 else W).append({"text": f"Medium-scenario payback of your budget: {pb:.1f} months.", "basis": C})
    T.append({"text": "Expected customers/day, price and expenses are your own assumptions and are not verified.", "basis": U})
    if r["retrieval"]["truncated"]:
        T.append({"text": "Overpass results hit the retrieval cap. Counts are lower bounds.", "basis": R})
    O.append({"text": f"Your target customers: {r['input']['target_customers']}.", "basis": U})
    return {"strengths": S, "weaknesses": W, "opportunities": O, "threats": T}


def highlights(r):
    m, mk, cp = r["metrics"], r["market"], r["competition"]
    med = r["financials"]["scenarios"]["medium"]
    cur = r["input"]["currency"]
    out = [
        {"text": f"Feasibility index {r['feasibility']['score']}/100 ({r['feasibility']['band']}).", "basis": "Calculated estimate"},
        {"text": f"{cp['total']} mapped competitors within {mk['radius_km']} km; nearest {cp['nearest_m'] if cp['nearest_m'] is not None else 'n/a'} m.", "basis": "Retrieved fact"},
        {"text": f"{sum(s['count'] for s in mk['segments'])} customer-generating places and {mk['transit']['total']} transit stops mapped within {mk['radius_km']} km.", "basis": "Retrieved fact"},
        {"text": f"Medium scenario: {cur} {med['revenue']:,.0f} revenue and {cur} {med['profit']:,.0f} profit per month.", "basis": "Calculated estimate"},
    ]
    be = r["financials"]["breakeven_customers_per_day"]
    out.append({"text": f"Break-even at {be:.1f} customers/day." if be is not None else "Break-even is not reachable at this price and variable cost.", "basis": "Calculated estimate"})
    return out


def limitations(r):
    L = [
        "OpenStreetMap is volunteer-maintained. Missing, unnamed or outdated places are possible, and competitor counts may be understated.",
        "OSM contains no foot traffic, population, income, rent, ratings or reviews. None are shown and none were estimated.",
        "Customer-POI weights, scoring curves and thresholds are fixed model parameters, not market research. They are fixed in the code.",
        "Customers/day, price, expenses and budget are user assumptions. Low/High scenarios apply fixed multipliers (60% / 130%).",
        "Distances are straight-line, not travel time. A place mapped as both a node and a building outline may be counted twice.",
    ]
    if r["retrieval"]["truncated"]:
        L.insert(0, f"Overpass results reached the retrieval cap of {r['retrieval']['elements_returned']} elements. Counts are lower bounds. Use a smaller radius for complete data.")
    if r["alternatives"].get("status") != "ok":
        L.append("Alternative locations could not be retrieved for this analysis.")
    else:
        L.append("Alternative candidates are OSM place names, not verified vacant or leasable sites.")
    return L
