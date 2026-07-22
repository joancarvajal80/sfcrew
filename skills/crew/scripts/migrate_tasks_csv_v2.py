# -*- coding: utf-8 -*-
"""
migrate_tasks_csv_v2.py — Migra un tasks.csv SFCrew v1 al esquema v2.

Esquema v2 = v1 + notion_page_id;hu_code;req_origin;commit;deploy_ref;sync_state

Acciones:
  1. Backup del CSV original en .sfcrew/archive/
  2. Agrega las 6 columnas nuevas
  3. Backfill hu_code por regex sobre `prompt`
  4. Backfill notion_page_id desde el mapa code→page_id (--map)
  5. Normaliza: agent='tbd' → vacío
  6. Escritura atómica (temp + os.replace)

Uso:
  python migrate_tasks_csv_v2.py <ruta tasks.csv> --map notion_map.csv [--dry-run]
"""
import argparse
import csv
import os
import re
import shutil
import sys
import tempfile
from datetime import date

V1_HEADER = [
    "id", "status", "project", "org", "object", "task_type", "depends_on",
    "agent", "worktree", "prompt", "result", "created", "started", "completed",
]
NEW_COLS = ["notion_page_id", "hu_code", "req_origin", "commit", "deploy_ref", "sync_state"]
V2_HEADER = V1_HEADER + NEW_COLS

CODE_RE = re.compile(
    r"(HU-[A-Z]{1,2}\d{2}[A-Za-z]?|ADJ-\d{2}|DT-ACC-\d{2}|DT-CON-\d{2}|ÉPICA\s?\d{1,2})"
)


def load_map(path):
    mapping = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            code = row["code"].strip()
            pid = row["page_id"].strip()
            if code and pid:
                mapping[code] = pid
    return mapping


def migrate(csv_path, map_path, dry_run=False):
    notion_map = load_map(map_path) if map_path else {}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.reader(f, delimiter=";") if any(c.strip() for c in r)]
    header, data = rows[0], rows[1:]
    if header == V2_HEADER:
        print("Ya está en esquema v2 — nada que hacer (idempotente).")
        return
    if header != V1_HEADER:
        sys.exit(f"Header inesperado, aborto:\n{header}")
    out, stats = [V2_HEADER], {"hu": 0, "notion": 0, "tbd": 0}
    for r in data:
        r = (r + [""] * len(V1_HEADER))[:len(V1_HEADER)]
        row = dict(zip(V1_HEADER, r))
        if row["agent"].strip().lower() == "tbd":
            row["agent"] = ""
            stats["tbd"] += 1
        codes = []
        for m in CODE_RE.findall(row["prompt"]):
            code = re.sub(r"ÉPICA\s?", "ÉPICA ", m.strip())
            if code not in codes:
                codes.append(code)
        hu_code = ",".join(codes)
        if hu_code:
            stats["hu"] += 1
        page_id, sync_state = "", ""
        if codes and codes[0] in notion_map:
            page_id = notion_map[codes[0]]
            sync_state = "ok"
            stats["notion"] += 1
        elif hu_code:
            sync_state = "dirty"
        out.append([row[c] for c in V1_HEADER] + [page_id, hu_code, "", "", "", sync_state])
    print(f"Filas: {len(data)} | hu_code: {stats['hu']} | notion_page_id: {stats['notion']} | tbd: {stats['tbd']}")
    if dry_run:
        print("--dry-run: no se escribió nada.")
        return
    archive_dir = os.path.join(os.path.dirname(csv_path), "archive")
    os.makedirs(archive_dir, exist_ok=True)
    backup = os.path.join(archive_dir, f"tasks_v1_backup_{date.today():%Y%m%d}.csv")
    shutil.copy2(csv_path, backup)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(csv_path), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter=";", lineterminator="\n").writerows(out)
    os.replace(tmp, csv_path)
    print(f"Migrado OK. Backup: {backup}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("csv_path")
    p.add_argument("--map", dest="map_path")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    migrate(a.csv_path, a.map_path, a.dry_run)
