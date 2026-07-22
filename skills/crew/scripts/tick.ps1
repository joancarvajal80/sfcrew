# tick.ps1 - Un tick = un ciclo del pipeline SF Crew 3.0.
#
# Cadena: launcher (runners headless tier auto) -> review (payload + guards)
#         -> pre-revision GLM headless -> SE DETIENE.
#
# La revision FINAL (Opus) es MANUAL: se hace por lotes por runner,
# en sesion Architect, leyendo PAYLOAD + PREREVIEW.
#
# NOTA: archivo ASCII-only (PowerShell 5.1 sin BOM lee ANSI).
#
# Uso:
#   .\tick.ps1 -Sfcrew "C:\...\Medirex_DevSB01\.sfcrew"      # modo PLAN
#   .\tick.ps1 -Sfcrew "..." -Execute                        # lanza runners
#   .\tick.ps1 -Sfcrew "..." -Execute -PreReview             # + pre-revision GLM
param(
    [Parameter(Mandatory = $true)][string]$Sfcrew,
    [switch]$Execute,
    [switch]$PreReview
)
$ErrorActionPreference = "Continue"
$scripts = $PSScriptRoot

$env:SFCREW_TICK = "1"
Write-Host "=== SFCrew tick $(Get-Date -Format 'yyyy-MM-dd HH:mm') - $Sfcrew ==="

if ($Execute) {
    python (Join-Path $scripts "launcher.py") $Sfcrew --tier auto --execute
} else {
    python (Join-Path $scripts "launcher.py") $Sfcrew --tier auto
}

python (Join-Path $scripts "review.py") $Sfcrew --reviewer glm --exclude-agent glm

if ($PreReview) {
    $revDir = Join-Path $Sfcrew "reviews"
    Get-ChildItem $revDir -Filter "PAYLOAD-*.md" |
        Where-Object { $_.Name -notmatch "directo-opus" } |
        ForEach-Object {
            $key = $_.BaseName -replace "^PAYLOAD-", ""
            $out = Join-Path $revDir ("PREREVIEW-" + $key + ".md")
            if (-not (Test-Path $out)) {
                Write-Host "Pre-revision GLM -> $out"
                bash -lc "claude-zai -p `"`$(cat '$($_.FullName)')`"" | Out-File $out -Encoding utf8
            }
        }
}

python (Join-Path $scripts "dashboard.py") $Sfcrew | Out-Null

Write-Host ""
Write-Host "Tick completo. Revision final (Opus) = MANUAL: abrir sesion Architect,"
Write-Host "revisar por lote los PAYLOAD/PREREVIEW en $Sfcrew\reviews\, aplicar"
Write-Host "APROBADA / returned / blocked en el CSV, y 'crew approve' cuando pase."
Remove-Item Env:\SFCREW_TICK -ErrorAction SilentlyContinue
