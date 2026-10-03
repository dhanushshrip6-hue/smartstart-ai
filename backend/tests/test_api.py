"""End-to-end API test with a fake network layer (Nominatim / Overpass / Gemini are mocked at the HTTP boundary)."""
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
LAT, LON = 13.0827, 80.2707


class FakeResp:
    def __init__(self, data, status=200):
        self._d, self.status_code = data, status

    def json(self):
        return self._d


def overpass_answer(q):
    if "out count" in q:
        n = len(re.findall(r"out count", q))
        return {"elements": [{"type": "count", "id": 0, "tags": {"total": str((i * 3) % 7 + 1)}} for i in range(n)]}
    if '"place"' in q:
        return {"elements": [
            {"type": "node", "id": 1, "lat": LAT + 0.03, "lon": LON, "tags": {"place": "suburb", "name": "Alpha Nagar"}},
            {"type": "node", "id": 2, "lat": LAT - 0.04, "lon": LON + 0.02, "tags": {"place": "neighbourhood", "name": "Beta Colony"}},
            {"type": "node", "id": 3, "lat": LAT, "lon": LON + 0.001, "tags": {"place": "suburb", "name": "TooClose"}},
        ]}
    els = []
    for i in range(8):
        els.append({"type": "node", "id": 100 + i, "lat": LAT + 0.002 * i, "lon": LON + 0.001, "tags": {"amenity": "cafe", **({"name": f"Cafe {i}"} if i % 2 else {})}})
    for i in range(6):
        els.append({"type": "node", "id": 200 + i, "lat": LAT - 0.003 * i, "lon": LON - 0.002, "tags": {"amenity": "college", "name": f"College {i}"}})
    els.append({"type": "way", "id": 300, "center": {"lat": LAT + 0.004, "lon": LON}, "tags": {"office": "company", "name": "Office"}})
    els.append({"type": "node", "id": 400, "lat": LAT, "lon": LON + 0.003, "tags": {"highway": "bus_stop"}})
    return {"elements": els}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "100")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    import osm
    import gemini

    def fake_get(url, **kw):
        if "/search" in url:
            if kw["params"]["q"].lower().startswith("nowhere"):
                return FakeResp([])
            return FakeResp([{"lat": str(LAT), "lon": str(LON), "display_name": "Chennai, Tamil Nadu, India", "address": {"city": "Chennai"}, "osm_type": "relation", "osm_id": 1, "category": "boundary", "type": "administrative"}])
        raise AssertionError(url)

    def fake_post(url, **kw):
        if "generativelanguage" in url:
            assert kw["headers"]["x-goog-api-key"] == "test-key"
            sent = kw["json"]["contents"][0]["parts"][0]["text"]
            assert "feasibility_score" in sent and "Cafe 1" in sent
            return FakeResp({"candidates": [{"content": {"parts": [{"text": json.dumps({k: f"Text for {k}.\n\nSecond paragraph." for k in gemini.SECTIONS})}]}}]})
        return FakeResp(overpass_answer(kw["data"]["data"]))

    monkeypatch.setattr(osm.requests, "get", fake_get)
    monkeypatch.setattr(osm.requests, "post", fake_post)
    monkeypatch.setattr(gemini.requests, "post", fake_post)
    monkeypatch.setattr(osm.time, "sleep", lambda s: None)
    import app as appmod
    appmod.db.init_db()
    return appmod.app.test_client()


PAYLOAD = {
    "business_name": "Brew & Co", "category": "Cafe / Coffee Shop", "description": "Specialty coffee and pastries near colleges.",
    "budget": 1500000, "target_customers": "College students and office workers", "location": "T Nagar, Chennai",
    "avg_price": 180, "customers_per_day": 120, "working_days": 26, "variable_cost_pct": 35,
    "expenses": {"rent": 60000, "salaries": 90000, "utilities": 15000, "marketing": 10000, "other": 8000},
    "poi_radius_km": 3, "alt_radius_km": 10, "currency": "INR",
}


def test_validation(client):
    r = client.post("/api/analyses", json={**PAYLOAD, "poi_radius_km": 2, "budget": -5, "business_name": ""})
    assert r.status_code == 422
    f = r.get_json()["fields"]
    assert {"poi_radius_km", "budget", "business_name"} <= set(f)
    assert client.post("/api/analyses", data="nope", content_type="text/plain").status_code == 400
    r = client.post("/api/analyses", json={**PAYLOAD, "category": "Other (custom OSM tag)", "competitor_tag": 'shop=x"];out;'})
    assert "competitor_tag" in r.get_json()["fields"]


def test_unknown_location(client):
    r = client.post("/api/analyses", json={**PAYLOAD, "location": "Nowhere land"})
    assert r.status_code == 422 and "location" in r.get_json()["fields"]


def test_full_flow(client):
    r = client.post("/api/analyses", json=PAYLOAD)
    assert r.status_code == 201, r.get_data(as_text=True)
    d = r.get_json()
    aid = d["id"]
    # facts
    assert d["competition"]["total"] == 8 and d["competition"]["named"] == 4 and d["competition"]["unnamed"] == 4
    assert d["metrics"]["t1k"] == 1
    # score is the exact weighted sum, bounded
    comps = d["feasibility"]["components"]
    assert abs(sum(c["weight"] for c in comps) - 1) < 1e-9
    assert abs(sum(c["score"] * c["weight"] for c in comps) - d["feasibility"]["score"]) < 0.1
    assert 0 <= d["feasibility"]["score"] <= 100
    # financial maths (medium): 180*120*26 = 561600 revenue
    med = d["financials"]["scenarios"]["medium"]
    assert round(med["revenue"]) == 561600
    assert round(med["profit"]) == round(561600 * 0.65 - 183000)
    assert round(d["financials"]["breakeven_customers_per_day"], 3) == round(183000 / (180 * 0.65 * 26), 3)
    # alternatives: TooClose excluded, no ranking words
    rows = d["alternatives"]["rows"]
    assert d["alternatives"]["status"] == "ok" and [x["name"] for x in rows] == ["Selected location", "Alpha Nagar", "Beta Colony"]
    assert "best" not in json.dumps(d["alternatives"]).lower() and "winner" not in json.dumps(d["alternatives"]).lower()
    assert set(d["swot"]) == {"strengths", "weaknesses", "opportunities", "threats"}
    # history / get
    assert client.get("/api/analyses").get_json()[0]["id"] == aid
    assert client.get(f"/api/analyses/{aid}").get_json()["ai"] is None
    assert client.get("/api/analyses/../etc").status_code == 404
    # AI
    a = client.post(f"/api/analyses/{aid}/ai")
    assert a.status_code == 200 and "executive_summary" in a.get_json()["sections"]
    assert client.get(f"/api/analyses/{aid}").get_json()["ai"]["model"]
    # PDF
    p = client.get(f"/api/analyses/{aid}/report.pdf")
    assert p.status_code == 200 and p.data[:5] == b"%PDF-" and p.mimetype == "application/pdf"
    from pypdf import PdfReader
    import io
    rd = PdfReader(io.BytesIO(p.data))
    text = "\n".join(pg.extract_text() for pg in rd.pages)
    for needle in ["Startup details", "Location and map", "Market analysis", "Competition", "Customer analysis", "Revenue analysis", "Expenses and profit",
                   "Break-even", "SWOT analysis", "Feasibility index", "Alternative locations", "Brew & Co"]:
        assert needle in text, needle
    assert "AI business analysis" not in text and "Gemini" not in text
    assert "Final summary" not in text and "Data limitations" not in text
    open("/tmp/sample_report.pdf", "wb").write(p.data)
    assert client.delete(f"/api/analyses/{aid}").status_code == 200
    assert client.get(f"/api/analyses/{aid}").status_code == 404


def test_ai_not_configured(client, monkeypatch):
    aid = client.post("/api/analyses", json=PAYLOAD).get_json()["id"]
    monkeypatch.setenv("GEMINI_API_KEY", "")
    r = client.post(f"/api/analyses/{aid}/ai")
    assert r.status_code == 503 and r.get_json()["code"] == "ai_not_configured"
    assert client.get(f"/api/analyses/{aid}/report.pdf").status_code == 200  # PDF works without AI


def test_overpass_down_keeps_alternatives_graceful(client, monkeypatch):
    import osm
    real = osm.requests.post

    def flaky(url, **kw):
        if '"place"' in kw["data"]["data"]:
            return type("R", (), {"status_code": 429, "json": lambda s: {}})()
        return real(url, **kw)
    monkeypatch.setattr(osm.requests, "post", flaky)
    r = client.post("/api/analyses", json=PAYLOAD)
    assert r.status_code == 201 and r.get_json()["alternatives"]["status"] == "unavailable"
    assert client.get(f"/api/analyses/{r.get_json()['id']}/report.pdf").status_code == 200


def test_overpass_total_failure(client, monkeypatch):
    import osm
    monkeypatch.setattr(osm.requests, "post", lambda url, **kw: type("R", (), {"status_code": 504, "json": lambda s: {}})())
    r = client.post("/api/analyses", json=PAYLOAD)
    assert r.status_code == 502 and r.get_json()["source"] == "overpass"


def test_overpass_timeout_fails_over_to_next_server(client, monkeypatch):
    """First server always times out; the next configured server must be used for every query, incl. alternatives."""
    import osm
    monkeypatch.setenv("OVERPASS_URLS", "https://slow.example/api/interpreter,https://overpass-api.de/api/interpreter")
    real, seen = osm.requests.post, []

    def post(url, **kw):
        seen.append(url)
        if "slow.example" in url:
            raise osm.requests.ReadTimeout("read timed out")
        return real(url, **kw)
    monkeypatch.setattr(osm.requests, "post", post)
    r = client.post("/api/analyses", json=PAYLOAD)
    assert r.status_code == 201
    d = r.get_json()
    assert d["alternatives"]["status"] == "ok" and len(d["alternatives"]["rows"]) == 3
    assert any("slow.example" in u for u in seen) and any("overpass-api.de" in u for u in seen)


def test_overpass_runtime_error_remark_tries_next_server(client, monkeypatch):
    import osm
    monkeypatch.setenv("OVERPASS_URLS", "https://busy.example/api/interpreter,https://overpass-api.de/api/interpreter")
    real = osm.requests.post

    def post(url, **kw):
        if "busy.example" in url:
            return FakeResp({"elements": [], "remark": "runtime error: Query timed out in \"query\" at line 1"})
        return real(url, **kw)
    monkeypatch.setattr(osm.requests, "post", post)
    d = client.post("/api/analyses", json=PAYLOAD).get_json()
    assert d["competition"]["total"] == 8 and d["alternatives"]["status"] == "ok"


def test_alternatives_keep_partial_results_when_later_chunk_fails(client, monkeypatch):
    """Candidate counts are fetched 2 at a time; if a later chunk fails, earlier candidates are still shown."""
    import osm
    real = osm.requests.post
    state = {"count_calls": 0}
    cands = [{"name": f"Area {i}", "place_type": "suburb", "lat": LAT + 0.03 * (i + 1), "lon": LON, "osm_id": i} for i in range(3)]
    monkeypatch.setattr(osm, "fetch_candidates", lambda *a, **k: cands)

    def post(url, **kw):
        if "out count" in kw["data"]["data"]:
            state["count_calls"] += 1
            if state["count_calls"] > 1:
                return type("R", (), {"status_code": 504, "json": lambda s: {}})()
        return real(url, **kw)
    monkeypatch.setattr(osm.requests, "post", post)
    d = client.post("/api/analyses", json=PAYLOAD).get_json()
    names = [x["name"] for x in d["alternatives"]["rows"]]
    assert d["alternatives"]["status"] == "ok" and names == ["Selected location", "Area 0", "Area 1"]
