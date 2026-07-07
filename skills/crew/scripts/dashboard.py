# -*- coding: utf-8 -*-
"""
dashboard.py — Genera el tablero HTML estático de SF Crew 2.0 para un proyecto.

Lee tasks.csv v2 (+ config.json y, si existe, un snapshot Notion) y escribe
{proyecto}/.sfcrew/dashboard/index.html + data.json. Solo lectura del estado:
el tablero es reportería, no operación (Opción B, decisión D11).

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
from sync_csv import V2_HEADER, CANONICAL, APPROVAL_STATES, EXCEPTION_STATES  # noqa: E402

ORDEN = ["pending", "assigned", "in_progress", "ready_to_merge", "qa",
         "deployed", "blocked", "partial", "tech-debt"]
LABEL = {"pending": "Pendiente", "assigned": "Asignada", "in_progress": "En ejecución",
         "ready_to_merge": "Lista para aprobar", "qa": "QA", "deployed": "Desplegada",
         "blocked": "Bloqueada", "partial": "Parcial", "tech-debt": "Deuda técnica"}
COLOR = {"pending": "#8a8f98", "assigned": "#b07d2b", "in_progress": "#2b6cb0",
         "ready_to_merge": "#805ad5", "qa": "#805ad5", "deployed": "#2f855a",
         "blocked": "#c53030", "partial": "#dd6b20", "tech-debt": "#718096"}


def read_rows(csv_path):
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.reader(f, delimiter=";") if any(c.strip() for c in r)]
    assert rows[0] == V2_HEADER, "CSV no es v2"
    return [dict(zip(V2_HEADER, (r + [""] * len(V2_HEADER))[: len(V2_HEADER)])) for r in rows[1:]]


def build_data(sfcrew_dir, view):
    rows = read_rows(os.path.join(sfcrew_dir, "tasks.csv"))
    cfg = {}
    cfg_path = os.path.join(sfcrew_dir, "config.json")
    if os.path.exists(cfg_path):
        cfg = json.load(open(cfg_path, encoding="utf-8"))

    for r in rows:
        r["canon"] = CANONICAL.get(r["status"], r["status"])

    counts = {s: 0 for s in ORDEN}
    for r in rows:
        counts[r["canon"]] = counts.get(r["canon"], 0) + 1

    def brief(r, with_tech=True):
        d = {"id": r["id"], "hu": r["hu_code"], "estado": LABEL.get(r["canon"], r["canon"]),
             "objeto": r["object"], "resumen": (r["result"] or r["prompt"])[:160]}
        if with_tech and view != "cliente":
            d.update({"runner": r["agent"], "rama": r["worktree"]})
        return d

    data = {
        "proyecto": cfg.get("project", os.path.basename(os.path.dirname(sfcrew_dir))),
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "vista": view,
        "conteos": {LABEL[s]: counts.get(s, 0) for s in ORDEN if counts.get(s)},
        "colores": {LABEL[s]: COLOR[s] for s in ORDEN},
        "total": len(rows),
        "pct_desplegado": round(100 * counts.get("deployed", 0) / max(len(rows), 1)),
        "actividad": [brief(r) for r in rows if r["canon"] in ("assigned", "in_progress")],
        "cola_aprobacion": [brief(r) for r in rows if r["canon"] in APPROVAL_STATES],
        "excepciones": [brief(r) for r in rows if r["canon"] in EXCEPTION_STATES
                        or r["sync_state"] == "conflict"],
        "recientes": sorted([brief(r) for r in rows if r["canon"] == "deployed"],
                            key=lambda x: x["id"], reverse=True)[:10],
        "adopcion": None,  # lo llena adoption-tracker vía adoption.json
    }
    adoption_path = os.path.join(sfcrew_dir, "adoption.json")
    if os.path.exists(adoption_path):
        data["adopcion"] = json.load(open(adoption_path, encoding="utf-8"))
    if view == "cliente":
        data.pop("excepciones")
        data["actividad"] = [{k: v for k, v in a.items()} for a in data["actividad"]]
    return data


HTML = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="{refresh}">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SF Crew — {proyecto}</title><style>
body{{font-family:Segoe UI,system-ui,sans-serif;margin:0;background:#f5f6f8;color:#1a202c}}
header{{background:#1a3a5c;color:#fff;padding:14px 24px;display:flex;justify-content:space-between;align-items:baseline}}
header h1{{font-size:18px;margin:0}} header span{{font-size:12px;opacity:.75}}
main{{padding:20px 24px;max-width:1100px;margin:auto}}
.cards{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}}
.card{{background:#fff;border-radius:8px;padding:12px 18px;box-shadow:0 1px 3px rgba(0,0,0,.08);min-width:110px}}
.card b{{display:block;font-size:26px}} .card small{{color:#4a5568}}
section{{background:#fff;border-radius:8px;padding:14px 18px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
h2{{font-size:14px;text-transform:uppercase;letter-spacing:.05em;color:#4a5568;margin:0 0 10px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
td,th{{text-align:left;padding:6px 8px;border-bottom:1px solid #edf2f7;vertical-align:top}}
th{{color:#718096;font-weight:600}}
.pill{{display:inline-block;padding:1px 8px;border-radius:10px;color:#fff;font-size:11px}}
.empty{{color:#a0aec0;font-style:italic}}
.bar{{height:10px;background:#e2e8f0;border-radius:5px;overflow:hidden;margin-top:6px}}
.bar div{{height:100%;background:#2f855a}}
</style></head><body>
<header><h1>SF Crew — {proyecto}{sufijo}</h1><span>Actualizado {generado} · auto-refresh {refresh}s</span></header>
<main>
<div class="cards">{cards}
<div class="card"><b>{pct}%</b><small>Desplegado</small><div class="bar"><div style="width:{pct}%"></div></div></div>
</div>
{secciones}
</main></body></html>"""


def tabla(items, cols):
    if not items:
        return '<p class="empty">Nada por aquí.</p>'
    head = "".join(f"<th>{c}</th>" for c in cols)
    body = ""
    for it in items:
        body += "<tr>" + "".join(f"<td>{it.get(c.lower(), '') or ''}</td>" for c in cols) + "</tr>"
    return f"<table><tr>{head}</tr>{body}</table>"


def render(data, refresh):
    cards = "".join(
        f'<div class="card"><b style="color:{data["colores"].get(k, "#333")}">{v}</b><small>{k}</small></div>'
        for k, v in data["conteos"].items())
    cols_t = ["Id", "Hu", "Objeto", "Runner", "Resumen"] if data["vista"] != "cliente" \
        else ["Id", "Hu", "Objeto", "Estado"]
    secs = f'<section><h2>Cola de aprobación ({len(data["cola_aprobacion"])})</h2>{tabla(data["cola_aprobacion"], cols_t)}</section>'
    secs += f'<section><h2>Actividad de agentes</h2>{tabla(data["actividad"], cols_t)}</section>'
    if "excepciones" in data:
        secs += f'<section><h2>Excepciones ({len(data["excepciones"])})</h2>{tabla(data["excepciones"], ["Id", "Hu", "Estado", "Resumen"])}</section>'
    secs += f'<section><h2>Desplegado recientemente</h2>{tabla(data["recientes"], ["Id", "Hu", "Objeto", "Resumen"])}</section>'
    if data.get("adopcion"):
        secs += f'<section><h2>Adopción por épica</h2>{tabla(data["adopcion"], ["Epica", "Construido", "Adoptado"])}</section>'
    return HTML.format(proyecto=data["proyecto"], generado=data["generado"],
                       refresh=refresh, cards=cards, pct=data["pct_desplegado"],
                       sufijo=" · vista cliente" if data["vista"] == "cliente" else "",
                       secciones=secs)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("sfcrew_dir")
    p.add_argument("--view", default="interna", choices=["interna", "cliente"])
    p.add_argument("--refresh", type=int, default=300)
    a = p.parse_args()

    data = build_data(a.sfcrew_dir, a.view)
    out = os.path.join(a.sfcrew_dir, "dashboard")
    os.makedirs(out, exist_ok=True)
    name = "index.html" if a.view == "interna" else "cliente.html"
    with open(os.path.join(out, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out, name), "w", encoding="utf-8") as f:
        f.write(render(data, a.refresh))
    print(f"Tablero generado: {os.path.join(out, name)}")


if __name__ == "__main__":
    main()
