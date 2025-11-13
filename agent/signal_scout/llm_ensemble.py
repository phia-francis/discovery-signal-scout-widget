from __future__ import annotations
import os, re, json
from functools import lru_cache
from typing import Tuple, Dict

LABELS = ["shape_of_things","counter_intuitive","canary","insights_from_field","outlier","big_idea"]
_LABEL_SET = set(LABELS)

_PROMPT = """You are an analyst. Classify the archetype of this signal into exactly one of:
["shape_of_things","counter_intuitive","canary","insights_from_field","outlier","big_idea"].
Return ONLY JSON: {"label": "<label|abstain>", "confidence": <0..1>, "rationale": "<<=12 words>"}.

Title: {title}
Summary: {summary}
Source: {source}
JSON:
"""

# Minimal client shim; replace with org client as needed.
def _openai_call(prompt: str) -> str:
    # Safety default: abstain if no API key present.
    if not os.getenv("OPENAI_API_KEY"):
        return '{"label":"abstain","confidence":0.0,"rationale":""}'
    try:
        import openai  # optional; not in requirements by default
        openai.api_key = os.environ["OPENAI_API_KEY"]
        resp = openai.ChatCompletion.create(
            model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
            messages=[{"role":"user","content":prompt}],
            temperature=0.0,
            max_tokens=120,
        )
        return resp.choices[0].message["content"]
    except Exception:
        return '{"label":"abstain","confidence":0.0,"rationale":""}'

def _parse(s: str) -> Dict:
    try:
        j = json.loads(s.strip().splitlines()[-1])
        label = str(j.get("label",""))
        conf = float(j.get("confidence", 0))
        rat = str(j.get("rationale",""))
        if label not in _LABEL_SET:
            label, conf = "abstain", 0.0
        return {"label": label, "confidence": max(0.0, min(1.0, conf)), "rationale": rat}
    except Exception:
        return {"label":"abstain","confidence":0.0,"rationale":""}

@lru_cache(maxsize=4096)
def classify_archetype_llm(title: str, summary: str, source: str) -> Tuple[str, float]:
    prompt = _PROMPT.format(title=title[:300], summary=summary[:800], source=source[:120])
    raw = _openai_call(prompt)
    j = _parse(raw)
    return j["label"], j["confidence"]

def ensemble_archetype(title: str, summary: str, source: str,
                       rule_label: str, rule_fit01: float,
                       tau_rules: float = 0.7, tau_llm: float = 0.6) -> Tuple[str, float, Dict]:
    if rule_fit01 >= tau_rules:
        return rule_label, round(rule_fit01*5.0,2), {"used":"rules","rule_label":rule_label,"rule_fit01":rule_fit01}
    l_label, l_conf = classify_archetype_llm(title, summary, source)
    if l_label in _LABEL_SET and l_conf >= tau_llm:
        return l_label, round(l_conf*5.0,2), {"used":"llm","rule_label":rule_label,"rule_fit01":rule_fit01,"llm_label":l_label,"llm_conf01":l_conf}
    return rule_label, round(rule_fit01*5.0,2), {"used":"fallback","rule_label":rule_label,"rule_fit01":rule_fit01,"llm_label":l_label,"llm_conf01":l_conf}
