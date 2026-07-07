# sf-experience-cloud — Skill para Experience Cloud (Aura) en Salesforce

Guía completa para crear, configurar y mantener portales Experience Cloud usando la plantilla **Build Your Own (Aura)** vía Metadata API / SFDX.

---

## Cuándo invocar

Usar este skill cuando el usuario diga:
- "crea un portal de Experience Cloud"
- "configura el portal / sitio de comunidad"
- "despliega cambios en el Experience Bundle"
- "agrega una página al portal"
- "el portal se ve feo, mejora el diseño"
- "agrega un componente al portal"
- "el flow no funciona desde el portal"

---

## Limitaciones críticas de plataforma (leer primero)

| Situación | Regla |
|---|---|
| **LWR vs Aura** | Solo "Build Your Own (Aura)" se puede recuperar/desplegar vía Metadata API. "Build Your Own (LWR)" **no funciona** con `sf project retrieve/deploy` — plataforma no lo soporta. |
| **ExperienceBundle setting** | Antes del primer retrieve, habilitar en Setup → Digital Experiences → Settings → "Activar la API de metadatos de ExperienceBundle". Sin esto, el retrieve falla silenciosamente o con error de "no activado". |
| **Publicar después de deploy** | Después de cualquier deploy de ExperienceBundle, hay que **Publicar** el sitio en Experience Builder (o Setup → Digital Experiences) para que los cambios sean visibles a los usuarios. El deploy solo actualiza el draft, no la versión live. |
| **routeTypes disponibles** | Solo existen tipos de ruta del sistema: `home`, `list`, `detail`, `createrecord`, `login`, etc. No existe un routeType genérico personalizado. Intentar `namedPage` da error de deploy. |
| **flowWrapper en detail** | `forceCommunity:flowWrapper` solo funciona en páginas tipo `home`. En páginas `detail` da error de deploy. Para lanzar flows desde registros, usar Quick Action de tipo Flow. |
| **richTextInline y CSS** | El componente `forceCommunity:richTextInline` preserva HTML complejo (CSS grid, flexbox, divs anidados) cuando se despliega vía metadata. Pero si el usuario edita ese componente en Experience Builder UI, el editor WYSIWYG limpia los estilos avanzados. **Nunca editar desde el UI si tiene CSS custom.** |
| **URLs externas en imágenes** | Las políticas CSP del org pueden bloquear `<img src="https://...">` externo. Subir imágenes como **Content Asset** y referenciar con `{!contentAsset.NOMBRE_ASSET.1}`. |

---

## Estructura del ExperienceBundle en metadata

```
force-app/main/default/experiences/<NombreSitio>/
├── config/
│   └── <nombreSitio>.json          # configuración general del sitio
├── routes/
│   ├── inicio.json                 # ruta home
│   ├── listaDeRegistros.json       # ruta list
│   ├── detallesDelRegistro.json    # ruta detail
│   └── ...otros
├── views/
│   ├── inicio.json                 # diseño de la página home
│   ├── listaDeRegistros.json       # diseño de la lista
│   ├── detallesDelRegistro.json    # diseño del detalle de registro
│   └── ...otros
└── themes/
    └── buildYourOwn.json
```

Los archivos `routes/*.json` definen el routeType y la URL. Los archivos `views/*.json` definen los componentes en cada región (header, content, footer).

---

## Comandos esenciales

```bash
# Retrieve del bundle completo
sf project retrieve start \
  --source-dir force-app/main/default/experiences/<NombreSitio>/ \
  --target-org <ORG_ALIAS>

# Deploy de una sola vista (ej: inicio)
sf project deploy start \
  --source-dir "force-app/main/default/experiences/<NombreSitio>/views/inicio.json" \
  --target-org <ORG_ALIAS>

# Deploy del bundle completo
sf project deploy start \
  --source-dir force-app/main/default/experiences/<NombreSitio>/ \
  --target-org <ORG_ALIAS>

# Descubrir el nombre API del ExperienceBundle en el org
sf org list metadata --metadata-type ExperienceBundle --target-org <ORG_ALIAS>
```

---

## Componentes Aura más usados en vistas

| Componente | Tipo de página | Uso |
|---|---|---|
| `forceCommunity:richTextInline` | cualquiera | Bloque HTML libre con CSS custom. Para banners, botones estilizados, logos. |
| `forceCommunity:objectHome` | home/list | Lista de registros de un objeto con filtros y búsqueda. Prop `scope`: nombre del objeto. |
| `forceCommunity:recordHeadline` | detail | Encabezado del registro con nombre y actions. |
| `forceCommunity:recordHomeTabs` | detail | Pestañas (Datos, Relacionados, Actividad). Configurar `tab1Type`, `tab2Type`, labels. |
| `forceCommunity:seoAssistant` | cualquiera | Metadatos SEO (title, description). Va en `sfdcHiddenRegion`. |

### Estructura mínima de una vista (view JSON)

```json
{
  "appPageId": "<ID_DE_APP_PAGE>",
  "componentName": "siteforce:sldsOneColLayout",
  "dataProviders": [],
  "id": "<UUID>",
  "label": "Nombre de la página",
  "regions": [
    { "id": "<UUID>", "regionName": "header", "type": "region" },
    {
      "components": [
        {
          "componentAttributes": { "...": "..." },
          "componentName": "forceCommunity:richTextInline",
          "id": "<UUID>",
          "renderPriority": "NEUTRAL",
          "renditionMap": {},
          "type": "component"
        }
      ],
      "id": "<UUID>",
      "regionName": "content",
      "type": "region"
    },
    { "id": "<UUID>", "regionName": "footer", "type": "region" },
    {
      "components": [
        {
          "componentAttributes": { "title": "...", "description": "" },
          "componentName": "forceCommunity:seoAssistant",
          "id": "<UUID>",
          "renditionMap": {},
          "type": "component"
        }
      ],
      "id": "<UUID>",
      "regionName": "sfdcHiddenRegion",
      "type": "region"
    }
  ],
  "themeLayoutType": "Inner",
  "type": "view",
  "viewType": "home"
}
```

---

## Lanzar un Screen Flow desde el portal (en página de detalle)

La única forma correcta es una **Quick Action de tipo Flow** en el objeto:

```xml
<!-- force-app/main/default/quickActions/<Objeto>.<NombreAction>.quickAction-meta.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<QuickAction xmlns="http://soap.sforce.com/2006/04/metadata">
    <flowDefinition>NOMBRE_API_DEL_FLOW</flowDefinition>
    <label>Etiqueta del Botón</label>
    <optionsCreateFeedItem>false</optionsCreateFeedItem>
    <type>Flow</type>
</QuickAction>
```

**Notas críticas:**
- El nombre del archivo determina el objeto: `Individual.MiAction` → se asigna al objeto `Individual`
- NO incluir `<actionSubtype>` ni `<targetObject>` — son inválidos para `type: Flow`
- Después de desplegar la Quick Action, agregarla al **Page Layout** del objeto en el org (Setup → Object Manager → Layouts → Mobile & Lightning Actions)
- El Flow debe tener una variable `recordId` de tipo String como input para recibir el Id del registro

---

## Diseño visual: template de banner con logo (richTextInline)

Usar siempre single quotes en atributos HTML para evitar problemas con el JSON:

```html
<div style='font-family: Salesforce Sans, Arial, sans-serif;'>
  <!-- Header card con logo -->
  <div style='background: #ffffff; border-radius: 16px; padding: 32px 24px 28px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.09); margin-bottom: 20px; border: 1px solid #e8edf2;'>
    <img src='{!contentAsset.NOMBRE_ASSET.1}'
         style='height: 80px; width: auto; margin-bottom: 18px; display: block; margin-left: auto; margin-right: auto;'
         alt='Logo de la organización' />
    <h2 style='color: #1a3a5c; font-size: 22px; font-weight: 700; margin: 0 0 8px 0;'>Título del Portal</h2>
    <p style='color: #5a6a7a; font-size: 14px; margin: 0; line-height: 1.6;'>Subtítulo descriptivo</p>
  </div>
  <!-- Botones de acción en grid -->
  <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 28px;'>
    <a href='recordlist/OBJETO' style='background: #ffffff; border: 2px solid #c8ddf0; border-radius: 14px; padding: 28px 16px; text-align: center; text-decoration: none; box-shadow: 0 2px 10px rgba(0,0,0,0.05); display: block;'>
      <div style='font-size: 40px; margin-bottom: 12px;'>&#128101;</div>
      <div style='font-size: 15px; font-weight: 600; color: #1a3a5c; margin-bottom: 5px;'>Acción 1</div>
      <div style='font-size: 12px; color: #7a8a9a;'>Descripción corta</div>
    </a>
    <a href='recordlist/OBJETO' style='background: linear-gradient(145deg, #2e6da4 0%, #1a3a5c 100%); border-radius: 14px; padding: 28px 16px; text-align: center; text-decoration: none; box-shadow: 0 4px 16px rgba(46,109,164,0.35); display: block;'>
      <div style='font-size: 40px; margin-bottom: 12px;'>&#127968;</div>
      <div style='font-size: 15px; font-weight: 600; color: #ffffff; margin-bottom: 5px;'>Acción 2</div>
      <div style='font-size: 12px; color: rgba(255,255,255,0.75);'>Descripción corta</div>
    </a>
  </div>
</div>
```

---

## Configuración de la pestaña "Relacionados" en detalle de registro

En `views/detallesDelRegistro.json`, el componente `forceCommunity:recordHomeTabs`:

```json
{
  "componentAttributes": {
    "detailsTabLabel": "Datos",
    "discussionsTabLabel": "Chatter",
    "recordId": "{!recordId}",
    "relatedTabLabel": "Relacionados",
    "showLegacyActivityComposer": false,
    "tab1Type": "details",
    "tab2Type": "related",
    "tab3Type": "none",
    "tab4Type": "none",
    "timelineTabLabel": "Actividad"
  },
  "componentName": "forceCommunity:recordHomeTabs"
}
```

---

## Checklist de deploy

1. [ ] `sf project retrieve start --source-dir force-app/main/default/experiences/<Sitio>/ --target-org <ALIAS>` — siempre retrieve antes de modificar
2. [ ] Editar el archivo JSON de la vista
3. [ ] `sf project deploy start --source-dir ... --target-org <ALIAS>`
4. [ ] Verificar `Status: Succeeded` en la salida
5. [ ] **Publicar el sitio** en Experience Builder o Setup → Digital Experiences
6. [ ] Verificar en el portal que los cambios se ven correctamente

---

## Troubleshooting frecuente

| Error | Causa | Fix |
|---|---|---|
| "ExperienceBundle no está activado para sitios Aura" | Setting no habilitado | Setup → Digital Experiences → Settings → activar "API de metadatos de ExperienceBundle" |
| "Entity of type ExperienceBundle named X cannot be found" | Es un sitio LWR | Crear un sitio Aura nuevo |
| "Ha especificado rutas duplicadas" | routeType duplicado (ej: dos home) | Eliminar la ruta duplicada |
| "forceCommunity:flowWrapper no implementa availableForAllPageTypes" | flowWrapper en página detail | Usar Quick Action de tipo Flow en su lugar |
| "No se puede establecer el campo para el tipo Flujo" | `<actionSubtype>` en Quick Action de Flow | Eliminar `<actionSubtype>` y `<targetObject>` del XML |
| Flow falla con REQUIRED_FIELD_MISSING | Campos con `required=true` a nivel de metadata | Cambiar a `required=false` en los XML de campos y redesplegar |
| Botones del richText se ven feos después de editar en UI | El editor WYSIWYG limpió los estilos | Redesplegar el JSON via metadata, no editar desde el Experience Builder |
