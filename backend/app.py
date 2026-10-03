"""SmartStart AI – Flask API."""
import os
import re
import time
from collections import defaultdict, deque

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from flask import Flask, jsonify, request, send_from_directory, Response  # noqa: E402

import analysis  # noqa: E402
import categories  # noqa: E402
import db  # noqa: E402
import gemini  # noqa: E402
import osm  # noqa: E402
import report_pdf  # noqa: E402
from validators import ValidationError, validate  # noqa: E402

DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
db.init_db()
_hits = defaultdict(deque)
ID_RE = re.compile(r"^[a-f0-9]{12}$")


def rate_limited(bucket):
    limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "12"))
    q = _hits[(bucket, request.remote_addr)]
    now = time.time()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


def err(msg, status, **extra):
    return jsonify({"error": msg, **extra}), status


@app.after_request
def headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


@app.errorhandler(ValidationError)
def _val(e):
    return err(str(e), 422, fields=e.fields)


@app.errorhandler(osm.UpstreamError)
def _up(e):
    return err(str(e), 502, source=e.source)


@app.errorhandler(413)
def _big(e):
    return err("Request is too large.", 413)


@app.errorhandler(404)
def _nf(e):
    return err("Not found.", 404)


@app.errorhandler(500)
def _500(e):
    return err("Unexpected server error.", 500)


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "gemini_configured": bool(os.getenv("GEMINI_API_KEY", "").strip())})


@app.get("/api/catalog")
def catalog():
    return jsonify(categories.public_catalog())


def run_analysis(inp):
    geo = osm.geocode(inp["location"])
    if not geo:
        raise ValidationError({"location": "Nominatim could not find this location. Add a city or area name."})
    spec = categories.spec(inp["category"], inp["competitor_tag"])
    elements, truncated = osm.fetch_area(geo["lat"], geo["lon"], inp["poi_radius_km"] * 1000, spec)
    alt_block = None
    try:
        raw = osm.fetch_candidates(geo["lat"], geo["lon"], inp["alt_radius_km"] * 1000)
        cands = analysis.pick_candidates(raw, (geo["lat"], geo["lon"]), inp["alt_radius_km"] * 1000)
        if cands:
            counts = osm.fetch_candidate_counts(cands, inp["poi_radius_km"] * 1000, spec)
            kept = [(c, k) for c, k in zip(cands, counts) if k is not None]
            alt_block = analysis.make_alt_block(inp, spec, [c for c, _ in kept], [k for _, k in kept])
        else:
            alt_block = lambda m, ev: {"status": "none_found", "error": "No named OSM places found inside the alternative radius.", "rows": []}  # noqa: E731
    except osm.UpstreamError as ex:
        msg = str(ex)
        alt_block = lambda m, ev: {"status": "unavailable", "error": msg, "rows": []}  # noqa: E731
    return analysis.build_result(inp, geo, elements, truncated, spec, alt_block, db.now_iso())


@app.post("/api/analyses")
def create():
    if rate_limited("create"):
        return err("Too many analyses in a minute. Wait a moment and try again.", 429)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return err("Send a JSON object.", 400)
    result = run_analysis(validate(data))
    db.save_analysis(result)
    return jsonify(result), 201


@app.get("/api/analyses")
def history():
    return jsonify(db.list_analyses())


def _load(aid):
    if not ID_RE.match(aid):
        return None
    return db.get_analysis(aid)


@app.get("/api/analyses/<aid>")
def get_one(aid):
    r = _load(aid)
    return jsonify(r) if r else err("Analysis not found.", 404)


@app.delete("/api/analyses/<aid>")
def delete_one(aid):
    if ID_RE.match(aid) and db.delete_analysis(aid):
        return jsonify({"deleted": True})
    return err("Analysis not found.", 404)


@app.post("/api/analyses/<aid>/ai")
def ai(aid):
    r = _load(aid)
    if not r:
        return err("Analysis not found.", 404)
    if rate_limited("ai"):
        return err("Too many AI requests in a minute. Wait a moment.", 429)
    try:
        out = gemini.generate(r)
    except gemini.AIUnavailable as ex:
        return err(str(ex), 503, code="ai_not_configured")
    except gemini.AIError as ex:
        return err(str(ex), 502, code="ai_failed")
    db.set_ai(aid, out)
    return jsonify(out)


@app.get("/api/analyses/<aid>/report.pdf")
def pdf(aid):
    r = _load(aid)
    if not r:
        return err("Analysis not found.", 404)
    data = report_pdf.build_pdf(r, r.get("ai"))
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", r["input"]["business_name"])[:40] or "report"
    return Response(data, mimetype="application/pdf", headers={"Content-Disposition": f'attachment; filename="SmartStart_{name}.pdf"'})


@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def spa(path):
    if path.startswith("api/"):
        return err("Not found.", 404)
    if os.path.isdir(DIST):
        full = os.path.join(DIST, path)
        if path and os.path.isfile(full):
            return send_from_directory(DIST, path)
        return send_from_directory(DIST, "index.html")
    return Response("SmartStart AI API is running. Start the frontend with `npm run dev` (see README) or build it with `npm run build`.", mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
