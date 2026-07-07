# -*- coding: utf-8 -*-
"""
sync_csv.py — Helper determinista del motor de sync SFCrew 2.0 (skill notion-sync).

El Architect (Claude) orquesta; este script hace el trabajo local: parsear el CSV,
calcular hashes, detectar deltas/conflictos y emitir el plan de sync. Las escrituras
a Notion las ejecuta Claude vía MCP siguiendo el plan; las escrituras al CSV y al
estado las hace este script de forma atómica.

Subcomandos:
  stats <csv>                                  Resumen operativo (crew status / exceptions)
  plan <csv> --notion <snapshot.json>          Emite plan de sync (JSON a stdout)
       [--state <sync_state.json>]
  apply-csv <csv> --plan <plan.json>           Aplica cambios lado-CSV del plan (atómico)
  commit-state --plan <plan.json>              Persiste hashes post-sync
       --state <sync_state.json>

Formato snapshot Notion (lo genera Claude desde la consulta SQL al data source):
  [{"page_id": "<32hex>", "status": "Hecho", "completed_on": "2026-07-01",
    "sfcrew_task_id": "TASK-0026", "runner": "", "exec_result": "", "deploy_commit": ""}]
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from datetime import date, datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

V2_HEADER = [
    "id", "status", "project", "org", "object", "task_type", "depends_on",
    "agent", "worktree", "prompt", "result", "created", "started", "completed",
    "notion_page_id", "hu_code", "req_origin", "commit", "deploy_ref", "sync_state",
]

# Mapa de estados normativo (D3). CSV es dueño del estado de ejecución;
# Notion Status se deriva de aquí. 'completed' y 'failed' son alias legacy v1.
CANONICAL = {
    "pending": "pending", "assigned": "assigned", "in_progress": "in_progress",
    "dry_run_ok": "ready_to_merge", "ready_to_merge": "ready_to_merge",
    "completed": "ready_to_merge",  # legacy v1
    "deployed": "deployed", "blocked": "blocked", "failed": "blocked",  # legacy v1
    "partial": "partial", "qa": "qa", "tech-debt": "tech-debt",
}
STATE_TO_NOTION = {
    "pending": "No Comenzado", "assigned": "En Progreso SFCrew",
    "in_progress": "En Progreso SFCrew", "ready_to_merge": "QA",
    "qa": "QA", "deployed": "Hecho", "blocked": "Bloqueado",
    "partial": "En Progreso", "tech-debt": "En Progreso",
}
# Cola de aprobación del integrator
APPROVAL_STATES = {"ready_to_merge"}
EXCEPTION_STATES = {"blocked", "partial"}

# Una tarjeta Notion puede tener varias TASK enlazadas: su Status refleja la
# tarea MENOS avanzada (blocked domina), y Completed on solo cuando todas
# están deployed. Orden de avance:
PROGRESS_ORDER = ["blocked", "pending", "assigned", "in_progress", "partial",
                  "tech-debt", "qa", "ready_to_merge", "deployed"]


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.reader(f, delimiter=";") if any(c.strip() for c in r)]
    if rows[0] != V2_HEADER:
        sys.exit("El CSV no está en esquema v2. Correr primero migrate_tasks_csv_v2.py")
    return [dict(zip(V2_HEADER, (r + [""] * len(V2_HEADER))[: len(V2_HEADER)])) for r in rows[1:]]


def write_csv(path, rows):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(V2_HEADER)
        w.writerows([[r[c] for c in V2_HEADER] for r in rows])
    os.replace(tmp, path)


def csv_hash(row):
    owned = "|".join(row[c] for c in ("status", "result", "commit", "deploy_ref", "started", "completed"))
    return hashlib.sha1(owned.encode("utf-8")).hexdigest()


def notion_hash(card):
    owned = "|".join(str(card.get(k) or "") for k in ("status", "completed_on"))
    return hashlib.sha1(owned.encode("utf-8")).hexdigest()


def load_json(path, default):
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def cmd_stats(args):
    rows = read_csv(args.csv_path)
    by = {}
    for r in rows:
        canon = CANONICAL.get(r["status"], r["status"])
        by[canon] = by.get(canon, 0) + 1
    approval = [r for r in rows if CANONICAL.get(r["status"]) in APPROVAL_STATES]
    exceptions = [r for r in rows if CANONICAL.get(r["status"]) in EXCEPTION_STATES
                  or r["sync_state"] == "conflict"]
    unassigned = [r for r in rows if CANONICAL.get(r["status"]) == "pending" and not r["agent"].strip()]
    unlinked = [r for r in rows if not r["notion_page_id"] and r["hu_code"]]
    print(json.dumps({
        "total": len(rows),
        "por_estado_canonico": dict(sorted(by.items())),
        "cola_aprobacion": [{"id": r["id"], "hu": r["hu_code"], "agent": r["agent"],
                             "worktree": r["worktree"], "object": r["object"]} for r in approval],
        "excepciones": [{"id": r["id"], "status": r["status"], "hu": r["hu_code"],
                         "sync_state": r["sync_state"],
                         "resumen": (r["result"] or r["prompt"])[:140]} for r in exceptions],
        "pending_sin_agente": len(unassigned),
        "sin_enlace_notion": [r["id"] for r in unlinked],
    }, ensure_ascii=False, indent=2))


def cmd_plan(args):
    rows = read_csv(args.csv_path)
    cards = {c["page_id"]: c for c in load_json(args.notion, [])}
    state = load_json(args.state, {})
    plan, conflicts = [], []

    groups = {}
    for r in rows:
        pid = r["notion_page_id"].strip()
        if pid:
            groups.setdefault(pid, []).append(r)

    for pid, members in groups.items():
        card = cards.get(pid)
        if card is None:
            if not args.partial:
                conflicts.append({"tasks": [m["id"] for m in members],
                                  "tipo": "tarjeta_no_encontrada", "page_id": pid})
            continue

        canons = [CANONICAL.get(m["status"], "pending") for m in members]
        agg = min(canons, key=lambda c: PROGRESS_ORDER.index(c) if c in PROGRESS_ORDER else 1)
        expected_status = STATE_TO_NOTION.get(agg)
        all_deployed = all(c == "deployed" for c in canons)
        group_hash = hashlib.sha1("|".join(csv_hash(m) for m in members).encode()).hexdigest()

        prev = state.get(pid, {})
        nh = notion_hash(card)
        csv_changed = prev.get("csv_hash") != group_hash
        notion_changed = prev.get("notion_hash") != nh
        first_sync = not prev

        updates = {}
        if expected_status and card.get("status") != expected_status:
            if notion_changed and csv_changed and not first_sync:
                conflicts.append({
                    "tasks": [m["id"] for m in members], "tipo": "conflicto_status",
                    "page_id": pid, "csv_dice": expected_status,
                    "notion_dice": card.get("status"),
                    "politica": "CSV es dueño del estado de ejecución; revisar y decidir",
                })
                continue
            updates["Status"] = expected_status
        if all_deployed and not card.get("completed_on"):
            dates = [m["completed"][:10] for m in members if m["completed"]]
            updates["Completed on"] = max(dates) if dates else str(date.today())
        task_ids = ",".join(m["id"] for m in members)
        if card.get("sfcrew_task_id") != task_ids:
            updates["SFCrew Task ID"] = task_ids
        agents = ",".join(sorted({m["agent"] for m in members if m["agent"]}))
        if agents and card.get("runner") != agents.split(",")[0]:
            updates["Runner"] = agents.split(",")[0]  # select admite un valor
        results = " || ".join(f'{m["id"]}: {m["result"]}' for m in members if m["result"])[:1900]
        if results and card.get("exec_result") != results:
            updates["Exec Result"] = results
        refs = ",".join((m["deploy_ref"] or m["commit"]) for m in members
                        if (m["deploy_ref"] or m["commit"]))
        if refs and card.get("deploy_commit") != refs:
            updates["Deploy Commit"] = refs

        needs_flag = any(m["sync_state"] != "ok" for m in members)
        if updates or needs_flag:
            plan.append({
                "tasks": [m["id"] for m in members], "page_id": pid,
                "hu": members[0]["hu_code"],
                "notion_updates": updates,
                "csv_updates": {"sync_state": "ok"},
                "hashes": {"csv_hash": group_hash},
            })

    print(json.dumps({
        "generado": datetime.now().isoformat(timespec="seconds"),
        "acciones": plan, "conflictos": conflicts,
        "resumen": {"tarjetas_a_sincronizar": len(plan), "conflictos": len(conflicts)},
    }, ensure_ascii=False, indent=2))


def cmd_apply_csv(args):
    rows = read_csv(args.csv_path)
    plan = load_json(args.plan, {})
    by_id = {r["id"]: r for r in rows}
    n = 0
    for a in plan.get("acciones", []):
        for tid in a["tasks"]:
            r = by_id.get(tid)
            if r:
                r.update(a.get("csv_updates", {}))
                n += 1
    for c in plan.get("conflictos", []):
        for tid in c.get("tasks", []):
            r = by_id.get(tid)
            if r:
                r["sync_state"] = "conflict"
    write_csv(args.csv_path, rows)
    print(f"CSV actualizado: {n} filas, {len(plan.get('conflictos', []))} conflictos marcados.")


def cmd_commit_state(args):
    plan = load_json(args.plan, {})
    state = load_json(args.state, {})
    now = datetime.now().isoformat(timespec="seconds")
    for a in plan.get("acciones", []):
        expected = a.get("notion_updates", {})
        st = state.get(a["page_id"], {})
        st["tasks"] = a["tasks"]
        st["csv_hash"] = a["hashes"]["csv_hash"]
        if "Status" in expected or "Completed on" in expected:
            base = {"status": expected.get("Status", st.get("notion_status")),
                    "completed_on": expected.get("Completed on", st.get("notion_completed_on"))}
            st["notion_hash"] = notion_hash(base)
            st["notion_status"] = base["status"]
            st["notion_completed_on"] = base["completed_on"]
        st["last_synced"] = now
        state[a["page_id"]] = st
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(args.state) or ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os.replace(tmp, args.state)
    print(f"sync_state actualizado: {len(plan.get('acciones', []))} tarjetas.")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stats"); s.add_argument("csv_path"); s.set_defaults(fn=cmd_stats)
    s = sub.add_parser("plan"); s.add_argument("csv_path")
    s.add_argument("--notion", required=True); s.add_argument("--state")
    s.add_argument("--partial", action="store_true",
                   help="El snapshot no cubre todas las tarjetas: omitir las ausentes en vez de marcar conflicto")
    s.set_defaults(fn=cmd_plan)
    s = sub.add_parser("apply-csv"); s.add_argument("csv_path")
    s.add_argument("--plan", required=True); s.set_defaults(fn=cmd_apply_csv)
    s = sub.add_parser("commit-state")
    s.add_argument("--plan", required=True); s.add_argument("--state", required=True)
    s.set_defaults(fn=cmd_commit_state)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
