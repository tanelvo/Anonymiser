import json
import os
import random
from functools import lru_cache

try:
    import gender_guesser.detector as gender_detector
    _gender_detector = gender_detector.Detector(case_sensitive=False)
except Exception:
    _gender_detector = None

_DATA_PATH = os.path.join(os.path.dirname(__file__), "estonian_names_expanded.json")


@lru_cache(maxsize=1)
def _load_name_data():
    print("Load name data")
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    lookup = {}
    male = []
    female = []
    unisex = []

    for item in data:
        name = (item.get("name") or "").strip()
        gender = (item.get("gender") or "").strip().lower()
        if not name or not gender:
            continue
        lookup[name.lower()] = gender
        if gender == "male":
            male.append(name)
        elif gender == "female":
            female.append(name)
        else:
            unisex.append(name)

    return lookup, male, female, unisex


def get_gender(name):
    if not name:
        return "unknown"
    print(f"[gender] check name='{name}'")
    lookup, _, _, _ = _load_name_data()
    gender = lookup.get(name.lower())
    if gender:
        return gender

    if _gender_detector is None:
        return "unknown"

    g = _gender_detector.get_gender(name)
    if g in ("male", "mostly_male"):
        return "male"
    if g in ("female", "mostly_female"):
        return "female"
    if g in ("andy",):
        return "unisex"
    return "unknown"


def pick_replacement_first(original_first):
    _, male, female, unisex = _load_name_data()
    gender = get_gender(original_first)

    if gender == "male" and male:
        return random.choice(male)
    if gender == "female" and female:
        return random.choice(female)
    if unisex:
        return random.choice(unisex)
    # fallback: any available list
    pool = male + female + unisex
    if pool:
        return random.choice(pool)
    return original_first
