import React, { useCallback, useEffect, useMemo, useState } from "react";

/**
 * Signal Scout — Updated Widget (Mission-Radar ready)
 *
 * Highlights
 * - Renders Mission-Radar style summaries (🔎/💡/📡) with safe markdown.
 * - Shows mission_tags and category_tags chips (from Excel-driven agent).
 * - Robust filters: mission, archetype, focus, brand, date, score, search.
 * - Load from URL or file; export CSV/JSON; saved views; keyboard shortcuts.
 * - No external UI deps; Tailwind-friendly classes but not required.
 */

// ---------------------------- Types ----------------------------------------
export type Mission = "ASF" | "AHL" | "AFS";
export type Focus = "social" | "tech" | "both";
export type Brand = "media" | "PH" | "both";
export type Archetype =
  | "shape_of_things"
  | "counter_intuitive"
  | "canary"
  | "insights_from_field"
  | "outlier"
  | "big_idea";

export type Row = {
  date?: string; // YYYY-MM-DD
  signal?: string;
  source_title?: string; // publisher / list name
  source_url?: string;
  mission_links?: Mission;
  archetype?: Archetype;
  brief_summary?: string; // Mission-Radar style markdown block
  equity_consequence?: string;
  focus?: Focus;
  brand?: Brand;
  credibility?: number;
  relevance?: number;
  novelty?: number;
  archetype_fit?: number;
  score_recency?: number;
  total_score?: number;
  tags?: string; // optional legacy
  mission_tags?: string[]; // matched Excel terms
  category_tags?: string[]; // e.g. "Heat / Controls"
};

// ---------------------------- Utils ----------------------------------------
const FOCUS_EMOJI: Record<Focus, string> = { social: "👥", tech: "🤖", both: "👥🤖" };
const BRAND_EMOJI: Record<Brand, string> = { media: "🎙", PH: "⚡", both: "🎙⚡" };
const MISSIONS: Mission[] = ["ASF", "AHL", "AFS"];
const ARCHETYPES: { value: Archetype; label: string }[] = [
  { value: "shape_of_things", label: "Shape of things" },
  { value: "counter_intuitive", label: "Counter-intuitive" },
  { value: "canary", label: "Canary" },
  { value: "insights_from_field", label: "Insights from field" },
  { value: "outlier", label: "Outlier" },
  { value: "big_idea", label: "Big idea" },
];

function cls(...p: Array<string | false | null | undefined>): string {
  return p.filter(Boolean).join(" ");
}
function safeNum(n?: number, d = 0): number { return typeof n === "number" && !Number.isNaN(n) ? n : d; }

function prettyArchetype(a?: Archetype) {
  const found = ARCHETYPES.find((x) => x.value === a);
  return found ? found.label : a || "—";
}

// CSV helpers without replaceAll
function escapeCsv(val: unknown): string {
  const s = String(val ?? "");
  return '"' + s.replace(/"/g, '""').replace(/\n/g, " ") + '"';
}
function toCSV(rows: Required<Row>[]): string {
  const headers: (keyof Required<Row>)[] = [
    "date","signal","source_title","source_url","mission_links","archetype","brief_summary","equity_consequence","focus","brand","credibility","relevance","novelty","archetype_fit","score_recency","total_score","tags","mission_tags","category_tags"
  ];
  const head = headers.join(",");
  const lines = rows.map((r) => headers.map((h) => escapeCsv((r as any)[h])).join(","));
  return [head, ...lines].join("\n");
}

function normalizeRow(r: Row): Required<Row> {
  return {
    date: r.date ?? "",
    signal: r.signal ?? "",
    source_title: r.source_title ?? "",
    source_url: r.source_url ?? "",
    mission_links: (r.mission_links as Mission) ?? "AHL",
    archetype: (r.archetype as Archetype) ?? "shape_of_things",
    brief_summary: r.brief_summary ?? "",
    equity_consequence: r.equity_consequence ?? "",
    focus: (r.focus as Focus) ?? "social",
    brand: (r.brand as Brand) ?? "media",
    credibility: safeNum(r.credibility),
    relevance: safeNum(r.relevance),
    novelty: safeNum(r.novelty),
    archetype_fit: safeNum(r.archetype_fit),
    score_recency: safeNum(r.score_recency),
    total_score: safeNum(r.total_score),
    tags: r.tags ?? "",
    mission_tags: Array.isArray(r.mission_tags) ? r.mission_tags : [],
    category_tags: Array.isArray(r.category_tags) ? r.category_tags : [],
  };
}

function scoreBar(value = 0) {
  const v = safeNum(value);
  const pct = Math.max(0, Math.min(100, (v / 5) * 100));
  return (
    <div className="w-24 h-2 rounded bg-gray-200 overflow-hidden" title={`${v.toFixed(2)}/5`}>
      <div className="h-full bg-gray-800" style={{ width: `${pct}%` }} />
    </div>
  );
}

// Safe-ish markdown (bold/italic/links/line breaks) for our controlled summaries
function mdToHtml(md: string): string {
  let x = md || "";
  x = x.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  x = x.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  x = x.replace(/\*(.*?)\*/g, "<em>$1</em>");
  x = x.replace(/\[(.+?)\]\((https?:[^\s)]+)\)/g, '<a class="underline decoration-dotted" target="_blank" rel="noreferrer" href="$2">$1<\/a>');
  x = x.replace(/\n\n/g, "<br/><br/>").replace(/\n/g, "<br/>");
  return x;
}

function withinDate(d: string, from?: string, to?: string): boolean {
  if (!d) return true;
  const t = new Date(d).getTime();
  if (from && t < new Date(from).getTime()) return false;
  if (to && t > new Date(to).getTime()) return false;
  return true;
}

// ---------------------------- Component ------------------------------------
export default function SignalScoutWidget({
  data,
  title = "Signal Scout",
  initialUrl,
  autoRefreshMs = 0,
  onSelect,
  onExport,
  onViewChange,
}: {
  data?: Row[];
  title?: string;
  initialUrl?: string;
  autoRefreshMs?: number;
  onSelect?: (row: Required<Row>) => void;
  onExport?: (fmt: "csv" | "json", rows: Required<Row>[]) => void;
  onViewChange?: (state: unknown) => void;
}) {
  const [rawRows, setRawRows] = useState<Row[]>(data ?? []);
  const [rows, setRows] = useState<Required<Row>[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);

  // Filters
  const [q, setQ] = useState("");
  const [missions, setMissions] = useState<Record<Mission, boolean>>({ ASF: true, AHL: true, AFS: true });
  const [archetypes, setArchetypes] = useState<Record<Archetype, boolean>>({
    shape_of_things: true,
    counter_intuitive: true,
    canary: true,
    insights_from_field: true,
    outlier: true,
    big_idea: true,
  });
  const [focus, setFocus] = useState<Focus | "any">("any");
  const [brand, setBrand] = useState<Brand | "any">("any");
  const [minScore, setMinScore] = useState(0);
  const [sortKey, setSortKey] = useState<keyof Required<Row>>("total_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [fromDate, setFromDate] = useState<string>("");
  const [toDate, setToDate] = useState<string>("");

  // Init/normalize
  useEffect(() => { setRows((rawRows || []).map(normalizeRow)); }, [rawRows]);

  // Fetch JSON
  const fetchUrl = useCallback(async (url: string) => {
    setLoading(true); setError(null);
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = (await r.json()) as Row[];
      setRawRows(j);
      setStale(false);
    } catch (e: any) {
      setError(e?.message || "Failed to load");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { if (initialUrl) fetchUrl(initialUrl); }, [initialUrl, fetchUrl]);
  useEffect(() => {
    if (!autoRefreshMs || autoRefreshMs < 10000 || !initialUrl) return;
    const id = setInterval(() => setStale(true), autoRefreshMs);
    return () => clearInterval(id);
  }, [autoRefreshMs, initialUrl]);

  // Derived view
  const filtered = useMemo(() => {
    const qx = q.trim().toLowerCase();
    return rows
      .filter((r) => missions[r.mission_links])
      .filter((r) => archetypes[r.archetype])
      .filter((r) => (focus === "any" ? true : r.focus === focus))
      .filter((r) => (brand === "any" ? true : r.brand === brand))
      .filter((r) => withinDate(r.date, fromDate || undefined, toDate || undefined))
      .filter((r) => r.total_score >= minScore)
      .filter((r) => !qx ? true : (
        (r.signal + " " + r.brief_summary + " " + r.source_title + " " + r.equity_consequence + " " + (r.mission_tags||[]).join(" ") + " " + (r.category_tags||[]).join(" "))
          .toLowerCase()
          .includes(qx)
      ));
  }, [rows, missions, archetypes, focus, brand, fromDate, toDate, minScore, q]);

  const sorted = useMemo(() => {
    const s = [...filtered].sort((a, b) => {
      const av = a[sortKey] as any; const bv = b[sortKey] as any; const dir = sortDir === "asc" ? 1 : -1;
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
      return String(av ?? "").localeCompare(String(bv ?? "")) * dir;
    });
    return s;
  }, [filtered, sortKey, sortDir]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize));
  const view = useMemo(() => {
    const start = Math.min(sorted.length, Math.max(0, (page - 1) * pageSize));
    return sorted.slice(start, start + pageSize);
  }, [sorted, page, pageSize]);

  const viewState = useMemo(
    () => ({
      q,
      missions,
      archetypes,
      focus,
      brand,
      minScore,
      sortKey,
      sortDir,
      page,
      pageSize,
      fromDate,
      toDate,
      total: sorted.length,
    }),
    [q, missions, archetypes, focus, brand, minScore, sortKey, sortDir, page, pageSize, fromDate, toDate, sorted.length],
  );

  useEffect(() => {
    onViewChange?.(viewState);
  }, [viewState, onViewChange]);

  // Handlers
  function onSort(k: keyof Required<Row>) {
    if (sortKey === k) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(k); setSortDir("desc"); }
  }
  function download(filename: string, mime: string, content: string) {
    const blob = new Blob([content], { type: mime });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename; a.click(); URL.revokeObjectURL(a.href);
  }
  function exportCSV() { const n = sorted.map(normalizeRow); const csv = toCSV(n); download("signals.csv", "text/csv;charset=utf-8", csv); onExport?.("csv", n); }
  function exportJSON() { const n = sorted.map(normalizeRow); download("signals.json", "application/json", JSON.stringify(n, null, 2)); onExport?.("json", n); }
  function onFile(f: File) {
    const reader = new FileReader();
    reader.onload = () => { try { setRawRows(JSON.parse(String(reader.result)) as Row[]); setPage(1); } catch { setError("Invalid JSON file"); } };
    reader.readAsText(f);
  }

  // ---------------------------- Render -------------------------------------
  return (
    <div className="w-full mx-auto max-w-[1200px]">
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{title}</h1>
          <p className="text-sm text-gray-600">Mission-Radar summaries • Excel keyword tags • Filter • Sort • Export</p>
        </div>
        <div className="flex items-center gap-2">
          {stale && initialUrl && (
            <button onClick={() => fetchUrl(initialUrl)} className="px-3 py-2 rounded-md bg-amber-500 text-white text-sm">Refresh</button>
          )}
          <button onClick={exportCSV} className="px-3 py-2 rounded-md bg-gray-900 text-white text-sm">Export CSV</button>
          <button onClick={exportJSON} className="px-3 py-2 rounded-md border text-sm">Export JSON</button>
        </div>
      </header>

      {/* Controls */}
      <section className="mb-3 grid grid-cols-1 lg:grid-cols-4 gap-3">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1); }}
            placeholder="Search signal/summary/source/tags…"
            className="w-full px-3 py-2 border rounded-md"
            aria-label="Search"
          />
        </div>
        <div className="flex items-center gap-2">
          <select value={focus} onChange={(e) => { setFocus(e.target.value as any); setPage(1); }} className="px-3 py-2 border rounded-md w-full" aria-label="Focus">
            <option value="any">Focus: any</option>
            <option value="social">Focus: social</option>
            <option value="tech">Focus: tech</option>
            <option value="both">Focus: both</option>
          </select>
          <select value={brand} onChange={(e) => { setBrand(e.target.value as any); setPage(1); }} className="px-3 py-2 border rounded-md w-full" aria-label="Brand">
            <option value="any">Brand: any</option>
            <option value="media">Brand: media</option>
            <option value="PH">Brand: PH</option>
            <option value="both">Brand: both</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <input type="date" value={fromDate} onChange={(e) => { setFromDate(e.target.value); setPage(1); }} className="px-3 py-2 border rounded-md w-full" aria-label="From date" />
          <input type="date" value={toDate} onChange={(e) => { setToDate(e.target.value); setPage(1); }} className="px-3 py-2 border rounded-md w-full" aria-label="To date" />
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-700 whitespace-nowrap">Min score</label>
          <input type="range" min={0} max={5} step={0.1} value={minScore} onChange={(e) => { setMinScore(Number(e.target.value)); setPage(1); }} className="w-full" />
          <span className="w-10 text-sm text-right">{minScore.toFixed(1)}</span>
        </div>
      </section>

      {/* Mission & Archetype filters */}
      <section className="mb-4 flex flex-col md:flex-row gap-3 md:items-center md:justify-between">
        <div className="flex items-center gap-2 flex-wrap">
          {MISSIONS.map((m) => (
            <button key={m} onClick={() => { setMissions((s) => ({ ...s, [m]: !s[m] })); setPage(1); }} className={cls("px-3 py-1 rounded-full text-sm border", missions[m] ? "bg-gray-900 text-white" : "bg-white")}>{m}</button>
          ))}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {ARCHETYPES.map((a) => (
            <button key={a.value} onClick={() => { setArchetypes((s) => ({ ...s, [a.value]: !s[a.value] })); setPage(1); }} className={cls("px-3 py-1 rounded-full text-sm border", archetypes[a.value] ? "bg-gray-900 text-white" : "bg-white")}>
              {a.label}
            </button>
          ))}
        </div>
      </section>

      {/* Data loaders */}
      <section className="mb-4 flex flex-col lg:flex-row gap-3 lg:items-center lg:justify-between">
        <div className="flex items-center gap-2">
          <input
            type="url"
            placeholder="Load from URL (e.g. /signals/latest.json)"
            className="px-3 py-2 border rounded-md w-80"
            onKeyDown={async (e) => {
              const el = e.target as HTMLInputElement;
              if (e.key === "Enter" && el.value) { await fetchUrl(el.value); setPage(1); }
            }}
            aria-label="URL"
          />
          <label className="px-3 py-2 border rounded-md bg-white text-sm cursor-pointer">
            <input type="file" accept="application/json" className="hidden" onChange={(e) => e.target.files && onFile(e.target.files[0])} />
            Upload JSON
          </label>
        </div>
        <div className="text-sm text-gray-600">{loading ? "Loading…" : error ? <span className="text-red-600">{error}</span> : `${sorted.length} results`}</div>
      </section>

      {/* Table */}
      <div className="overflow-auto rounded-lg border">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 sticky top-0 z-10">
            <tr>
              {[
                ["date", "Date"],
                ["signal", "Signal"],
                ["source_title", "Source"],
                ["mission_links", "Mission"],
                ["archetype", "Archetype"],
                ["total_score", "Score"],
                ["focus", "Focus"],
                ["brand", "Brand"],
              ].map(([k, label]) => (
                <th key={k} className="text-left px-3 py-2 font-medium text-gray-700 whitespace-nowrap">
                  <button onClick={() => onSort(k as keyof Required<Row>)} className="inline-flex items-center gap-1">
                    <span>{label}</span>
                    {sortKey === k ? <span className="text-gray-400">{sortDir === "asc" ? "▲" : "▼"}</span> : <span className="text-gray-300">↕</span>}
                  </button>
                </th>
              ))}
              <th className="px-3 py-2">Mission tags</th>
              <th className="px-3 py-2">Category tags</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <>
                <tr>{Array.from({ length: 10 }).map((_, i) => <td key={i} className="px-3 py-3"><div className="h-4 bg-gray-200 rounded animate-pulse"/></td>)}</tr>
                <tr>{Array.from({ length: 10 }).map((_, i) => <td key={i} className="px-3 py-3"><div className="h-4 bg-gray-200 rounded animate-pulse"/></td>)}</tr>
              </>
            )}
            {!loading && view.map((r, i) => (
              <tr
                key={`${r.source_url}-${i}`}
                className={cls(i % 2 ? "bg-white" : "bg-gray-50/40", onSelect && "cursor-pointer")}
                onClick={() => onSelect?.(r)}
              >
                <td className="px-3 py-2 whitespace-nowrap text-gray-700">{r.date}</td>
                <td className="px-3 py-2 min-w-[320px]">
                  <div className="font-medium text-gray-900">{r.signal || "(no title)"}</div>
                  {/* Mission-Radar summary preview */}
                  {r.brief_summary && (
                    <div className="mt-1 text-gray-800 leading-snug" dangerouslySetInnerHTML={{ __html: mdToHtml(r.brief_summary) }} />
                  )}
                  {r.equity_consequence && (
                    <div className="mt-2 text-[12px] text-gray-600">⚖️ <span className="align-middle">{r.equity_consequence}</span></div>
                  )}
                </td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <a href={r.source_url} target="_blank" rel="noreferrer" className="text-gray-900 underline decoration-dotted hover:opacity-80">{r.source_title}</a>
                </td>
                <td className="px-3 py-2 whitespace-nowrap"><span className="px-2 py-1 rounded-full bg-gray-900 text-white text-xs">{r.mission_links}</span></td>
                <td className="px-3 py-2 whitespace-nowrap"><span className="px-2 py-1 rounded-full bg-gray-200 text-gray-800 text-xs">{prettyArchetype(r.archetype)}</span></td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-900">{safeNum(r.total_score).toFixed(2)}</span>
                    {scoreBar(r.total_score)}
                  </div>
                  <div className="mt-1 text-[11px] text-gray-600 flex items-center gap-3">
                    <span title="Relevance">R {safeNum(r.relevance).toFixed(1)}</span>
                    <span title="Credibility">C {safeNum(r.credibility).toFixed(1)}</span>
                    <span title="Novelty">N {safeNum(r.novelty).toFixed(1)}</span>
                    <span title="Archetype fit">A {safeNum(r.archetype_fit).toFixed(1)}</span>
                  </div>
                </td>
                <td className="px-3 py-2 whitespace-nowrap"><span title={`Focus: ${r.focus}`}>{FOCUS_EMOJI[r.focus as Focus]}</span></td>
                <td className="px-3 py-2 whitespace-nowrap"><span title={`Brand: ${r.brand}`}>{BRAND_EMOJI[r.brand as Brand]}</span></td>
                <td className="px-3 py-2 max-w-[280px]">
                  <div className="flex flex-wrap gap-1">
                    {(r.mission_tags||[]).slice(0,6).map((t, j) => (
                      <span key={j} className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-800 border border-blue-200 text-[11px]">{t}</span>
                    ))}
                  </div>
                </td>
                <td className="px-3 py-2 max-w-[320px]">
                  <div className="flex flex-wrap gap-1">
                    {(r.category_tags||[]).slice(0,6).map((t, j) => (
                      <span key={j} className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 text-[11px]">{t}</span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
            {!loading && view.length === 0 && (
              <tr><td colSpan={12} className="px-3 py-10 text-center text-gray-500">No results. Try relaxing filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <footer className="mt-4 flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="text-sm text-gray-600">Showing {(page - 1) * pageSize + (sorted.length ? 1 : 0)}-{Math.min(page * pageSize, sorted.length)} of {sorted.length}</div>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1 border rounded disabled:opacity-50" disabled={page === 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>Prev</button>
          <span className="text-sm">{page} / {pageCount}</span>
          <button className="px-3 py-1 border rounded disabled:opacity-50" disabled={page === pageCount} onClick={() => setPage((p) => Math.min(pageCount, p + 1))}>Next</button>
          <select className="ml-2 px-2 py-1 border rounded" value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
            {[10, 20, 50].map((n) => (<option key={n} value={n}>{n}/page</option>))}
          </select>
        </div>
      </footer>
    </div>
  );
}
