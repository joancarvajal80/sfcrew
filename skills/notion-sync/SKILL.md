---
name: notion-sync
description: Motor de sincronización bidireccional Notion ⇄ .sfcrew (SF Crew 2.0). Mantiene la base de tareas de Notion y el tasks.csv del proyecto consistentes sin transcripción manual — write-back de estados, Completed on, Runner, Exec Result y Deploy Commit. Usar cuando el usuario diga "sincroniza", "crew sync", "actualiza Notion con lo ejecutado", o automáticamente al inicio de "crew approve" y "crew status".
---

# notion-sync — Motor de sync SFCrew 2.0

Elimina la transcripción manual entre Notion (fuente de verdad de negocio/PM) y
`.sfcrew/tasks.csv` v2 (fuente de verdad de ejecución). El helper
`scripts/sync_csv.py` hace el trabajo determinista (hashes, deltas, plan);
Claude ejecuta las lecturas/escrituras Notion vía MCP siguiendo ese plan.

## Prerrequisitos

- CSV en esquema **v2** (20 columnas, incluye `notion_page_id` y `sync_state`).
  Si está en v1: correr `~/.claude/skills/crew/scripts/migrate_tasks_csv_v2.py`
  primero (o `crew init`, que hace el onboarding completo de un proyecto).
- `{proyecto}/.sfcrew/config.json` con el data source de Notion:
  ```json
  { "project": "<proyecto>", "org": "<org_alias>",
    "notion_database": "<NOTION_DATABASE_ID>", "notion_data_source": "collection://<NOTION_DATA_SOURCE_UUID>" }
  ```
- Conector Notion MCP activo (`notion-query-data-sources`, `notion-update-page`).

## Dirección de verdad por campo (normativo — el sync nunca adivina)

| Campo | Dueño | Dirección |
|---|---|---|
| `status` canónico, `result`, `commit`, `deploy_ref`, `started/completed` | `.sfcrew` | CSV → Notion |
| Notion `Status` (negocio, derivado del canónico), `Completed on`, `SFCrew Task ID`, `Runner`, `Exec Result`, `Deploy Commit` | derivados de `.sfcrew` | CSV → Notion |
| Prioridad, épica, título, descripción, `Assignee` humano | Notion | Notion → CSV (informativo, no persiste en CSV v2) |
| `UAT Status`, `Adoption` | Notion (QA/cliente) | Notion → CSV (informativo) |

**Conflicto** = ambos lados cambiaron desde el último sync (hashes en
`.sfcrew/sync_state.json`). Política: el dueño gana; el cambio ajeno se registra
en `.sfcrew/sync_conflicts.md` y la fila queda `sync_state=conflict`. Nunca se
resuelve en silencio.

## Mapa de estados (normativo — única fuente; protocolo v2 lo referencia)

| Canónico `.sfcrew` | Alias legacy v1 | Notion `Status` | Extra |
|---|---|---|---|
| `pending` | — | `No Comenzado` | |
| `assigned` / `in_progress` | — | `En Progreso SFCrew` | |
| `ready_to_merge` | `completed`, `dry_run_ok` | `QA` | precondición: dry-run OK en `result` |
| `qa` | — | `QA` | |
| `deployed` | — | `Hecho` | + `Completed on` = fecha real |
| `blocked` | `failed` | `Bloqueado` | error en `result` |
| `partial` | — | `En Progreso` | |
| `tech-debt` | — | `En Progreso` | + tag `Improvement` (manual por ahora) |

## Procedimiento

Rutas: `CSV = {proyecto}/.sfcrew/tasks.csv`, `STATE = {proyecto}/.sfcrew/sync_state.json`,
`SNAP = {proyecto}/.sfcrew/.notion_snapshot.json`, helper en `~/.claude/skills/notion-sync/scripts/sync_csv.py`.

1. **Snapshot Notion.** Consultar el data source (SQL vía MCP) las tarjetas enlazadas:
   ```sql
   SELECT url, Status, "date:Completed on:start" as completed_on,
          "SFCrew Task ID" as sfcrew_task_id, Runner as runner,
          "Exec Result" as exec_result, "Deploy Commit" as deploy_commit
   FROM "collection://<uuid>"
   ```
   Escribir `SNAP` como array JSON con `page_id` = últimos 32 hex del `url`
   (sin guiones), y las demás claves en minúscula como arriba.
2. **Plan.** `python <helper> plan CSV --notion SNAP --state STATE > {proyecto}/.sfcrew/.sync_plan.json`
   (en PowerShell usar `| Out-File -Encoding utf8`). Si el snapshot no cubre
   todas las tarjetas enlazadas (prueba puntual), agregar `--partial` para no
   generar falsos `tarjeta_no_encontrada`.

   **Tarjetas con varias TASK:** el plan agrega por tarjeta — su `Status` refleja
   la tarea **menos avanzada** (`blocked` domina) y `Completed on` solo se llena
   cuando **todas** las tareas del grupo están `deployed`. `SFCrew Task ID` lleva
   la lista separada por comas; `Exec Result` concatena los resultados.
3. **Modo report (default en las primeras corridas o si el consultor lo pide):** mostrar al
   consultor el resumen del plan (tareas a sincronizar, campos, conflictos) y **parar**.
   No escribir nada.
4. **Modo apply:**
   a. Por cada acción con `notion_updates` no vacío → `notion-update-page` sobre
      `page_id` con las propiedades indicadas. `Status` y `Completed on` tal cual;
      `SFCrew Task ID`, `Runner`, `Exec Result`, `Deploy Commit` como propiedades.
   b. `python <helper> apply-csv CSV --plan .sync_plan.json` (marca `sync_state`).
   c. `python <helper> commit-state --plan .sync_plan.json --state STATE`.
5. **Conflictos:** por cada conflicto del plan, agregar entrada a
   `.sfcrew/sync_conflicts.md` (fecha, task, qué dice cada lado, política) y
   avisar al consultor en el resumen final. No tocar la tarjeta ni la fila en conflicto.
6. **Resumen final al consultor:** N tarjetas actualizadas, campos propagados,
   M conflictos registrados, tareas sin enlace Notion (`stats` los lista).

## Garantías

- **Idempotente:** el plan se computa por diff de hashes; segunda corrida
  consecutiva = plan vacío = cero escrituras.
- **Atómico lado archivo:** CSV y `sync_state.json` se escriben vía temp+rename.
- **Único escritor hacia Notion:** solo este skill escribe propiedades SFCrew en
  Notion. Los runners nunca tocan Notion.
- **Tarjetas nuevas en Notion** (ADJ de demos): este skill NO las crea como
  tareas — las reporta como candidatas; `hu-to-task` (Fase 2) las convierte.
