---
name: notion-sync
description: Motor de sincronización bidireccional Notion ⇄ .sfcrew (SF Crew 3.0). Mantiene la base de tareas de Notion y el tasks.csv del proyecto consistentes sin transcripción manual — write-back de estados (incluye `returned`), Completed on, Runner, Exec Result y Deploy Commit. Usar cuando el usuario diga "sincroniza", "crew sync", "actualiza Notion con lo ejecutado", o automáticamente al inicio de "crew approve" y "crew status".
---

# notion-sync — Motor de sync SFCrew 3.0

Elimina la transcripción manual entre Notion (fuente de verdad de negocio/PM) y
`.sfcrew/tasks.csv` v2 (fuente de verdad de ejecución). El helper
`scripts/sync_csv.py` hace el trabajo determinista (hashes, deltas, plan);
Claude ejecuta las lecturas/escrituras Notion vía MCP siguiendo ese plan.

## Prerrequisitos

- CSV en esquema **v2** (20 columnas, incluye `notion_page_id` y `sync_state`).
  Si está en v1: correr `~/.claude/skills/crew/scripts/migrate_tasks_csv_v2.py`
  primero (o `crew init`, que hace el onboarding completo de un proyecto).
- `{proyecto}/.sfcrew/config.json` con el data source de Notion.
- Conector Notion MCP activo (`notion-query-data-sources`, `notion-update-page`).

## Dirección de verdad por campo

| Campo | Dueño | Dirección |
|---|---|---|
| `status` canónico, `result`, `commit`, `deploy_ref`, `started/completed` | `.sfcrew` | CSV → Notion |
| Notion `Status`, `Completed on`, `SFCrew Task ID`, `Runner`, `Exec Result`, `Deploy Commit` | derivados de `.sfcrew` | CSV → Notion |
| Prioridad, épica, título, descripción, `Assignee` humano | Notion | Notion → CSV (informativo) |
| `UAT Status`, `Adoption` | Notion (QA/cliente) | Notion → CSV (informativo) |

**Conflicto** = ambos lados cambiaron desde el último sync. Política: el dueño gana;
el cambio ajeno se registra en `.sfcrew/sync_conflicts.md`. Nunca se resuelve en silencio.

## Mapa de estados

| Canónico `.sfcrew` | Alias legacy v1 | Notion `Status` | Extra |
|---|---|---|---|
| `pending` | — | `No Comenzado` | |
| `assigned` / `in_progress` | — | `En Progreso SFCrew` | |
| `ready_to_merge` | `completed`, `dry_run_ok` | `QA` | precondición: dry-run OK en `result` |
| `returned` | `de_vuelta` | `En Progreso SFCrew` | color #d97706; el sync NO escribe este estado — solo Opus vía CSV |
| `qa` | — | `QA` | |
| `deployed` | — | `Hecho` | + `Completed on` = fecha real |
| `blocked` | `failed` | `Bloqueado` | error en `result` |
| `partial` | — | `En Progreso` | |
| `tech-debt` | — | `En Progreso` | |

## Procedimiento

Rutas: `CSV = {proyecto}/.sfcrew/tasks.csv`, `STATE = {proyecto}/.sfcrew/sync_state.json`,
`SNAP = {proyecto}/.sfcrew/.notion_snapshot.json`, helper en `~/.claude/skills/notion-sync/scripts/sync_csv.py`.

1. **Snapshot Notion.** Consultar el data source (SQL vía MCP):
   ```sql
   SELECT url, Status, "date:Completed on:start" as completed_on,
          "SFCrew Task ID" as sfcrew_task_id, Runner as runner,
          "Exec Result" as exec_result, "Deploy Commit" as deploy_commit
   FROM "collection://<uuid>"
   ```
   Escribir `SNAP` como array JSON con `page_id` = últimos 32 hex del `url`.
2. **Plan.** `python <helper> plan CSV --notion SNAP --state STATE > {proyecto}/.sfcrew/.sync_plan.json`
3. **Modo report (default):** mostrar resumen del plan y **parar**.
4. **Modo apply:**
   a. `notion-update-page` por cada acción con `notion_updates` no vacío.
   b. `python <helper> apply-csv CSV --plan .sync_plan.json`.
   c. `python <helper> commit-state --plan .sync_plan.json --state STATE`.
5. **Conflictos:** agregar entrada a `.sfcrew/sync_conflicts.md` y avisar a Joan.
6. **Resumen final:** N tarjetas actualizadas, M conflictos, tareas sin enlace Notion.

## Garantías

- **Idempotente:** segunda corrida consecutiva = plan vacío = cero escrituras.
- **Atómico lado archivo:** CSV y `sync_state.json` se escriben vía temp+rename.
- **Único escritor hacia Notion:** solo este skill escribe propiedades SFCrew.
- **Tarjetas nuevas en Notion** (ADJ de demos): las reporta como candidatas; `hu-to-task` las convierte.
