"""
Compliance retrieval tool — Module 3: retrieval-as-a-tool.

A curated Swiss-compliance corpus (data/compliance_kb.json) queried by
the Reporter with each practice's FAILED CHECKS, so the report cites the
legal obligations that actually apply to that practice.

Scoring: tag match (strong signal) + keyword overlap (weak signal).
Deliberately embedding-free at this corpus size (8 docs) — deterministic,
inspectable, zero latency. Upgrade path documented in README: Vertex AI
vector search when the corpus outgrows keyword retrieval.
"""

import json
import os
import re
from typing import Union

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_PATH = os.path.join(BASE, "data", "compliance_kb.json")

_KB = None


def _load_kb():
    global _KB
    if _KB is None:
        with open(KB_PATH, encoding="utf-8") as f:
            _KB = json.load(f)
    return _KB


def retrieve_compliance(failed_checks: Union[list, str], query: str = "", top_k: int = 4) -> dict:
    """Retrieve the compliance obligations relevant to a practice's audit result.

    Args:
        failed_checks: list of failed check ids (e.g. ['https', 'online_booking']).
        query: optional free-text query for additional keyword matching.
        top_k: maximum documents to return.

    Returns:
        dict with 'documents': list of {id, topic, text_de, source, score}.
    """
    import json
    import ast
    if isinstance(failed_checks, str):
        try:
            failed_checks = json.loads(failed_checks)
        except Exception:
            try:
                failed_checks = ast.literal_eval(failed_checks)
            except Exception:
                # Fallback: split by commas if it is a comma-separated list
                failed_checks = [c.strip().strip("'\"[]") for c in failed_checks.split(",") if c.strip()]

    kb = _load_kb()
    failed = set(failed_checks or [])
    words = set(re.findall(r"\w{4,}", (query or "").lower()))

    scored = []
    for doc in kb:
        tag_hits = len(failed & set(doc["tags"]))
        kw_hits = len(words & set(re.findall(r"\w{4,}", (doc["topic"] + " " + doc["text_de"]).lower())))
        score = tag_hits * 10 + kw_hits
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: -x[0])
    docs = [{**doc, "score": s} for s, doc in scored[:top_k]]
    return {"documents": docs, "corpus_size": len(kb), "matched": len(scored)}
