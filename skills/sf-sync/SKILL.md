# sf-sync — Sincronización Org ↔ Local ↔ Git

## Cuándo invocar

Cuando el usuario diga:
- "sincroniza el org", "retrieve y commit", "haz un retrieve completo"
- "actualiza el local", "baja los cambios del org"
- "commit y push de todo", "versiona los cambios"

---

## Modos de operación

### Modo 1: Retrieve completo + commit + push
Baja TODO el org, commitea y pushea.

```bash
# 1. Retrieve completo usando el manifest
sf project retrieve start --manifest manifest/package.xml --target-org {ORG_ALIAS}

# 2. Ver qué cambió
git status --short | wc -l
git status --short | head -30

# 3. Commit y push
git add -A
git commit -m "chore: retrieve completo org {ORG_ALIAS} — {FECHA}"
git push origin main
```

### Modo 2: Retrieve selectivo + commit + push
Cuando el usuario especifica qué componentes bajar.

```bash
sf project retrieve start \
  --metadata "CustomObject:Lead" \
  --metadata "Profile:Admin" \
  --metadata "FlexiPage:Lead_Record_Page_Three_Column" \
  --target-org {ORG_ALIAS}
```

### Modo 3: Solo commit + push (ya hay cambios locales)
```bash
git add -A
git commit -m "feat/chore/fix: {descripcion}"
git push origin main
```

---

## Reglas importantes

- **Nunca** hacer `git add -A` antes de revisar qué archivos cambiaron
- Si hay archivos en `.claude/` no comprometer información sensible
- El mensaje de commit debe describir QUÉ cambió y POR QUÉ, no solo "retrieve"
- Después de un retrieve completo, verificar que no se sobrescribieron cambios locales pendientes de deploy

---

## Nombres de PathAssistant

Los PathAssistants no siempre tienen el nombre esperado. Para encontrarlos:
```bash
sf org list metadata --metadata-type PathAssistant --target-org {ORG_ALIAS}
```

## Nombres de FlexiPage de Lead/Account/Contact/Opportunity

Siempre usar los nombres que están en `force-app/main/default/flexipages/`. Los nombres más comunes:
- `Lead_Record_Page_Three_Column`
- `Account_Record_Page_Three_Column`
- `Contact_Record_Page_Three_Column`
- `Opportunity_Record_Page_Three_Column`
