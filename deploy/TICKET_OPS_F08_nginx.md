# Ticket DevOps — Anonymiser le header `Server` du Nginx frontal MA2E

**Priorité** : Standard (finding pentest 🟡 Mineur)
**Environnement cible** : Production Azure — `ma2e.swedencentral.cloudapp.azure.com`
**Composant** : Ingress Nginx (Azure Container Apps)
**Origine** : Rapport de test d'intrusion MA2E v1.0 du 03/08/2026 — finding **F-08** (Divulgation de versions et de la pile technique)
**Responsable remédiation applicative** : Flora EBAH — OVERNETFLOW
**Responsable côté ops** : *(à assigner)*

---

## 1. Contexte

Un test d'intrusion mené par la Sécurité Opérationnelle GS2E a identifié que la réponse HTTP du serveur frontal MA2E expose la version précise du composant :

```
HTTP/1.1 200 OK
Server: nginx/1.22.1
```

Un attaquant peut aligner immédiatement des exploits publics (CVE-2022-*, CVE-2023-*, …) sur cette version exacte.

Le code applicatif a déjà été durci (commit `be73ebb` sur `main`) :
- `frontend/middleware.ts` écrase `Server` et retire les headers `X-Nextjs-*` côté Next.js
- `backend/app/main.py` idem côté FastAPI

**Mais tant que Nginx en amont a la main sur le header `Server` final, ces fixes applicatifs sont écrasés.** L'action côté ops est le seul moyen de fermer le finding en production.

## 2. Action demandée

Intégrer le snippet [`deploy/nginx-security.conf`](../deploy/nginx-security.conf) du repo dans la configuration Nginx de l'ingress Azure.

### Option 1 — Immédiat, aucun module additionnel (recommandé pour commencer)

Ajouter dans le bloc `http {}` ou `server {}` de la config Nginx :

```nginx
server_tokens off;
```

Effet : la bannière devient `Server: nginx` (sans le numéro de version). Fonctionne sur Nginx open-source standard, aucune image à changer, aucun downtime.

### Option 2 — Bannière personnalisée (finition)

Si vous préférez masquer complètement Nginx et afficher `Server: MA2E`, il faut le module `ngx_headers_more` :

```nginx
more_set_headers "Server: MA2E";
more_clear_headers "X-Powered-By";
```

Cela requiert une image Nginx qui embarque le module :

```dockerfile
FROM nginx:1.25-alpine
RUN apk add --no-cache nginx-mod-http-headers-more
COPY nginx-security.conf /etc/nginx/conf.d/security.conf
```

## 3. Vérification

Après déploiement, la commande suivante ne doit plus renvoyer de numéro de version :

```bash
curl -sI https://ma2e.swedencentral.cloudapp.azure.com/login | grep -i "^server:"
```

**Attendu** :
- Option 1 : `Server: nginx`
- Option 2 : `Server: MA2E`

**Non attendu** : `Server: nginx/1.22.1` ou toute variante avec numéro.

Vous pouvez aussi relancer Wappalyzer sur la page de connexion : la carte « Reverse proxies » ne doit plus afficher `1.22.1`.

## 4. Livrable côté ops

- Config Nginx mise à jour et déployée sur l'ingress production
- Capture ou log de vérification `curl -sI` (attendu ci-dessus)
- Signaler à Flora EBAH pour clôture du finding F-08 dans le plan de remédiation

## 5. Rappel — ce que ce ticket ne couvre PAS (et pourquoi)

- **La détection de Next.js et React par Wappalyzer** restera possible. Elle utilise des empreintes DOM (`data-reactroot`, classes Tailwind, hash des chunks webpack `/_next/static/*`) qui **ne sont pas des bannières de version** et ne peuvent pas être supprimées sans casser l'application. Le pentester lui-même juge l'impact « limité dès lors que ces composants sont tenus à jour » — la parade réelle est la mise à jour continue.
- **La version de Nginx installée** n'est pas changée : on masque uniquement l'exposition publique. La mise à jour de Nginx suit le cycle normal des images de base.

---

## Références

- Rapport de test d'intrusion MA2E v1.0 — 03/08/2026 — finding F-08
- [SECURITY_REMEDIATION_PLAN.md](../backend/SECURITY_REMEDIATION_PLAN.md) — plan global
- [PENTEST_COMPLIANCE_AUDIT.md](../backend/PENTEST_COMPLIANCE_AUDIT.md) — audit de conformité détaillé F-08
- [deploy/nginx-security.conf](nginx-security.conf) — snippet complet à appliquer
