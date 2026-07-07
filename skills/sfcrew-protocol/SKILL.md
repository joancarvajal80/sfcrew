---
name: sfcrew-protocol
description: Protocolo de coordinación multi-agente SFCrew v2 (SF Crew 2.0) para cualquier proyecto Salesforce. Un Architect (Claude Code) planifica y aprueba en lote; Runners asíncronos ejecutan en worktrees; el motor notion-sync mantiene Notion ⇄ CSV consistentes. Usar cuando el usuario diga "crea una tarea para SFCrew", "crea una tarea para [agente]", "planifica y manda a ejecutar", o cuando un Runner necesite las reglas de ejecución. Para operar el sistema usar la consola crew (crew status/sync/approve/exceptions).
---

# SFCrew — Protocolo v2 (SF Crew 2.0)

Sistema **estándar multi-proyecto**: cada proyecto SFDX se incorpora con
`crew init` y se parametriza por `{proyecto}/.sfcrew/config.json`. Nada del
protocolo es específico de un cliente.

Cambios v1 → v2: esquema CSV de 20 columnas, state machine canónica única,
sync automático con Notion (skill `notion-sync`), integración por **lote
aprobado** (skill `integrator`), roster consolidado, dispatcher con política.
Migración de un CSV v1: ver `MIGRATION.md` en este skill.

## Roster

| Rol | Modelo | Estado | Alias CSV | Rama |
|---|---|---|---|---|
| **Architect** | Claude Code (Sonnet/Opus) | activo | `claude` | — (opera `main`) |
| Runner complejo | Claude headless/worktree | activo | `claude` | `ExeClaude` |
| Runner mecánico | DeepSeek (CodeWhale) | activo | `deepseek` | `ExeDeepSeek` |
| Runner reserva | GLM (ZhipuAI) | reserva | `glm` | `ExeGLM` |
| Runner reserva | Grok (xAI) | reserva | `grok` | `ExeGrok` |

Reactivar un runner de reserva = marcarlo `activo` en `config.json`
(`runners_activos`) y sincronizar su rama con `main`. El protocolo es agnóstico
del modelo: el ejecutor solo necesita filesystem, `git`, `sf` CLI y seguir el
`.md` de la tarea.

## Arquitectura

```
{proyecto}/.sfcrew/
├── config.json          ← parámetros del proyecto (org, prefijo, data source Notion, roster)
├── tasks.csv            ← índice de ejecución, esquema v2, separador ;
├── tasks/TASK-NNNN.md   ← spec completa de cada tarea
├── notion_map.csv       ← mapa code→page_id (generado por crew init)
├── sync_state.json      ← hashes del motor de sync (no editar a mano)
├── sync_conflicts.md    ← conflictos registrados por el sync
└── archive/             ← tareas archivadas + backups
```

Notion es la fuente de verdad de **negocio/PM**; `tasks.csv` la de **ejecución**.
El skill `notion-sync` propaga entre ambos según dueño-por-campo; **nadie más
escribe propiedades SFCrew en Notion**.

## `tasks.csv` v2 — esquema (separador `;`)

```
id;status;project;org;object;task_type;depends_on;agent;worktree;prompt;result;created;started;completed;notion_page_id;hu_code;req_origin;commit;deploy_ref;sync_state
```

| Columna | Escribe | Notas |
|---|---|---|
| `id` | Architect | `TASK-NNNN` autoincremental |
| `status` | Ambos | Solo valores de la state machine (abajo) |
| `project`/`org`/`object`/`task_type`/`depends_on` | Architect | `task_type`: field/gvs/fls/object/layout/profile/record_type/validation_rule/approval_process/flow/apex/report/deploy/sync/soql/custom |
| `agent`/`worktree` | Dispatcher | Nunca `tbd`; vacío solo si ningún runner es elegible (razón en `result`) |
| `prompt` | Architect | **Ruta** al `.md`: `.sfcrew/tasks/TASK-NNNN.md` (sin prosa) |
| `result` | Runner | Resumen de ejecución o error |
| `created`/`started`/`completed` | Architect/Runner | ISO-8601 |
| `notion_page_id` | hu-to-task / crew init | 32 hex de la tarjeta origen |
| `hu_code` | Architect | `HU-M20`, `ADJ-09`, `DT-ACC-06`, `ÉPICA 15`… (múltiples: coma) |
| `req_origin` | Architect | REQ(s) del BRD |
| `commit` | Runner | Hash del commit en su rama `Exe*` |
| `deploy_ref` | Integrator | Merge commit + Deploy ID |
| `sync_state` | Sync | `ok` / `dirty` / `conflict` — solo lo escribe notion-sync |

**Reglas de escritura (previenen corrupción del CSV):**
- Un runner solo modifica `status/result/started/completed/commit` de filas cuyo `agent` = su alias.
- Toda reescritura del archivo es atómica (archivo temporal + rename).
- El Architect no modifica filas en `in_progress` de un runner.

## State machine canónica (única — el mapa a Notion vive en `notion-sync`)

```
pending → assigned → in_progress → ready_to_merge → deployed → (UAT) → adopted
                          ↓              ↑ (integrator, tras aprobación del consultor)
                       blocked ──────────┘
laterales: partial · qa · tech-debt
```

- `ready_to_merge` requiere **dry-run limpio** documentado en `result`.
- `blocked` sustituye al viejo `failed`; el error va en `result`.
- Alias legacy v1 que el motor todavía entiende pero **no se escriben en filas
  nuevas**: `completed` (=ready_to_merge), `dry_run_ok` (=ready_to_merge),
  `failed` (=blocked).

## Flujo de una tarea

1. **Entrada:** HU/ADJ aprobada en Notion → `hu-to-task` genera `.md` + fila(s)
   `pending` (o el Architect las crea a mano con la plantilla de abajo).
2. **Ruteo:** `dispatcher` asigna `agent`+`worktree` → `assigned`.
3. **Ejecución (Runner):** `in_progress` + `started` → ejecutar el `.md` →
   dry-run hasta limpio → commit en su rama → `ready_to_merge` + `result` +
   `commit` + `completed`. Entrada de borrador en `referencias/BITACORA.md` de su rama.
4. **Integración:** el consultor corre `crew approve` → `integrator` presenta el lote →
   merge `--no-ff` → dry-run scoped → deploy → push → `deployed` + `deploy_ref`.
5. **Write-back:** `notion-sync` deja la tarjeta en `Hecho` + `Completed on`.

**Los Runners nunca:** hacen deploy real, mergean a `main`, hacen retrieve por
iniciativa propia (pedirlo al Architect vía `result`), ni escriben en Notion.

**Dry-run:** libre para cualquier runner. Si la tarea toca perfiles, correr
antes `python scripts/fix_invalid_tabvisibilities.py` sobre los afectados.

**BITÁCORA:** en conflicto de merge, gana `main` (`git checkout --ours`) y el
Architect redacta la entrada final desde `result`.

## Plantilla del `.md` de tarea

```markdown
# TASK-NNNN — <Título>

## Origen
- **HU/ADJ**: <código> · **REQ**: <REQ-XXX> · **Notion**: <page_id>

## Objetivo
<Una oración.>

## Metadata a crear/modificar
- **Objeto**: `<SObject>` · **Componente**: `<PFX_Nombre__c>` · **Tipo**: <tipo>
- **Required**: `false` (siempre; obligatoriedad vía Validation Rule)

## FLS — Perfiles (si aplica)
| Perfil | Editable | Readable |
|---|---|---|

## Orden de deploy
1. GVS (si aplica, tarea separada de la que esta depende)
2. Campos → 3. Perfiles (retrieve fresco antes de editar) → 4. Layouts

## Al completar (Runner)
- Dry-run limpio → `status=ready_to_merge`, `result`, `commit`, `completed`
- Entrada borrador en `referencias/BITACORA.md` de la rama
```

## Convenciones generales

Prefijo del proyecto en toda la metadata custom · `required=false` siempre ·
GVS antes que campos · retrieve fresco de perfiles antes de editar FLS ·
`fieldPermissions` contiguos antes de `layoutAssignments`.

## Archivado

Cada 100 tareas `deployed`, mover filas a `.sfcrew/archive/batch_NNN.csv` y sus
`.md` a `.sfcrew/archive/tasks/`. El CSV activo conserva todo lo no-deployed.
