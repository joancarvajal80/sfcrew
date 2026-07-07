# sf-campos — Skill de Claude Code para Salesforce

Automatiza la creación y despliegue de campos custom en Salesforce: genera XMLs, actualiza FLS en perfiles, actualiza layouts y hace deploy en orden correcto.

---

## Cuándo invocar

Usar este skill cuando el usuario diga:
- "crea los campos de [Objeto]"
- "despliega campos en [Objeto]"
- "agrega campos a [Objeto]"
- "genera los XMLs de campos"
- Cuando haya una lista de campos a crear para un objeto Salesforce

---

## Variables de entrada

| Variable | Descripción | Ejemplo |
|---|---|---|
| `OBJETO` | Nombre API del objeto Salesforce | `Account`, `Opportunity`, `{PREFIJO}_Objeto__c` |
| `PREFIJO` | Prefijo del proyecto | `PRY`, `ABC` |
| `ORG_ALIAS` | Alias del org en SF CLI | `proyecto-sb01`, `cliente-dev` |
| `CAMPOS` | Lista de campos con: nombre, tipo, label, descripción, help text, valores picklist si aplica | ver ejemplos abajo |
| `PERFILES` | Lista de perfiles que deben tener acceso | `Admin`, `Sales User` |
| `LAYOUT` | Nombre del layout a actualizar | `Account-Account Layout` |

---

## Flujo del skill (paso a paso)

### Paso 1: Verificar Global Value Sets

Antes de generar campos, identificar si algún campo usa una picklist que debe ser **compartida** entre múltiples objetos (ej: Tipo_Identificacion en Account y Contact, Especialidad_Medica en Lead y Account, Zona_Geografica en Account y Opportunity).

**Criterio:** si el mismo picklist se usa en 2+ objetos → Global Value Set. Si solo se usa en 1 objeto → picklist local.

Si hay GVS nuevos:

1. Crear archivo en `force-app/main/default/globalValueSets/{PREFIJO}_NombreGVS.globalValueSet-meta.xml`
2. Hacer deploy PRIMERO, en deploy separado antes de los campos:

```bash
sf project deploy start \
  --metadata "GlobalValueSet:{PREFIJO}_NombreGVS" \
  --target-org {ORG_ALIAS}
```

3. Verificar que el deploy fue exitoso antes de continuar.

**Formato XML de un Global Value Set:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<GlobalValueSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <customValue>
        <fullName>Valor_API</fullName>
        <default>true</default>
        <label>Label del valor</label>
    </customValue>
    <customValue>
        <fullName>Otro_Valor</fullName>
        <default>false</default>
        <label>Otro valor</label>
    </customValue>
    <description>Descripcion del GVS. Objetos donde se usa.</description>
    <masterLabel>{PREFIJO} Nombre GVS</masterLabel>
    <sorted>false</sorted>
</GlobalValueSet>
```

---

### Paso 2: Generar archivos de campos

**Path destino:** `force-app/main/default/objects/{OBJETO}/fields/`

Usar el script `crear_campos.py` ubicado en el mismo directorio del skill:

```bash
python "<SKILLS_DIR>/sf-campos/scripts/crear_campos.py"
```

O bien generar los archivos XML directamente siguiendo las reglas:

**Reglas criticas:**
- NUNCA usar `<required>true</required>` — siempre `<required>false</required>`. Para campos obligatorios, usar Validation Rule.
- Campos formula: `<type>Text</type>` o `<type>Currency</type>` segun retorno, con `<formulaTreatBlanksAs>BlankAsZero</formulaTreatBlanksAs>`.
- Siempre incluir `<description>` y `<inlineHelpText>`.
- External IDs: agregar `<externalId>true</externalId>`.
- Nombre de archivo: `{PREFIJO}_NombreCampo__c.field-meta.xml`

**Plantillas XML por tipo:**

**Text:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>{PREFIJO}_NombreCampo__c</fullName>
    <description>Descripcion del campo.</description>
    <inlineHelpText>Texto de ayuda para el usuario.</inlineHelpText>
    <label>Label del Campo</label>
    <length>255</length>
    <required>false</required>
    <type>Text</type>
</CustomField>
```

**Currency:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>{PREFIJO}_NombreCampo__c</fullName>
    <description>Descripcion del campo.</description>
    <inlineHelpText>Texto de ayuda para el usuario.</inlineHelpText>
    <label>Label del Campo</label>
    <precision>16</precision>
    <required>false</required>
    <scale>2</scale>
    <type>Currency</type>
</CustomField>
```

**Number:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>{PREFIJO}_NombreCampo__c</fullName>
    <description>Descripcion del campo.</description>
    <inlineHelpText>Texto de ayuda para el usuario.</inlineHelpText>
    <label>Label del Campo</label>
    <precision>18</precision>
    <required>false</required>
    <scale>0</scale>
    <type>Number</type>
</CustomField>
```

**Picklist local (un solo objeto):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>{PREFIJO}_NombreCampo__c</fullName>
    <description>Descripcion del campo.</description>
    <inlineHelpText>Texto de ayuda para el usuario.</inlineHelpText>
    <label>Label del Campo</label>
    <required>false</required>
    <type>Picklist</type>
    <valueSet>
        <restricted>true</restricted>
        <valueSetDefinition>
            <sorted>false</sorted>
            <value>
                <fullName>Valor_API_1</fullName>
                <default>true</default>
                <label>Label Valor 1</label>
            </value>
            <value>
                <fullName>Valor_API_2</fullName>
                <default>false</default>
                <label>Label Valor 2</label>
            </value>
        </valueSetDefinition>
    </valueSet>
</CustomField>
```

**Picklist global (referencia a GVS):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>{PREFIJO}_NombreCampo__c</fullName>
    <description>Descripcion del campo.</description>
    <inlineHelpText>Texto de ayuda para el usuario.</inlineHelpText>
    <label>Label del Campo</label>
    <required>false</required>
    <type>Picklist</type>
    <valueSet>
        <valueSetName>{PREFIJO}_NombreGVS</valueSetName>
    </valueSet>
</CustomField>
```

**Formula (Text):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>{PREFIJO}_NombreCampo__c</fullName>
    <description>Descripcion del campo.</description>
    <formula>CASE(TEXT(OtroCampo__c), "Valor", "Resultado", "Default")</formula>
    <inlineHelpText>Texto de ayuda para el usuario.</inlineHelpText>
    <label>Label del Campo</label>
    <required>false</required>
    <type>Text</type>
    <formulaTreatBlanksAs>BlankAsZero</formulaTreatBlanksAs>
</CustomField>
```

**Checkbox:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>{PREFIJO}_NombreCampo__c</fullName>
    <defaultValue>false</defaultValue>
    <description>Descripcion del campo.</description>
    <inlineHelpText>Texto de ayuda para el usuario.</inlineHelpText>
    <label>Label del Campo</label>
    <type>Checkbox</type>
</CustomField>
```

**Lookup:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>{PREFIJO}_NombreCampo__c</fullName>
    <description>Descripcion del campo.</description>
    <inlineHelpText>Texto de ayuda para el usuario.</inlineHelpText>
    <label>Label del Campo</label>
    <referenceTo>ObjetoDestino__c</referenceTo>
    <relationshipLabel>Label de la relacion</relationshipLabel>
    <relationshipName>NombreRelacion</relationshipName>
    <required>false</required>
    <type>Lookup</type>
</CustomField>
```

**TextArea (Long):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>{PREFIJO}_NombreCampo__c</fullName>
    <description>Descripcion del campo.</description>
    <inlineHelpText>Texto de ayuda para el usuario.</inlineHelpText>
    <label>Label del Campo</label>
    <length>32768</length>
    <type>LongTextArea</type>
    <visibleLines>4</visibleLines>
</CustomField>
```

**Text con ExternalId:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>{PREFIJO}_NombreCampo__c</fullName>
    <description>Descripcion del campo.</description>
    <inlineHelpText>Texto de ayuda para el usuario.</inlineHelpText>
    <label>Label del Campo</label>
    <length>20</length>
    <required>false</required>
    <type>Text</type>
    <externalId>true</externalId>
</CustomField>
```

---

### Paso 3: Actualizar FLS en perfiles

Para cada perfil que debe tener acceso a los campos:

1. Hacer retrieve FRESCO del perfil antes de modificar (nunca editar el archivo sin retrieve):

```bash
sf project retrieve start \
  --metadata "Profile:NombrePerfil" \
  --target-org {ORG_ALIAS}
```

2. Abrir el archivo `force-app/main/default/profiles/NombrePerfil.profile-meta.xml`

3. Agregar los `<fieldPermissions>` para cada campo nuevo. Insertar **antes de `</Profile>`**, agrupados y contiguos.

   - NUNCA duplicar un bloque que ya exista para el mismo campo.
   - Campos formula: `<editable>false</editable>` + `<readable>true</readable>`
   - Campos normales: `<editable>true</editable>` + `<readable>true</readable>`

```xml
<fieldPermissions>
    <editable>true</editable>
    <field>{OBJETO}.{PREFIJO}_NombreCampo__c</field>
    <readable>true</readable>
</fieldPermissions>
```

---

### Paso 4: Actualizar layout

1. Hacer retrieve del layout:

```bash
sf project retrieve start \
  --metadata "Layout:{OBJETO}-{OBJETO} Layout" \
  --target-org {ORG_ALIAS}
```

2. Agregar los campos en secciones con nombres descriptivos por propósito. NO usar secciones genéricas sin contexto funcional.

   Estilos recomendados de sección:
   - "Informacion Basica"
   - "Informacion de Identificacion"
   - "Clasificacion Comercial"
   - "Cartera y Credito"
   - "Datos de Integracion"

3. Campos formula en layout: `<behavior>Readonly</behavior>`
4. Campos normales en layout: `<behavior>Edit</behavior>`

```xml
<layoutSections>
    <customLabel>true</customLabel>
    <detailHeading>true</detailHeading>
    <editHeading>true</editHeading>
    <label>Informacion de Identificacion</label>
    <layoutColumns>
        <layoutItems>
            <behavior>Edit</behavior>
            <field>{PREFIJO}_Tipo_Identificacion__c</field>
        </layoutItems>
        <layoutItems>
            <behavior>Edit</behavior>
            <field>{PREFIJO}_Numero_Identificacion__c</field>
        </layoutItems>
    </layoutColumns>
    <layoutColumns/>
    <style>TwoColumnsTopToBottom</style>
</layoutSections>
```

---

### Paso 5: Deploy en orden correcto

```bash
# 1. Global Value Sets — solo si hay GVS nuevos, deploy separado PRIMERO
sf project deploy start \
  --metadata "GlobalValueSet:{PREFIJO}_NombreGVS1" \
  --metadata "GlobalValueSet:{PREFIJO}_NombreGVS2" \
  --target-org {ORG_ALIAS}

# 2. Campos + Perfiles + Layout — todo junto en un solo deploy
sf project deploy start \
  --metadata "CustomField:{OBJETO}.{PREFIJO}_Campo1__c" \
  --metadata "CustomField:{OBJETO}.{PREFIJO}_Campo2__c" \
  --metadata "Profile:NombrePerfil1" \
  --metadata "Profile:NombrePerfil2" \
  --metadata "Layout:{OBJETO}-{OBJETO} Layout" \
  --target-org {ORG_ALIAS}
```

**Nota:** Los campos y perfiles van en el mismo deploy. Los GVS siempre van antes.

---

### Paso 6: Verificar y sincronizar

1. Si hay errores, consultar la tabla de errores conocidos (sección siguiente).

2. Verificar haciendo retrieve de lo desplegado:

```bash
sf project retrieve start \
  --metadata "CustomField:{OBJETO}.{PREFIJO}_Campo1__c" \
  --target-org {ORG_ALIAS}
```

3. Confirmar en la org: revisar el objeto en Setup > Object Manager > Fields.

4. Commit y push:

```bash
git add force-app/main/default/objects/{OBJETO}/fields/ \
        force-app/main/default/globalValueSets/ \
        force-app/main/default/profiles/ \
        force-app/main/default/layouts/
git commit -m "feat: campos custom {OBJETO} — {PREFIJO}"
git push
```

---

## Errores conocidos y fixes

| Error | Causa | Fix |
|---|---|---|
| `You cannot deploy to a required field` | Campo tiene `<required>true</required>` | Cambiar a `<required>false</required>` + crear Validation Rule en la org |
| `Element fieldPermissions is duplicated` | Dos bloques de fieldPermissions en el profile para el mismo campo | Extraer todos los `<fieldPermissions>`, ordenar, deduplicar por `<field>`, reinsertar contiguos antes de `</Profile>` |
| `Field must be Readonly in the page layout` | Campo formula con `<behavior>Edit</behavior>` en el layout | Cambiar a `<behavior>Readonly</behavior>` en el layoutItem del campo formula |
| `GlobalValueSet not found` | Campo referencia un GVS que no existe en la org | Desplegar el GVS primero en deploy separado antes de desplegar el campo |
| `Dependent class is invalid and needs recompilation` | Apex existente referencia el objeto/campo y hay error de compilación | Hacer full retrieve del objeto y redeployar, o compilar Apex desde Developer Console |
| `Invalid field in related list` | Layout referencia un campo que no existe en la org aun | Asegurarse de que el campo fue desplegado antes que el layout, o incluirlo en el mismo deploy |
| `Cannot set editable=true on formula field` | FLS de campo formula marcado como editable | Cambiar a `<editable>false</editable>` en el profile para ese campo |
