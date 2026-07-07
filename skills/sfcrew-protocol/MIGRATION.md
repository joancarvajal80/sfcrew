# Migración SFCrew v1 → v2 (cualquier proyecto)

La hace `crew init` automáticamente. Manual, si se prefiere:

1. **Backup** — lo hace el script solo, pero verifica que exista
   `.sfcrew/archive/tasks_v1_backup_YYYYMMDD.csv` después.
2. **Mapa Notion** — generar `.sfcrew/notion_map.csv` (`code;page_id;title`):
   consultar los títulos de la base Notion del proyecto (tarjetas con código
   HU-/ADJ-/DT-/ÉPICA) vía `notion-query-data-sources` y extraer el código de
   cada título. Códigos duplicados en Notion: incluir solo la tarjeta correcta
   y anotar las demás en la columna `title`.
3. **Migrar:**
   ```
   python ~/.claude/skills/crew/scripts/migrate_tasks_csv_v2.py <ruta tasks.csv> --map <ruta notion_map.csv> [--dry-run]
   ```
   Agrega las 6 columnas nuevas, backfill de `hu_code` (regex sobre `prompt`) y
   `notion_page_id` (vía mapa), normaliza `agent=tbd` → vacío, elimina líneas
   vacías. Idempotente: si ya es v2, no hace nada.
4. **Propiedades Notion** — agregar a la base del proyecto si faltan
   (idempotente, verificar esquema antes): `SFCrew Task ID` (text), `Runner`
   (select), `Exec Result` (text), `Deploy Commit` (text), `UAT Status`
   (select: Pendiente/En UAT/Aprobado/Rechazado), `Adoption` (select: Sin
   medir/Bajo umbral/En adopción/Adoptado).
5. **config.json** — crear `{proyecto}/.sfcrew/config.json`:
   ```json
   { "project": "<carpeta SFDX>", "org": "<alias sf>", "org_type": "sandbox",
     "prefix": "<PFX_>", "notion_database": "<NOTION_DATABASE_ID>",
     "notion_data_source": "collection://<NOTION_DATA_SOURCE_UUID>",
     "runners_activos": ["claude", "deepseek"],
     "runners_reserva": ["glm", "grok"], "schema_version": 2 }
   ```
6. **Estados legacy** — no se reescriben en la migración; el motor entiende
   `completed/dry_run_ok/failed` como alias. Las filas nuevas usan solo la
   state machine v2.
7. **Primer sync** — correr `crew sync` en modo **report** y revisar el plan
   con el consultor antes del primer apply (puede reclasificar tarjetas en masa).
