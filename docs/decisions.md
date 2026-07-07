# Decisiones de arquitectura — SFCrew 2.0

Registro de las decisiones tomadas durante el diseño del sistema.

## D1 — Roster de runners
**Decisión:** Roster inicial: `claude` + `deepseek`. GLM/Grok en reserva (reactivar en `config.json`).
**Razón:** Simplifica la operación diaria. Dos runners cubre el 95% de los casos: mecánico (DeepSeek, barato) y complejo (Claude).

## D2 — CSV vs SQLite
**Decisión:** CSV con separador `;`, escritura atómica.
**Razón:** Portable, legible por humanos, sin dependencias de runtime. Suficiente para volúmenes de 100-500 tareas por proyecto. SQLite es over-engineering para este caso de uso.

## D3 — State machine canónica única
**Decisión:** Una sola state machine: `pending → assigned → in_progress → ready_to_merge → deployed → adopted`. Alias legacy `completed/failed` entendidos pero no escritos en filas nuevas.
**Razón:** La v1 tenía estados informales que divergían entre proyectos.

## D4 — Sync por hash
**Decisión:** El sync calcula hashes de los campos relevantes. Segunda corrida = plan vacío = cero escrituras.
**Razón:** Idempotencia. El consultor puede correr `crew sync` sin miedo a duplicar escrituras.

## D5 — Política de autonomía en hu-to-task
**Decisión:** Tareas mecánicas (`Estimates ≤ 3`) → auto-encolar. Complejas → borrador para revisión.
**Razón:** Equilibrio entre autonomía y control. Las tareas de alto riesgo (flows, Apex) requieren revisión del Architect antes de entrar a la cola.

## D6 — Política push en dispatcher
**Decisión:** El Architect asigna. No hay pull self-service por los runners.
**Razón:** El Architect conoce el contexto del sprint, dependencias y carga. El pull self-service puede generar carreras en el CSV.

## D7 — Aprobación sandbox/prod
**Decisión:** Sandbox: aprobación en lote vía `crew approve`. Producción: aprobación explícita separada, nombrando el org.
**Razón:** Sandbox es el flujo normal; producción requiere intención explícita para evitar deploys accidentales.

## D8 — Architect operativo
**Decisión:** El Architect operativo es **Claude Code (Sonnet/Opus)**, no modelos más grandes ni costosos.
**Razón:** La mecánica pesada vive en helpers Python deterministas (`sync_csv.py`, `dashboard.py`). El Architect solo interpreta planes JSON acotados — no necesita un modelo enorme.

## D9 — Sistema multi-proyecto (no atado a un cliente)
**Decisión:** SFCrew 2.0 es genérico. Cada proyecto se parametriza por `{proyecto}/.sfcrew/config.json`. El onboarding es `crew init`.
**Razón:** La v1 tenía hardcoding de paths y referencias a proyectos específicos. Esto imposibilitaba reusar el sistema en nuevos clientes.

## D10 — Worktrees por runner
**Decisión:** Cada runner tiene su propio git worktree (`ExeDeepSeek/`, `ExeClaude/`, etc.).
**Razón:** Permite ejecución paralela sin conflictos de branch. El runner headless solo hace `Push-Location` al worktree y trabaja — sin `git checkout`.

## D11 — Tablero HTML estático
**Decisión:** `dashboard.py` genera HTML estático + `data.json`. Solo lectura del estado; no operación.
**Razón:** Un dashboard que también opera crea estados confusos. El HTML es compartible con el cliente sin exponer credenciales.
