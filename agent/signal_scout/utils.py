from __future__ import annotations
import os, re, json, time, hashlib, urllib.parse
from typing import Any, Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dparser

CACHE_DIR = ".cache/signals"
os.makedirs(CACHE_DIR, exist_ok=True)

def parse_date(s: str):
    try: return dparser.parse(s)
    except Exception: return None

def clean_html(x: str) -> str:
    return re.sub(r"\s+", " ", BeautifulSoup(x or "", "html5lib").get_text(" ")).strip()

def canonical_url(url: str) -> str:
    try:
        p = urllib.parse.urlsplit(url)
        q = urllib.parse.parse_qsl(p.query)
        q = [(k,v) for k,v in q if not k.lower().startswith(("utm_","gclid","fbclid"))]
        return urllib.parse.urlunsplit((p.scheme or "https", p.netloc.lower(), p.path, urllib.parse.urlencode(q), ""))
    except Exception:
        return url

def unshorten(url: str, timeout=5) -> str:
    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout)
        return r.url or url
    except Exception:
        return url

def cache_path(url: str) -> str:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{h}.json")
