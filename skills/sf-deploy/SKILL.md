# sf-deploy — Deploy Salesforce Metadata a Sandbox o Producción

Skill para ejecutar deploys de metadata Salesforce desde el repositorio local hacia cualquier org (sandbox o producción), siguiendo el orden de dependencias correcto y con validación previa.

---

## Cuándo invocar

Cuando el usuario diga:
- "despliega a producción", "despliega al sandbox", "deploy a [org]"
- "sube esto a la org", "publica los cambios"
- "valida el deploy", "dry-run del deploy"
- "despliega [campos / layout / FlexiPage / perfiles / flows / objetos]"
- "prepara el deploy de [componente]"

---

## Paso 0: Verificar orgs disponibles

Siempre ejecutar primero para confirmar qué orgs están conectadas y cuáles necesitan re-autenticación:

```bash
sf org list
```

**Configuración de orgs del proyecto** (ver `{proyecto}/.sfcrew/config.json`):

| Alias | Tipo | URL de autenticación |
|---|---|---|
| `{SANDBOX_ALIAS}` | Sandbox | `https://test.salesforce.com` |
| `{PROD_ALIAS}` | Production | `https://login.salesforce.com` |

Si el org de destino no aparece o dice "expired":

```bash
# Sandbox
sf org login web --alias {SANDBOX_ALIAS} --instance-url https://test.salesforce.com

# Producción
sf org login web --alias {PROD_ALIAS} --instance-url https://login.salesforce.com
```

---

## Paso 1: Identificar qué se va a desplegar

Revisar cambios locales pendientes:

```bash
git status --short
git diff --name-only HEAD
```

Clasificar los archivos cambiados por tipo de metadata:

| Ruta | Tipo metadata |
|---|---|
| `force-app/main/default/globalValueSets/` | GlobalValueSet |
| `force-app/main/default/objects/*/fields/` | CustomField |
| `force-app/main/default/profiles/` | Profile |
| `force-app/main/default/layouts/` | Layout |
| `force-app/main/default/flexipages/` | FlexiPage |
| `force-app/main/default/flows/` | Flow |
| `force-app/main/default/objects/*.object-meta.xml` | CustomObject |
| `force-app/main/default/lwc/` | LightningComponentBundle |
| `force-app/main/default/approvalProcesses/` | ApprovalProcess |
| `force-app/main/default/sharingRules/` | SharingRules |
| `force-app/main/default/tabs/` | CustomTab |

---

## Paso 2: Orden de deploy — CRÍTICO

Siempre respetar este orden para evitar errores de dependencia:

```
1. GlobalValueSets          ← campos picklist que referencian GVS deben existir primero
2. CustomObjects (si nuevo) ← el objeto debe existir antes que sus campos
3. CustomFields             ← deben existir antes de perfiles y layouts
4. Profiles (FLS)           ← deben ir DESPUÉS de los campos que referencian
5. Layouts                  ← deben ir DESPUÉS de los campos que muestran
6. FlexiPages               ← deben ir DESPUÉS del layout
7. Flows                    ← pueden depender de campos y objetos
8. LWC / Aura               ← componentes independientes, van al final
9. ApprovalProcesses        ← dependen de campos y perfiles
```

**Regla de oro:** Si A depende de B, B se despliega primero — en un paso separado o en el mismo deploy si SF CLI puede resolverlo. Cuando hay duda, hacer deploy separado y verificar.

---

## Paso 3: Comandos de deploy

### 3a. Deploy por componente específico (recomendado para deploys pequeños)

```bash
# Un campo
sf project deploy start \
  --metadata "CustomField:{Objeto__c}.{PREFIJO}_Campo__c" \
  --target-org {ORG_ALIAS}

# Un layout
sf project deploy start \
  --metadata "Layout:{Objeto__c}-{Objeto} Layout" \
  --target-org {ORG_ALIAS}

# Un FlexiPage
sf project deploy start \
  --metadata "FlexiPage:{NombreFlexiPage}" \
  --target-org {ORG_ALIAS}

# Un perfil
sf project deploy start \
  --metadata "Profile:Admin" \
  --target-org {ORG_ALIAS}

# Un flow
sf project deploy start \
  --metadata "Flow:{PREFIJO}_NombreFlow" \
  --target-org {ORG_ALIAS}

# Un objeto completo (todos sus campos y metadatos)
sf project deploy start \
  --source-dir force-app/main/default/objects/{Objeto__c} \
  --target-org {ORG_ALIAS}
```

### 3b. Deploy por source-dir (carpeta completa)

```bash
# Layout + FlexiPage de un objeto
sf project deploy start \
  --source-dir "force-app/main/default/layouts/{Objeto__c}-{Objeto} Layout.layout-meta.xml" \
  --source-dir force-app/main/default/flexipages/{NombreFlexiPage}.flexipage-meta.xml \
  --target-org {ORG_ALIAS}

# Todo el force-app (deploy completo — usar con cuidado)
sf project deploy start \
  --source-dir force-app/main/default \
  --target-org {ORG_ALIAS}
```

### 3c. Deploy múltiple con orden de dependencias

```bash
# Paso 1: GVS (si hay nuevos)
sf project deploy start \
  --metadata "GlobalValueSet:{PREFIJO}_NombreGVS" \
  --target-org {ORG_ALIAS}

# Paso 2: Campos + Perfiles + Layout en un solo comando
sf project deploy start \
  --metadata "CustomField:{Objeto__c}.{PREFIJO}_Campo1__c" \
  --metadata "CustomField:{Objeto__c}.{PREFIJO}_Campo2__c" \
  --metadata "Profile:Admin" \
  --metadata "Profile:{PREFIJO}_PerfilNegocio" \
  --metadata "Layout:{Objeto__c}-{Objeto} Layout" \
  --target-org {ORG_ALIAS}

# Paso 3: FlexiPage (después de que layout esté en la org)
sf project deploy start \
  --metadata "FlexiPage:{NombreFlexiPage}" \
  --target-org {ORG_ALIAS}
```

---

## Paso 4: Validación previa (dry-run) — SIEMPRE antes de producción

Antes de cualquier deploy a producción, ejecutar validación:

```bash
sf project deploy start \
  --source-dir force-app/main/default/layouts/ \
  --target-org {PROD_ALIAS} \
  --dry-run
```

O con `--metadata`:

```bash
sf project deploy start \
  --metadata "Layout:{Objeto__c}-{Objeto} Layout" \
  --metadata "FlexiPage:{NombreFlexiPage}" \
  --target-org {PROD_ALIAS} \
  --dry-run
```

El flag `--dry-run` (equivalente a `--check-only` en versiones anteriores) valida sin desplegar. Si la validación pasa, el deploy real usa el mismo comando sin `--dry-run`.

---

## Paso 5: Deploy a producción

Confirmar siempre con el usuario antes de ejecutar contra producción.

```bash
sf project deploy start \
  --metadata "Layout:{Objeto__c}-{Objeto} Layout" \
  --metadata "FlexiPage:{NombreFlexiPage}" \
  --target-org {PROD_ALIAS}
```

Capturar el Deploy ID que aparece en la salida para tracking:
```
Deploy ID: 0AfXXXXXXXXXXXXXX
```

Verificar estado de un deploy en curso:
```bash
sf project deploy report --job-id 0AfXXXXXXXXXXXXXX --target-org {PROD_ALIAS}
```

---

## Paso 6: Verificación post-deploy

### Verificar que el componente llegó a la org

```bash
# Retrieve del componente recién desplegado y comparar con local
sf project retrieve start \
  --metadata "FlexiPage:{NombreFlexiPage}" \
  --target-org {ORG_ALIAS}

# Verificar diff (debería ser vacío si el deploy fue limpio)
git diff force-app/main/default/flexipages/{NombreFlexiPage}.flexipage-meta.xml
```

### Confirmar metadata disponible en la org

```bash
# Listar FlexiPages disponibles en la org
sf org list metadata --metadata-type FlexiPage --target-org {ORG_ALIAS}

# Listar Layouts de un objeto
sf org list metadata --metadata-type Layout --target-org {ORG_ALIAS}

# Listar flows
sf org list metadata --metadata-type Flow --target-org {ORG_ALIAS}
```

---

## Paso 7: Commit post-deploy

Después de un deploy exitoso, commitear los archivos deployados:

```bash
git add force-app/main/default/layouts/ \
        force-app/main/default/flexipages/ \
        force-app/main/default/objects/ \
        force-app/main/default/profiles/

git commit -m "feat(deploy): {Objeto} Layout + FlexiPage — desplegado a {ORG_ALIAS}"
git push origin main
```

---

## Errores conocidos y fixes

| Error | Causa | Fix |
|---|---|---|
| `No package.xml found` | Deploy con `--source-dir` sobre carpeta sin metadata | Usar `--metadata` o apuntar a subcarpeta con archivos `*-meta.xml` |
| `GlobalValueSet X does not exist` | Campo referencia GVS que no está en la org | Desplegar el GVS en un paso separado antes de desplegar el campo |
| `Element fieldPermissions is duplicated` | Dos bloques FLS para el mismo campo en un profile | Extraer todos los `<fieldPermissions>`, deduplicar por `<field>`, reinsertar contiguos antes de `</Profile>` |
| `Field must be Readonly` | Campo formula con `<behavior>Edit</behavior>` en layout | Cambiar a `<behavior>Readonly</behavior>` |
| `Cannot set editable=true on formula field` | FLS de formula como editable en profile | Cambiar a `<editable>false</editable>` |
| `You cannot deploy to a required field` | Campo con `<required>true</required>` | Cambiar a `<required>false</required>` y usar Validation Rule |
| `FlexiPage sobjectType does not match` | El `<sobjectType>` en el FlexiPage no coincide con el objeto real | Verificar nombre API exacto del objeto en `sf org list metadata --metadata-type CustomObject` |
| `Layout name invalid` | El nombre del archivo layout no coincide con el nombre API | El nombre debe ser `{ObjectAPIName}-{LayoutLabel}.layout-meta.xml`. Caracteres especiales como `é` se mantienen en el label pero no en el API name del archivo |
| `Insufficient access rights on cross-reference` | Perfil no tiene visibilidad del objeto | Verificar que el objeto tiene `<deploymentStatus>Deployed</deploymentStatus>` y que el perfil tiene acceso al objeto |
| `Session expired or invalid` | Token de autenticación vencido | Ejecutar `sf org login web --alias {ALIAS} --instance-url {URL}` |

---

## Comandos de utilidad

```bash
# Ver qué metadata existe en la org para un tipo
sf org list metadata --metadata-type {MetadataType} --target-org {ORG_ALIAS}

# Descargar metadata específica para comparar
sf project retrieve start \
  --metadata "{Type}:{APIName}" \
  --target-org {ORG_ALIAS}

# Generar package.xml desde los archivos locales
sf project generate manifest \
  --source-dir force-app/main/default \
  --output-dir manifest \
  --name package

# Deploy usando package.xml (deploy completo)
sf project deploy start \
  --manifest manifest/package.xml \
  --target-org {ORG_ALIAS}

# Cancelar un deploy en curso
sf project deploy cancel --job-id 0AfXXXXXXXXXXXXXX --target-org {ORG_ALIAS}
```

---

## Checklist pre-deploy a producción

Antes de desplegar a producción, confirmar:

- [ ] El deploy pasó en sandbox (`{SANDBOX_ALIAS}`) sin errores
- [ ] Se ejecutó `--dry-run` contra producción y pasó
- [ ] No hay campos con `<required>true</required>`
- [ ] Los campos formula tienen `<behavior>Readonly</behavior>` en layout y `<editable>false</editable>` en FLS
- [ ] El FlexiPage tiene el `<sobjectType>` correcto
- [ ] Se tiene el alias de producción autenticado y activo
- [ ] El usuario confirmó explícitamente que quiere desplegar a producción
