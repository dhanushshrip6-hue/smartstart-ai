
import hashlib
import os
import threading
import time

import requests

import db

ELEMENT_CAP = 4000
_lock = threading.Lock()
_last_call = [0.0]


class UpstreamError(Exception):
    def __init__(self, message, source):
        super().__init__(message)
        self.source = source


def _ua():
    return {"User-Agent": os.getenv("NOMINATIM_USER_AGENT", "SmartStartAI/1.0 (set NOMINATIM_USER_AGENT in .env)")}


# ---------- Nominatim ----------
def geocode(query: str) -> dict | None:
    key = "geo:" + query.strip().lower()
    hit = db.cache_get(key, 7 * 86400)
    if hit is not None:
        return hit or None
    base = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org").rstrip("/")
    with _lock:  # Nominatim policy: max 1 request/second
        wait = 1.1 - (time.time() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        try:
            r = requests.get(f"{base}/search", headers=_ua(), timeout=20,
                             params={"q": query, "format": "jsonv2", "limit": 1, "addressdetails": 1})
        except requests.RequestException as e:
            raise UpstreamError(f"Nominatim is unreachable ({type(e).__name__}).", "nominatim")
        finally:
            _last_call[0] = time.time()
    if r.status_code != 200:
        raise UpstreamError(f"Nominatim returned HTTP {r.status_code}.", "nominatim")
    try:
        rows = r.json()
    except ValueError:
        raise UpstreamError("Nominatim returned an unreadable response.", "nominatim")
    if not rows:
        db.cache_set(key, {})
        return None
    x = rows[0]
    out = {
        "lat": float(x["lat"]), "lon": float(x["lon"]), "display_name": x.get("display_name", query),
        "address": x.get("address", {}), "osm_type": x.get("osm_type"), "osm_id": x.get("osm_id"),
        "place_class": x.get("category") or x.get("class"), "place_type": x.get("type"), "source": "Nominatim (OpenStreetMap)",
    }
    db.cache_set(key, out)
    return out


# ---------- Overpass ----------
def _flt(key, values):
    if values is None:
        return f'["{key}"]'
    if len(values) == 1:
        return f'["{key}"="{values[0]}"]'
    return f'["{key}"~"^({"|".join(values)})$"]'


def around_union(filters, radius_m, lat, lon):
    return "".join(f"nwr(around:{int(radius_m)},{lat:.6f},{lon:.6f}){_flt(k, v)};" for k, v in filters)


DEFAULT_OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
]


def _overpass_urls():
    cfg = [u.strip() for u in os.getenv("OVERPASS_URLS", "").split(",") if u.strip()]
    return cfg + [u for u in DEFAULT_OVERPASS if u not in cfg]  # configured servers first, spare mirrors last


def overpass(query: str, timeout: int = 100) -> dict:
    key = "ovp:" + hashlib.sha256(query.encode()).hexdigest()
    hit = db.cache_get(key, 86400)
    if hit is not None:
        return hit
    last = "no Overpass endpoint configured"
    for url in _overpass_urls():  # a timeout/error on one server -> try the next one
        try:
            r = requests.post(url, data={"data": query}, headers=_ua(), timeout=timeout)
            if r.status_code == 200:
                data = r.json()
                if "runtime error" in str(data.get("remark", "")).lower():
                    last = f"{url} query timed out or ran out of memory"
                    continue
                if "elements" in data:
                    db.cache_set(key, data)
                    return data
                last = f"{url} returned no elements ({data.get('remark', 'unknown remark')})"
            else:
                last = f"{url} returned HTTP {r.status_code}"
        except (requests.RequestException, ValueError) as e:
            last = f"{url} failed ({type(e).__name__})"
    raise UpstreamError(f"Overpass API unavailable: {last}", "overpass")


def fetch_area(lat, lon, radius_m, spec):
    filters = list(spec["competitor"]) + [f for s in spec["segments"].values() for f in s["filters"]] + list(spec["transit"])
    q = f"[out:json][timeout:90];({around_union(filters, radius_m, lat, lon)});out center tags {ELEMENT_CAP};"
    els = overpass(q)["elements"]
    return els, len(els) >= ELEMENT_CAP


PLACE_RANK = {"town": 0, "suburb": 1, "neighbourhood": 2, "quarter": 2, "village": 3, "city": 4}


def fetch_candidates(lat, lon, radius_m):
    q = (f'[out:json][timeout:40];node(around:{int(radius_m)},{lat:.6f},{lon:.6f})'
         f'["place"~"^(city|town|suburb|neighbourhood|quarter|village)$"]["name"];out tags center 400;')
    out = []
    for e in overpass(q, timeout=50)["elements"]:
        t = e.get("tags", {})
        if "lat" in e and t.get("name"):
            out.append({"name": t["name"], "place_type": t.get("place"), "lat": e["lat"], "lon": e["lon"], "osm_id": e["id"]})
    return out


def fetch_candidate_counts(cands, radius_m, spec):
    """Exact Overpass counts per candidate, requested 2 candidates at a time so each query stays light.
    Returns a list aligned with `cands`; entries are None for candidates that could not be retrieved."""
    segs = list(spec["segments"])
    per = 2 + 2 * len(segs) + 1
    out, last = [None] * len(cands), None
    for i in range(0, len(cands), 2):
        chunk = cands[i:i + 2]
        parts, n = ["[out:json][timeout:40];"], 0

        def cnt(filters, r, c):
            nonlocal n
            n += 1
            parts.append(f"({around_union(filters, r, c['lat'], c['lon'])})->.s{n};.s{n} out count;")

        for c in chunk:
            cnt(spec["competitor"], radius_m, c)
            cnt(spec["competitor"], 1000, c)
            for s in spec["segments"].values():
                cnt(s["filters"], radius_m, c)
                cnt(s["filters"], 1000, c)
            cnt(spec["transit"], 1000, c)
        try:
            els = [e for e in overpass("".join(parts), timeout=50)["elements"] if e.get("type") == "count"]
            if len(els) != per * len(chunk):
                raise UpstreamError("Overpass returned an unexpected number of count results.", "overpass")
        except UpstreamError as ex:
            last = ex
            break  # every server failed for this chunk; stop here and keep what was retrieved
        vals = [int(e["tags"]["total"]) for e in els]
        for j in range(len(chunk)):
            v = vals[j * per:(j + 1) * per]
            out[i + j] = {"cR": v[0], "c1k": v[1],
                          "seg_R": {s: v[2 + 2 * k] for k, s in enumerate(segs)},
                          "seg_1k": {s: v[3 + 2 * k] for k, s in enumerate(segs)}, "t1k": v[-1]}
    if all(o is None for o in out):
        raise last or UpstreamError("Overpass returned no candidate counts.", "overpass")
    return out
