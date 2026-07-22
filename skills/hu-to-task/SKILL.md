---
name: hu-to-task
description: Convierte HU/ADJ aprobadas de Notion en tareas SFCrew (TASK-NNNN.md + filas CSV v2) automáticamente, aplicando convenciones StudioDX. Reemplaza la transcripción manual del Architect. Usar cuando el usuario diga "crew plan <HU|épica>", "planifica esta HU", "convierte estas historias en tareas", "cierra la demo y encola el feedback" (crew close-demo), o cuando notion-sync reporte tarjetas nuevas sin tarea.
---

# hu-to-task — Autogeneración de tareas desde HU/ADJ (SF Crew 3.0)

Multi-proyecto: opera sobre el proyecto activo vía `{proyecto}/.sfcrew/config.json`.

## Entrada

Una de: código (`HU-M31`, `ADJ-15`), URL/id de tarjeta Notion, una épica
(`ÉPICA 16` → todas sus HU sin tarea), o modo `close-demo` (tarjetas ADJ
creadas desde la última demo sin `SFCrew Task ID`).

## Procedimiento

1. **Leer la tarjeta** (`notion-fetch`): título, descripción, criterios de aceptación, `Priority`, `Estimates`, épica padre.
2. **Descomponer en tareas técnicas** (reglas StudioDX):
   - GVS nuevo → tarea propia (`task_type=gvs`); campos que lo referencian con `depends_on` al GVS.
   - Campos + FLS + layout del mismo objeto → una tarea (`field`); objetos distintos → tareas separadas.
   - Flow/VR/Apex → tarea propia, dependiente de los campos que use.
   - `required=false` siempre.
3. **Generar artefactos** por tarea:
   - `.sfcrew/tasks/TASK-NNNN.md` con la plantilla del protocolo v3 (CA de la HU copiados como criterios de verificación; espacio reservado para `## Revisión N — ajustes solicitados`).
   - Fila CSV v2: `prompt` = ruta al `.md`, `hu_code`, `req_origin`, `notion_page_id`, `status` según política de autonomía, `agent` vacío. Escritura atómica.
4. **Enlace inverso:** actualizar `SFCrew Task ID` en la tarjeta Notion.
5. **Actualizar** `.sfcrew/notion_map.csv` si el código no estaba.

## Política de autonomía

| Caso | Acción |
|---|---|
| `task_type` mecánico (`field, gvs, fls, layout, validation_rule, related_list, listview, report`) **y** `Estimates` ≤ 3 | **Auto-encolar** como `pending` |
| `flow, apex, approval_process, integration, security, profiles, price_book` o `Estimates` ≥ 5 | **Borrador**: mostrar a Joan antes de escribir la fila CSV |
| Ambigüedad (CA contradictorios, objeto no identificable) | **No inventar**: listar preguntas y parar |

## Salida

N tareas creadas (ids + tipos + dependencias), M en borrador, K preguntas abiertas.
