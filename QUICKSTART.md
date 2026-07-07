# Quickstart — SFCrew 2.0

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

# Claude Code normal (Anthropic)
function claude-anthropic { claude @args }

# DeepSeek V4 via API compatible con Anthropic
function claude-deepseek {
    $env:ANTHROPIC_BASE_URL = "https://api.deepseek.com/anthropic"
    $env:ANTHROPIC_AUTH_TOKEN = $env:DEEPSEEK_API_KEY
    $env:ANTHROPIC_MODEL = "deepseek-chat"
    $env:ANTHROPIC_DEFAULT_SONNET_MODEL = "deepseek-chat"
    $env:ANTHROPIC_DEFAULT_HAIKU_MODEL = "deepseek-chat"
    claude @args
}

# ZAI / GLM (Zhipu AI)
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

Genera `{proyecto}/.sfcrew/config.json` y actualiza la base Notion con las propiedades SFCrew.

## 4. Migrar desde v1 (si ya tienes un tasks.csv)

```bash
python ~/.claude/skills/crew/scripts/migrate_tasks_csv_v2.py .sfcrew/tasks.csv --map .sfcrew/notion_map.csv --dry-run
# Revisar el plan, luego:
python ~/.claude/skills/crew/scripts/migrate_tasks_csv_v2.py .sfcrew/tasks.csv --map .sfcrew/notion_map.csv
```

## 5. Operación diaria

```
crew status          # pulso del proyecto
crew plan HU-XXX    # planifica una HU y asigna runners
crew sync           # sincroniza Notion ⇄ CSV
crew approve        # integra el lote listo
crew exceptions     # solo lo que necesita atención
crew dashboard      # tablero HTML local
```

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
│   └── archive/
├── force-app/
└── ...

{proyecto}_worktrees/
├── ExeClaude/
├── ExeDeepSeek/
├── ExeGLM/
└── ExeGrok/
```
