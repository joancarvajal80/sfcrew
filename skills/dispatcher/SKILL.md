---
name: dispatcher
description: Ruteo y asignación de tareas SFCrew (SF Crew 2.0). Asigna cada tarea pending a un runner del roster activo según tipo y carga — elimina las tareas sin asignar (tbd). Usar cuando el usuario diga "rutea la cola", "asigna las tareas", "crew dispatch", o automáticamente después de hu-to-task y dentro de crew plan.
---

# dispatcher — Ruteo de la cola (SF Crew 2.0)

Multi-proyecto vía `{proyecto}/.sfcrew/config.json` (`runners_activos`).
Política **push** (D6): el Architect asigna; no hay pull self-service.

## Reglas de asignación

1. **Elegibilidad:** solo tareas `pending` con `agent` vacío cuyo `depends_on`
   esté vacío o en `deployed`. Dependencia no satisfecha → la tarea queda
   `pending` sin agente y se lista como "en espera de TASK-X" (nunca silencio).
2. **Capacidad:**
   - Mecánicas (`field, gvs, fls, layout, validation_rule, related_list,
     listview, report, record_type, soql`) → runner económico activo (`deepseek`).
   - Complejas (`flow, apex, approval_process, path_assistant, quick_action,
     integration, custom`) → `claude`.
   - `qa_manual, setup_manual, training, data` → `humano` (worktree `n/a`) — son
     tareas humanas, se listan en `crew exceptions` como pendientes del consultor.
3. **Balanceo:** si un runner acumula >5 tareas `assigned/in_progress` y otro
   activo está libre y es capaz, repartir. Nunca dos runners en la misma rama.
4. **Worktree:** `agent=X` → `worktree=ExeX` (exacto al nombre de la rama).
   Antes de asignar, verificar que la rama `Exe*` esté sincronizada con `main`
   (`git log Exe*..main --oneline` vacío); si no, sincronizarla primero
   (`git -C <worktree> merge main`) o anotarlo.
5. **Escritura:** `status=assigned`, `agent`, `worktree`. Atómica. No tocar
   filas `in_progress` de otros.

## Salida al consultor

Tabla: asignadas por runner, en-espera-de-dependencia (con el TASK que las
bloquea), humanas (humano). Criterio de éxito: **0 tareas elegibles sin agente.**

Además de la tabla, generar el script de ejecución (ver sección siguiente).

## Script de ejecución headless

Después de escribir el CSV, generar
`{proyecto}/.sfcrew/crew_dispatch_run.ps1` con una invocación por tarea
asignada a runner automatizable (`claude` o `deepseek`; omitir `humano`).

**Alias por runner:**

| Runner CSV | Alias PowerShell | Worktree path |
|---|---|---|
| `claude` | `claude-anthropic` | `{workspace}\{proyecto}_worktrees\ExeClaude` |
| `deepseek` | `claude-deepseek` | `{workspace}\{proyecto}_worktrees\ExeDeepSeek` |
| `glm` | `claude-zai` | `{workspace}\{proyecto}_worktrees\ExeGLM` |
| `grok` | `claude-grok` (si existe) | `{workspace}\{proyecto}_worktrees\ExeGrok` |

**Template del script:**

```powershell
# crew_dispatch_run.ps1 — generado por crew dispatch [{fecha}]
# Proyecto: {proyecto} | Org: {org}
# Revisar antes de ejecutar. Correr tareas en orden o en paralelo según dependencias.

$workspace = "<WORKSPACE_ROOT>"

# --- TASK-NNNN — <título> ---
Push-Location "$workspace\{proyecto}_worktrees\{worktree}"
{alias} -p (Get-Content ".sfcrew\tasks\TASK-NNNN.md" -Raw)
Pop-Location

# --- TASK-MMMM — <título> ---
Push-Location "$workspace\{proyecto}_worktrees\{worktree}"
{alias} -p (Get-Content ".sfcrew\tasks\TASK-MMMM.md" -Raw)
Pop-Location
```

**Reglas del script:**
- Tareas del mismo runner en el mismo worktree van secuenciales (mismo `Push-Location`).
- Tareas de runners distintos pueden ir en bloques paralelos con un comentario
  `# --- PARALELO: lanzar en terminales separadas ---`.
- Tareas con `depends_on` no satisfecho se comentan con `# BLOQUEADA: espera TASK-X`.
- Tareas `humano` se listan solo como comentario al final del script:
  `# MANUAL (humano): TASK-NNNN — <título>`.
- El script no se ejecuta automáticamente; el consultor lo revisa y lo corre.
