# -*- coding: utf-8 -*-
"""
review.py — Revisor headless de SF Crew 3.0.

Ensambla un payload (spec + diff de commits) y lo entrega a un modelo revisor
headless. El revisor nunca hace checkout ni escribe en git ni en el CSV.

Fuente del diff:
  1. Commits registrados en la columna `commit` de cada fila (ancla exacta).
  2. Fallback: git diff main...<worktree> si alguna fila no tiene commit.

Uso:
  python review.py <ruta .sfcrew> [--branch ExeDeepSeek] [--reviewer glm|opus]
                   [--exclude-agent <alias>] [--if-needed]
"""
import argparse
import csv
import hashlib
import os
import re
import subprocess
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "notion-sync", "scripts"))
from sync_csv import CANONICAL

MAX_DIFF_CHARS = 180_000

STABLE_BLOCK = """# Revisión de lote SFCrew — metadata Salesforce

Eres el revisor técnico de un lote de tareas Salesforce ejecutadas por un runner.
Cada tarea pasó un dry-run limpio: lo mecánico ya está filtrado.
Tu valor está en lo que el dry-run NO ve: lógica, fechas, contenido, FLS,
dependencias y convenciones. Tu reporte lo lee el Architect (Opus).

## Reglas duras

- **No inventes defectos.** Un falso positivo dispara un ciclo de re-ejecución
  de ~200k tokens. Si un archivo está bien, dilo: `APROBADA — sin hallazgos`.
- Un Get Records sin resultados devuelve null, NO hace fault.
- Cada hallazgo cita el elemento XML o la línea concreta, nunca generalidades.
- Sin acceso al org: metadata externa referenciada se declara como dependencia.

## Checklist funcional

1. **Fechas y horizontes**: filtros de Get Records sin offset cuando la spec pide N días.
2. **Contenido placeholder**: textos TODO/Ajustar/Colocar, emails sin merge fields.
3. **Merge fields**: sintaxis `{!...}` válida; parámetros vacíos.
4. **Estados**: flows Active cuando la spec pide Draft (o viceversa).
5. **Convenciones StudioDX**: prefijo en toda metadata custom; `required=false`;
   GVS antes que campos; `fieldPermissions` contiguos antes de `layoutAssignments`.
6. **FLS**: perfiles correctos según la spec.
7. **Coherencia spec⇔código**: lo entregado hace lo que la tarea pide.
8. **Duplicados**: sortOrder, nombres de elemento, bloques repetidos.

## Formato de salida

Por CADA tarea:

```
### TASK-NNNN
Veredicto: APROBADA | AJUSTE_MENOR | DEFECTO_DE_FONDO
Hallazgos:
- [CRITICO|MAYOR|MENOR] <archivo> · <elemento>: <qué y por qué> → <fix propuesto>
Dependencias a verificar:
- <metadata externa>
Spec de ajuste (solo si AJUSTE_MENOR): <instrucción precisa para el runner>
```

Cierra con `## Resumen del lote`: aprobadas / con ajuste / de fondo.
"""


def read_rows(csv_path):
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        raw = [r for r in csv.reader(f, delimiter=";") if any(c.strip() for c in r)]
    header = raw[0]
    rows = []
    for r in raw[1:]:
        d = dict(zip(header, (r + [""] * len(header))[:len(header)]))
        if header[0] != "id" and "id" in header[0]:
            d["id"] = d.pop(header[0])
        if "cid" in d and "id" not in d:
            d["id"] = d["cid"]
        rows.append(d)
    return rows


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def spec_tokens(rows, specs_text):
    tokens = set()
    for r in rows:
        obj = (r.get("object") or "").strip()
        if obj:
            tokens.add(obj)
    tokens |= set(re.findall(r"[A-Z]{2,5}_[A-Za-z0-9_]+", specs_text))
    return {t for t in tokens if len(t) > 5}


def diff_for_batch(repo, branch, rows, specs_text):
    commits = []
    for r in rows:
        c = (r.get("commit") or "").strip().split()[0] if (r.get("commit") or "").strip() else ""
        if c and c not in commits:
            commits.append(c)
    parts, source, warnings = [], "", []
    for c in commits:
        names = git(repo, "diff", "--name-only", f"{c}^..{c}").splitlines()
        if not names:
            parts.append(f"--- COMMIT {c} --- (no encontrado o vacío)")
            continue
        sel = names
        if len(names) > 50:
            toks = spec_tokens(rows, specs_text)
            sel = [n for n in names if any(t in n for t in toks)][:200]
            warnings.append(
                f"COMMIT {c} CONTAMINADO: {len(names):,} archivos para "
                f"{len(rows)} tarea(s). Diff acotado a {len(sel)} paths.")
        if sel:
            patch = git(repo, "diff", f"{c}^..{c}", "--", *sel)
            parts.append(f"--- COMMIT {c} ({len(sel)}/{len(names)} archivos) ---\n{patch}")
        else:
            parts.append(f"--- COMMIT {c} --- (ningún path matchea la spec)")
    source = f"commits del CSV: {', '.join(commits)}" if commits else ""
    if not any("diff --git" in p for p in parts):
        branch_diff = git(repo, "diff", f"main...{branch}")
        if branch_diff.strip():
            source = f"git diff main...{branch}"
            parts = [branch_diff]
    body = "\n\n".join(parts)
    if len(body) > MAX_DIFF_CHARS:
        body = body[:MAX_DIFF_CHARS] + "\n\n[... DIFF TRUNCADO ...]"
    return body, source, warnings


def read_specs(sfcrew_dir, rows):
    tasks_dir = os.path.join(sfcrew_dir, "tasks")
    specs = []
    for r in rows:
        tid = r.get("id", "?")
        md = os.path.join(tasks_dir, f"{tid}.md")
        if os.path.exists(md):
            with open(md, encoding="utf-8", errors="replace") as f:
                specs.append(f"## SPEC {tid}\n\n{f.read()}")
        else:
            specs.append(f"## SPEC {tid}\n\n(sin .md — prompt: {r.get('prompt','')})")
    return "\n\n".join(specs)


def build_payload(rows, branch, specs_text, diff_body, diff_source, warnings):
    warn_block = ""
    if warnings:
        warn_block = ("\n## ADVERTENCIAS DEL ENSAMBLADOR\n" +
                      "\n".join(f"- {w}" for w in warnings) + "\n")
    variable = [
        f"\n\n---\n\n# LOTE A REVISAR — rama {branch}",
        f"Tareas: {', '.join(r.get('id','?') for r in rows)}",
        f"Fuente del diff: {diff_source}",
        warn_block,
        specs_text,
        f"# DIFF DEL LOTE\n\n```diff\n{diff_body}\n```",
    ]
    return STABLE_BLOCK + "\n".join(variable)


def batch_key(rows):
    sig = "|".join(sorted(f"{r.get('id','?')}:{(r.get('commit') or '').strip()}"
                          for r in rows))
    return hashlib.sha1(sig.encode()).hexdigest()[:12]


def acquire_lock(out_dir, max_age_s=600):
    lock = os.path.join(out_dir, ".lock")
    if os.path.exists(lock):
        if time.time() - os.path.getmtime(lock) < max_age_s:
            return None
        os.remove(lock)
    with open(lock, "w") as f:
        f.write(str(os.getpid()))
    return lock


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sfcrew_dir")
    ap.add_argument("--branch")
    ap.add_argument("--reviewer", choices=["glm", "opus"])
    ap.add_argument("--exclude-agent")
    ap.add_argument("--if-needed", action="store_true")
    args = ap.parse_args()

    if args.if_needed and os.environ.get("SFCREW_TICK"):
        return

    sfcrew = os.path.abspath(args.sfcrew_dir)
    repo = os.path.dirname(sfcrew)
    rows = read_rows(os.path.join(sfcrew, "tasks.csv"))
    ready = [r for r in rows if CANONICAL.get(r.get("status", ""), "") == "ready_to_merge"]
    if args.branch:
        ready = [r for r in ready if r.get("worktree") == args.branch]
    if not ready:
        if not args.if_needed:
            print("Nada en ready_to_merge para revisar.")
        return

    out_dir = os.path.join(sfcrew, "reviews")
    os.makedirs(out_dir, exist_ok=True)
    lock = acquire_lock(out_dir)
    if lock is None:
        if not args.if_needed:
            print("Otra revisión en curso (reviews/.lock).")
        return
    try:
        run_batches(args, sfcrew, repo, rows, ready, out_dir)
    finally:
        if os.path.exists(lock):
            os.remove(lock)


def run_batches(args, sfcrew, repo, rows, ready, out_dir):
    ts = datetime.now().strftime("%Y%m%d-%H%M")
    PENDING = {"assigned", "in_progress", "returned"}
    by_branch = {}
    for r in ready:
        by_branch.setdefault(r.get("worktree") or "sin-rama", []).append(r)
    for branch, batch in sorted(by_branch.items()):
        open_rows = [r for r in rows if (r.get("worktree") or "") == branch
                     and CANONICAL.get(r.get("status", ""), "") in PENDING]
        if open_rows:
            msg = (f"[{branch}] lote incompleto: {len(open_rows)} tarea(s) aún en curso.")
            if not args.if_needed:
                print(msg)
            continue
        key = batch_key(batch)
        existing = [f for f in os.listdir(out_dir) if key in f]
        if existing:
            if not args.if_needed:
                print(f"[{branch}] lote {key} ya tiene artefactos: {', '.join(sorted(existing))}.")
            continue
        own, others = [], []
        for r in batch:
            (own if args.exclude_agent and r.get("agent") == args.exclude_agent
             else others).append(r)
        for label, group in ("", others), ("-directo-opus", own):
            if not group:
                continue
            specs_text = read_specs(sfcrew, group)
            diff_body, diff_source, warnings = diff_for_batch(repo, branch, group, specs_text)
            payload = build_payload(group, branch, specs_text, diff_body, diff_source, warnings)
            name = f"PAYLOAD-{branch}{label}-{key}.md"
            path = os.path.join(out_dir, name)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(f"<!-- lote {key} · generado {ts} -->\n" + payload)
            print(f"[{branch}{label}] {len(group)} tarea(s), lote {key} → {path}"
                  f"  (~{len(payload)//4:,} tokens)")
            if label:
                print("   ↳ trabajo del pre-revisor: solo lo revisa Opus.")
            if args.reviewer == "opus" and not label:
                print(f"   Revisar:  claude -p \"$(cat '{path}')\"")
            elif args.reviewer == "glm" and not label:
                print(f"   Pre-revisar:  claude-zai -p \"$(cat '{path}')\"")
    if not args.if_needed:
        print("\nv0 modo reporte: este script no escribe estados.")


if __name__ == "__main__":
    main()
