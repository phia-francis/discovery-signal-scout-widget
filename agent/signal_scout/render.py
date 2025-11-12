from __future__ import annotations
from typing import Dict, List
from string import Template

def render_markdown(rows: List[Dict]) -> str:
    def sym(r):
        focus = {"social":"👥","tech":"🤖","both":"👥🤖"}[r["focus"]]
        brand = {"media":"🎙","PH":"⚡","both":"🎙⚡"}[r["brand"]]
        return f"{r['mission_links']} • {r['archetype']} {focus} {brand}"
    header = "| Signal | Source | Mission | Archetype | Brief summary | Equity | Score | Tags |\n|---|---|---|---|---|---|---|---|"
    lines = []
    for r in rows:
        lines.append(
            f"| {r['signal']} | [{r['source_title']}]({r['source_url']}) | {r['mission_links']} | {r['archetype']} | "
            f"{r['brief_summary']} | {r['equity_consequence']} | {r['total_score']} | {sym(r)} |"
        )
    return "\n".join([header] + lines)

def render_html(rows: List[Dict], report_date: str) -> str:
    head_template = Template(
        """<!doctype html><html><head><meta charset="utf-8"><title>Signal Scout</title>
<style>
body{font-family:system-ui,Segoe UI,Arial;padding:24px}
table{border-collapse:collapse;width:100%} th,td{border:1px solid #ddd;padding:8px;vertical-align:top}
th{cursor:pointer;position:sticky;top:0;background:#fafafa}
.small{color:#555;font-size:12px}
.badge{display:inline-block;padding:2px 6px;border-radius:6px;background:#eef;font-size:12px;margin-right:4px}
tfoot td{background:#fafafa;font-weight:600}
</style></head><body><h1>Signal Scout — Daily Results</h1>
<p class="small">Date: ${report_date}</p>
    head = f"""<!doctype html><html><head><meta charset="utf-8"><title>Signal Scout</title>
<style>
body{{font-family:system-ui,Segoe UI,Arial;padding:24px}}
table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #ddd;padding:8px;vertical-align:top}}
th{{cursor:pointer;position:sticky;top:0;background:#fafafa}}
.small{{color:#555;font-size:12px}}
.badge{{display:inline-block;padding:2px 6px;border-radius:6px;background:#eef;font-size:12px;margin-right:4px}}
tfoot td{{background:#fafafa;font-weight:600}}
</style></head><body><h1>Signal Scout — Daily Results</h1>
<p class="small">Date: {report_date}</p>
<table id="tbl"><thead><tr>
<th>Signal</th><th>Source</th><th>Mission</th><th>Archetype</th><th>Brief summary</th><th>Equity</th><th>Score</th><th>Tags</th>
</tr></thead><tbody>
"""
    )
    head = head_template.substitute(report_date=report_date)
    rows_html = []
    for r in rows:
        tags = f"{r['mission_links']} " + {"social":"👥","tech":"🤖","both":"👥🤖"}[r["focus"]] + " " + {"media":"🎙","PH":"⚡","both":"🎙⚡"}[r["brand"]]
        rows_html.append(
            f"<tr><td>{r['signal']}</td>"
            f"<td><a href='{r['source_url']}' target='_blank'>{r['source_title']}</a></td>"
            f"<td>{r['mission_links']}</td>"
            f"<td><span class='badge'>{r['archetype']}</span></td>"
            f"<td>{r['brief_summary']}</td>"
            f"<td>{r['equity_consequence']}</td>"
            f"<td>{r['total_score']}</td>"
            f"<td>{tags}</td></tr>"
        )
    # footer stats
    avg = lambda k: round(sum(r[k] for r in rows) / len(rows), 2) if rows else 0
    missions = ", ".join(sorted(set(r["mission_links"] for r in rows)))
    archs = ", ".join(sorted(set(r["archetype"] for r in rows)))
    foot_template = Template(
        """
</tbody><tfoot><tr>
<td colspan="8">Avg relevance=${avg_relevance} • Avg credibility=${avg_credibility} • Avg novelty=${avg_novelty} • Missions=[${missions}] • Archetypes=[${archetypes}]</td>
    avg = lambda k: round(sum(r[k] for r in rows)/len(rows),2) if rows else 0
    missions = ", ".join(sorted(set(r["mission_links"] for r in rows)))
    archs = ", ".join(sorted(set(r["archetype"] for r in rows)))
    foot = f"""
</tbody><tfoot><tr>
<td colspan="8">Avg relevance={avg('relevance')} • Avg credibility={avg('credibility')} • Avg novelty={avg('novelty')} • Missions=[{missions}] • Archetypes=[{archs}]</td>
</tr></tfoot></table>
<script>
const getCell=(tr,i)=>tr.children[i].innerText||tr.children[i].textContent;
document.querySelectorAll('#tbl th').forEach((th,i)=>{
  th.addEventListener('click',()=>{
    const tbody=th.closest('table').querySelector('tbody');
    const rows=[...tbody.querySelectorAll('tr')];
    const asc=!th.classList.contains('asc');
    rows.sort((a,b)=>getCell(a,i).localeCompare(getCell(b,i),undefined,{numeric:true})*(asc?1:-1));
    tbody.innerHTML='';
    rows.forEach(r=>tbody.appendChild(r));
    tbody.innerHTML=''; rows.forEach(r=>tbody.appendChild(r));
    th.parentElement.querySelectorAll('th').forEach(x=>x.classList.remove('asc','desc'));
    th.classList.add(asc?'asc':'desc');
  });
});
</script>
</body></html>"""
    )
    foot = foot_template.substitute(
        avg_relevance=f"{avg('relevance')}",
        avg_credibility=f"{avg('credibility')}",
        avg_novelty=f"{avg('novelty')}",
        missions=missions,
        archetypes=archs,
    )
    return head + "\n".join(rows_html) + foot
