"""
Guardrail 2 / Eval — Claim verifier.

Before any report or email draft leaves the system, verify that every
pass/fail claim it makes matches the ground-truth audit JSON. LLMs can
hallucinate ("your site has no HTTPS" when it does) — sending a doctor
a factually wrong audit would destroy credibility instantly.

Maps to Bootcamp Module 4: write evaluations that catch regressions,
monitor reliability and output quality.
"""

# German + English phrases the reporter uses per check, for detection
CHECK_SYNONYMS = {
    "https": ["https", "ssl", "verschlüsselung", "encryption"],
    "mobile_responsive": ["mobil", "mobile", "responsive", "smartphone"],
    "page_load": ["ladezeit", "load time", "geschwindigkeit", "speed"],
    "google_business": ["google business", "google-profil", "google maps"],
    "online_booking": ["online-buchung", "online buchung", "onedoc", "terminbuchung", "booking"],
    "update_recency": ["aktualisiert", "aktualität", "updated", "veraltet"],
    "social_links": ["social media", "instagram", "facebook"],
    "meta_description": ["meta-beschreibung", "meta description", "seo-beschreibung"],
    "image_optimization": ["bildoptimierung", "bilder", "image"],
    "contact_form": ["kontaktformular", "contact form"],
    "multilingual": ["mehrsprachig", "sprachen", "multilingual", "languages"],
    "testimonials": ["bewertungen", "testimonial", "erfahrungsberichte", "reviews"],
}

NEGATIVE_MARKERS = ["fehlt", "keine", "kein ", "nicht vorhanden", "✗", "missing", "no ", "fehlende", "ohne"]
POSITIVE_MARKERS = ["vorhanden", "✓", "erfüllt", "present", "aktiv", "funktioniert"]


def verify_report_claims(report_text: str, audit_result: dict) -> dict:
    """Verify that a generated report's claims match the audit ground truth.

    Heuristic sentence-level check: for each audit check mentioned in the
    report, the polarity (pass/fail) stated must match the audit JSON.

    Args:
        report_text: full text of the generated report or email draft.
        audit_result: the dict returned by run_website_audit().

    Returns:
        dict with 'passed' (bool), 'mismatches' (list), 'checked' (int),
        and 'coverage' (fraction of failed checks actually mentioned).
    """
    if audit_result.get("status") != "ok":
        return {"passed": False, "error": "no valid audit to verify against"}

    text_low = report_text.lower()
    checks = audit_result["checks"]
    mismatches = []
    mentioned = 0

    sentences = [s.strip() for s in text_low.replace("\n", ". ").split(".") if s.strip()]

    for check, truth_passed in checks.items():
        syns = CHECK_SYNONYMS[check]
        relevant = [s for s in sentences if any(k in s for k in syns)]
        if not relevant:
            continue
        mentioned += 1
        for s in relevant:
            says_fail = any(m in s for m in NEGATIVE_MARKERS)
            says_pass = any(m in s for m in POSITIVE_MARKERS)
            if truth_passed and says_fail and not says_pass:
                mismatches.append({"check": check, "truth": "pass", "report_says": "fail", "sentence": s[:140]})
            if (not truth_passed) and says_pass and not says_fail:
                mismatches.append({"check": check, "truth": "fail", "report_says": "pass", "sentence": s[:140]})

    failed_checks = audit_result.get("failed_checks", [])
    covered = sum(1 for c in failed_checks if any(k in text_low for k in CHECK_SYNONYMS[c]))
    coverage = round(covered / len(failed_checks), 2) if failed_checks else 1.0

    return {
        "passed": len(mismatches) == 0,
        "mismatches": mismatches,
        "checked": mentioned,
        "coverage_of_failed_checks": coverage,
    }
