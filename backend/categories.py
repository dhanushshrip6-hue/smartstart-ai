"""Business categories -> OpenStreetMap tag filters.

A filter is (key, [values]) or (key, None) meaning "key exists".
Competitors and customer-generating segments never overlap by design, so counts
retrieved element-by-element and counts retrieved via Overpass `out count` agree.
"""
import re

SEGMENTS = {
    "Students & education": {"filters": [("amenity", ["school", "college", "university", "library"])], "weight": 1.0},
    "Office workers": {"filters": [("office", None)], "weight": 0.5},
    "Shoppers": {"filters": [("shop", ["mall", "supermarket", "department_store"]), ("amenity", ["marketplace"])], "weight": 1.5},
    "Tourists & visitors": {"filters": [("tourism", ["attraction", "museum", "hotel", "hostel", "guest_house", "gallery", "viewpoint"])], "weight": 1.0},
    "Leisure & sports": {"filters": [("leisure", ["park", "sports_centre", "swimming_pool", "stadium"])], "weight": 0.8},
    "Healthcare visitors": {"filters": [("amenity", ["hospital", "clinic", "doctors", "dentist"])], "weight": 1.0},
}

TRANSIT = [("highway", ["bus_stop"]), ("railway", ["station", "halt", "tram_stop", "subway_entrance"]), ("amenity", ["bus_station"])]

CATEGORIES = {
    "Cafe / Coffee Shop": ([("amenity", ["cafe"])], ["Students & education", "Office workers", "Shoppers", "Tourists & visitors", "Leisure & sports"]),
    "Restaurant / Fast Food": ([("amenity", ["restaurant", "fast_food", "food_court"])], ["Office workers", "Students & education", "Shoppers", "Tourists & visitors", "Leisure & sports"]),
    "Bakery & Sweets": ([("shop", ["bakery", "confectionery", "pastry"])], ["Shoppers", "Students & education", "Office workers", "Tourists & visitors"]),
    "Gym / Fitness Studio": ([("leisure", ["fitness_centre"])], ["Office workers", "Students & education", "Leisure & sports", "Shoppers"]),
    "Pharmacy": ([("amenity", ["pharmacy"])], ["Healthcare visitors", "Shoppers", "Office workers", "Students & education"]),
    "Salon / Beauty": ([("shop", ["hairdresser", "beauty"])], ["Shoppers", "Office workers", "Students & education", "Tourists & visitors"]),
    "Grocery / Convenience Store": ([("shop", ["supermarket", "convenience", "greengrocer"])], ["Office workers", "Students & education", "Healthcare visitors", "Leisure & sports"]),
    "Tutoring / Training Center": ([("amenity", ["language_school", "music_school", "driving_school", "prep_school"])], ["Students & education", "Office workers", "Shoppers"]),
    "Co-working Space": ([("amenity", ["coworking_space"])], ["Office workers", "Students & education", "Tourists & visitors"]),
    "Clothing / Boutique": ([("shop", ["clothes", "boutique", "shoes", "fashion_accessories"])], ["Shoppers", "Students & education", "Tourists & visitors", "Office workers"]),
}
CUSTOM = "Other (custom OSM tag)"
CUSTOM_SEGMENTS = ["Shoppers", "Office workers", "Students & education", "Tourists & visitors"]
_TAG_RE = re.compile(r"^[a-z0-9_:]{1,40}=[a-z0-9_]{1,40}$")


def category_names():
    return list(CATEGORIES) + [CUSTOM]


def valid_custom_tag(tag: str) -> bool:
    return bool(_TAG_RE.match(tag or ""))


def spec(name, custom_tag=None):
    if name == CUSTOM:
        k, v = custom_tag.split("=")
        comp, segs = [(k, [v])], CUSTOM_SEGMENTS
    else:
        comp, segs = CATEGORIES[name]
    return {"name": name, "competitor": comp, "segments": {s: SEGMENTS[s] for s in segs}, "transit": TRANSIT}


def public_catalog():
    return {
        "categories": category_names(),
        "segments": {k: {"weight": v["weight"]} for k, v in SEGMENTS.items()},
    }
