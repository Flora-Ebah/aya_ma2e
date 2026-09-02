# Décision produit — F-03 : contrôle d'authenticité des pièces d'identité

**Origine** : Rapport de test d'intrusion MA2E v1.0 — 03/08/2026 — finding **F-03** (Acceptation de pièces d'identité contrefaites) — criticité 🔴 **Critique**.

**Statut** : ⚠️ **À arbitrer** — décision produit/budget.
**Portée** : intégration d'un référentiel officiel d'identité ou d'un service tiers de vérification biométrique.
**Responsables pressentis** : Direction MA2E, DSI GS2E, DPO, OVERNETFLOW (implémentation).

---

## 1. Contexte

Le pentester a démontré qu'un document manifestement fabriqué (marqué SPECIMEN, numéro `IC000000411`) était accepté par le parcours d'inscription MA2E avec un score de confiance OCR de 88 %. Le score ne porte que sur la lisibilité de l'extraction, jamais sur la véracité du document. Aucun contrôle d'authenticité (éléments de sécurité, référentiel officiel) n'est en place aujourd'hui.

La reco pentester en 2 points :
1. **Introduire un contrôle d'authenticité de la pièce** (éléments de sécurité, détection de fabrication, confrontation obligatoire à un référentiel officiel).
2. **Subordonner la poursuite du parcours à la réussite de ces contrôles.**

Ces contrôles nécessitent une brique externe — MA2E ne peut pas les fabriquer en interne. Ce document présente les options.

---

## 2. Mitigations déjà en place (sans intégration externe)

Ces mesures ferment la porte aux cas triviaux mais **n'écartent pas un attaquant sophistiqué**. Elles sont livrées dans le commit courant :

| Mesure | Effet | Fichier |
|---|---|---|
| Détection heuristique « SPECIMEN / TEST / DEMO » | Bloque le PoC exact du pentester + variantes évidentes | `app/services/ocr_guardrails.py:detect_counterfeit_markers` |
| Détection de numéros de pièce triviaux (`000000`, séquences, `IC000000...`) | Bloque les documents forgés à la main | idem |
| Blocage automatique en `priority_review` | Un dossier avec marqueur remonte en revue humaine, quel que soit l'état des autres contrôles | `app/conversation/default_actions.py:create_real_dossier` |
| Confrontation saisie ↔ OCR (F-06) | Un usager qui saisit « Didier » avec un document « SPECIMEN » déclenche mismatch → arbitrage forcé | `app/conversation/default_actions.py:verify_user_data_vs_ocr` |
| Certification sur l'honneur (Gate 3, loi 2013-546) | Engage la responsabilité pénale de l'usager en cas de fausse déclaration | Workflow inscription |
| Validation humaine finale par agent MA2E | Aucun dossier n'obtient un numéro sociétaire sans validation manuelle | Back-office |
| Rate-limit + allowlist Origin sur uploads (F-01/F-04) | Bloque le scanning en masse et l'appel depuis un site tiers | `app/core/rate_limit.py`, `app/webhooks/web.py` |

**Test de non-régression** : `python -m tests.test_counterfeit_detection` — 31 assertions couvrant le PoC pentester exact + les variantes.

**Ce qui reste possible pour un attaquant** :
- Fabriquer un faux document plausible (nom réel-sonnant, numéro `C00234567`, photos volées) → **non détecté par les heuristiques**.
- Utiliser une vraie photo de CNI d'une personne réelle mais dont il n'est pas titulaire → l'OCR extrait des données cohérentes, aucun signal d'alarme.

C'est exactement pour ces cas qu'un référentiel officiel est requis.

---

## 3. Options techniques

### Option A — Intégration ANI Côte d'Ivoire (Agence Nationale d'Identification)

**Principe** : appel API vers l'ANI (ou son back-office ONI) pour valider qu'un numéro de CNI existe et correspond aux nom/prénoms saisis.

**Avantages** :
- Référentiel officiel — c'est LA source de vérité.
- Aligné avec les exigences ARTCI (loi 2013-450 sur la protection des données).
- Politiquement fort — MA2E se positionne comme partenaire des institutions.

**Difficultés** :
- Signer une convention avec l'ANI/ONI (délai administratif estimé **3-6 mois**).
- Obtenir des accès API + certificats (dépendant du niveau d'agrément accordé).
- Traiter les cas où l'ANI est en panne (fallback dégradé — file d'attente ?).

**Coût estimé** : à cadrer avec l'ANI (probable modèle par requête).

### Option B — Service tiers de vérification biométrique

**Principe** : le sociétaire prend un selfie, l'API compare le visage au portrait de la CNI, et optionnellement cross-check le numéro sur registre officiel.

Prestataires actifs sur l'Afrique de l'Ouest :

| Prestataire | Origine | Spécificité |
|---|---|---|
| **Smile ID** | Nigéria/USA | Leader Afrique de l'Ouest. Cross-check registres CNI ivoirien, sénégalais, ghanéen. Selfie match. **Recommandé pour un pilote**. |
| **Youverify** | Nigéria | Similaire. AML/KYC + document verification. |
| **Onfido** | UK | Global. Coût plus élevé. Bonne réputation. |
| **Jumio** | USA | Similaire à Onfido. |
| **Trulioo** | Canada | Focus KYC entreprise. |

**Avantages** :
- Déploiement rapide (2-4 semaines pour un pilote).
- API standardisée, SDK web/mobile disponibles.
- Modèle « paie à l'usage » — pas d'investissement initial.

**Difficultés** :
- Coût récurrent (~150-800 FCFA/vérification selon volume et niveau).
- Dépendance à un prestataire externe (audit conformité ARTCI à prévoir : où sont hébergées les données ?).
- Nécessite d'ajouter une étape « selfie » au parcours (impact UX à mesurer).

### Option C — Statu quo + reliance sur validation humaine

**Principe** : garder les mitigations heuristiques déjà en place, s'appuyer sur l'agent MA2E en back-office pour arbitrer visuellement chaque dossier priority_review.

**Avantages** :
- Coût nul.
- Fonctionnel dès maintenant.

**Difficultés** :
- Ne passe **pas** l'audit pentest à 100 % — F-03 reste ouvert.
- Charge de travail agent proportionnelle au volume (pas scalable au-delà de ~500 dossiers/jour/agent).
- Faux positifs (agent voit un dossier légitime marqué `priority_review` par F-06 ou F-03) et faux négatifs (agent laisse passer un vrai faux).
- Risque légal si un dossier frauduleux passe et cause préjudice.

---

## 4. Trois questions à trancher au comité

1. **Quel est le volume de faux dossiers acceptable ?**
   - Zéro tolérance → Option A ou B **obligatoire**.
   - Tolérance résiduelle (« l'agent bloquera ») → Statu quo (Option C).

2. **Combien MA2E est prête à payer par inscription pour éliminer ce risque ?**
   - ≤ 200 FCFA → seule l'Option A permet ce coût (à négocier avec l'ANI).
   - 200-500 FCFA → Option B (Smile ID) réaliste.
   - > 500 FCFA → Onfido / Jumio possibles.

3. **Y a-t-il une contrainte réglementaire qui impose la vérification biométrique ?**
   - À faire vérifier par le DPO et la Direction juridique.
   - Loi 2013-450 (ARTCI) — silence sur biométrie mais impose « minimisation ».
   - Recommandation MA2E : commencer par la vérification identitaire simple (nom+numéro contre ANI) avant biométrie.

---

## 5. Reco OVERNETFLOW

**Chemin recommandé** — hybride en 2 vagues :

### Vague 1 (immédiat, coût nul) — Statu quo renforcé
- Les mitigations heuristiques du commit courant sont déployées.
- L'agent MA2E utilise le badge « Revue prioritaire » du back-office (F-06) pour arbitrer visuellement chaque dossier signalé.
- Score de conformité pentest : **7/10** sur F-03.

### Vague 2 (Q4 2026, coût récurrent) — Pilote Smile ID
- Demander un devis Smile ID en indiquant le volume prévisionnel MA2E année 1 (à préciser par la Direction).
- Pilote sur 500 dossiers pour mesurer :
  - taux de match biométrique
  - taux de faux positifs / faux négatifs
  - latence moyenne
  - coût réel par vérification
- Décision go/no-go pour production à l'issue du pilote.
- Score cible : **9.5/10** sur F-03.

### Vague 3 (T1 2027, si stratégique) — Convention ANI
- En parallèle du pilote Smile ID, engager le processus institutionnel avec l'ANI.
- Si convention obtenue, remplacer Smile ID par ANI (Smile ID reste fallback).
- Score cible : **10/10** sur F-03.

---

## 6. Décision attendue du comité

À trancher lors du prochain comité de pilotage :

| Question | Décision |
|---|---|
| **Vague 1 (statu quo renforcé)** — Confirmez-vous la livraison en l'état ? | ☐ Oui / ☐ Non |
| **Vague 2 (pilote Smile ID)** — Autorisez-vous une demande de devis + POC Q4 2026 ? | ☐ Oui / ☐ Non |
| **Vague 3 (convention ANI)** — Souhaitez-vous engager le processus ? | ☐ Oui / ☐ Non / ☐ Plus tard |
| **Contrainte biométrie ARTCI** — Le DPO confirme-t-il l'absence d'obligation ? | ☐ Confirmé / ☐ À vérifier |

**Livrable OVERNETFLOW post-décision** : mise à jour du plan de remédiation, chiffrage d'implémentation, roadmap trimestrielle.

---

## 7. Historique

| Version | Date | Auteur | Modification |
|---|---|---|---|
| 1.0 | 28/08/2026 | Flora EBAH / OVERNETFLOW | Création du dossier suite à l'audit de conformité pentest. |
