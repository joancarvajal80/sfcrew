# -*- coding: utf-8 -*-
"""
console.py — Crew Console v0 (SF Crew 3.0). Servidor web local solo-lectura.

Lee tasks.csv en vivo en cada request. Sin dependencias externas (stdlib).
Puerto por defecto: 8787.

Uso:
  python console.py [--root "C:/Users/Joan/Proyectos Salesforce"] [--port 8787]

Vistas:
  /                  Excepciones — lo que necesita atención de Joan
  /board             Kanban por estado canónico
  /task/TASK-NNNN    Detalle de tarea (fila CSV + TASK-NNNN.md)
"""
import argparse
import html
import os
import re
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(__file__))
import dashboard as dash

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "notion-sync", "scripts"))
from sync_csv import APPROVAL_STATES, EXCEPTION_STATES

DEFAULT_ROOT = r"C:\Users\Joan\Proyectos Salesforce"
KANBAN_COLS = ["pending", "assigned", "in_progress", "ready_to_merge",
               "blocked", "partial", "deployed"]


def discover_projects(root):
    out = {}
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        csv_path = os.path.join(root, name, ".sfcrew", "tasks.csv")
        if os.path.isfile(csv_path):
            out[name] = os.path.join(root, name, ".sfcrew")
    return out


def e(s):
    return html.escape(str(s or ""), quote=True)


def md_to_html(text):
    lines = text.splitlines()
    out, in_code, in_list = [], False, False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    def inline(s):
        s = e(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        return s

    for ln in lines:
        if ln.strip().startswith("```"):
            close_list()
            out.append("</pre>" if in_code else "<pre>")
            in_code = not in_code
            continue
        if in_code:
            out.append(e(ln))
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", ln)
        if m:
            close_list()
            lvl = min(len(m.group(1)) + 1, 5)
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            continue
        if re.match(r"^\s*[-*]\s+", ln):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(re.sub(r'^\\s*[-*]\\s+', '', ln))}</li>")
            continue
        close_list()
        if ln.strip() == "":
            out.append("")
        elif ln.startswith("|"):
            out.append(f'<div class="mdrow"><code>{e(ln)}</code></div>')
        else:
            out.append(f"<p>{inline(ln)}</p>")
    close_list()
    if in_code:
        out.append("</pre>")
    return "\n".join(out)


PAGE = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
{refresh}
<title>Crew Console · {title}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#f0f2f5;color:#111827;font-size:13px}}
header{{background:#0f2744;color:#fff;padding:10px 22px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}}
header h1{{font-size:15px;font-weight:600;margin-right:6px}}
header a{{color:#cbd5e1;text-decoration:none;font-size:13px;padding:3px 10px;border-radius:14px}}
header a.on{{background:#fff;color:#0f2744;font-weight:600}}
header form{{margin-left:auto}}
header select{{border:none;border-radius:6px;padding:4px 8px;font-size:12px}}
header .ts{{font-size:11px;opacity:.6}}
.wrap{{padding:18px 22px}}
h2{{font-size:14px;margin:14px 0 8px;color:#0f2744}}
.pill{{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:600;color:#fff;white-space:nowrap}}
.card{{background:#fff;border-radius:10px;padding:12px 16px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:10px}}
.card.exc{{border-left:3px solid #dc2626}}
.card.app{{border-left:3px solid #7c3aed}}
.card.warn{{border-left:3px solid #ea580c}}
.card .tid{{font-weight:700}} .card .meta{{color:#6b7280;font-size:11px;margin-top:2px}}
.card p{{margin-top:6px;color:#374151}}
a.tlink{{color:#0f2744;text-decoration:none}} a.tlink:hover{{text-decoration:underline}}
.empty{{color:#16a34a;font-weight:600;padding:8px 0}}
.board{{display:flex;gap:12px;align-items:flex-start;overflow-x:auto;padding-bottom:12px}}
.col{{background:#e8ecf1;border-radius:10px;padding:10px;min-width:230px;max-width:230px;flex-shrink:0}}
.col h3{{font-size:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center}}
.col .count{{background:#fff;border-radius:10px;padding:0 8px;font-size:11px;color:#374151}}
.tcard{{background:#fff;border-radius:8px;padding:8px 10px;margin-bottom:8px;box-shadow:0 1px 2px rgba(0,0,0,.06);font-size:12px}}
.tcard .hu{{color:#6b7280;font-size:11px}}
.tcard .obj{{color:#374151}}
.detail{{background:#fff;border-radius:10px;padding:18px 22px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.detail table{{margin:10px 0;border-collapse:collapse}}
.detail table td{{padding:3px 14px 3px 0;vertical-align:top}}
.detail table td:first-child{{color:#6b7280;font-size:11px;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}}
.detail pre{{background:#0f172a;color:#e2e8f0;border-radius:8px;padding:12px;overflow-x:auto;font-size:12px;margin:8px 0;font-family:Consolas,monospace}}
.detail code{{background:#f1f5f9;border-radius:4px;padding:0 4px;font-family:Consolas,monospace;font-size:12px}}
.detail h2,.detail h3,.detail h4{{margin:14px 0 6px;color:#0f2744}}
.detail ul{{margin:6px 0 6px 22px}}
.detail p{{margin:5px 0;line-height:1.5}}
.mdrow{{font-size:11px;overflow-x:auto;white-space:nowrap}}
</style></head><body>
<header>
  <h1>Crew Console</h1>
  <a href="/?p={p}" class="{on_exc}">Excepciones</a>
  <a href="/board?p={p}" class="{on_board}">Tablero</a>
  <form method="get" action="{path}">
    <select name="p" onchange="this.form.submit()">{proj_opts}</select>
  </form>
  <span class="ts">{ts}</span>
</header>
<div class="wrap">
{body}
</div></body></html>"""


def status_pill(canon):
    return (f'<span class="pill" style="background:'
            f'{dash.STATUS_COLOR.get(canon, "#333")}">'
            f'{e(dash.STATUS_LABEL.get(canon, canon))}</span>')


def task_link(r, p):
    tid = r.get("id", "")
    return f'<a class="tlink" href="/task/{e(tid)}?p={e(p)}"><strong>{e(tid)}</strong></a>'


def render_exceptions(data, p):
    rows = data["rows"]
    exc = [r for r in rows if r["canon"] in EXCEPTION_STATES]
    conf = [r for r in rows if (r.get("sync_state") or "") in ("conflict", "dirty")]
    unassigned = [r for r in rows if r["canon"] == "pending"
                  and (r.get("agent") or "").strip() in ("", "tbd")]
    approve = [r for r in rows if r["canon"] in APPROVAL_STATES]

    def cards(items, css, extra=None):
        out = ""
        for r in items:
            note = (r.get("result") or r.get("prompt") or "")[:220]
            xtra = f" · {e(extra(r))}" if extra else ""
            out += (f'<div class="card {css}">'
                    f'<span class="tid">{task_link(r, p)}</span> '
                    f'{status_pill(r["canon"])}'
                    f'<div class="meta">{e(r.get("hu_code", ""))} · '
                    f'{e(r.get("object", ""))} · runner: {e(r.get("agent", "") or "—")}'
                    f'{xtra}</div>'
                    f'<p>{e(note)}</p></div>')
        return out or '<div class="empty">&#10003; Nada aquí</div>'

    body = "<h2>&#9888; Excepciones (blocked / partial)</h2>"
    body += cards(exc, "exc")
    body += "<h2>&#8645; Conflictos de sync</h2>"
    body += cards(conf, "warn", extra=lambda r: f"sync: {r.get('sync_state', '')}")
    body += "<h2>&#9675; Pendientes sin asignar</h2>"
    body += cards(unassigned, "warn")
    body += (f"<h2>&#10003; Cola de aprobación ({len(approve)} listas "
             f"para crew approve)</h2>")
    body += cards(approve, "app")
    return body


def render_board(data, p):
    rows = data["rows"]
    cols_html = ""
    for canon in KANBAN_COLS:
        items = [r for r in rows if r["canon"] == canon]
        cards = ""
        for r in items:
            tier = r.get("headless_tier", "") or ""
            cards += (f'<div class="tcard">{task_link(r, p)} '
                      f'<span class="pill" style="background:'
                      f'{dash.METHOD_COLOR.get(tier, "#94a3b8")};font-size:10px">'
                      f'{e(dash.METHOD_LABEL.get(tier, "—"))}</span>'
                      f'<div class="hu">{e(r.get("hu_code", ""))} · '
                      f'{e(r.get("agent", "") or "—")}</div>'
                      f'<div class="obj">{e(r.get("object", ""))}</div></div>')
        cols_html += (f'<div class="col"><h3>'
                      f'{status_pill(canon)}'
                      f'<span class="count">{len(items)}</span></h3>{cards}</div>')
    closed = len([r for r in rows if r["canon"] == "closed"])
    note = (f'<p style="color:#6b7280;font-size:11px;margin-top:8px">'
            f'{closed} cerradas no mostradas · {data["pct_deployed"]}% desplegado '
            f'sobre {data["active_total"]} activas</p>')
    return f'<div class="board">{cols_html}</div>{note}'


def render_task(data, sfcrew_dir, tid, p):
    row = next((r for r in data["rows"] if r.get("id") == tid), None)
    if not row:
        return f"<h2>{e(tid)} no existe en tasks.csv</h2>"
    tier = row.get("headless_tier", "") or ""
    fields = [
        ("Estado", status_pill(row["canon"])),
        ("Método", f'<span class="pill" style="background:'
                   f'{dash.METHOD_COLOR.get(tier, "#94a3b8")}">'
                   f'{e(dash.METHOD_LABEL.get(tier, "—"))}</span>'),
        ("HU", e(row.get("hu_code", ""))),
        ("REQ origen", e(row.get("req_origin", ""))),
        ("Objeto", e(row.get("object", ""))),
        ("Tipo", e(row.get("task_type", ""))),
        ("Runner", e(row.get("agent", ""))),
        ("Worktree", e(row.get("worktree", ""))),
        ("Depende de", e(row.get("depends_on", "")) or "—"),
        ("Creada / Inicio / Fin", f'{e(row.get("created", ""))} / '
                                  f'{e(row.get("started", ""))} / '
                                  f'{e(row.get("completed", ""))}'),
        ("Commit", e(row.get("commit", "")) or "—"),
        ("Deploy ref", e(row.get("deploy_ref", "")) or "—"),
        ("Sync", e(row.get("sync_state", "")) or "—"),
        ("Resultado", e(row.get("result", "")) or "—"),
    ]
    tbl = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in fields)
    md_path = os.path.join(sfcrew_dir, "tasks", f"{tid}.md")
    if os.path.isfile(md_path):
        with open(md_path, encoding="utf-8") as f:
            md_html = md_to_html(f.read())
    else:
        md_html = f'<p style="color:#9ca3af">No hay {e(tid)}.md en .sfcrew/tasks/</p>'
    return (f'<div class="detail"><h2>{e(tid)}</h2>'
            f'<table>{tbl}</table><hr style="border:none;border-top:1px solid '
            f'#e5e7eb;margin:12px 0">{md_html}</div>')


class Handler(BaseHTTPRequestHandler):
    projects = {}

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        path = parsed.path
        if path == "/favicon.ico":
            self._send(404, "")
            return
        if not self.projects:
            self._send(500, "No se encontraron proyectos con .sfcrew/tasks.csv")
            return
        p = qs.get("p", [next(iter(self.projects))])[0]
        if p not in self.projects:
            p = next(iter(self.projects))
        sfcrew_dir = self.projects[p]
        try:
            data = dash.build_data(sfcrew_dir)
        except Exception as ex:
            self._send(500, f"<pre>Error leyendo {e(sfcrew_dir)}:\n{e(ex)}</pre>")
            return
        refresh = '<meta http-equiv="refresh" content="60">'
        if path == "/board":
            body, title, view = render_board(data, p), "Tablero", "board"
        elif path.startswith("/task/"):
            tid = urllib.parse.unquote(path[len("/task/"):])
            body, title, view = render_task(data, sfcrew_dir, tid, p), tid, "task"
            refresh = ""
        elif path == "/":
            body, title, view = render_exceptions(data, p), "Excepciones", "exc"
        else:
            self._send(404, "<h2>404</h2>")
            return
        opts = "".join(
            f'<option value="{e(name)}"{" selected" if name == p else ""}>{e(name)}</option>'
            for name in self.projects)
        page = PAGE.format(
            refresh=refresh, title=e(title), p=e(p),
            on_exc="on" if view == "exc" else "",
            on_board="on" if view == "board" else "",
            path=e(parsed.path), proj_opts=opts,
            ts=f'{e(data["proyecto"])} · {e(data["generado"])}',
            body=body)
        self._send(200, page)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--port", type=int, default=8787)
    a = ap.parse_args()
    Handler.projects = discover_projects(a.root)
    if not Handler.projects:
        print(f"Sin proyectos con .sfcrew/tasks.csv bajo {a.root}")
        sys.exit(1)
    print(f"Crew Console v0 — http://localhost:{a.port}")
    print("Proyectos:", ", ".join(Handler.projects))
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
