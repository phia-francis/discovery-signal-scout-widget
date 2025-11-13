from __future__ import annotations
import re
from typing import Dict, List, Tuple

def classify_archetype_rules(title: str, summary: str, source: str, patterns: Dict[str, List[str]]) -> Tuple[str, float]:
    txt = f"{title}. {summary}".lower()
    def any_pat(pats): return any(re.search(p, txt, flags=re.I) for p in pats)
    if any_pat(patterns["canary"]): return "canary", 4.5
    if any_pat(patterns["counter_intuitive"]): return "counter_intuitive", 4.0
    if any_pat(patterns["insights_from_field"]) or any(x in source.lower() for x in ["hansard","gtr","council","nhs","trust"]):
        return "insights_from_field", 4.0
    if any_pat(patterns["outlier"]) or any(x in txt for x in ["artist","collective","hack","lawsuit","strike","grassroots"]):
        return "outlier", 4.0
    if any_pat(patterns["big_idea"]) or any(x in txt for x in ["framework","roadmap","manifesto","agenda","grand challenge"]):
        return "big_idea", 3.5
    if any_pat(patterns["shape_of_things"]) or any(x in txt for x in ["deployment","uptake","orders","capacity","interoperability"]):
        return "shape_of_things", 3.5
    return "shape_of_things", 2.5
