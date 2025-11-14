from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import feedparser
import requests

from .utils import cache_path, canonical_url, clean_html, parse_date, unshorten

try:  # discovery_utils ships via git dependency but remains optional at runtime
    from discovery_utils.getters import crunchbase as du_crunchbase  # type: ignore
except Exception:  # pragma: no cover - network-only dependency
    du_crunchbase = None

try:  # pragma: no cover
    from discovery_utils.getters import gtr as du_gtr  # type: ignore
except Exception:
    du_gtr = None

try:  # pragma: no cover
    from discovery_utils.getters import hansard as du_hansard  # type: ignore
except Exception:
    du_hansard = None

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

def _call_search(fn, query: str, limit: int = 5):
    """Call a discovery_utils search method with forgiving signatures."""

    attempts = (
        lambda: fn(query, limit),
        lambda: fn(query, n_results=limit),
        lambda: fn(query, size=limit),
        lambda: fn(query),
        lambda: fn(query=query, n_results=limit),
        lambda: fn(query=query, size=limit),
    )
    for attempt in attempts:
        try:
            return attempt()
        except TypeError:
            continue
    try:
        return fn(query)
    except Exception:
        return []


def _collect_du_gtr(window_days: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if du_gtr is None:
        return rows
    now = datetime.now(timezone.utc)
    try:
        client = du_gtr.GtrGetters(vector_db_path="./vector_dbs")  # type: ignore[attr-defined]
    except Exception as exc:
        logging.info("GTR getters unavailable: %s", exc)
        return rows
    for query in [
        "roadmap energy flexibility",
        "pilot heat pump retrofit",
        "UPF policy trial",
        "early years toolkit",
        "GLP-1 shortage equity",
    ]:
        try:
            hits = _call_search(client.vector_search, query)  # type: ignore[attr-defined]
        except AttributeError:
            logging.info("GTR getters missing vector_search")
            break
        for hit in hits or []:
            d = parse_date(str(hit.get("start", "")) or str(hit.get("updated", "")))
            if not d:
                continue
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            if (now - d).days > window_days:
                continue
            rows.append(
                {
                    "title": clean_html(hit.get("title", "")),
                    "summary": clean_html(hit.get("abstractText", "") or hit.get("abstract", "") or ""),
                    "url": canonical_url(hit.get("projectUrl", "") or hit.get("url", "")),
                    "date": d.isoformat(),
                    "source": "DU_GTR",
                    "tier": "policy",
                }
            )
    return rows


def _collect_du_hansard(window_days: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if du_hansard is None:
        return rows
    now = datetime.now(timezone.utc)
    try:
        client = du_hansard.HansardGetters()  # type: ignore[attr-defined]
    except Exception as exc:
        logging.info("Hansard getters unavailable: %s", exc)
        return rows
    for query in [
        "ultra-processed backlash",
        "GLP-1 shortage",
        "sleep inequality",
        "community retrofit lessons",
    ]:
        try:
            hits = _call_search(client.text_search, query)  # type: ignore[attr-defined]
        except AttributeError:
            logging.info("Hansard getters missing text_search")
            break
        for hit in hits or []:
            d = parse_date(hit.get("date", ""))
            if not d:
                continue
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            if (now - d).days > window_days:
                continue
            rows.append(
                {
                    "title": clean_html(hit.get("title", "")) or f"Hansard: {query}",
                    "summary": clean_html(hit.get("snippet", "") or ""),
                    "url": canonical_url(hit.get("url", "")),
                    "date": d.isoformat(),
                    "source": "DU_Hansard",
                    "tier": "policy",
                }
            )
    return rows


def _collect_du_crunchbase(window_days: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if du_crunchbase is None:
        return rows
    now = datetime.now(timezone.utc)
    try:
        client = getattr(du_crunchbase, "CrunchbaseGetters")()
    except Exception as exc:
        logging.info("Crunchbase getters unavailable: %s", exc)
        return rows
    search_method = None
    for name in (
        "search_organisations",
        "search_organizations",
        "search_companies",
        "search",
        "vector_search",
    ):
        method = getattr(client, name, None)
        if callable(method):
            search_method = method
            break
    if search_method is None:
        logging.info("Crunchbase getters missing search method")
        return rows
    for query in [
        "heat pump retrofit startup",
        "nutrition AI platform",
        "sleep tech equity",
        "family support edtech",
        "grid flexibility software",
    ]:
        hits = _call_search(search_method, query) or []
        for hit in hits:
            d = None
            for key in (
                "announced_on",
                "announced_date",
                "updated_at",
                "created_at",
                "funded_on",
                "date",
            ):
                d = parse_date(str(hit.get(key, "")))
                if d:
                    break
            if not d:
                d = now
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            if (now - d).days > window_days:
                continue
            rows.append(
                {
                    "title": clean_html(hit.get("name", "") or hit.get("title", "")),
                    "summary": clean_html(
                        hit.get("short_description", "")
                        or hit.get("description", "")
                        or hit.get("summary", "")
                    ),
                    "url": canonical_url(
                        hit.get("homepage_url", "")
                        or hit.get("profile_url", "")
                        or hit.get("url", "")
                    ),
                    "date": d.isoformat(),
                    "source": "DU_Crunchbase",
                    "tier": "trade",
                }
            )
    return rows


def collect_discovery_utils(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    sources = {
        s.get("url", "").split(":", 1)[1].lower()
        for s in cfg.get("sources", [])
        if s.get("url", "").lower().startswith("discovery_utils:")
    }
    if not sources:
        return rows
    window_days = cfg.get("window_days", 30)
    if "gtr" in sources:
        rows.extend(_collect_du_gtr(window_days))
    if "hansard" in sources:
        rows.extend(_collect_du_hansard(window_days))
    if "crunchbase" in sources:
        rows.extend(_collect_du_crunchbase(window_days))
    return rows

def collect_all(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for s in cfg["sources"]:
        if s["url"].startswith("discovery_utils:"):
            continue
        items += collect_rss(s, cfg["window_days"], cfg["rate_delay_sec"])
    items += collect_discovery_utils(cfg)
    return items
