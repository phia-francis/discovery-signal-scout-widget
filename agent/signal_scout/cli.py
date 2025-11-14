from __future__ import annotations
import argparse, os, json, datetime as dt, logging
from typing import List, Dict, Optional

try:  # Optional dependency; only needed for full CLI runs
    import pandas as pd  # type: ignore
except ImportError:  # pragma: no cover - exercised in proxy-restricted CI
    pd = None  # type: ignore

from .config import load_config
from .classifiers import mission_relevance, focus_brand_rules, brief_summary_from, equity_lens, sentence_signal
from .archetypes import classify_archetype_rules
from .llm_ensemble import ensemble_archetype
from .render import render_markdown, render_html
from .persistence import ensure_db, log_raw, log_picks

def _coerce_datetime(value: str) -> Optional[dt.datetime]:
    """Convert date strings to timezone-aware datetimes without requiring pandas."""

    if pd is not None:
        item_dt = pd.to_datetime(value, utc=True, errors="coerce")  # type: ignore[assignment]
        return item_dt.to_pydatetime() if item_dt is not None else None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except Exception:
        return None


def build_rows(items: List[Dict], cfg: Dict) -> List[Dict]:
    from .scoring import credibility, novelty, has_data_terms  # Heavy deps imported lazily

    prior_titles = [it["title"] for it in items]
    rows = []
    for it in items:
        title, summary = it["title"], it["summary"]
        mission, rel, _ = mission_relevance(f"{title}. {summary}", cfg["topic_lattice"])
        focus, brand = focus_brand_rules(title, summary)
        cred = credibility(it.get("tier","trade"), cfg["source_weights"], has_data_terms(summary))
        nov = novelty(title, prior_titles)
        rule_label, rule_fit = classify_archetype_rules(title, summary, it.get("source",""), cfg["archetype_patterns"])
        # LLM ensemble (optional; uses abstain when no API key)
        arch, a_fit, _meta = ensemble_archetype(title, summary, it.get("source",""), rule_label, rule_fit/5.0)
        # Nudges
        if arch == "outlier":
            nov = min(5.0, nov + cfg["archetype_nudges"]["outlier_novelty_bonus"])
        if arch == "canary":
            cred = min(5.0, cred + cfg["archetype_nudges"]["canary_cred_bonus"])
        if arch == "insights_from_field" and any(x in it.get("source","").lower() for x in ["hansard","gtr","council","nhs","trust"]):
            a_fit = min(5.0, a_fit + cfg["archetype_nudges"]["field_fit_bonus"])
        # Recency
        run_dt = dt.datetime.now(dt.timezone.utc)
        item_dt = _coerce_datetime(it["date"])
        days = max(1, (run_dt - item_dt).days if item_dt is not None else 999)
        recency = max(0.0, 5.0 - min(5.0, days/6.0))
        w = cfg["weights"]
        total = round(w["relevance"]*rel + w["credibility"]*cred + w["novelty"]*nov + w["archetype"]*a_fit + w.get("recency_bonus",0)*recency, 2)
        rows.append({
            "date": str(it["date"])[:10],
            "signal": sentence_signal(title, summary),
            "source_title": it["source"],
            "source_url": it["url"],
            "mission_links": mission,
            "archetype": arch,
            "brief_summary": brief_summary_from(title, summary),
            "equity_consequence": equity_lens(summary),
            "focus": focus,
            "brand": brand,
            "credibility": round(cred,2),
            "relevance": round(rel,2),
            "novelty": round(nov,2),
            "archetype_fit": round(a_fit,2),
            "score_recency": round(recency,2),
            "total_score": total,
            "tags": json.dumps([mission, arch, focus, brand]),
        })
    return rows

def shortlist(rows: List[Dict], cfg: Dict) -> List[Dict]:
    rows_sorted = sorted(rows, key=lambda r: r["total_score"], reverse=True)
    out, used, have_arch = [], set(), set()
    # phase 1: archetype diversity
    for r in rows_sorted:
        if len(out) >= cfg["daily_top_n"]: break
        if r["source_url"] in used: continue
        if len(have_arch) < cfg["ensure_archetype_diversity"] and r["archetype"] in have_arch:
            continue
        out.append(r); used.add(r["source_url"]); have_arch.add(r["archetype"])
    # phase 2: mission coverage
    if cfg.get("ensure_mission_coverage", True):
        missions_present = set([r["mission_links"] for r in out])
        for m in ["ASF","AHL","AFS"]:
            if len(out) >= cfg["daily_top_n"]: break
            if m in missions_present: continue
            cand = next((x for x in rows_sorted if x["mission_links"]==m and x["source_url"] not in used), None)
            if cand:
                out.append(cand); used.add(cand["source_url"]); missions_present.add(m)
    # phase 3: fill
    for r in rows_sorted:
        if len(out) >= cfg["daily_top_n"]: break
        if r["source_url"] in used: continue
        out.append(r); used.add(r["source_url"])
    return out

def run_once(cfg_path: str) -> List[Dict]:
    cfg = load_config(cfg_path)
    from .collectors import collect_all  # Imported lazily to avoid feedparser dependency in tests
    from .dedupe import dedupe as ddu, cap_per_source  # avoid langdetect import when unused

    items = collect_all(cfg)
    items = ddu(items)
    items = cap_per_source(items, cfg["per_source_cap"])
    if not items:
        print("No items collected.")
        return []
    rows = build_rows(items, cfg)
    picks = shortlist(rows, cfg)

    # outputs
    os.makedirs("signals", exist_ok=True)
    today = dt.date.today().isoformat()
    base = f"signals/{today}"
    md = render_markdown(picks)
    print(md)
    if pd is None:
        raise RuntimeError("pandas is required to export CSV/HTML outputs; install optional deps.")
    pd.DataFrame(picks).to_csv(base + ".csv", index=False)
    open(base + ".json","w",encoding="utf-8").write(json.dumps(picks, ensure_ascii=False, indent=2))
    open(base + ".html","w",encoding="utf-8").write(render_html(picks, today))

    # logs
    from .persistence import ensure_db, log_raw, log_picks
    conn = ensure_db(); log_raw(conn, items); log_picks(conn, today, picks)
    print(f"\nSaved: {base}.csv\nSaved: {base}.json\nSaved: {base}.html")
    return picks

def main():
    parser = argparse.ArgumentParser(prog="signal-scout")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="Run once and output table + files")
    run.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if args.cmd == "run":
        run_once(args.config)
