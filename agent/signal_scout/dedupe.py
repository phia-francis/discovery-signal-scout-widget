from __future__ import annotations
from typing import Dict, List
from langdetect import detect as lang_detect, LangDetectException
from simhash import Simhash
from rapidfuzz import fuzz

def is_english(text: str) -> bool:
    try: return lang_detect(text or "") == "en"
    except LangDetectException: return True

def simhash_text(title: str, summary: str) -> int:
    return Simhash((title or "") + " " + (summary or "")).value

def dedupe(items: List[Dict]) -> List[Dict]:
    seen_urls, seen_titles, seen_hashes = set(), [], []
    uniq = []
    for it in items:
        u = it["url"]
        if u in seen_urls: 
            continue
        title = it["title"]; sh = simhash_text(it["title"], it["summary"])
        similar = any(fuzz.token_set_ratio(title, t) > 92 for t in seen_titles) or any(abs(sh - h) < (1 << 16) for h in seen_hashes)
        if similar: 
            continue
        if not is_english(f"{it['title']} {it['summary']}"):
            continue
        seen_urls.add(u); seen_titles.append(title); seen_hashes.append(sh); uniq.append(it)
    return uniq

def cap_per_source(items: List[Dict], cap: int) -> List[Dict]:
    buckets = {}
    out = []
    for it in sorted(items, key=lambda x: x["date"], reverse=True):
        s = it["source"]
        if buckets.get(s, 0) >= cap: 
            continue
        buckets[s] = buckets.get(s, 0) + 1
        out.append(it)
    return out
