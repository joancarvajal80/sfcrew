# sf-doc-metadata — Documentación básica de metadata Salesforce

Genera un `.md` básico por componente (objeto, flow, permission set, etc.)
leyendo el **XML real** ya creado/desplegado — no la conversación — para
usarlo después como insumo de `tech-documentation` (manuales, handover,
release notes).

---

## Cuándo invocar

- "documenta lo que acabas de crear/modificar"
- "genera el .md de [Objeto/Flow/Componente]"
- "documenta la metadata de esta tarea"
- Como **paso final** de cualquier tarea de creación/modificación de metadata
  (`sf-campos`, `sf-objeto-custom`, `salesforce-dev`, tareas de runners SFCrew) —
  antes de cerrar la tarea o el checkpoint.

---

## Variables de entrada

| Variable | Descripción | Default |
|---|---|---|
| `PROYECTO` | Raíz del proyecto SFDX (carpeta con `sfdx-project.json`) | directorio actual |
| `COMPONENTES` | Lista de objetos/flows/etc. a documentar | auto-detectar vía `git status`/`git diff` |
| `DESTINO` | Carpeta de salida | `referencias/docs-metadata/` |

---

## Paso 1: Identificar el alcance

Si el usuario no especifica componentes, detectarlos a partir de los
archivos tocados en la tarea:

```bash
git status --porcelain force-app/main/default/
git diff --name-only HEAD~1 -- force-app/main/default/   # si ya hubo commit
```

Agrupar los paths por componente, por ejemplo:

- `objects/{PREFIJO}_Objeto__c/**` → objeto `{PREFIJO}_Objeto__c`
- `flows/{PREFIJO}_NombreFlow.flow-meta.xml` → flow `{PREFIJO}_NombreFlow`
- `profiles/*.profile-meta.xml` (solo `fieldPermissions` nuevos) → cambios de FLS de la tarea

Confirmar con el usuario la lista antes de generar (si hay ambigüedad).

---

## Paso 2: CustomObject (campos, record types, validation rules)

Usar el script `generar_doc_objeto.py` — lee `objects/<Objeto>/` completo
(`*.object-meta.xml`, `fields/*.field-meta.xml`, `recordTypes/*.recordType-meta.xml`,
`validationRules/*.validationRule-meta.xml`) y genera la tabla de campos +
record types + validation rules automáticamente:

```bash
python "<SKILLS_DIR>/sf-doc-metadata/scripts/generar_doc_objeto.py" \
  "<PROYECTO>" "<ObjectApiName>"
```

Salida: `<PROYECTO>/referencias/docs-metadata/<ObjectApiName>.md`

Repetir por cada objeto custom o estándar tocado (incluyendo objetos
estándar como `Account`, `Lead`, `Opportunity`, `Campaign`, `User` si se
agregaron campos `{PREFIJO}_*`).

Si el objeto ya tenía un `.md` previo (de una tarea anterior), el script lo
**sobreescribe** con el estado actual completo — esto es correcto, el `.md`
de `docs-metadata/` siempre refleja el estado actual del XML, no un diff
acumulado. El historial de decisiones vive en `BITACORA.md`.

---

## Paso 3: Otros tipos de metadata (manual, sin script)

Para componentes que no son CustomObject, leer el XML directamente y volcar
en un `.md` siguiendo estas plantillas mínimas. Mantenerlo **básico**: esto
es insumo, no el documento final.

### Flow (`flows/<Nombre>.flow-meta.xml`)

```markdown
# <Nombre del Flow>

**API Name:** <fullName interno o nombre de archivo>
**Tipo:** <processType> (Screen Flow / Autolaunched / Path Assistant...)
**Estado:** <status> (Active/Draft)
**Trigger / Punto de entrada:** <descripción del start o dónde se invoca>

## Propósito
<description del flow, en lenguaje de negocio>

## Pasos / elementos principales
- <Screen/Decision/Assignment/RecordCreate/Subflow ...>: <qué hace, en una línea>
- ...

## Variables de entrada/salida relevantes
- <nombre variable>: <tipo> — <para qué sirve>

## Subflows / dependencias
- <subflow o clase Apex invocada>
```

### PermissionSet / Profile (cambios de FLS de la tarea)

```markdown
# <Nombre Permission Set / Profile> — cambios de FLS

## Objeto: <Objeto>
| Campo | Readable | Editable |
|---|---|---|
| <Campo__c> | true/false | true/false |

## Permisos de objeto (si se modificaron)
- <Objeto>: create/read/edit/delete/viewAll/modifyAll
```

### GlobalValueSet

```markdown
# GVS: <Nombre>

**Descripción:** <description>

| Valor API | Label | Default |
|---|---|---|
| <fullName> | <label> | sí/no |

**Usado en:** <Objeto.Campo__c, Objeto2.Campo__c, ...>
```

### ApprovalProcess / PathAssistant

```markdown
# <Nombre>

**Objeto:** <objeto asociado>
**Tipo:** Approval Process / Path Assistant

## Pasos / etapas
1. <paso>: <criterio de entrada / campos clave de la etapa>
```

---

## Paso 4: Guardar y referenciar

1. Guardar cada `.md` en `<PROYECTO>/referencias/docs-metadata/<Nombre>.md`
   (un archivo por componente — objeto, flow, permission set, etc.).
2. Agregar **una línea** en `referencias/BITACORA.md` apuntando al archivo
   generado (no duplicar contenido):

```markdown
- Documentación generada: `referencias/docs-metadata/<Nombre>.md`
```

3. Hacer commit junto con el resto de la tarea:

```bash
git add referencias/docs-metadata/
```

---

## Paso 5: Confirmar al usuario

Listar los `.md` generados/actualizados (ruta + 1 línea de qué contienen).
No repetir el contenido completo en la respuesta — el usuario puede abrir
el archivo.

---

## Notas

- `docs-metadata/` es **insumo**, no el entregable final. Para manuales,
  release notes, guías de usuario o handover, usar el skill
  `tech-documentation` tomando estos `.md` como fuente.
- Mantener `{PREFIJO}_` tal como aparece en el XML — no traducir nombres API.
- Si un objeto/flow no tiene `description` en el XML, dejarlo vacío en el
  `.md` y sugerir al usuario completarlo en la org (mejora la metadata y la
  doc al mismo tiempo).
