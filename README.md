# SmartStart AI – Startup Location & Feasibility Analyzer

Multi-page analysis app: **Startup input → 12-page analysis workspace → final report → PDF download.**
Stack: React + TypeScript + Vite · Flask · SQLite · Leaflet/OpenStreetMap · Nominatim · Overpass · Gemini (server-side only) · Chart.js · ReportLab/Matplotlib (PDF).

## Run it

Requirements: Python 3.10+, Node 18+.

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then edit: GEMINI_API_KEY and NOMINATIM_USER_AGENT (with your email)
python app.py               # http://127.0.0.1:5000

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev                 # http://localhost:5173  (proxies /api to Flask)
```

Single-server mode: run `npm run build` in `frontend/`, then `python app.py` and open http://127.0.0.1:5000.

`GEMINI_API_KEY` is optional. Without it everything works except the AI report page, which shows a clear message. The PDF notes that AI text was not generated.

## Pages
1 Overview · 2 Location (geocode + Leaflet map) · 3 Nearby Market · 4 Competition (map, rings, density) · 5 Revenue (Low/Medium/High) ·
6 Expense & Profit (+ break-even chart) · 7 Customer Analysis · 8 SWOT · 9 Feasibility Index · 10 Alternative Locations ·
11 AI Business Report · 12 Final Summary · **Final Report** (Download Complete Report PDF, Print / Save as PDF). Past analyses: `/history`.

## Evidence labels
Every card carries one of: **Retrieved fact** (Nominatim/Overpass) · **User assumption** (your inputs) · **Calculated estimate** (deterministic formulas) · **AI interpretation** (Gemini).
Nothing is invented: no ratings, reviews, population or financial facts. OSM has none, so none appear.

## Feasibility index (deterministic, `backend/analysis.py`)
Weights: Market 25 · Location Fit 20 · Competition 15 · Customer Accessibility 15 · Revenue 20 · Risk 5. Gemini never touches it.

| Component | Formula |
|---|---|
| Market | `100·(1−e^(−d/10))`, d = weighted customer-POI density per km² inside the POI radius |
| Location Fit | `100·(1−e^(−w/8))`, w = weighted customer POIs within 1 km |
| Competition | `100·e^(−p/8)`, p = competitors ≤1 km + 0.25 × competitors beyond (higher = less pressure) |
| Accessibility | `100·(1−e^(−t/5))`, t = bus/rail/tram stops within 1 km |
| Revenue | 50% margin score (30% medium margin = 100) + 50% payback score (36 months = 0) |
| Risk | `100·clamp((1 − breakeven/expected customers per day)/0.5)` |

Customer-POI group weights, curve constants and the 60%/130% scenario multipliers are **model parameters**, not market research. Tune them in `analysis.py` / `categories.py`.

## Alternative locations
Candidates are real named OSM `place` nodes (suburb, neighbourhood, town, village) inside the separate alternative radius, spaced apart. Each is scored with the same formulas using exact Overpass `out count` queries (one request for all candidates). Revenue potential scales your customers/day by a demand-index ratio capped at 0.75×–1.25×. Rows are listed by distance. Nothing is called "best" or "winner" (the Gemini prompt forbids it too).

## API
`GET /api/health` · `GET /api/catalog` · `POST /api/analyses` · `GET /api/analyses` · `GET|DELETE /api/analyses/<id>` · `POST /api/analyses/<id>/ai` · `GET /api/analyses/<id>/report.pdf`
Validation errors return `422 {error, fields}`; upstream failures `502 {error, source}`; AI not configured `503 {code:"ai_not_configured"}`.

## Security
Secrets only in `backend/.env` (git-ignored). Gemini is called only from Flask. Strict server-side validation (custom OSM tags are regex-checked before entering Overpass queries), parameterized SQL, 64 KB request limit, per-IP rate limit, PDF text escaped, security headers. Nominatim 1 req/s limit and a SQLite response cache (geocode 7 d, Overpass 24 h) respect public-service policies.

## Tests
```bash
cd backend && python -m pytest -q
```
Covers validation, scoring math, financials, alternatives, Gemini prompt/response handling, upstream failures, PDF contents. The network is faked at the HTTP boundary.
`backend/tests/mock_server.py` runs the real app with synthetic network data for offline browser checks. **Dev only. Never used in normal operation.**

## Known limits
- OSM completeness varies by city, so competitor counts can be understated.
- Overpass queries are capped at 4000 elements. If hit, the UI and PDF say counts are lower bounds. Use a smaller radius.
- The PDF map is a plotted schematic of retrieved points (no tile download, to respect the OSM tile policy). The in-app map uses OSM tiles.
- Public Overpass/Nominatim servers can be slow or rate-limit. For heavy use, host your own and set `OVERPASS_URLS` / `NOMINATIM_URL`.
