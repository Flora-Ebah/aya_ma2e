# Plan de conduite du changement — Lancement MA2E digital

> Programme accompagnant la mise en production de la plateforme d'identification.
> Cible : équipe MA2E (gestionnaires, administrateurs, DPO, comm') + sociétaires CIE/SODECI/ERANOVE.
> Date cible production : **12/09/2026**. Document version 1.0 — 2026-06-15.

---

## 1. Objectifs et indicateurs

### 1.1 Objectifs

| # | Objectif | Mesure du succès |
|---|----------|------------------|
| 1 | Toute l'équipe MA2E formée à la plateforme | 100% des gestionnaires ont validé la formation avant J0 |
| 2 | 80% des sociétaires informés du nouveau service | Reach des 3 vagues comm > 80% de la base CIE+SODECI+ERANOVE |
| 3 | Adoption rapide : 30% d'inscriptions digitales en M+3 | Taux d'inscription via WhatsApp/Web ÷ total inscriptions ≥ 30% |
| 4 | Pas de régression sur les délais d'instruction | Temps moyen validation reste ≤ 48h ouvrées |
| 5 | Satisfaction utilisateurs ≥ 4/5 | Enquête sociétaire à M+1 |

### 1.2 Indicateurs à publier chaque semaine

- Nombre d'inscriptions digitales (WhatsApp vs Web)
- Taux de complétion du parcours (démarré → soumis)
- Taux de validation
- Temps moyen de traitement par gestionnaire
- Top 5 motifs de refus
- Volume de demandes de support N2

---

## 2. Planning J-30 → J+90

### 📅 J-30 (mi-août 2026) — Préparation finale

| Action | Responsable | Livrable |
|--------|-------------|----------|
| Validation finale plateforme (recette MA2E) | DSI MA2E + GS2E | PV de recette signé |
| Création des comptes back-office MA2E (5-10 users) | Admin tenant MA2E | Liste utilisateurs créés |
| Activation MFA obligatoire pour tous les admins | Chaque utilisateur | 100% MFA actif |
| Paramétrage final (persona, templates, settings) | Admin tenant + Marketing MA2E | Capture d'écran de chaque page settings |
| Ingestion base de connaissances initiale (site ma2e.ci) | Admin | > 30 sources ingérées |
| Configuration référentiel agents (CSV ou API ERANOVE) | DSI MA2E | Test 10 matricules OK |
| Test webhook compta (URL + secret + politique events) | DSI MA2E | Delivery `success` |
| Formation gestionnaires (cf. §3) | RH MA2E + GS2E | Tous présents, support distribué |

### 📅 J-15 (fin août 2026) — Communication interne et vague comm 1

| Action | Responsable | Livrable |
|--------|-------------|----------|
| Annonce interne MA2E (mail directeur général) | DG MA2E | Email diffusé |
| Briefing chefs d'agence | DRH MA2E | Brief réalisé en agence |
| Lancement vague 1 communication sociétaires | Comm MA2E | Cf. §4 |
| Affichage QR codes en agence MA2E | Comm + agences | QR posters en agence |
| Page d'aide en ligne publiée | Comm MA2E | https://www.ma2e.ci/aide |
| Article LinkedIn / réseaux MA2E | Comm MA2E | Publication réalisée |

### 📅 J-7 → J0 (mi-septembre 2026) — Bascule

| Action | Responsable | Livrable |
|--------|-------------|----------|
| Tests de charge (simulation 100 inscriptions/h) | GS2E | Rapport perfs |
| Plan de bascule formellement signé | DSI + DG MA2E + GS2E | Document signé |
| Vague 2 communication sociétaires (annonce d'ouverture J0) | Comm MA2E | Cf. §4 |
| Mise en production officielle | DSI MA2E + GS2E | Service en ligne https://app.ma2e.ci |
| War-room 48h post-lancement | Équipe projet | Slack/Teams dédié, monitoring App Insights ouvert |
| Communiqué interne « c'est lancé » | DG MA2E | Email collaborateurs |

### 📅 J+7 — Premier debrief

- **Lundi suivant** : revue des KPIs (cf. §1.2)
- **Mardi** : war-room post-mortem (s'il y a eu des incidents)
- **Mercredi** : retour gestionnaires (qu'est-ce qui marche / qui coince)
- **Jeudi** : ajustements paramétrage IA + templates si besoin
- **Vendredi** : communication interne « bilan semaine 1 »

### 📅 J+30 — Bilan mensuel + vague comm 3

- Rapport mensuel exécutif (KPI + tendances)
- Enquête de satisfaction sociétaires (1 question : « note de 1 à 5 + commentaire libre »)
- Enquête de satisfaction gestionnaires (3 questions)
- Vague 3 communication sociétaires : rappel + push d'engagement (cf. §4)

### 📅 J+60 — Optimisation

- Analyse des motifs de refus récurrents → action correctrice (FAQ, template, formation)
- Revue de la persona IA et des templates si feedback négatif
- Ajout éventuel d'utilisateurs back-office selon la charge

### 📅 J+90 — Phase 3

- Bascule progressive vers CIE (nouveau tenant) si MA2E veut étendre
- Activation de fonctionnalités Phase B (MFA force pour admins, scheduled purge, etc.)
- Bilan trimestriel direction

---

## 3. Plan de formation

### 3.1 Public et durée

| Public | Durée | Format |
|--------|-------|--------|
| **Gestionnaires** (rôle `agent`) | **0,5 jour** | Présentiel + travaux pratiques |
| **Administrateurs tenant** | **1 jour** | Présentiel + paramétrage en live |
| **DPO MA2E** | **0,5 jour** | Atelier dédié conformité ARTCI |
| **Communication / marketing** | 2h | Briefing + capture d'écrans |

### 3.2 Programme gestionnaires (0,5 j)

**Matin (3h)** — Théorie + démo :
- 30 min : Présentation projet MA2E digital (vision, parcours sociétaire, valeur attendue)
- 30 min : Démonstration parcours sociétaire WhatsApp (live)
- 30 min : Démonstration parcours sociétaire web (live)
- 45 min : Visite guidée du back-office (sidebar, dossiers, reporting)
- 45 min : Comment examiner et valider/refuser un dossier (démo + questions)

**Après-midi (3h)** — Pratique :
- 1h : TP individuel — chaque gestionnaire traite 10 dossiers de démo (préparés à l'avance)
- 30 min : Mise en commun, cas piège (OCR raté, photo mal cadrée, motif inhabituel)
- 30 min : MFA — activation en live de chaque participant
- 30 min : Procédures d'escalade et support
- 30 min : Quiz de validation + Q&R

**Évaluation** : QCM de 10 questions, validation si ≥ 8/10. Re-passage possible 1 fois.

### 3.3 Programme administrateurs (1 j) — additionnel au gestionnaire

**Matin (3h)** : programme gestionnaire ci-dessus
**Après-midi (4h)** — Paramétrage :
- 1h : Settings généraux + IA (persona, modèle, températures)
- 1h : Templates de messages (édition, validation variables, preview)
- 1h : Sécurité, MFA, rétention ARTCI, intégrations
- 1h : Reporting, gestion utilisateurs, escalade DPO

### 3.4 Atelier DPO (0,5 j)

- Conformité ARTCI : où sont les preuves de consentement ?
- Comment répondre à une demande de droit d'accès / rectification / effacement ?
- Comment exporter un dossier complet en JSON (preuve litige) ?
- Comment lire et interpréter le journal d'audit (chaîne SHA-256) ?
- Notification de violation : qui prévenir et sous quel délai ?
- Politique de rétention : qui décide de la prolonger / raccourcir ?

### 3.5 Supports

| Support | Format | Destinataires |
|---------|--------|---------------|
| Présentation projet (slides) | PPTX | Tous |
| Guide gestionnaire | Markdown / PDF | Gestionnaires, admins |
| Guide sociétaire | Markdown / PDF | Sociétaires (référence comm) |
| Quiz QCM | Formulaire en ligne | Gestionnaires, admins |
| Cheat sheet 1 page « Que faire en cas de… » | A4 imprimable | Posters dans bureaux gestionnaires |

---

## 4. Communication sociétaires — 3 vagues

### 🎯 Vague 1 — J-15 : annonce

**Message clé** : « Bientôt, vous pourrez devenir sociétaire MA2E **en 5 minutes depuis votre téléphone**. »

**Canaux et messages-types** :

#### WhatsApp Broadcast (à tous les contacts MA2E déjà connus)
```
👋 Bonjour [PRENOM],

À partir du [DATE J0], vous pourrez devenir sociétaire MA2E directement
depuis votre téléphone, en 5 minutes !

✅ Plus de déplacement en agence
✅ Plus de paperasse
✅ Sécurisé et conforme ARTCI

Restez à l'écoute, on vous donne rendez-vous dans 15 jours 🤝

— Équipe MA2E
```

#### Email professionnel (via RH CIE/SODECI/ERANOVE)
- Objet : `[MA2E] Bientôt, votre mutuelle en 5 min depuis votre téléphone`
- Corps : message similaire, plus formel, avec logo MA2E

#### SMS (optionnel, base téléphone MA2E)
```
MA2E : devenez societaire en 5 min depuis votre tel a partir du [DATE].
Infos : ma2e.ci/digital
```

#### Affichage en agence MA2E
- **Poster A2** dans chaque agence : visuel + QR code de la page d'info
- **Tract A5** distribué au guichet
- **Banner site MA2E** : bandeau d'annonce sur ma2e.ci

#### Publication LinkedIn / Facebook MA2E
- Visuel attractif (avant/après le numérique)
- Lien vers la page d'information

### 🚀 Vague 2 — J0 : ouverture officielle

**Message clé** : « C'est maintenant ! **Inscrivez-vous en 5 minutes sur WhatsApp ou sur le web.** »

**Canaux et messages-types** :

#### WhatsApp Broadcast
```
🎉 Bonjour [PRENOM],

C'est officiel : la plateforme MA2E digitale est ouverte !

📱 Envoyez « Bonjour » à ce numéro pour démarrer
💻 Ou rendez-vous sur https://app.ma2e.ci

Vous avez juste besoin de :
• Votre matricule employeur
• Votre CNI
• 5 minutes

Bonne adhésion ! 🤝
— Équipe MA2E
```

#### Email RH
- Objet : `[MA2E] C'est ouvert : inscrivez-vous en ligne en 5 min`
- Corps : annonce officielle + lien direct + QR code

#### Affichage en agence
- Mise à jour des posters : « OUVERT — scannez ici »
- Animation à l'accueil : un agent MA2E montre la démo aux sociétaires curieux

#### Site MA2E
- Page d'accueil entièrement reprise avec un CTA principal « Inscrivez-vous maintenant »

#### Communiqué presse (optionnel)
- Communiqué à la presse économique CI : *« MA2E modernise l'adhésion mutualiste avec une plateforme digitale »*

### 📣 Vague 3 — J+30 : rappel et engagement

**Message clé** : « Vous n'êtes pas encore sociétaire ? **Ça prend 5 minutes, vraiment.** »

**Cible** : sociétaires potentiels qui n'ont **pas encore démarré** ou qui ont **abandonné en cours de parcours**.

**Canaux et messages-types** :

#### WhatsApp ciblé (pour les sociétaires non-inscrits)
```
Bonjour [PRENOM],

Vous n'avez pas encore rejoint MA2E ? C'est l'occasion 👇

📱 Envoyez « Bonjour » pour démarrer (5 min)
💻 https://app.ma2e.ci

Plus de 500 collègues l'ont déjà fait depuis le mois dernier.
Bénéficiez de la couverture santé groupe — c'est inclus dans votre statut.

— Équipe MA2E
```

#### WhatsApp ciblé (pour les sociétaires ayant abandonné en cours)
```
Bonjour [PRENOM],

Vous aviez commencé votre inscription MA2E. Il vous reste 2 minutes pour
la finaliser. Tapez « continuer » pour reprendre où vous vous étiez arrêté.

— Équipe MA2E
```

#### Email
- Témoignage d'un sociétaire récent (récolté à J+15) — humanise le message

#### Affichage agence (mise à jour)
- Compteur visible : *« Déjà X sociétaires inscrits en ligne ! »*

---

## 5. Plan de support post-lancement

### 5.1 Heures d'ouverture support humain (configurable dans settings)

- Lundi-Vendredi 8h-17h
- Pas de support week-end pour la Phase 2 (à étudier selon volume)

### 5.2 Cellule de gestion d'incident (J0 → J+14)

- **War-room Slack/Teams** dédiée : tous les acteurs MA2E + GS2E
- **Monitoring App Insights** ouvert en permanence
- **Page de statut publique** : status.ma2e.ci (V2)
- **Astreinte technique GS2E** : J0 → J+7 en 8h-22h

### 5.3 Tickets types de support N1 et N2

| Symptôme sociétaire | N1 (chefs agence MA2E) | N2 (DSI MA2E + GS2E) |
|---------------------|------------------------|---------------------|
| « L'assistante ne répond pas » | Vérifier que le numéro WhatsApp est bon, retry | Vérifier les logs Meta + restart pod si besoin |
| « OCR ne lit pas ma CNI » | Conseiller meilleure photo, lui montrer en agence | Vérifier les scores OCR moyens, contacter Mindee si dégradation |
| « Je n'ai pas reçu mon message de validation » | Vérifier statut sur le back-office | Webhook compta : vérifier la delivery dans l'historique |
| « Je n'arrive plus à me connecter » | Reset password (admin) | Si lockout : vérifier les échecs de login dans le journal d'audit |
| Demande de droits ARTCI | Transférer au DPO | DPO traite sous 30j max |

---

## 6. Risques et mitigation

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| **Mauvaise compréhension du parcours par les sociétaires** | Moyen | Élevé | Phase pilote 50 utilisateurs avant J0, ajustements |
| **Surcharge gestionnaires en début** | Élevé | Moyen | Renfort temporaire prévu J0 → J+14, file de priorisation |
| **Bug majeur en production** | Faible | Élevé | War-room J0+J+14, rollback procédure documentée (PROD_DEPLOYMENT §10) |
| **OCR Mindee dégrade qualité** | Faible | Moyen | Quota gestionnaires + alerte sur score OCR moyen < 70% |
| **Sociétaires inquiets pour leurs données** | Moyen | Faible | FAQ claire (cf. GUIDE_SOCIETAIRE §5), DPO disponible |
| **Refus syndical** | Faible | Élevé | Briefing préalable représentants du personnel J-30 |
| **Attaque externe (bruteforce, scraping)** | Faible | Élevé | Lockout login + WAF Front Door + rate-limiting + MFA admin obligatoire |

---

## 7. Budget conduite changement

| Poste | Estimation |
|-------|-----------|
| Formation gestionnaires (10 personnes × 0,5j × salaire chargé) | ~500 000 FCFA |
| Formation admins (3 personnes × 1j) | ~300 000 FCFA |
| Supports imprimés (guides + posters + tracts) | ~250 000 FCFA |
| Vague WhatsApp (Meta charges 0,02-0,05€/message) | ~150 000 FCFA |
| Renforts ponctuels gestionnaires J0 → J+14 | ~300 000 FCFA |
| Buffer imprévus (10%) | ~150 000 FCFA |
| **TOTAL** | **~1 650 000 FCFA (~2 500 €)** |

---

## 8. Comité de pilotage

### Cadence

- **Hebdo** (mardi 10h) jusqu'à J+30
- **Bi-mensuel** jusqu'à J+90
- **Mensuel** ensuite

### Composition

| Rôle | Nommé |
|------|-------|
| Sponsor | DG MA2E |
| Chef de projet métier | DRH MA2E |
| Chef de projet technique | DSI MA2E |
| DPO | DPO MA2E |
| Comm | Resp. Comm MA2E |
| Éditeur | Abdoul OUATTARA (GS2E) |
| User experts | 2 gestionnaires + 2 sociétaires (panel) |

### Ordre du jour type

1. KPIs de la semaine (10 min)
2. Incidents et actions correctrices (10 min)
3. Retours utilisateurs (10 min)
4. Décisions à prendre (10 min)
5. Prochaines étapes (10 min)

---

## 9. Annexes

- [GUIDE_SOCIETAIRE.md](GUIDE_SOCIETAIRE.md) — Référence détaillée du parcours sociétaire
- [GUIDE_GESTIONNAIRE.md](GUIDE_GESTIONNAIRE.md) — Manuel back-office
- [PROD_DEPLOYMENT.md](PROD_DEPLOYMENT.md) — Procédures techniques de déploiement
- [PHASE2_ROADMAP.md](PHASE2_ROADMAP.md) — Roadmap des chapitres Phase 2
- [CVATL_SPEECH.md](CVATL_SPEECH.md) — Script présentation comité CVATL

---

_Document de référence — version 1.0 — 2026-06-15. Maintenu par l'équipe projet MA2E + GS2E._
