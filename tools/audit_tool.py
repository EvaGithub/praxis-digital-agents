"""
Audit tool: 12 scored checks on any medical practice website.
Deterministic — no LLM. Wrapped as an ADK tool by the Auditor agent.
Total: 86 points. Grades: A>=90%, B>=75%, C>=60%, D>=45%, else F.
"""

import time
import requests
from bs4 import BeautifulSoup

from guardrails.sanitizer import strip_injection

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

CHECK_POINTS = {
    "https": 10,
    "mobile_responsive": 8,
    "page_load": 8,
    "google_business": 10,
    "online_booking": 12,
    "update_recency": 8,
    "social_links": 6,
    "meta_description": 5,
    "image_optimization": 6,
    "contact_form": 7,
    "multilingual": 6,
    "testimonials": 4,
    "broken_links": 8,
}
MAX_POINTS = sum(CHECK_POINTS.values())  # 94

IMPACT_DE = {
    "https": "Sicherheit für Patientendaten und Google-Ranking",
    "mobile_responsive": "Über 70% der Patienten suchen per Smartphone",
    "page_load": "Jede Sekunde Verzögerung kostet Besucher",
    "google_business": "Auffindbarkeit in Google Maps und lokaler Suche",
    "online_booking": "24/7 Terminvergabe entlastet die Praxis-Rezeption",
    "update_recency": "Aktualität signalisiert eine active Praxis",
    "social_links": "Patientennähe und Community-Aufbau",
    "meta_description": "Sichtbarkeit in Suchmaschinen-Ergebnissen",
    "image_optimization": "Schnellere Seiten, besseres Ranking",
    "contact_form": "Niedrigschwellige Patientenkommunikation",
    "multilingual": "Zugang für internationale Patienten",
    "testimonials": "Sozialer Beweis und Vertrauensaufbau",
    "broken_links": "Vermeidung von fehlerhaften Navigationslinks (z.B. httpdocs/)",
}


def run_website_audit(url: str) -> dict:
    """Run the 13-check audit on a medical practice website.

    Args:
        url: Website URL of the practice (with or without scheme).

    Returns:
        dict with per-check results, raw score, grade, and fetched page
        metadata. On fetch failure returns status='fetch_failed'.
    """
    if not url.startswith("http"):
        url = "http://" + url

    try:
        t0 = time.time()
        resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        load_time = round(time.time() - t0, 2)
        html = resp.text
        final_url = resp.url
    except Exception as e:
        return {"status": "fetch_failed", "url": url, "error": str(e)}

    soup = BeautifulSoup(html, "html.parser")
    low = html.lower()

    # Broken links check: scan all a tags for invalid paths containing 'httpdocs'
    has_broken_links = False
    for a in soup.find_all("a", href=True):
        if "httpdocs" in a["href"].lower():
            has_broken_links = True
            break

    checks = {
        "https": final_url.startswith("https"),
        "mobile_responsive": "viewport" in low,
        "page_load": load_time < 3.0,
        "google_business": any(k in low for k in ["google.com/maps", "maps.google", "business.google.com", "g.page"]),
        "online_booking": any(k in low for k in ["onedoc", "doctena", "medicosearch", "calendly", "doctolib", "termin buchen", "online termin", "terminbuchung", "book appointment"]),
        "update_recency": any(k in low for k in ["2025", "2026", "aktualisiert"]),
        "social_links": any(k in low for k in ["facebook.com", "instagram.com", "linkedin.com", "youtube.com"]),
        "meta_description": soup.find("meta", attrs={"name": "description"}) is not None,
        "image_optimization": (".webp" in low) or (low.count("<img") <= 15 and "<img" in low),
        "contact_form": bool(soup.find("form") and soup.find("form").find_all(["input", "textarea"])),
        "multilingual": any(k in low for k in ["/en/", "/fr/", "/it/", "hreflang", "sprache", "language"]),
        "testimonials": any(k in low for k in ["testimonial", "bewertung", "erfahrung", "empfehlung", "review"]),
        "broken_links": not has_broken_links,
    }

    score = sum(CHECK_POINTS[k] for k, passed in checks.items() if passed)
    pct = score / MAX_POINTS * 100
    grade = "A" if pct >= 90 else "B" if pct >= 75 else "C" if pct >= 60 else "D" if pct >= 45 else "F"

    failed = [k for k, v in checks.items() if not v]

    # The page <title> is attacker-controlled scraped text and is returned
    # into the auditor LLM's context — scan it through the same injection
    # filter as any other web content, so a malicious <title> cannot bypass
    # the guardrail. (Deterministic scoring above never trusts page text.)
    raw_title = soup.title.string.strip() if soup.title and soup.title.string else ""
    title_scan = strip_injection(raw_title)

    return {
        "status": "ok",
        "url": final_url,
        "load_time_s": load_time,
        "checks": checks,
        "failed_checks": failed,
        "impact_de": {k: IMPACT_DE[k] for k in failed},
        "score": score,
        "max_score": MAX_POINTS,
        "percentage": round(pct, 1),
        "grade": grade,
        "raw_html_length": len(html),
        "page_title": title_scan["clean"],
        "page_title_flags": title_scan["flags"],
    }
