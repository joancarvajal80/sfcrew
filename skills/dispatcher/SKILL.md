---
name: dispatcher
description: Ruteo y asignación de tareas SFCrew (SF Crew 3.0). Asigna cada tarea pending a un runner del roster activo según tipo y carga — elimina las tareas sin asignar (tbd). DeepSeek=runner principal, GLM=pre-revisor+runner secundario (nunca revisa su propia rama), Grok=nicho, Opus=revisor final. Usar cuando el usuario diga "rutea la cola", "asigna las tareas", "crew dispatch", o automáticamente después de hu-to-task y dentro de crew plan.
---

# dispatcher — Ruteo de la cola (SF Crew 3.0)

Multi-proyecto vía `{proyecto}/.sfcrew/config.json` (`runners_activos`).
Política **push**: el Architect asigna; no hay pull self-service.

## Reglas de asignación

1. **Elegibilidad:** solo tareas `pending` con `agent` vacío cuyo `depends_on` esté vacío o en `deployed`.
2. **Capacidad (roster v3 — benchmark 2026-07-18/19):**
   - Mecánicas (`field, gvs, fls, layout, related_list, listview, report, record_type, soql`) → `deepseek` o `glm`.
   - Complejas (`flow, apex, path_assistant, quick_action, integration, custom`) → `claude`.
   - `validation_rule, approval_process` → `deepseek` si `headless_tier=auto`; → `joan` si `interactive`.
   - `qa_manual, setup_manual, training, data` → `joan` (worktree `n/a`).
   - **Restricción:** GLM nunca revisa tareas cuyo `agent=glm`.
3. **`headless_tier` obligatorio:** si el `.md` no lo declara, clasificar como `interactive` por defecto.
4. **Balanceo:** si un runner acumula >5 tareas y otro activo capaz está libre, repartir.
5. **Worktree:** `agent=X` → `worktree=ExeX`. Verificar rama sincronizada con `main` antes de asignar.
6. **Escritura:** `status=assigned`, `agent`, `worktree`, `headless_tier`. Atómica.

## Salida

Tabla: asignadas por runner, en-espera-de-dependencia, humanas. Criterio: **0 tareas elegibles sin agente.**

Generar `{proyecto}/.sfcrew/crew_dispatch_run.sh` en **3 bloques**:

```bash
#!/usr/bin/env bash
# crew_dispatch_run.sh — generado por crew dispatch [{fecha}]
# BLOQUE 1 (auto)        → correr directamente
# BLOQUE 2 (manual)      → revisar y descomentar antes de correr
# BLOQUE 3 (interactive) → abrir en la herramienta indicada, NO headless

source ~/.bashrc
WORKSPACE="<WORKSPACE_ROOT>"

# ══ BLOQUE 1 — AUTO ══
# [deepseek — ExeDeepSeek]
(cd "$WORKSPACE/{proyecto}_worktrees/ExeDeepSeek" && \
  claude-deepseek -p "$(cat .sfcrew/tasks/TASK-NNNN.md)")

# ══ BLOQUE 2 — MANUAL-HEADLESS ══
# TASK-RRRR — <título> [deepseek]
# Condición: <verificar X antes de correr>
# (cd "$WORKSPACE/{proyecto}_worktrees/ExeDeepSeek" && \
#   claude-deepseek -p "$(cat .sfcrew/tasks/TASK-RRRR.md)")

# ══ BLOQUE 3 — INTERACTIVO ══
# TASK-SSSS — <título>
#   Herramienta : claude-deepseek
#   Razón       : <por qué necesita interacción>
```

**Comandos headless por runner:**

| Runner CSV | Comando bash | Worktree |
|---|---|---|
| `claude` | `claude -p "$(cat .sfcrew/tasks/TASK-NNNN.md)"` | `ExeClaude` |
| `deepseek` | `claude-deepseek -p "$(cat .sfcrew/tasks/TASK-NNNN.md)"` | `ExeDeepSeek` |
| `glm` | `claude-zai -p "$(cat .sfcrew/tasks/TASK-NNNN.md)"` | `ExeGLM` |
| `grok` | `grok -p "$(cat .sfcrew/tasks/TASK-NNNN.md)"` | `ExeGrok` |
