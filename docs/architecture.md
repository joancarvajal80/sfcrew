# Arquitectura SFCrew 2.0

## Capas del sistema

```
┌─────────────────────────────────────────────────────────┐
│  NOTION  (fuente de verdad de negocio/PM)               │
│  HUs, estados, épicas, criterios de aceptación          │
└────────────────────┬────────────────────────────────────┘
                     │ notion-sync (bidireccional)
┌────────────────────▼────────────────────────────────────┐
│  tasks.csv v2  (fuente de verdad de ejecución)          │
│  20 columnas · state machine canónica · separador ;     │
└──────┬────────────┬────────────────────────────┬────────┘
       │            │                            │
  dispatcher   integrator                   notion-sync
       │            │                            │
┌──────▼──┐  ┌──────▼──────┐          ┌─────────▼────────┐
│ Runners │  │ main branch │          │ Write-back Notion│
│headless │  │ + deploy org│          │ Status/Completed │
└─────────┘  └─────────────┘          └──────────────────┘
```

## Componentes

### Architect (Claude Code)
Opera en la rama `main`. Planifica, coordina, aprueba. No ejecuta metadata work directamente.

### Runners headless
Ejecutados vía `claude-deepseek -p`, `claude-zai -p` o `claude -p`, cada uno en su propio git worktree.

| Runner | Alias | Worktree | Tipo de tarea |
|---|---|---|---|
| Claude | `claude` | `ExeClaude` | Compleja: flows, Apex, integraciones |
| DeepSeek | `deepseek` | `ExeDeepSeek` | Mecánica: campos, FLS, layouts |
| GLM/ZAI | `glm` | `ExeGLM` | Reserva y overflow |
| Grok | `grok` | `ExeGrok` | Reserva |
| Humano | `humano` | n/a | UAT, setup manual, training |

### Motor notion-sync
Python puro (`sync_csv.py`). Calcula deltas por hash, emite plan JSON, Claude ejecuta escrituras vía MCP. Idempotente: segunda corrida = plan vacío.

### Integrator
Merge train con compuerta. Presenta el lote `ready_to_merge` en una interacción → aprobación → merge `--no-ff` → dry-run scoped → deploy → push → write-back.

## State machine canónica

```
pending → assigned → in_progress → ready_to_merge → deployed → (UAT) → adopted
                          ↓              ↑
                       blocked ──────────┘
laterales: partial · qa · tech-debt
```

## Dirección de verdad por campo

| Campo | Dueño | Dirección |
|---|---|---|
| `status`, `result`, `commit`, `deploy_ref` | `.sfcrew` | CSV → Notion |
| Prioridad, título, descripción | Notion | Notion → CSV (informativo) |
| `UAT Status`, `Adoption` | Notion (QA/cliente) | Notion → CSV (informativo) |

## Guardarraíles duros

1. Nada llega a `main` ni al org sin aprobación explícita del consultor.
2. Producción = aprobación separada, nombrando el org explícitamente.
3. Dry-run scoped obligatorio post-merge y pre-deploy.
4. Los runners nunca: hacen deploy real, mergean a `main`, escriben en Notion.
5. El sync nunca adivina: conflictos → `sync_conflicts.md`, nunca resolución silenciosa.
