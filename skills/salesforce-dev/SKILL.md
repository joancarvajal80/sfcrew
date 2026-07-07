---
name: salesforce-dev
description: Asiste en implementación técnica de proyectos Salesforce. Cubre diseño y construcción de Flows (Record-Triggered, Screen, Routing, AutoLaunched, Scheduled), Apex (clases, triggers, Schedulable, test classes), configuración de Omni-Channel / Digital Engagement (bots, session handlers, routeWork), metadata management con SF CLI (retrieve/deploy), y análisis de anomalías en automatizaciones existentes. Úsalo cuando el usuario diga "construye este flujo", "revisa esta clase Apex", "analiza estos flujos", "hay un bug en el enrutamiento", "haz retrieve/deploy", o cuando adjunte archivos .flow-meta.xml o .cls para revisar.
---

# Salesforce Dev

Asistente de implementación técnica Salesforce.

## Contexto

Los proyectos siguen este pipeline:
```
Discovery (BRD + HU) → Desarrollo → Pruebas → Documentación → Go-Live
```
Este skill cubre la fase de **Desarrollo**. Las HU aprobadas en Notion son el punto de partida.

## Capacidades principales

### Flows
- Diseño de arquitecturas multi-flujo (entry → subflows → routing)
- Record-Triggered Flows (AfterSave, scheduled paths)
- Screen Flows como Quick Actions en registros
- Routing Flows para session handlers de Omni-Channel
- AutoLaunched Flows invocados desde Apex o bots
- Detección de anomalías: bucles, condiciones incorrectas, variables sin usar

### Omni-Channel / Digital Engagement
- Session handlers, defaultOutboundFlow de bots
- Acción routeWork (Agent, QueueBased, Bot)
- MessagingSession / MessagingEndUser / MessagingChannel
- Bot dialogs, context variables, invocación de subflows desde bot

### Apex
- Clases Schedulable para jobs recurrentes
- Invocación de flows desde Apex (Flow.Interview)
- Test classes con cobertura >75%
- Batch Apex para procesamiento masivo

### Metadata & DevOps
- SF CLI: `sf project retrieve start`, `sf project deploy start`
- Retrieve selectivo por tipo: Flow, Bot, BotVersion, ApexClass, MessagingChannel
- Commit y push a git tras cada ciclo de trabajo
- Análisis de estado (Active/Draft) de flujos en producción

## Protocolo de trabajo

1. **Antes de cualquier cambio**: leer el archivo actual, analizar, proponer — esperar confirmación
2. **Retrieve primero**: si el archivo puede haber cambiado en producción, hacer retrieve antes de editar
3. **Deploy como Draft** por defecto salvo que el usuario indique activar
4. **Commit al finalizar** cada bloque de trabajo con mensaje descriptivo
