# -*- coding: utf-8 -*-
"""
dashboard.py — Tablero HTML estático de SF Crew 3.0.

Uso:
  python dashboard.py <ruta .sfcrew> [--view cliente] [--refresh 300]
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "notion-sync", "scripts"))
from sync_csv import CANONICAL, APPROVAL_STATES, EXCEPTION_STATES

STATUS_LABEL = {
    "pending": "Pendiente", "assigned": "Asignada", "in_progress": "En curso",
    "ready_to_merge": "Lista", "completed": "Lista", "qa": "QA",
    "deployed": "Desplegada", "blocked": "Bloqueada", "partial": "Parcial",
    "tech-debt": "Deuda técnica", "closed": "Cerrada", "returned": "De vuelta",
}
STATUS_COLOR = {
    "pending": "#8a8f98", "assigned": "#b07d2b", "in_progress": "#2563eb",
    "ready_to_merge": "#7c3aed", "completed": "#7c3aed", "qa": "#7c3aed",
    "deployed": "#16a34a", "blocked": "#dc2626", "partial": "#ea580c",
    "tech-debt": "#64748b", "closed": "#94a3b8", "returned": "#d97706",
}
METHOD_LABEL = {"auto": "Headless", "manual": "Manual", "interactive": "Interactivo", "": "—"}
METHOD_COLOR = {"auto": "#0e7490", "manual": "#92400e", "interactive": "#5b21b6", "": "#94a3b8"}

ORDEN_STATUS = ["in_progress", "assigned", "ready_to_merge", "completed", "qa",
                "partial", "blocked", "pending", "tech-debt", "deployed", "closed"]


def read_rows(csv_path):
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        raw = [r for r in csv.reader(f, delimiter=";") if any(c.strip() for c in r)]
    header = raw[0]
    rows = []
    for r in raw[1:]:
        d = dict(zip(header, (r + [""] * len(header))[:len(header)]))
        first_key = header[0]
        if first_key != "id" and "id" in first_key:
            d["id"] = d.pop(first_key)
        rows.append(d)
    return rows


def build_data(sfcrew_dir):
    rows = read_rows(os.path.join(sfcrew_dir, "tasks.csv"))
    cfg = {}
    cfg_path = os.path.join(sfcrew_dir, "config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
    for r in rows:
        status = r.get("status", "")
        canon = CANONICAL.get(status, status)
        r["canon"] = canon
        r["is_deployed"] = canon == "deployed" or bool(r.get("deploy_ref", ""))
    counts = {}
    for r in rows:
        counts[r["canon"]] = counts.get(r["canon"], 0) + 1
    active_total = len([r for r in rows if r["canon"] != "closed"])
    return {
        "proyecto": cfg.get("project", os.path.basename(os.path.dirname(sfcrew_dir))),
        "org": cfg.get("org", ""),
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total": len(rows),
        "active_total": active_total,
        "counts": counts,
        "pct_deployed": round(100 * counts.get("deployed", 0) / max(active_total, 1)),
        "rows": rows,
    }


HTML = r"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SF Crew — {proyecto}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#f0f2f5;color:#111827;font-size:13px}}
header{{background:#0f2744;color:#fff;padding:12px 24px;display:flex;justify-content:space-between;align-items:center}}
header h1{{font-size:16px;font-weight:600}} header span{{font-size:11px;opacity:.65}}
.kpis{{display:flex;gap:10px;padding:14px 24px;flex-wrap:wrap}}
.kpi{{background:#fff;border-radius:8px;padding:10px 16px;box-shadow:0 1px 3px rgba(0,0,0,.08);min-width:100px}}
.kpi .n{{font-size:28px;font-weight:700;line-height:1}} .kpi .l{{font-size:11px;color:#6b7280;margin-top:2px}}
.kpi.main{{border-left:3px solid #16a34a}}
.progress{{height:6px;background:#e5e7eb;border-radius:3px;margin-top:6px;overflow:hidden}}
.progress div{{height:100%;background:#16a34a;border-radius:3px}}
.wrap{{padding:0 24px 24px}}
.filters{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}}
.filters button{{border:1px solid #d1d5db;background:#fff;border-radius:20px;padding:4px 12px;font-size:12px;cursor:pointer;color:#374151}}
.filters button.on{{background:#0f2744;color:#fff;border-color:#0f2744}}
#searchbox{{border:1px solid #d1d5db;border-radius:20px;padding:4px 14px;font-size:12px;width:220px;outline:none}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.08);overflow:hidden}}
thead tr{{background:#f8fafc}}
th{{padding:8px 10px;text-align:left;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid #e5e7eb;white-space:nowrap}}
td{{padding:7px 10px;border-bottom:1px solid #f1f5f9;vertical-align:top;max-width:280px}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:#fafbfc}}
tr.hidden{{display:none}}
.pill{{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:600;color:#fff;white-space:nowrap}}
.dep-yes{{color:#16a34a;font-weight:600}} .dep-no{{color:#9ca3af}}
.resumen{{color:#4b5563;font-size:12px;max-width:260px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}}
</style>
</head><body>
<header>
  <h1>SF Crew · {proyecto}</h1>
  <span>Org: {org} &nbsp;·&nbsp; {generado}</span>
</header>
<div class="kpis">{kpis}</div>
<div class="wrap">
<div class="filters">
  <input id="searchbox" type="search" placeholder="Buscar ID, HU, objeto…" oninput="filter()">
  {filter_btns}
</div>
<table id="tasks">
<thead><tr>
  <th>ID</th><th>HU</th><th>Objeto</th><th>Estado</th><th>Método</th>
  <th>Runner</th><th>Desplegado</th><th>Resultado / Descripción</th>
</tr></thead>
<tbody>
{rows_html}
</tbody>
</table>
</div>
<script>
var activeStatus = null;
function filter() {{
  var q = document.getElementById('searchbox').value.toLowerCase();
  document.querySelectorAll('#tasks tbody tr').forEach(function(tr) {{
    var text = tr.textContent.toLowerCase();
    var matchQ = !q || text.includes(q);
    var matchS = !activeStatus || tr.dataset.status === activeStatus;
    tr.classList.toggle('hidden', !(matchQ && matchS));
  }});
}}
function setStatus(s, btn) {{
  activeStatus = (activeStatus === s) ? null : s;
  document.querySelectorAll('.filters button[data-s]').forEach(function(b) {{ b.classList.remove('on'); }});
  if (activeStatus) btn.classList.add('on');
  filter();
}}
</script>
</body></html>"""


def e(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def pill(text, color):
    return f'<span class="pill" style="background:{color}">{e(text)}</span>'


def render(data):
    kpi_order = ["in_progress", "completed", "ready_to_merge", "deployed",
                 "pending", "blocked", "partial", "closed"]
    kpis_html = ""
    for s in kpi_order:
        n = data["counts"].get(s, 0)
        if not n:
            continue
        label = STATUS_LABEL.get(s, s)
        color = STATUS_COLOR.get(s, "#333")
        kpis_html += (f'<div class="kpi"><div class="n" style="color:{color}">{n}</div>'
                      f'<div class="l">{label}</div></div>')
    pct = data["pct_deployed"]
    kpis_html += (f'<div class="kpi main"><div class="n">{pct}%</div>'
                  f'<div class="l">Desplegado</div>'
                  f'<div class="progress"><div style="width:{pct}%"></div></div></div>')
    status_set = sorted(set(r["canon"] for r in data["rows"]),
                        key=lambda s: ORDEN_STATUS.index(s) if s in ORDEN_STATUS else 99)
    btns = "".join(
        f'<button data-s="{s}" onclick="setStatus(\'{s}\',this)">'
        f'{STATUS_LABEL.get(s, s)} ({data["counts"].get(s, 0)})</button>'
        for s in status_set)

    def row_key(r):
        s = r["canon"]
        idx = ORDEN_STATUS.index(s) if s in ORDEN_STATUS else 99
        return (idx, r.get("id", ""))

    sorted_rows = sorted(data["rows"], key=row_key)
    rows_html = ""
    for r in sorted_rows:
        canon = r["canon"]
        tier = r.get("headless_tier", "") or ""
        is_dep = r.get("is_deployed", False)
        dep_html = '<span class="dep-yes">&#10003; Sí</span>' if is_dep else '<span class="dep-no">No</span>'
        resumen = (r.get("result") or r.get("prompt") or "")[:200]
        rows_html += (
            f'<tr data-status="{canon}">'
            f'<td><strong>{e(r.get("id", ""))}</strong></td>'
            f'<td>{e(r.get("hu_code", ""))}</td>'
            f'<td>{e(r.get("object", ""))}</td>'
            f'<td>{pill(STATUS_LABEL.get(canon, canon), STATUS_COLOR.get(canon, "#333"))}</td>'
            f'<td>{pill(METHOD_LABEL.get(tier, "—"), METHOD_COLOR.get(tier, "#94a3b8"))}</td>'
            f'<td>{e(r.get("agent", ""))}</td>'
            f'<td>{dep_html}</td>'
            f'<td><div class="resumen">{e(resumen)}</div></td>'
            f'</tr>\n'
        )
    return HTML.format(
        proyecto=e(data["proyecto"]), org=e(data["org"]), generado=e(data["generado"]),
        kpis=kpis_html, filter_btns=btns, rows_html=rows_html,
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("sfcrew_dir")
    p.add_argument("--view", default="interna", choices=["interna", "cliente"])
    p.add_argument("--refresh", type=int, default=300)
    a = p.parse_args()
    data = build_data(a.sfcrew_dir)
    out = os.path.join(a.sfcrew_dir, "dashboard")
    os.makedirs(out, exist_ok=True)
    html = render(data)
    name = "index.html" if a.view == "interna" else "cliente.html"
    with open(os.path.join(out, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out, name), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Tablero generado: {os.path.join(out, name)}")


if __name__ == "__main__":
    main()
