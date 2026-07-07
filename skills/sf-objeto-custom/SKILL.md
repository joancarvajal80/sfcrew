# sf-objeto-custom — Crear Objeto Custom en Salesforce

## Cuándo invocar

Cuando el usuario diga:
- "crea el objeto [Nombre]__c"
- "necesito el objeto custom de [entidad]"
- "construye el objeto [Nombre] con sus campos"

---

## Variables de entrada

- `NOMBRE_OBJETO`: Label singular (ej: Contrato Servicio)
- `NOMBRE_OBJETO_PLURAL`: Label plural (ej: Contratos de Servicio)
- `API_NAME`: Nombre técnico (ej: {PREFIJO}_Contrato_Servicio__c)
- `PREFIJO`: Prefijo del proyecto (ej: PRY)
- `ORG_ALIAS`: Alias del org en SF CLI
- Lista de campos con sus definiciones

---

## Paso 1: Crear el objeto

Path: `force-app/main/default/objects/{API_NAME}/`

Crear `{API_NAME}.object-meta.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>{Descripcion funcional del objeto}</description>
    <label>{NOMBRE_OBJETO}</label>
    <nameField>
        <label>Nombre</label>
        <type>AutoNumber</type>
        <displayFormat>{PREFIJO}-{000000}</displayFormat>
    </nameField>
    <pluralLabel>{NOMBRE_OBJETO_PLURAL}</pluralLabel>
    <searchable>true</searchable>
    <sharingModel>ReadWrite</sharingModel>
</CustomObject>
```

Notas sobre sharingModel:
- `ReadWrite` — todos los usuarios del mismo rol pueden editar (más común para objetos de negocio)
- `Private` — solo el dueño puede ver (usar para datos sensibles)
- `Read` — todos pueden ver, solo el dueño puede editar

---

## Paso 2: Crear campos

Seguir el skill `sf-campos` para generar los campos del objeto.
Path: `force-app/main/default/objects/{API_NAME}/fields/`

---

## Paso 3: Crear layout

Path: `force-app/main/default/layouts/{API_NAME}-{NOMBRE_OBJETO} Layout.layout-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <layoutSections>
        <customLabel>false</customLabel>
        <detailHeading>false</detailHeading>
        <editHeading>false</editHeading>
        <label>Informacion {NOMBRE_OBJETO}</label>
        <layoutColumns>
            <layoutItems>
                <behavior>Edit</behavior>
                <field>Name</field>
            </layoutItems>
            <!-- Agregar campos de la columna izquierda -->
        </layoutColumns>
        <layoutColumns>
            <!-- Columna derecha -->
        </layoutColumns>
        <style>TwoColumnsTopToBottom</style>
    </layoutSections>
    <showEmailCheckbox>false</showEmailCheckbox>
    <showHighlightsPanel>false</showHighlightsPanel>
    <showInteractionLogPanel>false</showInteractionLogPanel>
    <showRunAssignmentRulesCheckbox>false</showRunAssignmentRulesCheckbox>
    <showSubmitAndAttachButton>false</showSubmitAndAttachButton>
</Layout>
```

---

## Paso 4: Asignar perfiles

En el profile metadata, los objetos custom necesitan `<objectPermissions>`:

```xml
<objectPermissions>
    <allowCreate>true</allowCreate>
    <allowDelete>false</allowDelete>
    <allowEdit>true</allowEdit>
    <allowRead>true</allowRead>
    <modifyAllRecords>false</modifyAllRecords>
    <object>{API_NAME}</object>
    <viewAllRecords>false</viewAllRecords>
</objectPermissions>
```

Para el perfil Administrador: todos los permisos en true.
Para perfiles de negocio: ajustar según el rol.

---

## Paso 5: Deploy

```bash
# Primero el objeto base
sf project deploy start \
  --metadata "CustomObject:{API_NAME}" \
  --target-org {ORG_ALIAS}

# Luego los campos + perfiles + layout
sf project deploy start \
  --metadata "CustomField:{API_NAME}.{PREFIJO}_Campo__c" \
  --metadata "Profile:NombrePerfil" \
  --metadata "Layout:{API_NAME}-{NOMBRE_OBJETO} Layout" \
  --target-org {ORG_ALIAS}
```

**IMPORTANTE:** El objeto debe desplegarse en un paso ANTES que los campos y el layout. Si se intenta todo junto, Salesforce puede fallar por dependencias.

---

## Trampas conocidas

| Error | Fix |
|---|---|
| `Object {name} does not exist` al desplegar campos | Desplegar el objeto primero en paso separado |
| Layout name mismatch | El nombre del archivo de layout debe coincidir exactamente con `{API_NAME}-{Label del objeto} Layout` |
| sharingModel incompatible con OWD | Si el OWD del org está en Private para objetos relacionados, usar sharingModel controlledByParent |
