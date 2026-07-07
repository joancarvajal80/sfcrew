---
name: uat-generator
description: Genera el manual de pruebas / guion UAT de un proyecto Salesforce automáticamente desde los Criterios de Aceptación de las HU, con hoja de sign-off por REQ. Arranque formal del plan de adopción (SF Crew 2.0, Fase 4). Usar cuando el usuario diga "crew uat", "genera el UAT", "arma el manual de pruebas", "prepara el guion de pruebas del cliente".
---

# uat-generator — Manual UAT desde los CA (SF Crew 2.0)

Multi-proyecto: fuentes por `{proyecto}/.sfcrew/config.json` y la base Notion
del proyecto. Dos modos: `--skeleton` (al inicio, desde el BRD/HU) y `--final`
(pre-Go-Live, incorpora los ADJ del camino).

## Entradas

1. Tarjetas Notion del proyecto (HU + ADJ) con sus criterios de aceptación
   (CA-01, CA-02…) — leer con `notion-fetch` por épica.
2. El BRD del proyecto (tabla REQ → HU) para la matriz de trazabilidad.
3. `tasks.csv` v2: solo entran al UAT las HU con tareas `deployed`.

## Procedimiento

1. Recolectar HU/ADJ elegibles (modo skeleton: todas las aprobadas; modo final:
   las `deployed` + ADJ) con sus CA.
2. Por cada CA generar **al menos un caso de prueba verificable**:
   `ID (UAT-<HU>-<CA>) · Precondición · Pasos numerados (como usuario final,
   con nombres de menú/campo reales del org) · Resultado esperado · Resultado
   obtenido (vacío) · Pasa/Falla (vacío)`.
3. **Cobertura:** todo REQ del BRD debe aparecer en ≥1 caso. Los REQ sin caso
   se listan en una sección "Sin cobertura" — nunca se omiten en silencio.
4. Generar `.docx` con branding del proyecto (mismo pipeline que `brd-generator`):
   portada, matriz REQ↔HU↔casos, casos agrupados por épica, y **hoja de
   sign-off por REQ** (nombre, cargo, fecha, firma).
5. **Regeneración sin pérdida:** si ya existe un UAT con resultados
   registrados, no sobreescribir — generar delta (casos nuevos de ADJ) y
   anexarlo.
6. Write-back: poner `UAT Status = Pendiente` en las tarjetas incluidas
   (vía notion-sync o directamente si son pocas).

## Captura de resultados

El consultor o el cliente marcan Pasa/Falla en el docx o directamente en Notion
(`UAT Status`: En UAT → Aprobado/Rechazado por tarjeta). `crew exceptions`
lista los `Rechazado` como excepciones a resolver (vuelven al ciclo como ADJ).
