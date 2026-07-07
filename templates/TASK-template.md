# TASK-NNNN — <Título descriptivo>

## Origen
- **HU/ADJ**: <código> · **REQ**: <REQ-XXX> · **Notion**: <page_id 32 hex>

## Objetivo
<Una oración que describe qué se quiere lograr.>

## Metadata a crear/modificar
- **Objeto**: `<SObjectName>`
- **Componente**: `<PREFIJO_NombreComponente__c>`
- **Tipo**: <field / gvs / layout / flow / apex / ...>
- **Required**: `false` (siempre; obligatoriedad vía Validation Rule)

## FLS — Perfiles (si aplica)
| Perfil | Editable | Readable |
|---|---|---|
| Admin | true | true |
| <Perfil de negocio> | true | true |

## Layout (si aplica)
- **Layout**: `<ObjectName>-<Layout Name>`
- **Sección**: `<Nombre de sección>`

## Orden de deploy
1. GVS (si aplica — tarea separada de la que esta depende)
2. Campos
3. Perfiles (retrieve fresco antes de editar FLS)
4. Layouts

## Convenciones del proyecto
- Prefijo `<PREFIJO>_` en todos los nombres de API
- `required=false` en el XML del campo
- `<fieldPermissions>` en bloque contiguo, antes de `<layoutAssignments>`
- Retrieve fresco de cada perfil antes de modificarlo

## Al completar (Runner)
- Dry-run limpio → `status=ready_to_merge`, `result`, `commit`, `completed`
- Entrada borrador en `referencias/BITACORA.md` de la rama
