# -*- coding: utf-8 -*-
"""
launcher.py — Lanzador de runners headless de SF Crew 3.0.

Lee el CSV, selecciona la cola de cada runner (assigned / returned / pending
con agente, tier `auto` por defecto) y construye las invocaciones headless.

Modo por defecto: PLAN (imprime lo que lanzaría, no lanza nada).
--execute: lanza de verdad, secuencialmente por runner.

Uso:
  python launcher.py <ruta .sfcrew> [--tier auto] [--agent deepseek] [--execute]
"""
import argparse
import csv
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "notion-sync", "scripts"))
from sync_csv import CANONICAL

ALIAS_CMD = {
    "claude": "claude",
    "deepseek": "claude-deepseek",
    "glm": "claude-zai",
    "grok": "grok",
}
LAUNCHABLE = {"assigned", "returned", "pending"}


def read_rows(csv_path):
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        raw = [r for r in csv.reader(f, delimiter=";") if any(c.strip() for c in r)]
    header = raw[0]
    out = []
    for r in raw[1:]:
        d = dict(zip(header, (r + [""] * len(header))[:len(header)]))
        if header[0] != "id" and "id" in header[0]:
            d["id"] = d.pop(header[0])
        if "cid" in d and "id" not in d:
            d["id"] = d["cid"]
        out.append(d)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sfcrew_dir")
    ap.add_argument("--tier", default="auto")
    ap.add_argument("--agent")
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()

    sfcrew = os.path.abspath(args.sfcrew_dir)
    rows = read_rows(os.path.join(sfcrew, "tasks.csv"))

    queues, skipped = {}, []
    for r in rows:
        canon = CANONICAL.get(r.get("status", ""), "")
        agent = (r.get("agent") or "").strip()
        if canon not in LAUNCHABLE or not agent:
            continue
        if (r.get("headless_tier") or "").strip() != args.tier:
            continue
        if args.agent and agent != args.agent:
            continue
        if agent not in ALIAS_CMD:
            skipped.append((r.get("id", "?"), agent, "sin alias headless"))
            continue
        md = os.path.join(sfcrew, "tasks", f"{r.get('id','?')}.md")
        if not os.path.exists(md):
            skipped.append((r.get("id", "?"), agent, "sin .md de spec"))
            continue
        queues.setdefault(agent, []).append((r, md))

    if not queues and not skipped:
        print(f"Nada que lanzar (tier={args.tier}).")
        return

    for tid, agent, why in skipped:
        print(f"SKIP {tid} [{agent}]: {why}")

    for agent, items in sorted(queues.items()):
        cmd_alias = ALIAS_CMD[agent]
        returned = [r.get("id") for r, _ in items
                    if CANONICAL.get(r.get("status", "")) == "returned"]
        print(f"\n== {agent} ({cmd_alias}) — {len(items)} tarea(s)"
              + (f", {len(returned)} de vuelta: {', '.join(returned)}" if returned else ""))
        for r, md in items:
            tid = r.get("id", "?")
            invocation = f'bash -lc \'{cmd_alias} -p "$(cat "{md}")"\'\''
            if args.execute:
                print(f"  ▶ {tid} — ejecutando…")
                res = subprocess.run(invocation, shell=True)
                print(f"  ■ {tid} — exit {res.returncode}")
            else:
                print(f"  PLAN {tid}: {invocation}")

    if not args.execute:
        print("\nModo PLAN: nada fue lanzado. Repetir con --execute para lanzar.")


if __name__ == "__main__":
    main()
