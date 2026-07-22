# SFCrew 3.0 — Sistema multi-agente para proyectos Salesforce

SFCrew convierte al consultor/arquitecto en un **punto de control**, no en el middleware síncrono. Claude Code actúa como Architect; runners headless ejecutan la cola de tareas Salesforce en paralelo, con revisión Opus antes de cualquier merge.

## El problema que resuelve

En una implementación Salesforce con AI, todo pasa por el consultor: asigna manualmente cada tarea, actualiza Notion, aprueba cada merge. El throughput del equipo = velocidad del consultor.

SFCrew 3.0 invierte eso: el consultor aprueba colas, no tareas. Y no aprueba nada que Opus no haya revisado primero.

## Arquitectura

```
Notion (negocio/PM) ⇄ tasks.csv v2 (ejecución) ⇄ Org Salesforce
        ↑                      ↑                        ↑
   notion-sync            dispatcher              integrator
                               ↓
                    Runners headless (DeepSeek / GLM)
                               ↓
                    review.py → Opus gate → crew approve
```

## Roster de agentes

| Rol | Modelo | Alias |
|---|---|---|
| **Architect** | Claude Code (Sonnet/Opus) | `claude` |
| **Runner principal** | DeepSeek v3 | `deepseek` |
| **Runner secundario / pre-revisor** | GLM (ZhipuAI) | `glm` |
| **Revisor final** | Claude Opus | manual en sesión Architect |

El roster está fijado por benchmark (FASE-0). GLM nunca revisa su propia rama.

## Skills incluidos

### Coordinación (SFCrew)
| Skill | Función |
|---|---|
| `crew` | Consola: `init · status · sync · approve · exceptions · plan · dispatch · review · tick · console · dashboard · uat · adoption` |
| `sfcrew-protocol` | Protocolo v3 completo para Architect y Runners |
| `notion-sync` | Motor bidireccional Notion ⇄ CSV (nunca escribe estado `returned`) |
| `integrator` | Merge train + aprobación en lote; solo tareas con revisión Opus aprobada |
| `hu-to-task` | HU/ADJ → tareas técnicas con dependencias; plantilla v3 con sección de ajustes |
| `dispatcher` | Ruteo push por tipo, carga y `headless_tier`; genera `crew_dispatch_run.sh` |
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
2. `crew tick` (o lanzar `crew_dispatch_run.sh` manualmente) → runners arrancan headless
3. Runners actualizan el CSV al terminar → estado `ready_to_merge`
4. `crew review` → `review.py` ensambla el payload; Opus revisa el lote manualmente
5. Opus aprueba o devuelve (`returned`) con instrucciones precisas
6. `crew approve` → lote integrado → Notion actualizado (`Hecho` + `Completed on`)

## Intervención humana: solo 3 momentos

1. **`crew tick`** — lanza el ciclo (runners + pre-revisión GLM automática)
2. **Revisión Opus** — leer PAYLOAD + PREREVIEW, aplicar veredicto en CSV
3. **`crew approve`** — aprobación del lote completo
4. **`crew exceptions`** — solo lo que se rompió o fue devuelto

## Estado `returned` (nuevo en v3)

Cuando Opus detecta un defecto recuperable, marca la tarea como `returned` con instrucciones de ajuste. El runner la recoge en el siguiente tick sin intervención del Architect. Solo Opus escribe `returned`; notion-sync nunca lo sobreescribe.

## Scripts incluidos

| Script | Ubicación | Función |
|---|---|---|
| `console.py` | `crew/scripts/` | Servidor local solo-lectura (puerto 8787); sin dependencias |
| `launcher.py` | `crew/scripts/` | Genera y lanza invocaciones headless por runner |
| `review.py` | `crew/scripts/` | Ensambla payload de revisión anclado a commits del CSV |
| `tick.ps1` | `crew/scripts/` | Ciclo completo: launcher → review → pre-revisión GLM → dashboard |
| `dashboard.py` | `crew/scripts/` | Tablero HTML estático con filtros por estado |
| `migrate_tasks_csv_v2.py` | `crew/scripts/` | Migración tasks.csv v1 → v2 (idempotente, con backup) |
| `sync_csv.py` | `notion-sync/scripts/` | Helper determinista del motor de sync |

## Licencia

MIT
