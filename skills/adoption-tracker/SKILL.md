---
name: adoption-tracker
description: Instrumentación de adopción real del Salesforce entregado (SF Crew 2.0, Fase 4). Convierte "adoptado" en métrica medible por épica/HU usando señales del org (SOQL, LoginHistory, conteos de uso) y actualiza la propiedad Adoption en Notion. Usar cuando el usuario diga "crew adoption", "¿qué se construyó pero no se usa?", "mide la adopción", "reporte de adopción del cliente".
---

# adoption-tracker — Medición de adopción (SF Crew 2.0)

Multi-proyecto vía `{proyecto}/.sfcrew/config.json` (org alias). Aplica la
**Definition of Adopted**:

```
construido (deployed) → probado (UAT Aprobado) → entrenado (champion capacitado) → USADO (uso ≥ umbral)
```

Solo el último escalón marca `Adoption = Adoptado`. Cada escalón previo
incompleto deja la señal en el nivel que corresponda.

## Señales de uso (fallback SOQL — siempre disponible sin paquetes)

| Tipo de feature | Señal | SOQL base |
|---|---|---|
| Campo custom | % de registros recientes con el campo poblado | `SELECT COUNT(Id), COUNT(<campo>) FROM <obj> WHERE LastModifiedDate = LAST_N_DAYS:30` |
| Objeto custom | Registros creados/mes | `SELECT COUNT(Id) FROM <obj> WHERE CreatedDate = LAST_N_DAYS:30` |
| Flow/proceso | Registros que alcanzan el estado que el flow produce | según el flow |
| Record Type / layout | Registros por RT | `GROUP BY RecordTypeId` |
| Uso general | Logins por usuario | `SELECT UserId, COUNT(Id) FROM LoginHistory WHERE LoginTime = LAST_N_DAYS:30 GROUP BY UserId` |
| Reports/dashboards | Última vista | `SELECT Id, LastViewedDate FROM Report WHERE FolderName LIKE '<PFX>%'` |

Complementos recomendados (incluir en alcance del proyecto): **Salesforce
Adoption Dashboards** (AppExchange) y **Lightning Usage App**; **In-App
Guidance** para empujar features con adopción baja.

## Umbrales por defecto (ajustables por proyecto en config.json, clave `adoption_thresholds`)

- Campo: ≥40% de registros nuevos con valor → Adoptado; 10–40% En adopción; <10% Bajo umbral.
- Objeto/proceso: ≥1 registro/semana por usuario objetivo → Adoptado.
- Report/dashboard: visto en los últimos 14 días → Adoptado.

## Procedimiento

1. Construir el mapa HU → features desplegadas desde `tasks.csv` v2
   (`hu_code` + `object` + metadata en el `.md` de la tarea).
2. Correr las SOQL (`sf data query --target-org <org>`) por feature.
3. Clasificar según umbral y escalón de la Definition of Adopted (cruzar con
   `UAT Status` de Notion).
4. Write-back: `Adoption` en las tarjetas Notion; sección de adopción en el
   tablero (`dashboard.py` la lee de `.sfcrew/adoption.json` — escribir ahí:
   `[{"epica": "...", "construido": "N", "adoptado": "M (x%)"}]`).
5. Reporte al consultor: por épica % construido vs % adoptado + **lista de features
   entregadas sin uso** (candidatas a re-entrenamiento o In-App Guidance).
