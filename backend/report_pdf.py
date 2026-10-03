"""Professional PDF report (reportlab + matplotlib)."""
import io
import os
from datetime import datetime
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)  # noqa: E402

INK, ACCENT, MUTED, LINE = colors.HexColor("#17232d"), colors.HexColor("#d9480f"), colors.HexColor("#5c6b75"), colors.HexColor("#d5dbd7")
TAGC = {"Retrieved fact": "#1c7c54", "User assumption": "#8a5a00", "Calculated estimate": "#1f5fa8", "AI interpretation": "#7a3aa8"}


def _fonts():
    d = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
    try:
        pdfmetrics.registerFont(TTFont("DV", os.path.join(d, "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DV-B", os.path.join(d, "DejaVuSans-Bold.ttf")))
        pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV", boldItalic="DV-B")
        return "DV", "DV-B"
    except Exception:
        return "Helvetica", "Helvetica-Bold"


F, FB = _fonts()
S = {
    "body": ParagraphStyle("body", fontName=F, fontSize=9, leading=13, textColor=INK, alignment=TA_LEFT),
    "small": ParagraphStyle("small", fontName=F, fontSize=7.5, leading=10, textColor=MUTED),
    "h1": ParagraphStyle("h1", fontName=FB, fontSize=15, leading=19, textColor=INK, spaceBefore=6, spaceAfter=4, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName=FB, fontSize=10.5, leading=14, textColor=INK, spaceBefore=8, spaceAfter=3),
    "title": ParagraphStyle("title", fontName=FB, fontSize=26, leading=30, textColor=INK),
    "cell": ParagraphStyle("cell", fontName=F, fontSize=8, leading=10.5, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName=FB, fontSize=8, leading=10.5, textColor=INK),
}
e = lambda x: escape(str(x if x is not None else "—"))  # noqa: E731


def P(t, s="body"):
    return Paragraph(t, S[s])


def money(cur, v):
    return "—" if v is None else f"{cur} {v:,.0f}"


def tag(label):
    return Paragraph(f'<font color="{TAGC[label]}" size="7.5"><b>● {label.upper()}</b></font>', S["small"])


def H(num, title, label=None):
    items = [P(f"{num}. {e(title)}", "h1")]
    if label:
        items.append(tag(label))
    return items


def table(rows, widths, header=True, zebra=True):
    data = [[c if not isinstance(c, str) else Paragraph(e(c), S["cellb"] if (header and i == 0) else S["cell"]) for c in row] for i, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 4)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf0ec"))]
    if zebra:
        st += [("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, colors.HexColor("#f6f8f6")])]
    t.setStyle(TableStyle(st))
    return t


def fig_img(fig, width_mm):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    from reportlab.lib.utils import ImageReader
    ir = ImageReader(buf)
    w, h = ir.getSize()
    return Image(buf, width=width_mm * mm, height=width_mm * mm * h / w)


def _style_ax(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=7)


def chart_map(r, with_alts=False):
    lat0, lon0 = r["location"]["lat"], r["location"]["lon"]
    import math
    kx = math.cos(math.radians(lat0))
    to = lambda la, lo: ((lo - lon0) * 111.32 * kx, (la - lat0) * 110.57)  # noqa: E731
    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    R = r["input"]["poi_radius_km"]
    lim = r["input"]["alt_radius_km"] if with_alts else R
    for rad, ls in ((R, "-"),) + (((r["input"]["alt_radius_km"], ":"),) if with_alts else ()):
        ax.add_patch(plt.Circle((0, 0), rad, fill=False, color="#17232d", lw=0.8, ls=ls))
    if not with_alts:
        pts = [to(p["lat"], p["lon"]) for p in r["market"]["pois"]]
        if pts:
            ax.scatter(*zip(*pts), s=9, c="#1c7c54", alpha=0.7, label="Customer-generating places")
        cs = [to(c["lat"], c["lon"]) for c in r["competition"]["list"]]
        if cs:
            ax.scatter(*zip(*cs), s=16, c="#d9480f", marker="^", label="Competitors")
    else:
        for row in r["alternatives"].get("rows", []):
            if row["selected"]:
                continue
            x, y = to(row["lat"], row["lon"])
            ax.scatter([x], [y], s=34, c="#1f5fa8", zorder=3)
            ax.annotate(row["name"][:22], (x, y), fontsize=6, xytext=(3, 3), textcoords="offset points")
    ax.scatter([0], [0], s=90, c="#17232d", marker="*", zorder=5, label="Selected location")
    ax.set_xlim(-lim * 1.08, lim * 1.08)
    ax.set_ylim(-lim * 1.08, lim * 1.08)
    ax.set_aspect("equal")
    ax.set_xlabel("km east–west of selected location", fontsize=7)
    ax.set_ylabel("km north–south", fontsize=7)
    _style_ax(ax)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False)
    return fig_img(fig, 118)


def chart_bars(labels, vals, title, color="#1f5fa8", horizontal=True, w=150, h=2.6, fmt="{:.0f}"):
    fig, ax = plt.subplots(figsize=(6.2, h))
    (ax.barh if horizontal else ax.bar)(labels, vals, color=color)
    if horizontal:
        ax.invert_yaxis()
    for i, v in enumerate(vals):
        (ax.text(v, i, " " + fmt.format(v), va="center", fontsize=7) if horizontal else ax.text(i, v, fmt.format(v), ha="center", va="bottom", fontsize=7))
    ax.set_title(title, fontsize=8.5, loc="left")
    _style_ax(ax)
    return fig_img(fig, w)


def build_pdf(r, ai=None) -> bytes:
    cur, inp, loc = r["input"]["currency"], r["input"], r["location"]
    fin, feas, cp, mk = r["financials"], r["feasibility"], r["competition"], r["market"]
    buf = io.BytesIO()
    W = A4[0] - 36 * mm

    def footer(c, d):
        c.saveState()
        c.setFont(F, 7)
        c.setFillColor(MUTED)
        c.drawString(18 * mm, 10 * mm, f"SmartStart AI · {inp['business_name'][:50]} · Analysis {r['id']}")
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")
        c.setStrokeColor(ACCENT)
        c.setLineWidth(1.2)
        c.line(18 * mm, A4[1] - 12 * mm, 40 * mm, A4[1] - 12 * mm)
        c.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=17 * mm,
                            title=f"SmartStart AI report – {inp['business_name']}", author="SmartStart AI")
    s = []
    # cover
    s += [Spacer(1, 35 * mm), P("SmartStart AI", "small"), Spacer(1, 3 * mm), P(e(inp["business_name"]), "title"), Spacer(1, 2 * mm),
          P("Startup location &amp; feasibility report", "h2"), Spacer(1, 6 * mm),
          P(f"{e(inp['category'])} · {e(loc['display_name'])}", "body"), Spacer(1, 2 * mm),
          P(f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')} · OSM data retrieved {e(r['retrieval']['retrieved_at'][:10])}", "small"), Spacer(1, 14 * mm)]
    box = Table([[Paragraph(f'<font size="34" name="{FB}" color="#d9480f">{feas["score"]:.0f}</font><font size="12" color="#5c6b75"> / 100</font>', ParagraphStyle("sc", parent=S["body"], leading=40)),
                  Paragraph(f'<b>Feasibility index: {e(feas["band"])}</b><br/>{e(feas["note"])}', S["body"])]], colWidths=[45 * mm, W - 45 * mm])
    box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, INK), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("PADDING", (0, 0), (-1, -1), 9)]))
    s += [box, Spacer(1, 12 * mm), P("How to read this report", "h2"),
          P("Every section is labelled by evidence type: "
            + " ".join(f'<font color="{c}"><b>● {k}</b></font>' for k, c in TAGC.items() if k != "AI interpretation")
            + ". Retrieved facts come from Nominatim and Overpass (OpenStreetMap). User assumptions are your inputs. Calculated estimates are deterministic formulas. ", "body"), PageBreak()]

    # 1 details
    s += H(1, "Startup details", "User assumption")
    ex = inp["expenses"]
    s.append(table([["Field", "Value"], ["Business", inp["business_name"]], ["Category", inp["category"] + (f" ({inp['competitor_tag']})" if inp["competitor_tag"] else "")],
                    ["Description", inp["description"]], ["Target customers", inp["target_customers"]], ["Location entered", inp["location"]],
                    ["Initial budget", money(cur, inp["budget"])], ["Average price", money(cur, inp["avg_price"])],
                    ["Customers per day (expected)", f"{inp['customers_per_day']:g}"], ["Working days per month", str(inp["working_days"])],
                    ["Monthly expenses", f"Rent {money(cur, ex['rent'])} · Salaries {money(cur, ex['salaries'])} · Utilities {money(cur, ex['utilities'])} · Marketing {money(cur, ex['marketing'])} · Other {money(cur, ex['other'])}"],
                    ["Variable cost share", f"{inp['variable_cost_pct']:g}% of revenue"], ["Nearby POI radius", f"{inp['poi_radius_km']} km"],
                    ["Alternative-location radius", f"{inp['alt_radius_km']} km"]], [50 * mm, W - 50 * mm]))
    # 2 location
    s += [Spacer(1, 4 * mm)] + H(2, "Location and map", "Retrieved fact")
    s += [P(f"Geocoded by Nominatim to <b>{e(loc['display_name'])}</b> (lat {loc['lat']:.5f}, lon {loc['lon']:.5f}; OSM {e(loc['osm_type'])} {e(loc['osm_id'])}).", "body"), Spacer(1, 2 * mm),
          chart_map(r), P("Schematic plot of retrieved OpenStreetMap points around the selected location (no basemap tiles). Data © OpenStreetMap contributors. Circle = POI radius.", "small")]
    s.append(PageBreak())
    # 3 market
    s += H(3, "Market analysis", "Retrieved fact")
    s.append(P(f"Within {mk['radius_km']} km ({mk['area_km2']} km²) the data returned {sum(x['count'] for x in mk['segments'])} customer-generating places "
               f"(weighted indicator {mk['weighted_total']}, {mk['weighted_density_per_km2']} per km²) and {mk['transit']['total']} public-transport stops "
               f"({mk['transit']['within_1km']} within 1 km).", "body"))
    s += [Spacer(1, 2 * mm), table([["Customer group", "Places", "≤500 m", "≤1 km", "Nearest", "Weight"]] +
                                   [[x["segment"], str(x["count"]), str(x["within_500m"]), str(x["within_1km"]), f"{x['nearest_m']} m" if x["nearest_m"] is not None else "—", f"{x['weight']}"] for x in mk["segments"]],
                                   [58 * mm, 20 * mm, 20 * mm, 20 * mm, 24 * mm, W - 142 * mm])]
    # 4 competition
    s += [Spacer(1, 4 * mm)] + H(4, "Competition", "Retrieved fact")
    s.append(P(f"{cp['total']} mapped competitors ({cp['named']} named, {cp['unnamed']} unnamed) · density {cp['density_per_km2']}/km² · "
               f"{cp['within_500m']} within 500 m, {cp['within_1km']} within 1 km · nearest {cp['nearest_m'] if cp['nearest_m'] is not None else 'n/a'} m. "
               "Ratings and reviews are not available from OpenStreetMap and are not shown.", "body"))
    if cp["rings"]:
        s += [Spacer(1, 2 * mm), chart_bars([x["label"] for x in cp["rings"]], [x["competitors"] for x in cp["rings"]], "Competitors by distance ring", "#d9480f", horizontal=False, h=2.2)]
    if cp["list"]:
        s += [Spacer(1, 2 * mm), table([["Nearest competitors", "Type", "Distance"]] + [[c["name"] or "Unnamed", c["kind"], f"{c['distance_m']} m"] for c in cp["list"][:12]], [W - 60 * mm, 35 * mm, 25 * mm])]
    s.append(PageBreak())
    # 5 customers
    s += H(5, "Customer analysis", "Retrieved fact")
    s.append(P(f"Target customers (your description): {e(inp['target_customers'])}. {e(r['customers']['note'])}", "body"))
    for x in mk["segments"]:
        names = ", ".join(f"{e(t['name'] or 'unnamed ' + t['kind'])} ({t['distance_m']} m)" for t in x["top"][:5]) or "none mapped"
        s.append(P(f"<b>{e(x['segment'])}</b>: {x['count']} places. Nearest: {names}", "body"))
        s.append(Spacer(1, 1.5 * mm))
    # 6 revenue
    sc = fin["scenarios"]
    s += [Spacer(1, 3 * mm)] + H(6, "Revenue analysis", "Calculated estimate")
    s.append(table([["Scenario", "Customers/day", "Revenue / month", "Profit / month", "Margin", "Payback"]] +
                   [[n.capitalize() + f" ({v['multiplier'] * 100:.0f}%)", f"{v['customers_per_day']:.1f}", money(cur, v["revenue"]), money(cur, v["profit"]), f"{v['margin'] * 100:.1f}%",
                     f"{v['payback_months']:.1f} mo" if v["payback_months"] else "not reached"] for n, v in sc.items()],
                   [34 * mm, 26 * mm, 36 * mm, 36 * mm, 20 * mm, W - 152 * mm]))
    s.append(P("Scenarios multiply your expected customers/day by fixed factors. They are not forecasts.", "small"))
    # 7 expenses
    s += [Spacer(1, 4 * mm)] + H(7, "Expenses and profit", "User assumption")
    s.append(table([["Item (per month)", "Amount"]] + [[k.capitalize(), money(cur, v)] for k, v in ex.items()] +
                   [["Fixed total", money(cur, fin["fixed_monthly"])], [f"Variable costs, medium ({fin['variable_pct']:g}% of revenue)", money(cur, sc["medium"]["variable_costs"])],
                    ["Profit, medium scenario", money(cur, sc["medium"]["profit"])]], [W - 50 * mm, 50 * mm]))
    s.append(PageBreak())
    # 8 break-even
    s += H(8, "Break-even", "Calculated estimate")
    be = fin["breakeven_customers_per_day"]
    s.append(P((f"Break-even requires <b>{be:.1f} customers per day</b> (revenue {money(cur, fin['breakeven_revenue_monthly'])} per month) versus the expected {inp['customers_per_day']:g}."
                if be is not None else "Break-even is not reachable at this price and variable cost share."), "body"))
    fig, ax = plt.subplots(figsize=(6.2, 2.6))
    for n, col in (("low", "#8a5a00"), ("medium", "#1f5fa8"), ("high", "#1c7c54")):
        ax.plot(range(25), [v / 1000 for v in sc[n]["cash_curve"]], label=n.capitalize(), color=col, lw=1.6)
    ax.axhline(0, color="#17232d", lw=0.7)
    ax.set_title(f"Cumulative cash after initial budget ({cur} thousand)", fontsize=8.5, loc="left")
    ax.set_xlabel("Month", fontsize=7)
    ax.legend(fontsize=7, frameon=False)
    _style_ax(ax)
    s += [Spacer(1, 2 * mm), fig_img(fig, 150)]
    # 9 swot
    sw = r["swot"]

    def cell(items):
        return [Paragraph("• " + e(i["text"]) + f' <font size="6.5" color="{TAGC[i["basis"]]}">[{e(i["basis"])}]</font>', S["cell"]) for i in items] or [P("—", "cell")]
    s += [Spacer(1, 4 * mm)] + H(9, "SWOT analysis", "Calculated estimate")
    t = Table([[P("<b>Strengths</b>", "cell"), P("<b>Weaknesses</b>", "cell")], [cell(sw["strengths"]), cell(sw["weaknesses"])],
               [P("<b>Opportunities</b>", "cell"), P("<b>Threats</b>", "cell")], [cell(sw["opportunities"]), cell(sw["threats"])]], colWidths=[W / 2, W / 2])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5f2ea")),
                           ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#e8eef8")), ("PADDING", (0, 0), (-1, -1), 5)]))
    s.append(t)
    s.append(PageBreak())
    # 10 feasibility
    s += H(10, "Feasibility index", "Calculated estimate")
    s.append(P(f"<b>{feas['score']:.1f} / 100 — {e(feas['band'])}.</b>", "body"))
    s += [Spacer(1, 2 * mm), table([["Component", "Weight", "Score", "Points"]] +
                                   [[c["label"], f"{c['weight'] * 100:.0f}%", f"{c['score']:.1f}", f"{c['contribution']:.1f}"] for c in feas["components"]],
                                   [60 * mm, 25 * mm, 25 * mm, 25 * mm]),
          Spacer(1, 2 * mm), chart_bars([c["label"] for c in feas["components"]], [c["score"] for c in feas["components"]], "Component scores (0–100)", "#17232d", h=2.2)]
    # 11 alternatives
    alts = r["alternatives"]
    s += [Spacer(1, 4 * mm)] + H(11, "Alternative locations", "Calculated estimate")
    if alts.get("status") == "ok":
        s.append(P(e(alts["method"]) + " " + e(alts["caveats"]), "small"))
        s += [Spacer(1, 2 * mm), table([["Location", "Dist.", "Competitors", "Cust. POIs (w)", "Transit 1 km", "Revenue/mo (med)", "Index"]] +
                                       [[("Selected: " if x["selected"] else "") + x["name"], f"{x['distance_km']} km", f"{x['competitors_radius']} ({x['competitors_1km']} ≤1km)",
                                         f"{x['customer_poi_weighted']}", str(x["transit_1km"]), money(cur, x["revenue_medium"]), f"{x['feasibility']:.1f}"] for x in alts["rows"]],
                                       [W - 125 * mm, 14 * mm, 28 * mm, 22 * mm, 17 * mm, 27 * mm, 17 * mm]),
              Spacer(1, 2 * mm), chart_map(r, with_alts=True), P("Candidate places are listed by distance, not ranked.", "small")]
    else:
        s.append(P("Alternative locations could not be retrieved for this analysis (" + e(alts.get("error", "no candidates found")) + ").", "body"))
    s.append(PageBreak())
    doc.build(s, onFirstPage=lambda c, d: None, onLaterPages=footer)
    return buf.getvalue()
