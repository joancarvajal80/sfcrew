---
name: integrator
description: Merge train + compuerta de aprobación en lote de SF Crew 3.0. Solo entran al lote tareas con revisión Opus aprobada. Convierte la integración (merge Exe* → main, deploy al org, push) de operación manual síncrona a cola de aprobación en lote. Usar cuando el usuario diga "crew approve", "aprueba lo que esté listo", "integra el lote", "mergea y despliega lo aprobado". Nada llega a main ni al org sin aprobación explícita.
---

# integrator — Merge train con compuerta de aprobación (SF Crew 3.0)

Reúne las tareas `ready_to_merge` **con revisión Opus aprobada** (precondición
obligatoria en v3 — correr `crew review` antes de `crew approve`), las presenta
a Joan como **un lote aprobable en una sola interacción**, y tras aprobación
ejecutia merge → dry-run → deploy → push → write-back.

## Guardarraíles duros

1. **Nada llega a `main` ni al org sin aprobación explícita en esta sesión.**
2. **Producción jamás entra al lote estándar.** Deploy a prod = aprobación separada.
3. Dry-run scoped obligatorio **post-merge y pre-deploy**. Si falla: revertir el merge, tarea → `blocked`.
4. Backup del CSV antes de escribirlo.
5. Conflicto en `referencias/BITACORA.md` → `git checkout --ours` + redactar desde `result`.

## Procedimiento

### 1. Preparar
- Correr **notion-sync** en modo apply si hay deltas.
- `sync_csv.py stats` → `cola_aprobacion` = candidatas.
- Verificar `depends_on` satisfecho y rama con commits por delante de `main`.

### 2. Presentar el lote (UNA interacción)
Tabla: `TASK | HU | rama | commits | objeto | resumen result`. Aprobar todo / excluir / cancelar.

### 3. Ejecutar (por rama)
```
ref_pre = git rev-parse main
git merge --no-ff <ExeRama> -m "merge(sfcrew): <ExeRama> → main — TASK-XXXX[, TASK-YYYY]"
sf project deploy start --source-dir <paths tocados> --target-org <org> --dry-run
sf project deploy start --source-dir <paths tocados> --target-org <org>
```

### 4. Write-back
- CSV: `status=deployed`, `deploy_ref`, `completed`. Escritura atómica.
- `referencias/BITACORA.md`: entrada consolidada del lote.
- `git push origin main`.
- Correr **notion-sync** apply → tarjetas a `Hecho`.

### 5. Reporte final
N tareas desplegadas, M excluidas, K a `blocked`, push hecho, Notion actualizado.

## Métricas
Registrar en `.sfcrew/integrator_log.md`: fecha, tamaño del lote, tiempo desde el `ready_to_merge` más antiguo.
