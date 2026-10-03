import categories as cat

EXPENSE_KEYS = ["rent", "salaries", "utilities", "marketing", "other"]
CURRENCIES = ["INR", "USD", "EUR", "GBP", "AED", "SGD"]


class ValidationError(Exception):
    def __init__(self, fields):
        super().__init__("Some fields need attention.")
        self.fields = fields


def validate(d: dict) -> dict:
    errs, out = {}, {}

    def text(k, lo, hi, label):
        v = d.get(k)
        v = v.strip() if isinstance(v, str) else ""
        if not (lo <= len(v) <= hi):
            errs[k] = f"{label} must be {lo}–{hi} characters."
        out[k] = v

    def num(k, lo, hi, label, integer=False, lo_inclusive=True, src=None):
        raw = (src if src is not None else d).get(k)
        try:
            if isinstance(raw, bool):
                raise ValueError
            v = float(raw)
            if v != v or v in (float("inf"), float("-inf")):
                raise ValueError
        except (TypeError, ValueError):
            errs[k] = f"{label} must be a number."
            return 0
        if v < lo or (not lo_inclusive and v == lo) or v > hi:
            errs[k] = f"{label} must be {'above' if not lo_inclusive else 'at least'} {lo:g} and at most {hi:g}."
        return int(v) if integer else v

    text("business_name", 2, 80, "Business name")
    text("description", 10, 1000, "Description")
    text("target_customers", 3, 300, "Target customers")
    text("location", 3, 200, "Location")
    c = d.get("category")
    out["category"] = c
    out["competitor_tag"] = ""
    if c not in cat.category_names():
        errs["category"] = "Choose one of the listed categories."
    elif c == cat.CUSTOM:
        tag = (d.get("competitor_tag") or "").strip().lower()
        out["competitor_tag"] = tag
        if not cat.valid_custom_tag(tag):
            errs["competitor_tag"] = "Use an OSM tag like shop=florist (letters, digits, underscore)."
    out["budget"] = num("budget", 0, 1e11, "Budget", lo_inclusive=False)
    out["avg_price"] = num("avg_price", 0, 1e8, "Average price", lo_inclusive=False)
    out["customers_per_day"] = num("customers_per_day", 0, 1e5, "Customers per day", lo_inclusive=False)
    out["working_days"] = num("working_days", 1, 31, "Working days per month", integer=True)
    out["variable_cost_pct"] = num("variable_cost_pct", 0, 95, "Variable cost share")
    ex = d.get("expenses") if isinstance(d.get("expenses"), dict) else {}
    out["expenses"] = {k: num(k, 0, 1e10, k.capitalize() + " expense", src=ex) for k in EXPENSE_KEYS}
    for k in list(errs):
        if k in EXPENSE_KEYS:
            errs["expenses." + k] = errs.pop(k)
    out["poi_radius_km"] = num("poi_radius_km", 1, 10, "Nearby POI radius", integer=True)
    if out["poi_radius_km"] not in (1, 3, 5, 10):
        errs["poi_radius_km"] = "Choose 1, 3, 5 or 10 km."
    out["alt_radius_km"] = num("alt_radius_km", 5, 15, "Alternative-location radius", integer=True)
    if out["alt_radius_km"] not in (5, 10, 15):
        errs["alt_radius_km"] = "Choose 5, 10 or 15 km."
    out["currency"] = d.get("currency") if d.get("currency") in CURRENCIES else "INR"
    if not errs and sum(out["expenses"].values()) <= 0 and out["variable_cost_pct"] <= 0:
        errs["expenses.rent"] = "Enter at least one expense so profit and break-even can be calculated."
    if errs:
        raise ValidationError(errs)
    return out
