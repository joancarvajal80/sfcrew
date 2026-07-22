---
name: crew
description: Consola del Architect SF Crew 3.0. Punto de entrada conversacional de Joan para operar el sistema por intención, no por mecánica. Subcomandos - crew status (pulso del proyecto), crew sync (sincronizar Notion⇄CSV), crew review (Opus revisa lote del runner), crew approve (aprobar e integrar el lote revisado), crew exceptions (solo lo que necesita atención). Usar cuando el usuario escriba "crew <subcomando>", "¿cómo va el proyecto?", "¿qué necesita mi atención?", "aprueba lo que esté listo". Principio de diseño - el 90% de los días Joan solo corre crew exceptions y crew approve.
---

# crew — Consola del Architect (SF Crew 3.0)

**El sistema es estándar y multi-proyecto.** Nada aquí es específico de un
cliente: cada proyecto SFDX se incorpora con `crew init` y toda la operación se
parametriza por su `{proyecto}/.sfcrew/config.json`. El Architect es **Claude
Code (Sonnet/Opus)** — la mecánica pesada vive en helpers deterministas
precisamente para no depender de contexto gigante.

Router de intenciones. Determinar el proyecto activo (carpeta actual con
`.sfcrew/`, o preguntar si hay ambigüedad) y despachar:

| Subcomando | Acción |
|---|---|
| `init` | **Onboarding de cualquier proyecto** (idempotente): 1) crear `{proyecto}/.sfcrew/` con `tasks/`, `archive/` y `tasks.csv` v2 (solo header si es nuevo); 2) pedir a Joan la URL de la base Notion del proyecto y resolver su data source (`notion-fetch`); 3) escribir `config.json` (project, org, prefix, notion_database, notion_data_source, runners_activos, schema_version:2); 4) agregar a la base Notion las 6 propiedades SFCrew si faltan (`notion-update-data-source` con ADD COLUMN — verificar el esquema antes para no duplicar): `SFCrew Task ID` RICH_TEXT, `Runner` SELECT, `Exec Result` RICH_TEXT, `Deploy Commit` RICH_TEXT, `UAT Status` SELECT(Pendiente/En UAT/Aprobado/Rechazado), `Adoption` SELECT(Sin medir/Bajo umbral/En adopción/Adoptado); 5) generar `.sfcrew/notion_map.csv` (`code;page_id;title`) consultando los títulos de tarjetas con código HU-/ADJ-/DT-/ÉPICA; 6) si existe un `tasks.csv` v1, migrarlo: `python ~/.claude/skills/crew/scripts/migrate_tasks_csv_v2.py <csv> --map <notion_map.csv>` (hace backup automático). |
| `status` | Sync silencioso si hay deltas triviales → `sync_csv.py stats` → presentar pulso: conteos por estado canónico, cola de aprobación, excepciones, pending sin agente, tareas sin enlace Notion. Conciso: una tabla + una línea de lectura. |
| `sync` | Cargar skill **notion-sync**. Primera corrida del día o si Joan lo pide: modo report; si Joan confirma (o ya corrió report antes en la sesión): apply. |
| `approve` | Cargar skill **integrator**. Presenta el lote `ready_to_merge` para UNA aprobación; luego merge train + deploy + push + write-back. |
| `exceptions` | `sync_csv.py stats` → mostrar SOLO: `blocked`, `partial`, `sync_state=conflict`, dry-run fallidos recientes, decisiones de negocio pendientes (tareas con "[Pendiente cliente]" en prompt). Si no hay nada: "Sin excepciones." y ya. |
| `plan <HU\|épica>` | Cargar skill **hu-to-task** (genera `.md` + filas CSV desde la tarjeta Notion) y luego **dispatcher** (asigna runner). |
| `dispatch` | Cargar skill **dispatcher** — rutea toda la cola `pending` sin agente. |
| `close-demo` | Cargar skill **hu-to-task** en modo close-demo: detecta tarjetas ADJ nuevas sin `SFCrew Task ID` y las encola. |
| `dashboard [--view cliente]` | `python ~/.claude/skills/crew/scripts/dashboard.py "{proyecto}/.sfcrew" [--view cliente]` → regenera el HTML estático y ofrece abrirlo (`Invoke-Item`). Regenerarlo también al final de `sync` y `approve`. |
| `console [--port 8787]` | `python ~/.claude/skills/crew/scripts/console.py` (correr en background) → servidor local solo-lectura en `http://localhost:8787` que lee `tasks.csv` en vivo. Vistas: `/` excepciones + cola de aprobación, `/board` kanban, `/task/TASK-NNNN` detalle con el `.md` renderizado. Multi-proyecto (descubre `{proyecto}/.sfcrew/` bajo el workspace; `--root` para otro workspace). Sin dependencias (stdlib). v0: no ejecuta acciones — aprobar/despachar sigue siendo `crew approve`/`crew dispatch`. |
| `review [--branch Exe*] [--reviewer glm\|opus]` | `python ~/.claude/skills/crew/scripts/review.py "{proyecto}/.sfcrew" [--branch <rama>] [--reviewer glm\|opus] [--exclude-agent glm] [--if-needed]` → ensambla el payload de revisión **por lote completo** (solo cuando el runner drenó su cola: sin filas `assigned`/`in_progress`/`returned` en esa rama) con specs + diff **anclado a los commits del CSV**, acotado a paths de la spec si el commit está contaminado. Idempotente: clave de lote = hash(tareas+commits) en el nombre del artefacto — triggers duplicados son inofensivos. `--if-needed` = modo guard para hooks (sale mudo si `SFCREW_TICK` está activo, si el lote está incompleto o si ya existe). Solo-lectura: sin worktree, sin rama, sin escribir estados. **La revisión final (Opus) es MANUAL por ahora**: en sesión Architect, por lote por runner, leyendo PAYLOAD+PREREVIEW → aplicar APROBADA / `returned` / `blocked` en el CSV. Correr siempre antes de `approve`. |
| `tick [-Execute] [-PreReview]` | `powershell -File ~/.claude/skills/crew/scripts/tick.ps1 -Sfcrew "{proyecto}/.sfcrew" [-Execute] [-PreReview]` → un tick = un ciclo: launcher (runners headless tier `auto`, vía `launcher.py`; sin `-Execute` solo imprime el plan) → review por lote → pre-revisión GLM headless (`-PreReview`) → dashboard → **se detiene antes de Opus** (revisión final manual por ahora). Exporta `SFCREW_TICK=1` para que el Stop hook (red de seguridad en `{proyecto}/.claude/settings.json`) no duplique la revisión. Programable en Task Scheduler cuando el proceso esté pulido. |
| `uat [--skeleton\|--final]` | Cargar skill **uat-generator**. |
| `adoption` | Cargar skill **adoption-tracker**. |

Helper: `python ~/.claude/skills/notion-sync/scripts/sync_csv.py stats "{proyecto}/.sfcrew/tasks.csv"`

## Comportamiento proactivo (push)

Al iniciar una sesión de trabajo dentro de un proyecto con `.sfcrew/` (primera
interacción sustantiva, no cada mensaje): correr `stats` en silencio. Si hay
excepciones o cola de aprobación no vacía, avisar en una línea al final de la
primera respuesta: p. ej. *"SFCrew: 3 tareas listas para `crew approve`, 1
bloqueada."* Si no hay nada, no mencionar nada.

## Reglas

- Salidas concisas y accionables — tabla corta + siguiente acción sugerida.
- Nunca ejecutar merge/deploy desde `status`/`exceptions`; eso solo pasa por
  `approve` con su compuerta.
- Si el CSV está en esquema v1, ofrecer la migración
  (`~/.claude/skills/crew/scripts/migrate_tasks_csv_v2.py`) antes de operar.
- Si el proyecto no tiene `.sfcrew/config.json`, ofrecer `crew init` antes de
  cualquier otro subcomando.
