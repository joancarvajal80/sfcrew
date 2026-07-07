# SFCrew 2.0 — Sistema multi-agente para proyectos Salesforce

SFCrew convierte al consultor/arquitecto en un **punto de control**, no en el middleware síncrono. Claude Code actúa como Architect; runners headless (DeepSeek, GLM, Claude headless) ejecutan la cola de tareas Salesforce en paralelo.

## El problema que resuelve

En una implementación Salesforce tradicional con AI, todo pasa por el consultor: asigna manualmente cada tarea, actualiza Notion, aprueba cada merge. El throughput del equipo = velocidad del consultor.

SFCrew 2.0 invierte eso: el consultor aprueba colas, no tareas.

## Arquitectura

```
Notion (negocio/PM) ⇄ tasks.csv v2 (ejecución) ⇄ Org Salesforce
        ↑                      ↑                        ↑
   notion-sync            dispatcher              integrator
```

## Skills incluidos

### Coordinación (SFCrew)
| Skill | Función |
|---|---|
| `crew` | Consola: `init · status · sync · approve · exceptions · plan · dispatch · dashboard · uat · adoption` |
| `sfcrew-protocol` | Protocolo v2 completo para Architect y Runners |
| `notion-sync` | Motor bidireccional Notion ⇄ CSV |
| `integrator` | Merge train + aprobación en lote |
| `hu-to-task` | HU/ADJ → tareas técnicas con dependencias |
| `dispatcher` | Ruteo push por tipo y carga; genera script headless |
| `uat-generator` | Manual UAT desde Criterios de Aceptación |
| `adoption-tracker` | Métricas de adopción vía SOQL; write-back a Notion |

### Desarrollo Salesforce
| Skill | Función |
|---|---|
| `sf-campos` | Crear y desplegar campos custom (XML + FLS + layout) |
| `sf-objeto-custom` | Crear objetos custom completos |
| `sf-sync` | Retrieve, commit y push post-deploy |
| `sf-deploy` | Deploy a sandbox o producción con orden de dependencias |
| `sf-doc-metadata` | Documentar metadata en `.md` como insumo |
| `sf-experience-cloud` | Portales Experience Cloud (Aura) vía Metadata API |
| `salesforce-dev` | Flows, Apex, Omni-Channel, DevOps |

## Instalación rápida

Ver [QUICKSTART.md](QUICKSTART.md).

## Flujo de un sprint

1. HU aprobada en Notion → `crew plan HU-XXX` → tareas generadas + asignadas
2. Revisar y correr `crew_dispatch_run.ps1` (runners arrancan headless)
3. Runners actualizan el CSV al terminar
4. `crew approve` → lote presentado → aprobación en un comando
5. Notion actualizado automáticamente (`Hecho` + `Completed on`)

## Intervención humana: solo 3 momentos

1. **Revisar y lanzar** `crew_dispatch_run.ps1` — un script, no tarea a tarea
2. **`crew approve`** — aprobación del lote completo
3. **`crew exceptions`** — solo lo que se rompió

## Licencia

MIT
