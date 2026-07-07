---
name: hu-to-task
description: Convierte HU/ADJ aprobadas de Notion en tareas SFCrew (TASK-NNNN.md + filas CSV v2) automáticamente, aplicando convenciones del proyecto. Reemplaza la transcripción manual del Architect. Usar cuando el usuario diga "crew plan <HU|épica>", "planifica esta HU", "convierte estas historias en tareas", "cierra la demo y encola el feedback" (crew close-demo), o cuando notion-sync reporte tarjetas nuevas sin tarea.
---

# hu-to-task — Autogeneración de tareas desde HU/ADJ (SF Crew 2.0)

Multi-proyecto: opera sobre el proyecto activo vía `{proyecto}/.sfcrew/config.json`
(prefijo, org, data source Notion).

## Entrada

Una de: código (`HU-M31`, `ADJ-15`), URL/id de tarjeta Notion, una épica
(`ÉPICA 16` → todas sus HU sin tarea), o modo `close-demo` (tarjetas ADJ
creadas desde la última demo sin `SFCrew Task ID`).

## Procedimiento

1. **Leer la tarjeta** (`notion-fetch`): título, descripción (Como/Quiero/Para),
   criterios de aceptación (CA-01…), `Priority`, `Estimates`, épica padre.
2. **Descomponer en tareas técnicas** aplicando las reglas del proyecto:
   - GVS nuevo → tarea propia (`task_type=gvs`); los campos que lo referencian
     con `depends_on` al GVS.
   - Campos + FLS + layout de un mismo objeto → una tarea (`field`) con orden
     de deploy interno; objetos distintos → tareas separadas.
   - Flow/VR/Apex → tarea propia, dependiente de los campos que use.
   - `required=false` siempre; obligatoriedad → Validation Rule.
3. **Generar artefactos** por tarea:
   - `.sfcrew/tasks/TASK-NNNN.md` con la plantilla del protocolo v2 (sección
     Origen con hu_code, REQ y notion_page_id; CA de la HU copiados como
     criterios de verificación del runner).
   - Fila CSV v2: `prompt` = ruta al `.md`, `hu_code`, `req_origin`,
     `notion_page_id` (32 hex), `status` según política de autonomía (abajo),
     `agent` vacío (lo pone el dispatcher). Escritura atómica; id = último+1.
4. **Enlace inverso:** actualizar `SFCrew Task ID` en la tarjeta Notion
   (`notion-update-page`) — única excepción a "solo el sync escribe", porque
   la relación debe existir antes del primer sync.
5. **Actualizar** `.sfcrew/notion_map.csv` si el código no estaba.

## Política de autonomía (D5)

| Caso | Acción |
|---|---|
| `task_type` mecánico (`field, gvs, fls, layout, validation_rule, related_list, listview, report`) **y** `Estimates` ≤ 3 | **Auto-encolar** como `pending` |
| `flow, apex, approval_process, integration, security, profiles, price_book` o `Estimates` ≥ 5 | Generar como **borrador**: mostrar al consultor el `.md` para revisión antes de escribir la fila CSV |
| Ambigüedad (CA contradictorios, objeto no identificable, decisión de negocio) | **No inventar**: listar las preguntas y parar |

## Salida al consultor

Resumen: N tareas creadas (ids + tipos + dependencias), M en borrador esperando
revisión, K preguntas abiertas. Sugerir `crew status` o correr el dispatcher.
