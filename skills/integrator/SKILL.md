---
name: integrator
description: Merge train + compuerta de aprobación en lote de SF Crew 2.0. Convierte la integración (merge Exe* → main, deploy al org, push) de operación manual síncrona a cola de aprobación en lote. Usar cuando el usuario diga "crew approve", "aprueba lo que esté listo", "integra el lote", "mergea y despliega lo aprobado". Nada llega a main ni al org sin aprobación explícita.
---

# integrator — Merge train con compuerta de aprobación

Reúne las tareas `ready_to_merge` (alias legacy: `completed` con dry-run OK),
las presenta al consultor como **un lote aprobable en una sola interacción**, y tras
aprobación ejecuta merge → dry-run → deploy → push → write-back.

## Guardarraíles duros (no negociables)

1. **Nada llega a `main` ni al org sin aprobación explícita en esta sesión.**
   Aprobaciones pasadas no autorizan lotes futuros.
2. **Producción jamás entra al lote estándar.** Deploy a prod = aprobación
   separada, nombrando el org explícitamente. El flujo normal es sandbox.
3. Dry-run scoped obligatorio **post-merge y pre-deploy**. Si falla: revertir el
   merge (`git reset --hard <ref pre-merge>`), tarea → `blocked` con el error en
   `result`, `main` queda intacto, continuar con la siguiente rama del lote.
4. Backup del CSV antes de escribirlo (copia en `.sfcrew/archive/`).
5. Conflicto en `referencias/BITACORA.md` al mergear → `git checkout --ours` +
   redactar la entrada final desde el `result` del CSV (regla del protocolo).

## Procedimiento

### 1. Preparar
- Correr **notion-sync** (skill) en modo apply si hay deltas — el lote se arma
  sobre estado fresco.
- `python ~/.claude/skills/notion-sync/scripts/sync_csv.py stats {proyecto}/.sfcrew/tasks.csv`
  → `cola_aprobacion` = candidatas.
- Verificar por tarea: `depends_on` satisfecho (dependencia en `deployed`) y
  rama `worktree` con commits por delante de `main` (`git log main..Exe* --oneline`).
  Tareas cuyo trabajo ya está en `main` (merge previo) se marcan directo para
  write-back, sin re-merge.

### 2. Presentar el lote (UNA interacción)
Tabla: `TASK | HU | rama | commits | objeto | resumen result`. Preguntar al
consultor con AskUserQuestion: aprobar todo / excluir alguna / cancelar. Si pide excluir,
re-presentar el lote ajustado una sola vez.

### 3. Ejecutar (por rama, agrupando tareas de la misma rama)
```
ref_pre = git rev-parse main
git merge --no-ff <ExeRama> -m "merge(sfcrew): <ExeRama> → main — TASK-XXXX[, TASK-YYYY]"
# conflicto BITACORA → checkout --ours + redactar desde result
sf project deploy start --source-dir <paths tocados> --target-org <org> --dry-run
sf project deploy start --source-dir <paths tocados> --target-org <org>   # solo si dry-run OK
```
- Deploy scoped a los paths que tocó la rama (`git diff --name-only ref_pre..main`),
  nunca `force-app` completo.
- Registrar Deploy ID. Si el deploy real falla tras dry-run OK: analizar; si no es
  corregible en el momento → revert del merge + tarea `blocked`.

### 4. Write-back
- CSV: `status=deployed`, `deploy_ref=<merge commit>+<Deploy ID>`, `completed=<hoy>`
  si vacío. Escritura atómica; los perfiles del esquema v2 no se tocan a mano
  fuera de estas columnas.
- `referencias/BITACORA.md`: una entrada consolidada del lote.
- `git push origin main`.
- Correr **notion-sync** apply → tarjetas a `Hecho` + `Completed on`.

### 5. Reporte final al consultor
Lote: N tareas desplegadas (Deploy IDs), M excluidas, K a `blocked` (con error),
push hecho, Notion actualizado. Si K>0, dejarlas listadas como excepciones.

## Métricas del cuello de botella
Al terminar, registrar en `.sfcrew/integrator_log.md`: fecha, tamaño del lote,
tiempo desde el `ready_to_merge` más antiguo. Es la medida de si la compuerta
asíncrona está funcionando (tablero Fase 3 la lee).
