from __future__ import annotations
from typing import Dict, List
from rapidfuzz import fuzz

def credibility(tier: str, source_weights: Dict[str, float], has_data: bool) -> float:
    base = source_weights.get(tier, 0.5)
    return min(5.0, 5.0*base + (0.5 if has_data else 0.0))

def has_data_terms(text: str) -> bool:
    return any(k in text.lower() for k in ["randomized","randomised","cohort","dataset","preprint","doi:","method","confidence interval"])

def novelty(title: str, prior_titles: List[str]) -> float:
    if not prior_titles: return 5.0
    best = max((fuzz.token_set_ratio(title, t) for t in prior_titles), default=0)
    return max(0.0, 5.0 - (best/100.0)*5.0)
