from __future__ import annotations
import re
from typing import Dict, List, Tuple

def mission_relevance(text: str, topics: Dict[str, List[str]]) -> Tuple[str, float, List[str]]:
    t = text.lower(); scores, hits = {}, []
    for m, terms in topics.items():
        s, local = 0, []
        for term in terms:
            if term in t:
                s += 1; local.append(term)
        scores[m] = s; hits.extend(local)
    best = max(scores, key=scores.get)
    rel = min(5.0, scores[best] / 3.0 * 5.0)
    return best, rel, sorted(set(hits))

def focus_brand_rules(title: str, summary: str) -> Tuple[str, str]:
    txt = f"{title}. {summary}".lower()
    social_terms = ["inequality","poverty","community","education","policy","family","workers","marginalised","council"]
    tech_terms = ["ai","algorithm","sensor","platform","app","device","robot","trial","patent","standard","protocol"]
    social = any(t in txt for t in social_terms); tech = any(t in txt for t in tech_terms)
    focus = "both" if (social and tech) else ("social" if social else ("tech" if tech else "social"))
    media = len(title) <= 90 and any(x in txt for x in ["first","record","breakthrough","ban","trial","opens"])
    brand = "both" if media and ("ecosystem" in txt or "investment" in txt) else ("media" if media else "PH")
    return focus, brand

def brief_summary_from(title: str, summary: str) -> str:
    ACTION = r"(ban|tax|trial|launch|approve|publish|release|recall|invest|fund|regulate|mandate|restrict|lift|pilot)"
    STUDY  = r"(randomi[sz]ed|cohort|meta-analys|systematic review|case-control|RCT|trial|preprint|observational)"
    WHEN   = r"(today|this week|this month|in \d{4}|Q[1-4] \d{4}|last week|yesterday)"
    NUM    = r"(\b\d{1,3}(?:,\d{3})*(?:\.\d+)?%?|\b\d+\s?(?:million|billion|bn|m|k)\b)"
    WHERE  = r"\b(UK|United Kingdom|England|Scotland|Wales|NI|EU|US|Europe)\b"
    t = (title or "").strip().rstrip("."); s = summary or ""
    bits = []
    for pat in (ACTION, STUDY, NUM, WHERE, WHEN):
        m = re.search(pat, s, flags=re.I)
        if m: bits.append(m.group(0))
    sent = f"{t}. {' '.join(bits).strip()}.".replace("..",".")
    if len(sent.split()) <= 2:
        first = re.split(r"(?<=[.!?])\s+", s.strip())[0]
        sent = f"{t}. {first}"
    words = sent.split()
    return (" ".join(words[:28]).rstrip(",") + "...") if len(words) > 28 else sent

def equity_lens(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["glp-1","semaglutide","prescription","drug"]): return "Access & affordability gaps could widen for low-income groups."
    if "sleep" in t: return "Shift workers and caregivers may benefit least without tailored supports."
    if any(k in t for k in ["tax","ban","pricing"]): return "Policy effects may be regressive unless paired with subsidies."
    return "Consider differential impacts on low-income, rural and minority communities."

def sentence_signal(title: str, summary: str) -> str:
    import re
    text = (title.strip().rstrip(".") + ". " + (summary or "").strip())
    s = re.split(r"(?<=[.!?])\s+", text)[0]
    words = s.split()
    return (" ".join(words[:28]).rstrip(",") + "...") if len(words) > 28 else s
