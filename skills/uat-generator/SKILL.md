---
name: uat-generator
description: Genera el manual de pruebas / guion UAT de un proyecto Salesforce StudioDX automáticamente desde los Criterios de Aceptación de las HU, con hoja de sign-off por REQ. Arranque formal del plan de adopción (SF Crew 3.0). Usar cuando el usuario diga "crew uat", "genera el UAT", "arma el manual de pruebas", "prepara el guion de pruebas del cliente".
---

# uat-generator — Manual UAT desde los CA (SF Crew 3.0)

Multi-proyecto: fuentes por `{proyecto}/.sfcrew/config.json` y la base Notion.
Dos modos: `--skeleton` (al inicio, desde el BRD/HU) y `--final` (pre-Go-Live).

## Entradas

1. Tarjetas Notion (HU + ADJ) con criterios de aceptación (CA-01, CA-02…).
2. El BRD del proyecto (tabla REQ → HU) para la matriz de trazabilidad.
3. `tasks.csv` v2: solo entran al UAT las HU con tareas `deployed`.

## Procedimiento

1. Recolectar HU/ADJ elegibles con sus CA.
2. Por cada CA generar **al menos un caso de prueba verificable**:
   `ID (UAT-<HU>-<CA>) · Precondición · Pasos numerados · Resultado esperado · Resultado obtenido (vacío) · Pasa/Falla (vacío)`.
3. **Cobertura:** todo REQ del BRD debe aparecer en ≥1 caso. Los REQ sin caso se listan en "Sin cobertura" — nunca se omiten.
4. Generar `.docx` con branding StudioDX: portada, matriz REQ↔HU↔casos, casos por épica, hoja de sign-off por REQ.
5. **Regeneración sin pérdida:** si ya existe un UAT con resultados, no sobreescribir — generar delta.
6. Write-back: `UAT Status = Pendiente` en las tarjetas incluidas.

## Captura de resultados

Joan o el cliente marcan Pasa/Falla en el docx o en Notion (`UAT Status`: En UAT → Aprobado/Rechazado). `crew exceptions` lista los `Rechazado` como excepciones (vuelven al ciclo como ADJ).
