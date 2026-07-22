# Quickstart — SFCrew 3.0

## Prerequisitos

- [Claude Code](https://claude.ai/code) instalado (`npm install -g @anthropic-ai/claude-code`)
- Node 18+ y `sf` CLI autenticado (`sf org list`)
- Notion MCP configurado en Claude Code
- Python ≥ 3.8 (para los scripts)

## 1. Instalar los skills

Copiar las carpetas de `skills/` a tu directorio de skills de Claude Code:

```bash
# macOS/Linux
cp -r skills/* ~/.claude/skills/

# Windows (PowerShell)
Copy-Item -Recurse skills/* $env:USERPROFILE\.claude\skills\
```

## 2. Configurar los alias de runners (PowerShell)

Agregar a tu `$PROFILE` de PowerShell:

```powershell
# Cargar API keys desde archivo (no commitear)
$providersEnv = "$env:USERPROFILE\.claude\providers.env"
if (Test-Path $providersEnv) {
    Get-Content $providersEnv | ForEach-Object {
        if ($_ -match '^([^#][^=]*)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
        }
    }
}

# Claude Code (Architect)
function claude-anthropic { claude @args }

# DeepSeek v3 — runner principal
function claude-deepseek {
    $env:ANTHROPIC_BASE_URL = "https://api.deepseek.com/anthropic"
    $env:ANTHROPIC_AUTH_TOKEN = $env:DEEPSEEK_API_KEY
    $env:ANTHROPIC_MODEL = "deepseek-chat"
    $env:ANTHROPIC_DEFAULT_SONNET_MODEL = "deepseek-chat"
    $env:ANTHROPIC_DEFAULT_HAIKU_MODEL = "deepseek-chat"
    claude @args
}

# GLM (ZhipuAI) — runner secundario y pre-revisor
function claude-zai {
    $env:ANTHROPIC_BASE_URL = "https://api.z.ai/api/anthropic"
    $env:ANTHROPIC_AUTH_TOKEN = $env:ZAI_API_KEY
    $env:API_TIMEOUT_MS = "3000000"
    claude @args
}
```

Crear `~/.claude/providers.env` (no commitear):
```
DEEPSEEK_API_KEY=sk-...
ZAI_API_KEY=...
```

## 3. Inicializar un proyecto

Desde la raíz de tu proyecto SFDX:

```
crew init
```

El skill pedirá:
- URL de la base Notion del proyecto
- Alias del org en SF CLI
- Prefijo del proyecto (`PRY_`, `MDX_`, etc.)

Genera `{proyecto}/.sfcrew/config.json`, actualiza la base Notion con las propiedades SFCrew y crea `notion_map.csv`.

## 4. Migrar desde v1 (si ya tienes un tasks.csv)

```bash
python ~/.claude/skills/crew/scripts/migrate_tasks_csv_v2.py .sfcrew/tasks.csv --map .sfcrew/notion_map.csv --dry-run
# Revisar el plan, luego:
python ~/.claude/skills/crew/scripts/migrate_tasks_csv_v2.py .sfcrew/tasks.csv --map .sfcrew/notion_map.csv
```

## 5. Operación diaria

```
crew status          # pulso: conteos, cola de aprobación, excepciones
crew plan HU-XXX    # genera tareas desde una HU y asigna runners
crew tick            # un ciclo completo: runners → review → pre-revisión → dashboard
crew exceptions     # solo lo que necesita atención (blocked, returned, conflictos)
crew approve        # integra el lote revisado y aprobado por Opus
crew sync           # sincroniza Notion ⇄ CSV manualmente
crew dashboard      # regenera el tablero HTML local
crew console        # servidor local en http://localhost:8787 (solo lectura)
```

## 6. Ciclo tick detallado

```powershell
# Solo plan (sin ejecutar runners)
powershell -File ~/.claude/skills/crew/scripts/tick.ps1 -Sfcrew ".sfcrew"

# Ejecutar runners headless tier=auto
powershell -File ~/.claude/skills/crew/scripts/tick.ps1 -Sfcrew ".sfcrew" -Execute

# Ejecutar + pre-revisión GLM
powershell -File ~/.claude/skills/crew/scripts/tick.ps1 -Sfcrew ".sfcrew" -Execute -PreReview
```

El tick genera los artefactos de revisión en `.sfcrew/reviews/`. La revisión final Opus es manual por ahora: leer PAYLOAD + PREREVIEW en una sesión Architect y aplicar `APROBADA` / `returned` / `blocked` en el CSV.

## 7. Consola local

```bash
python ~/.claude/skills/crew/scripts/console.py
# Abrir http://localhost:8787
```

Vistas disponibles: `/` (excepciones + cola de aprobación), `/board` (kanban por estado), `/task/TASK-NNNN` (detalle con el .md renderizado). Solo lectura — las acciones siguen siendo `crew approve` / `crew dispatch`.

## Estructura del worktree de un proyecto

```
{proyecto}/
├── .sfcrew/
│   ├── config.json
│   ├── tasks.csv          ← esquema v2, separador ;
│   ├── tasks/
│   │   └── TASK-NNNN.md
│   ├── notion_map.csv
│   ├── sync_state.json
│   ├── reviews/           ← payloads de revisión generados por review.py
│   └── archive/
├── force-app/
└── ...

{proyecto}_worktrees/
├── ExeClaude/
├── ExeDeepSeek/
└── ExeGLM/
```

## Schema tasks.csv v2 (referencia)

```
id;status;project;org;object;task_type;depends_on;agent;worktree;prompt;
result;created;started;completed;notion_page_id;hu_code;req_origin;
commit;deploy_ref;sync_state;headless_tier
```

`headless_tier`: `auto` (dispatcher lanza sin intervención), `manual` (Joan lanza), `interactive` (requiere sesión interactiva).
