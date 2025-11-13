from __future__ import annotations

import argparse
import base64
import datetime as dt
import io
import json
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import zipfile
from xml.etree import ElementTree as ET

import pandas as pd
from bs4 import BeautifulSoup
from dateutil import parser as dparser
from rapidfuzz import fuzz
from simhash import Simhash


@dataclass
class MissionKeywords:
    core: Set[str] = field(default_factory=set)
    extended: Set[str] = field(default_factory=set)
    by_category: Dict[Tuple[str, str], Set[str]] = field(default_factory=lambda: defaultdict(set))


@dataclass
class ExcelKeywords:
    missions: Dict[str, MissionKeywords] = field(default_factory=dict)

    @staticmethod
    def load(xlsx_path: str) -> "ExcelKeywords":
        wb_path = Path(xlsx_path)
        if not wb_path.exists():
            materialise_keyword_workbook(wb_path)
        excel = ExcelKeywords()
        try:
            xls = pd.ExcelFile(wb_path)
            sheets = xls.sheet_names
            reader = lambda mission: pd.read_excel(wb_path, sheet_name=mission)
        except ImportError:
            sheets = []
            reader = None

        if reader is None:
            sheet_rows = _read_workbook_rows(wb_path.read_bytes())

            def iter_rows(mission: str):
                return sheet_rows.get(mission, [])
        else:

            def iter_rows(mission: str):
                if mission not in sheets:
                    return []
                df = reader(mission)
                columns = {c.lower().strip(): c for c in df.columns}

                def col(name: str) -> str:
                    key = name.lower()
                    if key not in columns:
                        raise KeyError(f"Missing column '{name}' in sheet '{mission}'")
                    return columns[key]

                out: List[List[str]] = []
                for _, row in df.iterrows():
                    out.append([
                        str(row.get(col("Category"), "")),
                        str(row.get(col("Subcategory"), "")),
                        str(row.get(col("Keywords"), "")),
                        str(row.get(col("Core"), "")),
                    ])
                return out

        for mission in ("ASF", "AFS", "AHL"):
            rows = iter_rows(mission)
            if not rows:
                continue
            header, *body = rows
            header_lookup = [h.strip().lower() for h in header]
            try:
                idx_category = header_lookup.index("category")
                idx_subcategory = header_lookup.index("subcategory")
                idx_keywords = header_lookup.index("keywords")
                idx_core = header_lookup.index("core")
            except ValueError as exc:
                raise KeyError(f"Missing required columns in sheet '{mission}'") from exc

            mission_keywords = excel.missions.setdefault(mission, MissionKeywords())
            for row in body:
                keywords = str(row[idx_keywords]).strip()
                if not keywords or keywords.lower() == "nan":
                    continue
                cat = str(row[idx_category]).strip() or "-"
                sub = str(row[idx_subcategory]).strip() or "-"
                core_flag = str(row[idx_core]).strip().lower()
                tokens = [k.strip() for k in re.split(r"[;,]", keywords) if k and k.strip()]
                for token in tokens:
                    lower = token.lower()
                    if core_flag == "core":
                        mission_keywords.core.add(lower)
                    else:
                        mission_keywords.extended.add(lower)
                    mission_keywords.by_category[(cat, sub)].add(token)
        return excel


def _read_workbook_rows(blob: bytes) -> Dict[str, List[List[str]]]:
    """Parse the workbook without pandas/openpyxl for restricted environments."""

    ns_main = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    ns_rel = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    ns_doc_rel = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        workbook = archive.read("xl/workbook.xml")
        rels_xml = archive.read("xl/_rels/workbook.xml.rels")

        wb_tree = ET.fromstring(workbook)
        rels_tree = ET.fromstring(rels_xml)

        rel_map = {
            rel.get("Id"): rel.get("Target")
            for rel in rels_tree.findall(f"{ns_rel}Relationship")
        }

        sheets = {}
        for sheet in wb_tree.findall(f"{ns_main}sheets/{ns_main}sheet"):
            name = sheet.get("name")
            rel_id = sheet.get(f"{ns_doc_rel}id")
            target = rel_map.get(rel_id)
            if not (name and target):
                continue
            sheets[name] = f"xl/{target}"

        rows_by_sheet: Dict[str, List[List[str]]] = {}
        for name, rel_path in sheets.items():
            sheet_xml = archive.read(rel_path)
            tree = ET.fromstring(sheet_xml)
            rows: List[List[str]] = []
            for row in tree.findall(f".//{ns_main}row"):
                values: List[str] = []
                for cell in row.findall(f"{ns_main}c"):
                    cell_type = cell.get("t")
                    if cell_type == "inlineStr":
                        is_elem = cell.find(f"{ns_main}is")
                        text_elem = is_elem.find(f"{ns_main}t") if is_elem is not None else None
                        values.append(text_elem.text if text_elem is not None else "")
                    else:
                        v_elem = cell.find(f"{ns_main}v")
                        values.append(v_elem.text if v_elem is not None else "")
                if values:
                    rows.append(values)
            if rows:
                rows_by_sheet[name] = rows
        return rows_by_sheet


def materialise_keyword_workbook(target: Path) -> None:
    """Write the committed base64 workbook to *target* if it is missing."""

    data_path = Path(__file__).resolve().parent / "data" / "auto_keywords.xlsx.b64"
    if not data_path.exists():
        raise FileNotFoundError(
            "Missing auto_keywords.xlsx.b64; cannot materialise Excel keywords workbook"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    blob = base64.b64decode(data_path.read_text("utf-8").strip())
    target.write_bytes(blob)


COUNTRY_TERMS = [
    "UK",
    "United Kingdom",
    "England",
    "Scotland",
    "Wales",
    "Northern Ireland",
    "EU",
    "Europe",
    "US",
    "USA",
    "Germany",
    "France",
    "Italy",
    "Spain",
    "Ireland",
    "Netherlands",
    "Belgium",
    "Sweden",
    "Norway",
    "Denmark",
    "Finland",
    "Poland",
    "Portugal",
    "Austria",
    "Switzerland",
    "Greece",
    "Czech",
    "Slovakia",
    "Hungary",
    "Romania",
    "Bulgaria",
    "Slovenia",
    "Croatia",
    "Estonia",
    "Latvia",
    "Lithuania",
    "Iceland",
    "Canada",
    "Australia",
    "New Zealand",
    "Japan",
    "South Korea",
    "China",
    "India",
    "Brazil",
    "Mexico",
    "Chile",
    "Colombia",
    "UAE",
    "Saudi Arabia",
    "Israel",
    "Turkey",
]
COUNTRY_RE = re.compile(r"\b(" + "|".join(map(re.escape, COUNTRY_TERMS)) + r")\b", re.I)

FUND_RE = re.compile(
    r"(?:(£|\$|€)\s?\d+(?:[.,]\d+)?\s?(?:k|m|bn|billion|million)?)"
    r"|"
    r"(Series\s+[ABCDEF])"
    r"|"
    r"(grant|seed round|seed|pre-seed|crowdfund|funding round)",
    re.I,
)


def parse_date(value: str) -> Optional[dt.datetime]:
    try:
        parsed = dparser.parse(value)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def clean_html(html: str) -> str:
    return re.sub(r"\s+", " ", BeautifulSoup(html or "", "html.parser").get_text(" ")).strip()


def simhash_text(*parts: str) -> int:
    return Simhash(" ".join(p or "" for p in parts)).value


def mission_relevance_weighted(
    text: str, keywords: ExcelKeywords
) -> Tuple[str, float, List[str], List[Tuple[str, str]]]:
    if not keywords.missions:
        return "AHL", 0.0, [], []
    matches: List[str] = []
    categories: Set[Tuple[str, str]] = set()
    scores: Dict[str, float] = {mission: 0.0 for mission in keywords.missions}
    lowered = text.lower()
    for mission, mk in keywords.missions.items():
        for term in mk.core:
            if term and term in lowered:
                scores[mission] += 1.0
                matches.append(term)
                for (category, subcategory), values in mk.by_category.items():
                    lowered_values = {v.lower() for v in values}
                    if term in lowered_values:
                        categories.add((category, subcategory))
        for term in mk.extended:
            if term and term in lowered:
                scores[mission] += 0.5
                matches.append(term)
                for (category, subcategory), values in mk.by_category.items():
                    lowered_values = {v.lower() for v in values}
                    if term in lowered_values:
                        categories.add((category, subcategory))
    best = max(scores, key=scores.get)
    relevance = max(0.0, min(5.0, (scores[best] / 3.0) * 5.0))
    return best, relevance, sorted(set(matches)), sorted(categories)


def focus_brand_rules(title: str, summary: str, cats: List[Tuple[str, str]]) -> Tuple[str, str]:
    text = f"{title}. {summary}".lower()
    social_terms = [
        "inequality",
        "poverty",
        "community",
        "education",
        "policy",
        "family",
        "workers",
        "marginalised",
        "council",
        "nhs",
        "schools",
    ]
    tech_terms = [
        "ai",
        "algorithm",
        "sensor",
        "platform",
        "app",
        "device",
        "robot",
        "trial",
        "patent",
        "standard",
        "protocol",
        "heat pump",
        "ml",
        "llm",
    ]
    social = any(term in text for term in social_terms)
    tech = any(term in text for term in tech_terms) or any(
        "ai" in "/".join(cat).lower() or "heat" in "/".join(cat).lower() for cat in cats
    )
    focus = "both" if (social and tech) else ("social" if social else ("tech" if tech else "social"))
    media = len(title) <= 96 and any(
        key in text for key in ["first", "record", "breakthrough", "ban", "trial", "opens", "series a", "series b", "grant", "pilot"]
    )
    brand = "both" if media and ("ecosystem" in text or "investment" in text) else ("media" if media else "PH")
    return focus, brand


ARCH_PATTERNS = {
    "shape_of_things": [r"(pilot|rollout|uptake|deployment|orders|capacity|standard|protocol)"],
    "counter_intuitive": [r"(counter[- ]?intuitive|paradox|backfire|rebound)", r"(trial|RCT|meta-analys)"],
    "canary": [r"(backlash|inactivism|blowback|recall|adverse|warning|shortage|misinfo)"],
    "insights_from_field": [r"(case study|council|NHS|trust|clinician|teacher|lessons|implementation)"],
    "outlier": [r"(artist|collective|hack|grassroots|lawsuit|strike|first[- ]of[- ]its[- ]kind|unprecedented)"],
    "big_idea": [r"(manifesto|white paper|framework|grand challenge|roadmap|review|commission|think tank)"],
}


def _any_pattern(patterns: List[str], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.I) for pattern in patterns)


def classify_archetype_rules(title: str, summary: str, source: str) -> Tuple[str, float]:
    text = f"{title}. {summary}".lower()
    if _any_pattern(ARCH_PATTERNS["canary"], text):
        return "canary", 4.5
    if _any_pattern(ARCH_PATTERNS["counter_intuitive"], text):
        return "counter_intuitive", 4.0
    if _any_pattern(ARCH_PATTERNS["insights_from_field"], text) or any(
        token in source.lower() for token in ["hansard", "gtr", "council", "nhs", "trust"]
    ):
        return "insights_from_field", 4.0
    if _any_pattern(ARCH_PATTERNS["outlier"], text) or any(
        token in text for token in ["artist", "collective", "hack", "lawsuit", "strike", "grassroots"]
    ):
        return "outlier", 4.0
    if _any_pattern(ARCH_PATTERNS["big_idea"], text) or any(
        token in text for token in ["framework", "roadmap", "manifesto", "agenda", "grand challenge"]
    ):
        return "big_idea", 3.5
    if _any_pattern(ARCH_PATTERNS["shape_of_things"], text) or any(
        token in text for token in ["deployment", "uptake", "orders", "capacity", "interoperability"]
    ):
        return "shape_of_things", 3.5
    return "shape_of_things", 2.5


def has_data_terms(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in ["randomized", "randomised", "cohort", "dataset", "preprint", "doi:", "method", "confidence interval"]
    )


def credibility(tier: str, weights: Dict[str, float], has_data: bool) -> float:
    base = weights.get(tier, 0.5)
    return min(5.0, 5.0 * base + (0.5 if has_data else 0.0))


def novelty(title: str, prior_titles: List[str]) -> float:
    if not prior_titles:
        return 5.0
    best = max((fuzz.token_set_ratio(title, candidate) for candidate in prior_titles), default=0)
    return max(0.0, 5.0 - (best / 100.0) * 5.0)


def extract_entity(title: str) -> str:
    parts = re.split(r"[-:–—]\s+", title or "", 1)
    head = parts[0] if parts else title
    words = re.findall(r"\b[A-Z][a-z0-9&\-]+\b", head)
    if words:
        return " ".join(words[:3])
    return (head or title).strip()[:60]


def extract_country(text: str) -> Optional[str]:
    match = COUNTRY_RE.search(text)
    return match.group(1) if match else None


def extract_funding(text: str) -> Optional[str]:
    match = FUND_RE.search(text)
    if not match:
        return None
    raw = match.group(0)
    raw = re.sub(r"\b(million)\b", "m", raw, flags=re.I)
    raw = re.sub(r"\b(billion|bn)\b", "bn", raw, flags=re.I)
    return re.sub(r"\s+", " ", raw).strip()


def compress_purpose(title: str, summary: str) -> str:
    text = (title or "").strip()
    if len(text.split()) < 4:
        sentences = re.split(r"(?<=[.!?])\s+", (summary or "").strip())
        if sentences:
            text = sentences[0]
    text = re.sub(r"^\s*(Breaking:|Study:|Report:)\s*", "", text, flags=re.I)
    text = re.sub(r"\s*[-:–—]\s*", " ", text)
    words = text.split()
    trimmed = " ".join(words[:9]).rstrip(",.")
    return trimmed


def format_mission_radar_block(title: str, summary: str) -> str:
    combined = f"{title or ''}. {summary or ''}"
    name = extract_entity(title or "")
    country = extract_country(combined)
    funding = extract_funding(combined)
    purpose = compress_purpose(title, summary)

    head_parts = [name]
    if country:
        head_parts.append(f"({country})")
    header = " ".join(head_parts)
    info_bits = []
    if funding:
        info_bits.append(funding)
    if purpose:
        info_bits.append(purpose)
    info_line = " | ".join(info_bits)

    if "heat" in combined.lower():
        what = f"AI is entering the boiler room. {summary}".strip()
    else:
        what = (summary or title or "").strip()
    why = "Could shift outcomes at scale if costs fall and deployment is simple."
    track = "Watch adoption, policy shifts, and any downside signals (equity, rebound)."

    return (
        f"**{header} |  {info_line}**\n\n"
        f"🔎 **What is it?** {what}\n\n"
        f"💡 **Why it matters:** {why}\n\n"
        f"📡 **What to track:** {track}"
    )


def equity_lens(text: str) -> str:
    lowered = text.lower()
    if any(key in lowered for key in ["glp-1", "semaglutide", "prescription", "drug"]):
        return "Access & affordability gaps could widen for low-income groups."
    if "sleep" in lowered:
        return "Shift workers and caregivers may benefit least without tailored supports."
    if any(key in lowered for key in ["tax", "ban", "pricing"]):
        return "Policy effects may be regressive unless paired with subsidies."
    return "Consider differential impacts on low-income, rural and minority communities."


def sentence_signal(title: str, summary: str) -> str:
    text = (title.strip().rstrip(".") + ". " + (summary or "").strip())
    first_sentence = re.split(r"(?<=[.!?])\s+", text)[0]
    words = first_sentence.split()
    return (" ".join(words[:28]).rstrip(",") + "...") if len(words) > 28 else first_sentence


def get_feed(url: str):
    import feedparser

    return feedparser.parse(url)


def collect_rss(source: Dict[str, Any], window_days: int, delay: float) -> List[Dict[str, Any]]:
    feed = get_feed(source["url"])
    items: List[Dict[str, Any]] = []
    now = dt.datetime.now(dt.timezone.utc)
    for entry in feed.entries:
        published = parse_date(
            getattr(entry, "published", "")
            or getattr(entry, "updated", "")
            or getattr(entry, "issued", "")
        )
        if not published:
            continue
        if (now - published).days > window_days:
            continue
        title = clean_html(getattr(entry, "title", ""))
        summary = clean_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))
        url = getattr(entry, "link", "")
        items.append(
            {
                "title": title,
                "summary": summary,
                "url": url,
                "date": published.isoformat(),
                "source": source["name"],
                "tier": source["tier"],
            }
        )
    time.sleep(delay)
    return items


def collect_all(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for source in cfg["sources"]:
        items.extend(collect_rss(source, cfg["window_days"], cfg.get("rate_delay_sec", 0.2)))
    return items


def dedupe(items: List[Dict]) -> List[Dict]:
    seen_urls: Set[str] = set()
    seen_titles: List[str] = []
    seen_hashes: List[int] = []
    unique: List[Dict] = []
    for item in items:
        url = item["url"]
        if url in seen_urls:
            continue
        title = item["title"]
        fingerprint = simhash_text(item["title"], item["summary"])
        similar = any(fuzz.token_set_ratio(title, prev) > 92 for prev in seen_titles) or any(
            abs(fingerprint - prev) < (1 << 16) for prev in seen_hashes
        )
        if similar:
            continue
        seen_urls.add(url)
        seen_titles.append(title)
        seen_hashes.append(fingerprint)
        unique.append(item)
    return unique


def cap_per_source(items: List[Dict], cap: int) -> List[Dict]:
    buckets: DefaultDict[str, int] = defaultdict(int)
    output: List[Dict] = []
    for item in sorted(items, key=lambda record: record["date"], reverse=True):
        source = item["source"]
        if buckets[source] >= cap:
            continue
        buckets[source] += 1
        output.append(item)
    return output


def build_rows(items: List[Dict], cfg: Dict, keywords: ExcelKeywords) -> List[Dict]:
    prior_titles = [item["title"] for item in items]
    rows: List[Dict] = []
    for item in items:
        title = item["title"]
        summary = item["summary"]
        text = f"{title}. {summary}"
        mission, relevance, matches, cats = mission_relevance_weighted(text, keywords)
        focus, brand = focus_brand_rules(title, summary, cats)
        cred = credibility(item.get("tier", "trade"), cfg["source_weights"], has_data_terms(summary))
        nov = novelty(title, prior_titles)
        archetype, archetype_fit = classify_archetype_rules(title, summary, item.get("source", ""))
        run_dt = dt.datetime.now(dt.timezone.utc)
        item_dt = pd.to_datetime(item["date"], utc=True, errors="coerce")
        days = max(1, int((run_dt - item_dt).days) if item_dt is not None else 999)
        recency = max(0.0, 5.0 - min(5.0, days / 6.0))
        weights = cfg["weights"]
        total = round(
            weights["relevance"] * relevance
            + weights["credibility"] * cred
            + weights["novelty"] * nov
            + weights["archetype"] * archetype_fit
            + weights.get("recency_bonus", 0) * recency,
            2,
        )
        radar = format_mission_radar_block(title, summary)
        rows.append(
            {
                "date": str(item["date"])[:10],
                "signal": sentence_signal(title, summary),
                "source_title": item["source"],
                "source_url": item["url"],
                "mission_links": mission,
                "archetype": archetype,
                "brief_summary": radar,
                "equity_consequence": equity_lens(summary),
                "focus": focus,
                "brand": brand,
                "credibility": round(cred, 2),
                "relevance": round(relevance, 2),
                "novelty": round(nov, 2),
                "archetype_fit": round(archetype_fit, 2),
                "score_recency": round(recency, 2),
                "total_score": total,
                "mission_tags": matches,
                "category_tags": [f"{category} / {subcategory}" for (category, subcategory) in cats],
            }
        )
    return rows


def shortlist(rows: List[Dict], cfg: Dict) -> List[Dict]:
    ordered = sorted(rows, key=lambda row: row["total_score"], reverse=True)
    out: List[Dict] = []
    used: Set[str] = set()
    have_arch: Set[str] = set()
    for row in ordered:
        if len(out) >= cfg["daily_top_n"]:
            break
        if row["source_url"] in used:
            continue
        if len(have_arch) < cfg["ensure_archetype_diversity"] and row["archetype"] in have_arch:
            continue
        out.append(row)
        used.add(row["source_url"])
        have_arch.add(row["archetype"])
    if cfg.get("ensure_mission_coverage", True):
        missions_present = {row["mission_links"] for row in out}
        for mission in ["ASF", "AHL", "AFS"]:
            if len(out) >= cfg["daily_top_n"]:
                break
            if mission in missions_present:
                continue
            candidate = next(
                (
                    row
                    for row in ordered
                    if row["mission_links"] == mission and row["source_url"] not in used
                ),
                None,
            )
            if candidate:
                out.append(candidate)
                used.add(candidate["source_url"])
                missions_present.add(mission)
    for row in ordered:
        if len(out) >= cfg["daily_top_n"]:
            break
        if row["source_url"] in used:
            continue
        out.append(row)
        used.add(row["source_url"])
    return out


def render_markdown(rows: List[Dict]) -> str:
    header = (
        "| Signal | Source | Mission | Archetype | Brief summary | Equity | Score |\n"
        "|---|---|---|---|---|---|---|"
    )
    lines = []
    for row in rows:
        lines.append(
            "| {signal} | [{source_title}]({source_url}) | {mission_links} | {archetype} | {brief_summary_line} | {equity} | {score} |".format(
                signal=row["signal"],
                source_title=row["source_title"],
                source_url=row["source_url"],
                mission_links=row["mission_links"],
                archetype=row["archetype"],
                brief_summary_line=row["brief_summary"].splitlines()[0] if row["brief_summary"] else "",
                equity=row["equity_consequence"],
                score=row["total_score"],
            )
        )
    return "\n".join([header] + lines)


def run_once(config_path: str, excel_keywords_path: str, out_dir: str) -> List[Dict]:
    import yaml

    with open(config_path, "r", encoding="utf-8") as cfg_file:
        config_data = yaml.safe_load(cfg_file) or {}
    keywords = ExcelKeywords.load(excel_keywords_path)
    items = collect_all(config_data)
    items = cap_per_source(dedupe(items), config_data["per_source_cap"])
    if not items:
        print("No items collected.")
        return []
    rows = build_rows(items, config_data, keywords)
    picks = shortlist(rows, config_data)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    base = output_dir / today
    df = pd.DataFrame(picks)
    df.to_csv(base.with_suffix(".csv"), index=False)
    (base.with_suffix(".json")).write_text(json.dumps(picks, ensure_ascii=False, indent=2), "utf-8")
    (output_dir / "latest.json").write_text(json.dumps(picks, ensure_ascii=False, indent=2), "utf-8")
    (base.with_suffix(".md")).write_text(render_markdown(picks), "utf-8")
    return picks


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Excel-enhanced Signal Scout agent")
    parser.add_argument("--config", default="agent/config.yaml", help="Path to config.yaml")
    parser.add_argument(
        "--excel_keywords",
        default="agent/Auto horizon scanning_ keywords.xlsx",
        help="Path to the Excel keywords workbook",
    )
    parser.add_argument("--out_dir", default="agent/signals", help="Directory to store output artifacts")
    args = parser.parse_args()
    run_once(args.config, args.excel_keywords, args.out_dir)


if __name__ == "__main__":
    main()
