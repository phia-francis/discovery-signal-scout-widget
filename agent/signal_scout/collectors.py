from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import feedparser
import requests

from .utils import cache_path, canonical_url, clean_html, parse_date, unshorten

try:
    from discovery_utils.getters import gtr, hansard  # type: ignore
    HAVE_DU = True
except Exception:
    HAVE_DU = False

def get_feed_cached(url: str, ttl_sec: int = 6 * 3600) -> feedparser.FeedParserDict:
    """Return a cached feedparser result, refreshing if the cache is stale."""

    cache_file = Path(cache_path(url))
    now = time.time()

    def _parse_cached() -> feedparser.FeedParserDict:
        try:
            return feedparser.parse(cache_file.read_text(encoding="utf-8"))
        except Exception:
            return feedparser.parse("")

    if cache_file.exists() and (now - cache_file.stat().st_mtime) < ttl_sec:
        cached = _parse_cached()
        if cached.entries:
            return cached

    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(resp.text, encoding="utf-8")
        return feedparser.parse(resp.text)
    except Exception:
        if cache_file.exists():
            cached = _parse_cached()
            if cached.entries:
                return cached
        return feedparser.parse(url)

def collect_rss(source: Dict[str, Any], window_days: int, delay: float) -> List[Dict[str, Any]]:
    fp = get_feed_cached(source["url"])
    out: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for e in fp.entries:
        d = parse_date(getattr(e, "published", "") or getattr(e, "updated", "") or getattr(e, "issued", ""))
        if not d:
            continue
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        if (now - d).days > window_days:
            continue
        title = clean_html(getattr(e, "title", ""))
        summary = clean_html(getattr(e, "summary", "") or getattr(e, "description", ""))
        url = canonical_url(unshorten(getattr(e, "link", "")))
        out.append({"title": title, "summary": summary, "url": url, "date": d.isoformat(), "source": source["name"], "tier": source["tier"]})
    time.sleep(delay)
    return out

def collect_discovery_utils(window_days: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    if not HAVE_DU:
        return rows
    # GTR
    try:
        GTR = gtr.GtrGetters(vector_db_path="./vector_dbs")  # type: ignore
        for q in ["roadmap energy flexibility","pilot heat pump retrofit","UPF policy trial","early years toolkit","GLP-1 shortage equity"]:
            hits = GTR.vector_search(q, n_results=5)
            for h in hits:
                d = parse_date(str(h.get("start","")) or str(h.get("updated","")))
                if not d:
                    continue
                if d.tzinfo is None:
                    d = d.replace(tzinfo=timezone.utc)
                if (now - d).days > window_days:
                    continue
                rows.append({
                    "title": clean_html(h.get("title","")),
                    "summary": clean_html(h.get("abstractText","") or h.get("abstract","") or ""),
                    "url": canonical_url(h.get("projectUrl","") or h.get("url","")),
                    "date": d.isoformat(),
                    "source": "DU_GTR",
                    "tier": "policy"
                })
    except Exception as e:
        logging.info("GTR vector unavailable: %s", e)
    # Hansard
    try:
        HANS = hansard.HansardGetters()  # type: ignore
        for q in ["ultra-processed backlash","GLP-1 shortage","sleep inequality","community retrofit lessons"]:
            hits = HANS.text_search(q, n_results=5)
            for h in hits:
                d = parse_date(h.get("date",""))
                if not d:
                    continue
                if d.tzinfo is None:
                    d = d.replace(tzinfo=timezone.utc)
                if (now - d).days > window_days:
                    continue
                rows.append({
                    "title": clean_html(h.get("title","")) or f"Hansard: {q}",
                    "summary": clean_html(h.get("snippet","") or ""),
                    "url": canonical_url(h.get("url","")),
                    "date": d.isoformat(),
                    "source": "DU_Hansard",
                    "tier": "policy"
                })
    except Exception as e:
        logging.info("Hansard search unavailable: %s", e)
    return rows

def collect_all(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for s in cfg["sources"]:
        if s["url"].startswith("discovery_utils:"):
            continue
        items += collect_rss(s, cfg["window_days"], cfg["rate_delay_sec"])
    items += collect_discovery_utils(cfg["window_days"])
    return items
