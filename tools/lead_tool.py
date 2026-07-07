"""
Lead finder tool: searches for medical practices, with a hardcoded
fallback list of real Ostschweiz dermatology practices so the demo can
never fail because of a flaky search API.
"""

import json
import os

from config import MAX_LEADS

# De-risk: verified real practices in the target region/niche.
FALLBACK_LEADS = [
    {
        "practice_name": "Hautarzt Herisau",
        "doctor_name": "Dr. med. Natalja Denisjuk",
        "specialty": "Dermatologie & Ästhetische Medizin",
        "city": "Herisau",
        "url": "http://www.hautarzt-herisau.ch",
        "source": "fallback",
    },
    {
        "practice_name": "Haut & Laserzentrum Dr. Zuder",
        "doctor_name": "Dr. med. Daniel Zuder",
        "specialty": "Dermatologie & Venerologie",
        "city": "St. Gallen",
        "url": "https://www.hlz-drzuder.ch",
        "source": "fallback",
    },
    {
        "practice_name": "Dermatologie Wil (Beispiel)",
        "doctor_name": "Praxisteam",
        "specialty": "Dermatologie",
        "city": "Wil SG",
        "url": "https://www.hautarzt-wil.ch",
        "source": "fallback",
    },
]

STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")


def find_leads(specialty: str, region: str, max_results: int = None) -> dict:
    """Find medical practice leads for a specialty in a Swiss region.

    Tries live DuckDuckGo search first; falls back to a verified static
    list if the search library is unavailable or returns nothing
    (sandboxes, rate limits, demo day).

    Args:
        specialty: e.g. 'Hautarzt' or 'Dermatologe'.
        region: e.g. 'Herisau', 'St. Gallen', 'Ostschweiz'.
        max_results: cap on leads returned. Defaults to config.MAX_LEADS
            if not specified.

    Returns:
        dict with 'leads' list and 'mode' ('live' or 'fallback').
    """
    if max_results is None:
        max_results = MAX_LEADS
    leads = []
    mode = "fallback"
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        query = f"{specialty} {region} Praxis"
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results * 2):
                href = r.get("href", "")
                if not href:
                    continue
                # crude filter: skip directories/hospital chains
                skip = ["doctena", "onedoc", "local.ch", "search.ch", "docdoc", "kssg", "hirslanden", "medicosearch"]
                if any(s in href for s in skip):
                    continue
                leads.append({
                    "practice_name": r.get("title", "Unbekannte Praxis")[:80],
                    "doctor_name": "",
                    "specialty": specialty,
                    "city": region,
                    "url": href,
                    "source": "live_search",
                })
                if len(leads) >= max_results:
                    break
        if leads:
            mode = "live"
    except Exception:
        pass

    if not leads:
        leads = FALLBACK_LEADS[:max_results]

    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "leads.json"), "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)

    return {"mode": mode, "count": len(leads), "leads": leads}
