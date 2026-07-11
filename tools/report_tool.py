"""
Reporter tools: PDF audit report + outreach email DRAFT.

IMPORTANT — human-in-the-loop by design: emails are NEVER sent.
Drafts land in outbox/ for manual review. Swiss law (UWG Art. 3 lit. o)
prohibits unsolicited commercial email without prior consent, so
autonomous sending is deliberately not implemented.
"""

import os
import json
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "outputs")
OUTBOX = os.path.join(BASE, "outbox")

CHECK_LABELS_DE = {
    "https": "HTTPS-Verschlüsselung",
    "mobile_responsive": "Mobile-Responsive Design",
    "page_load": "Schnelle Ladezeit",
    "google_business": "Google Business Profil",
    "online_booking": "Online-Terminbuchung",
    "update_recency": "Aktualität der Inhalte",
    "social_links": "Social Media Präsenz",
    "meta_description": "SEO Meta-Beschreibung",
    "image_optimization": "Bildoptimierung",
    "contact_form": "Kontaktformular",
    "multilingual": "Mehrsprachigkeit",
    "testimonials": "Patientenbewertungen",
    "broken_links": "Defekte Links",
}

GRADE_LABELS = {"A": "Ausgezeichnet", "B": "Gut", "C": "Befriedigend", "D": "Verbesserungsbedürftig", "F": "Unzureichend"}
GRADE_COLORS = {"A": "#27AE60", "B": "#F39C12", "C": "#E67E22", "D": "#E74C3C", "F": "#C0392B"}


def generate_pdf_report(audit_result, practice_name: str, doctor_name: str,
                        specialty: str, narrative: str = "", demo_url: str = "") -> dict:
    """Generate the 2-page PDF audit report for a practice.

    Args:
        audit_result: dict from run_website_audit().
        practice_name / doctor_name / specialty: practice metadata.
        narrative: optional LLM-written personalized findings paragraph
            (German). Falls back to a neutral standard text if empty.
        demo_url: link to the personalized demo website.

    Returns:
        dict with 'pdf_path'.
    """
    import json
    import ast
    if isinstance(audit_result, str):
        try:
            audit_result = json.loads(audit_result)
        except Exception:
            try:
                audit_result = ast.literal_eval(audit_result)
            except Exception:
                pass

    os.makedirs(OUT, exist_ok=True)
    safe = practice_name.lower().replace(" ", "-").replace("/", "-")
    path = os.path.join(OUT, f"audit_{safe}.pdf")

    doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    DARK = HexColor("#1A1A2E")
    ACCENT = HexColor("#0F9BE8")
    story = []

    grade = audit_result["grade"]
    gcolor = HexColor(GRADE_COLORS[grade])

    story.append(Spacer(1, 18*mm))
    story.append(Paragraph(f"<b>Website-Audit</b><br/>{practice_name}",
        ParagraphStyle("t", parent=styles["Normal"], fontSize=30, textColor=DARK,
                       fontName="Helvetica-Bold", leading=36)))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f"{doctor_name} • {specialty}",
        ParagraphStyle("d", parent=styles["Normal"], fontSize=11, textColor=HexColor("#666666"))))
    story.append(Spacer(1, 14*mm))

    gt = Table([[Paragraph(f"<b>{grade}</b><br/>{GRADE_LABELS[grade]}",
        ParagraphStyle("g", parent=styles["Normal"], fontSize=44, textColor=white,
                       alignment=1, fontName="Helvetica-Bold", leading=52))]], colWidths=[62*mm])
    gt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), gcolor),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 14), ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    story.append(gt)
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph(
        f"<b>Gesamtpunktzahl: {audit_result['score']} / {audit_result['max_score']} Punkte "
        f"({audit_result['percentage']}%)</b>",
        ParagraphStyle("s", parent=styles["Normal"], fontSize=14, textColor=DARK, fontName="Helvetica-Bold")))
    story.append(Spacer(1, 10*mm))

    if narrative:
        story.append(Paragraph("<b>Zusammenfassung</b>",
            ParagraphStyle("nh", parent=styles["Normal"], fontSize=12, fontName="Helvetica-Bold", textColor=DARK)))
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph(narrative,
            ParagraphStyle("n", parent=styles["Normal"], fontSize=10, textColor=HexColor("#333333"), leading=15)))
        story.append(Spacer(1, 8*mm))

    story.append(Paragraph("<b>Top-Prioritäten</b>",
        ParagraphStyle("p", parent=styles["Normal"], fontSize=12, fontName="Helvetica-Bold", textColor=DARK)))
    story.append(Spacer(1, 3*mm))
    prio_order = ["https", "online_booking", "mobile_responsive", "google_business",
                  "page_load", "multilingual", "meta_description"]
    prios = [c for c in prio_order if c in audit_result["failed_checks"]][:3]
    for i, c in enumerate(prios, 1):
        story.append(Paragraph(f"<b>{i}.</b> {CHECK_LABELS_DE[c]} — {audit_result['impact_de'][c]}",
            ParagraphStyle("pi", parent=styles["Normal"], fontSize=10, leftIndent=6*mm, spaceAfter=3*mm)))

    story.append(PageBreak())

    story.append(Paragraph("<b>Detaillierte Ergebnisse — 13 Kriterien</b>",
        ParagraphStyle("dt", parent=styles["Normal"], fontSize=14, fontName="Helvetica-Bold",
                       textColor=DARK, spaceAfter=8*mm)))

    rows = [["Kriterium", "Status", "Bedeutung"]]
    for check, passed in audit_result["checks"].items():
        rows.append([CHECK_LABELS_DE[check], "OK" if passed else "FEHLT",
                     IMPACT_SHORT.get(check, "")])
    tbl = Table(rows, colWidths=[52*mm, 22*mm, 86*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    for i, (check, passed) in enumerate(audit_result["checks"].items(), start=1):
        tbl.setStyle(TableStyle([("TEXTCOLOR", (1, i), (1, i),
                     HexColor("#27AE60") if passed else HexColor("#C0392B"))]))
    story.append(tbl)
    story.append(Spacer(1, 8*mm))

    cta_rows = [
        [Paragraph("<b>Wir bauen das für Sie — nDSG-konform, mit Online-Buchung</b>",
            ParagraphStyle("c1", parent=styles["Normal"], fontSize=11, textColor=white, fontName="Helvetica-Bold"))],
    ]
    if demo_url:
        cta_rows.append([Paragraph(f"Ihre persönliche Demo: <b>{demo_url}</b>",
            ParagraphStyle("c2", parent=styles["Normal"], fontSize=9, textColor=white))])
    cta_rows.append([Paragraph("Kostenloses Erstgespräch — Termin über den Link in unserer E-Mail",
        ParagraphStyle("c3", parent=styles["Normal"], fontSize=9, textColor=white))])
    cta = Table(cta_rows, colWidths=[160*mm])
    cta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (0, 0), 10), ("BOTTOMPADDING", (0, -1), (0, -1), 10),
    ]))
    story.append(cta)
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        f"Erstellt am {datetime.now().strftime('%d.%m.%Y')} • Vertraulich — ausschliesslich für {practice_name}",
        ParagraphStyle("f", parent=styles["Normal"], fontSize=7, textColor=HexColor("#999999"), alignment=1)))

    doc.build(story)
    return {"pdf_path": path}


IMPACT_SHORT = {
    "https": "Datensicherheit & Ranking",
    "mobile_responsive": "70%+ suchen mobil",
    "page_load": "Absprungrate",
    "google_business": "Lokale Auffindbarkeit",
    "online_booking": "24/7 Terminvergabe",
    "update_recency": "Vertrauenssignal",
    "social_links": "Patientennähe",
    "meta_description": "SEO-Sichtbarkeit",
    "image_optimization": "Seitengeschwindigkeit",
    "contact_form": "Kommunikation",
    "multilingual": "Internationale Patienten",
    "testimonials": "Sozialer Beweis",
    "broken_links": "Navigationsfehler",
}


def draft_outreach_email(practice_name: str, doctor_name: str, grade: str,
                         score: int, top_issues_de: str, demo_url: str,
                         email_body: str = "") -> dict:
    """Save an outreach email DRAFT to the outbox for human review.

    NEVER sends. Swiss UWG prohibits unsolicited commercial email
    without consent — a human must review, personalize, and decide.

    Args:
        practice_name / doctor_name: recipient context.
        grade / score: audit summary for the subject line.
        top_issues_de: short German summary of the top findings.
        demo_url: link to the personalized demo website.
        email_body: optional LLM-written body; a template is used if empty.

    Returns:
        dict with 'draft_path' and 'status': 'awaiting_human_approval'.
    """
    os.makedirs(OUTBOX, exist_ok=True)
    safe = practice_name.lower().replace(" ", "-").replace("/", "-")
    path = os.path.join(OUTBOX, f"draft_{safe}.md")

    if not email_body:
        email_body = f"""Guten Tag {doctor_name}

Bei einer Analyse von Praxis-Websites in Ihrer Region ist uns aufgefallen, dass die Website von {practice_name} technisch stark veraltet ist (Bewertung: {grade}, {score}/90 Punkte). Konkret: {top_issues_de}

Wir haben unverbindlich eine Demo erstellt, wie Ihre Praxis online auftreten könnte: {demo_url}

Falls Sie 20 Minuten Zeit haben, zeige ich Ihnen gerne die Details — hier können Sie direkt einen Termin wählen: [CALENDLY_LINK]

Freundliche Grüsse
[IHR NAME]"""

    content = f"""# EMAIL DRAFT — REQUIRES HUMAN APPROVAL — DO NOT AUTO-SEND
# Legal note: Swiss UWG Art. 3 lit. o — unsolicited commercial email
# requires consent. Review, personalize, verify recipient, decide.

To: [VERIFY: info@ practice address]
Subject: Website-Analyse {practice_name} — Note {grade} und was sich ändern lässt

{email_body}
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"draft_path": path, "status": "awaiting_human_approval"}
