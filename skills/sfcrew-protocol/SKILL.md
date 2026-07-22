---
name: sfcrew-protocol
description: Protocolo de coordinación multi-agente SFCrew v3 (SF Crew 3.0) para cualquier proyecto Salesforce. Un Architect (Claude Code) planifica y aprueba en lote; Runners asíncronos ejecutan en worktrees; Opus revisa por lote antes del merge; el motor notion-sync mantiene Notion ⇄ CSV consistentes. Usar cuando el usuario diga "crea una tarea para SFCrew", "crea una tarea para [agente]", "planifica y manda a ejecutar", o cuando un Runner necesite las reglas de ejecución. Para operar el sistema usar la consola crew (crew status/sync/approve/review/exceptions).
---

# SFCrew — Protocolo v3 (SF Crew 3.0)

Sistema **estándar multi-proyecto**: cada proyecto SFDX se incorpora con
`crew init` y se parametriza por `{proyecto}/.sfcrew/config.json`. Nada del
protocolo es específico de un cliente.

Cambios v2 → v3: revisión Opus obligatoria por lote antes de merge (gate único,
skill `crew review`), estado `returned` (runner corrige por spec, máx 2 ciclos),
roster fijado por benchmark 2026-07-18/19, arquitectura de triggers idempotente
(`tick.ps1` + Stop hook), revisión anclada a `commit` del CSV (no a la rama).
Cambios v1 → v2 (histórico): esquema CSV de 20 columnas, state machine canónica,
sync Notion, integración por lote aprobado, dispatcher con política.
Migración de un CSV v1: ver `MIGRATION.md` en este skill.

## Roster

| Rol | Modelo | Estado | Alias CSV | Alias bash | Rama |
|---|---|---|---|---|---|
| **Architect + Revisor final** | Claude Code (Sonnet/Opus) | activo | `claude` | `claude` | — (opera `main`) |
| Runner complejo | Claude headless/worktree | activo | `claude` | `claude` | `ExeClaude` |
| Runner principal | DeepSeek V4 Pro (1M) | activo | `deepseek` | `claude-deepseek` | `ExeDeepSeek` |
| Pre-revisor + Runner | GLM via z.ai (1M) | activo | `glm` | `claude-zai` | `ExeGLM` |
| Runner nicho (reports/config/translations) | Grok (xAI) | reserva | `grok` | `grok` | `ExeGrok` |

Roles de revisión (benchmark 2026-07-18, `Medirex_DevSB01/.sfcrew/benchmark-revisor/VEREDICTO.md`):
GLM pre-revisa (0 falsos positivos; sus misses son la clase que el dry-run caza),
Opus revisa **siempre** y es el único gate. **El pre-revisor nunca revisa su
propia rama** — lo de `ExeGLM` lo pre-revisa otro runner u Opus directo.

**Invocación por alias bash:**
- `claude-deepseek` y `claude-zai` — funciones bash en `~/.bashrc` que llaman a `claude "$@"` con las variables de entorno del proveedor. Soportan `-p` para headless.
- `grok` — CLI propio en `~/.grok/bin`. Soporta `-p` para headless.
- Uso principal: **headless** (`<alias> -p "$(cat .sfcrew/tasks/TASK-NNNN.md)"`). También disponibles en terminal interactiva corriendo el alias sin flags.

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
id;status;project;org;object;task_type;depends_on;agent;worktree;prompt;result;created;started;completed;notion_page_id;hu_code;req_origin;commit;deploy_ref;sync_state;headless_tier
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
| `headless_tier` | Architect | `auto` / `manual` / `interactive` — controla cómo el dispatcher genera el script (ver abajo) |

### `headless_tier` — valores

| Valor | Significado | Comportamiento en el script |
|---|---|---|
| `auto` | Determinista, zero riesgo, sin ambigüedad | Bloque ejecutable, puede correr sin intervención de Joan |
| `manual` | Headless pero con riesgo o condición previa | Bloque comentado en el script; Joan descomenta y ejecuta explícitamente |
| `interactive` | Requiere interacción con la herramienta | No genera comando headless; aparece como instrucción con la herramienta a usar |

**Criterio de asignación:**
- `auto`: genera XML local, retrieve, dry-run, scripts Python, SOQL lectura, tests, docs, campos/objetos/FLS **nuevos** (sin colisión posible)
- `manual`: deploy real a sandbox de componentes existentes, profiles en objetos existentes, FlexiPages, PathAssistant, record types, cualquier tarea donde el agente necesita verificar condición previa
- `interactive`: flow (edición), approval process, validation rules con lógica compleja, integraciones, cualquier tarea donde el agente necesita confirmar decisiones de negocio en el momento

**Reglas de escritura (previenen corrupción del CSV):**
- Un runner solo modifica `status/result/started/completed/commit` de filas cuyo `agent` = su alias.
- `status=returned` lo escribe **solo el Revisor** (Opus); el runner solo puede
  sacarlo de ahí vía re-ejecución → `ready_to_merge` (o `blocked` si no puede).
- Toda reescritura del archivo es atómica (archivo temporal + rename).
- El Architect no modifica filas en `in_progress` de un runner.

## State machine canónica (única — el mapa a Notion vive en `notion-sync`)

```
pending → assigned → in_progress → ready_to_merge → deployed → (UAT) → adopted
                          ↓  ↑            ↓ ↑ (integrator, tras aprobación de Joan)
                          ↓  └─ returned ←┘ (revisión devuelve al runner)
                       blocked ───────────┘
laterales: partial · qa · tech-debt
```

- `ready_to_merge` requiere **dry-run limpio** documentado en `result`.
- `returned` lo escribe **solo el Revisor (Opus)**. El runner re-ejecuta → dry-run → commit → `ready_to_merge` → nueva revisión completa. Máximo 2 ciclos; al tercero pasa a `blocked`.
- `blocked` sustituye al viejo `failed`; el error va en `result`.
- Alias legacy v1: `completed` (=ready_to_merge), `dry_run_ok` (=ready_to_merge), `failed` (=blocked), `de_vuelta` (=returned).

## Flujo de una tarea

1. **Entrada:** HU/ADJ aprobada en Notion → `hu-to-task` genera `.md` + fila(s) `pending`.
2. **Ruteo:** `dispatcher` asigna `agent`+`worktree` → `assigned`.
3. **Ejecución (Runner):** `in_progress` → ejecutar → dry-run:
   - Limpio → commit → `ready_to_merge` + `result` + `commit` + `completed`.
   - Con errores → corregir, máx 2 intentos; si el tercero falla → `blocked`.
4. **Revisión:** GLM pre-revisa (nunca su propio trabajo); Opus revisa siempre (gate único). Resultado: Aprobada / Ajuste menor (`returned`) / Defecto de fondo (`blocked`).
5. **Integración:** `crew approve` → merge `--no-ff` → dry-run scoped → deploy → push → `deployed`.
6. **Write-back:** `notion-sync` → tarjeta a `Hecho` + `Completed on`.

## Reglas de eficiencia

1. Revisar por rama/lote, no por tarea.
2. Gates ordenados por costo: dry-run (0 tokens) → pre-revisor → Opus.
3. La spec es inversión: 1-2k tokens de spec precisa ahorran 100k+ de exploración.
4. Prompt estable primero (caching): bloque fijo al inicio, tarea concreta al final.
5. Todo quirk nuevo se documenta en BITACORA/pitfalls.
6. Fallo rápido: 2 intentos → `blocked`. 2 ciclos `returned` → `blocked`.

## Plantilla del `.md` de tarea

```markdown
# TASK-NNNN — <Título>

## Origen
- **HU/ADJ**: <código> · **REQ**: <REQ-XXX> · **Notion**: <page_id>

## Objetivo
<Una oración.>

## Ejecución
- **headless_tier**: `auto` | `manual` | `interactive`
- **Razón** (obligatorio si `interactive`): <por qué necesita interacción>
- **Herramienta** (obligatorio si `interactive`): `claude-deepseek` | `claude-zai` | `grok` | `claude`

## Metadata a crear/modificar
- **Objeto**: `<SObject>` · **Componente**: `<PFX_Nombre__c>` · **Tipo**: <tipo>
- **Required**: `false` (siempre; obligatoriedad vía Validation Rule)

## FLS — Perfiles (si aplica)
| Perfil | Editable | Readable |
|---|---|---|

## Orden de deploy
1. GVS (si aplica, tarea separada)
2. Campos → 3. Perfiles (retrieve fresco antes) → 4. Layouts

## Al completar (Runner)
- Dry-run limpio → `status=ready_to_merge`, `result`, `commit`, `completed`
- Entrada borrador en `referencias/BITACORA.md` de la rama
```

## Convenciones StudioDX

Prefijo del proyecto en toda la metadata custom · `required=false` siempre ·
GVS antes que campos · retrieve fresco de perfiles antes de editar FLS ·
`fieldPermissions` contiguos antes de `layoutAssignments`.

## Archivado

Cada 100 tareas `deployed`, mover filas a `.sfcrew/archive/batch_NNN.csv` y sus
`.md` a `.sfcrew/archive/tasks/`. El CSV activo conserva todo lo no-deployed.
