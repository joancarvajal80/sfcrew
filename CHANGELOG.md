# CHANGELOG — SFCrew

## v3.0 (2026-07-20)

### Nuevos scripts
- `crew/scripts/review.py` — Ensamblador de payloads de revisión. Diff anclado a columna `commit` del CSV (idempotente por lote). `--exclude-agent` para autoexclusión GLM. Lock file para ejecuciones concurrentes.
- `crew/scripts/launcher.py` — Lee el CSV, filtra tareas `pending` con `headless_tier=auto`, genera y lanza invocaciones por runner. `--execute` para correr; sin flag, solo imprime el plan.
- `crew/scripts/tick.ps1` — Ciclo completo ASCII-only PS5.1: launcher → review → pre-revisión GLM opcional → dashboard. Exporta `SFCREW_TICK=1` para el Stop hook.
- `crew/scripts/console.py` — Servidor local solo-lectura stdlib (puerto 8787). Vistas: `/`, `/board`, `/task/TASK-NNNN`. Multi-proyecto sin dependencias externas.

### Skills actualizados
- **`crew`** — Router v3: subcomandos `review`, `tick`, `console` agregados; documentación de `headless_tier`.
- **`sfcrew-protocol`** — Protocolo v3: roster fijado por benchmark (claude+deepseek principal, glm secundario); estado `returned` (solo Opus escribe); Opus gate obligatorio antes de `approve`.
- **`notion-sync`** — Estado `returned` mapeado a `#d97706`; sync nunca sobreescribe `returned`.
- **`integrator`** — Precondición: solo tareas con revisión Opus aprobada entran al lote.
- **`hu-to-task`** — Plantilla v3 con sección `## Revisión N — ajustes solicitados` para ciclos de `returned`.
- **`dispatcher`** — Roster v3; respeta `headless_tier` para generar el script; GLM nunca revisa su propia rama.
- **`uat-generator`** — Label SFCrew 3.0.
- **`adoption-tracker`** — Label SFCrew 3.0; Definition of Adopted explícita.

### Estado `returned` (nuevo)
Cuando Opus detecta un defecto recuperable, marca la tarea `returned` con instrucciones. El runner la recoge en el siguiente tick. Solo Opus escribe este estado.

---

## v2.0 (2026-07-05)

### Skills nuevos
- `notion-sync` — Motor bidireccional Notion ⇄ CSV con subcomandos `stats`, `plan`, `apply-csv`, `commit-state`.
- `integrator` — Merge train + aprobación en lote.
- `hu-to-task` — Generación de tareas técnicas desde HU/ADJ de Notion.
- `dispatcher` — Ruteo push por tipo y carga; genera script headless.
- `uat-generator` — Manual UAT desde Criterios de Aceptación.
- `adoption-tracker` — Métricas de adopción vía SOQL.
- `crew` — Consola del Architect (router de intenciones).

### Scripts nuevos
- `crew/scripts/dashboard.py` — Tablero HTML estático con filtros por estado y KPIs.
- `crew/scripts/migrate_tasks_csv_v2.py` — Migración tasks.csv v1 → v2 (idempotente, con backup).
- `notion-sync/scripts/sync_csv.py` — Helper determinista del motor de sync.

### Schema tasks.csv v2
6 columnas nuevas sobre v1: `notion_page_id`, `hu_code`, `req_origin`, `commit`, `deploy_ref`, `sync_state`.

---

## v1.0 (2026-07-07)

Publicación inicial en GitHub. Skills: `sfcrew-protocol`, `sf-campos`, `sf-objeto-custom`, `sf-sync`, `sf-deploy`, `sf-doc-metadata`, `sf-experience-cloud`, `salesforce-dev`, `business-analyst`, `meeting-processor`, `brd-generator`, `user-stories-writer`, `notion-project-builder`, `data-analysis`.
