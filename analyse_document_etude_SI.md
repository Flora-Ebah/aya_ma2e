# 📋 Analyse — Document ETUDE SI : Ce que MA2E doit remplir

> **Document source** : `MA2E_Document Etude SI_ Plateforme Digitale Didentification_10072026.docx`  
> **Date d'analyse** : 15 juillet 2026  
> **Préparé pour** : Flora (équipe MA2E / GS2E — DAPSI)

---

## 🗺️ Vue d'ensemble du document

Le document est organisé en **17 chapitres** (~400 sections). Chaque chapitre indique en titre **quelle équipe doit le remplir**. Les sections qui concernent **MA2E** sont :

| Chapitre | Intitulé | Responsable(s) indiqué(s) |
|---|---|---|
| 1 | Résumé exécutif | **MA2E** |
| 2 | Présentation maître d'ouvrage | **MA2E** |
| 3 | Analyse de l'existant | **MA2E** |
| 4 | Objectifs du projet | **MA2E** |
| 5 | Périmètre du projet | **MA2E + AMOA + DCP + SDSO** |
| 6 | Bénéfices du KYC | **MA2E** |
| 7 | Processus cible KYC digital | **MA2E + DDI + AMOA** |
| 8 | Exigences fonctionnelles détaillées | **DDI + AMOA + MA2E** |
| 9 | Exigences non fonctionnelles | DPI (pas MA2E) |
| 10 | Architecture SI cible | LEAD ARCHITECT + DIT + DPI + AMOA |
| 11 | Sécurité et conformité | DCP / SSI / SDSO + DIT |
| 12 | Gouvernance IA, OCR et RAG | **DDI + MA2E + AMOA** |
| 13 | Intégrations SI | DDI + CAGECFI + DIT + Data Factory |
| 14 | Organisation projet | CP + PMO |
| 15 | Planning | Équipe projet + PMO |
| 16 | Gestion des risques | Équipe projet + PMO |
| 17 | Stratégie de recette | **Équipe projet + Sponsor** |

> [!IMPORTANT]
> Les chapitres **1, 2, 3, 4, 6, 7** sont **exclusivement de la responsabilité MA2E** (métier + contexte). Les chapitres **5, 8, 12** sont co-pilotés. Votre cheffe a raison de vouloir faire un point.

---

## 📝 Détail section par section — Ce que MA2E doit fournir

---

### Chapitre 1 — Résumé exécutif *(MA2E)*

Ces sections sont **vides dans le document actuel** — c'est ce que MA2E doit rédiger en premier car elles donnent le ton à tout le document.

| Section | Statut | Ce qu'on a déjà / Ce qu'il faut produire |
|---|---|---|
| 1.1 Contexte général | ✅ Base disponible | Le projet est décrit dans `CVATL_SPEECH.md` et `MA2E_Cahier_des_Charges_v1.docx`. Reprendre : procédure papier → digital, canal WhatsApp + web, groupes CIE/SODECI/SMB. |
| 1.2 Problématique actuelle | ⚡ À rédiger | Lister formellement : délais longs d'enrôlement, erreurs/incomplétude des dossiers, traçabilité limitée, absence de reporting consolidé. |
| 1.3 Vision cible | ✅ Base disponible | « Identification en < 10 min sur WhatsApp, 100% conforme ARTCI loi 2013-450. » |
| 1.4 Objectifs stratégiques | ⚡ À rédiger | Digitalisation KYC, traçabilité, conformité ARTCI, reporting C-Level. |
| 1.5 Bénéfices attendus | ✅ Base disponible | Chapitre 6 du document + `CVATL_SPEECH_ARCHITECTURE.md` (cheat sheet). |
| 1.6 Synthèse des risques majeurs | ⚡ À rédiger | À co-remplir avec PMO — liste dans `AUDIT_BACKLOG.md`. |
| 1.7 Décisions attendues du COPIL | ❓ MA2E métier | Question à poser à votre cheffe : quelles décisions d'arbitrage attendre du comité ? |

---

### Chapitre 2 — Présentation du maître d'ouvrage *(MA2E)*

> [!CAUTION]
> Ce chapitre est **entièrement vide** dans le document. Il s'agit d'informations purement **métier MA2E** — Flora ou sa cheffe doivent les fournir.

| Section | Ce qu'il faut écrire |
|---|---|
| 2.1 Présentation de MA2E | Qui est la MA2E ? Statut juridique, tutelle, date de création, effectifs, missions principales. |
| 2.2 Présentation des sociétaires | Qui sont-ils ? Employés actifs CIE, SODECI, SMB. Effectifs estimés (pour dimensionnement). |
| 2.3 Services proposés | Épargne, crédit, dépôt, retrait — décrire chaque service brièvement. |
| 2.4 Organisation actuelle des opérations | Organigramme ou description des directions impliquées dans l'enrôlement. |
| 2.5 Parties prenantes internes/externes | Listez : MA2E (métier), GS2E DAPSI (IT), ERANOVE AD, ARTCI, sociétaires. |
| 2.6 Contraintes secteur microfinance | Contraintes BCEAO, normes mutuelles, etc. |
| 2.7 Enjeux KYC digitalisation | Pourquoi digitaliser le KYC est stratégique pour MA2E. |

---

### Chapitre 3 — Analyse de l'existant *(MA2E)*

> [!CAUTION]
> Ce chapitre est **entièrement vide**. Ce sont des informations que seul le métier MA2E peut fournir — c'est la description de **comment ça se passe aujourd'hui avant le projet**.

| Section | Ce qu'il faut écrire |
|---|---|
| 3.1 Processus actuel d'identification | Comment un sociétaire est-il identifié aujourd'hui ? (formulaire papier, agence, etc.) |
| 3.2 Processus actuel d'enrôlement | Étapes de l'ouverture d'un compte sociétaire aujourd'hui. |
| 3.3 Processus actuel de demande de crédit | Comment une demande de crédit est instruite aujourd'hui. |
| 3.4 Processus actuel de validation back-office | Comment les agents valident-ils les dossiers papier ? |
| 3.5 Processus actuel de reporting | Comment le reporting est-il fait aujourd'hui ? (Excel, manuel ?) |
| 3.6 Transmission vers paie ou core banking | Le process actuel de transmission des données vers les systèmes de paie. |
| 3.7 Outils actuellement utilisés | Listez tous les outils SI actuels (logiciels, tableurs, ERP…). |
| 3.8 Volumétrie actuelle | Nombre de sociétaires actifs, nombre d'enrôlements par mois, nombre d'agents. |
| 3.9 Difficultés opérationnelles | Ce qui ne marche pas bien aujourd'hui (délais, erreurs, ressaisies…). |
| 3.10 Irritants utilisateurs | Ce que les agents et sociétaires trouvent pénible dans le processus actuel. |
| 3.11 Limites SI et IT | Limitations techniques des outils actuels. |
| 3.12 Synthèse des écarts | Tableau comparatif existant vs. cible. |

---

### Chapitre 4 — Objectifs du projet *(MA2E)*

> [!NOTE]
> On dispose d'éléments dans `MA2E_Cahier_des_Charges_v1.docx` et `CVATL_SPEECH.md`. À formaliser dans le document ETUDE SI.

| Section | Statut | Source disponible |
|---|---|---|
| 4.1 Objectifs business | ⚡ À formaliser | Réduction des délais d'enrôlement, digitalisation KYC. |
| 4.2 Objectifs opérationnels | ⚡ À formaliser | > 70% d'automatisation du parcours, SLA agent 24h. |
| 4.3 Objectifs réglementaires | ⚡ À formaliser | Conformité BCEAO + ARTCI loi 2013-450. |
| 4.4 Objectifs SI / IT | ✅ Disponible | Architecture FastAPI + PostgreSQL + Azure déjà documentée dans `CVATL_SPEECH_ARCHITECTURE.md`. |
| 4.5 Objectifs sécurité | ✅ Disponible | Chiffrement au repos/transit, audit log immuable, MFA agents. |
| 4.6 Objectifs conformité ARTCI | ⚡ À détailler | Consentement explicite, minimisation données, droit à l'oubli. |
| 4.7 Objectifs UX | ✅ Disponible | < 10 min via WhatsApp ou web, zéro app à installer. |
| 4.8 Objectifs de performance | ✅ Disponible | 300 req/min API, RPO 5 min, RTO 30 min, disponibilité cible. |
| 4.9 Objectifs reporting C-Level | ⚡ À préciser | KPI enrôlement, taux validation, taux rejet — à valider avec DG MA2E. |

---

### Chapitre 5 — Périmètre du projet *(MA2E + AMOA + DCP + SDSO)*

| Section | Statut | Notes |
|---|---|---|
| 5.1.1 Enrôlement digital | ✅ Implémenté | Parcours WhatsApp + Web complet dans le backend (`/webhooks`, `/dossiers`). |
| 5.1.2 KYC client | ✅ Implémenté | Module `dossiers` + `collaborateurs` dans le backend. |
| 5.1.3 OCR CNI | ✅ Implémenté | Azure AI Vision + fallback OCR.space. À décrire dans le document. |
| 5.1.4 Consentements électroniques | ✅ Implémenté | Consentement ARTCI intégré dans le workflow. |
| 5.1.5 Assistant virtuel | ✅ Implémenté | Module `knowledge` + LLM dans le backend. |
| 5.1.6 Demande de crédit | ❓ À clarifier | Non visible dans le backend actuel — hors scope MVP ? |
| 5.1.7 Back-office agent | ✅ Implémenté | Frontend Next.js avec validation dossiers. |
| 5.1.8 Reporting et exports | ✅ Implémenté | Module `stats` + `imports` dans le backend. |
| 5.1.9 Journal d'audit | ✅ Implémenté | Module `audit` dans le backend, append-only. |
| 5.1.10 Administration multi-tenant | ✅ Implémenté | Module `roles` + `settings` + `users`. |
| 5.2 Périmètre technique | ✅ Disponible | `CVATL_SPEECH_ARCHITECTURE.md` + `MA2E_Architecture_Technique_v1.docx`. |
| 5.7 Hors périmètre | ⚡ À lister | Ex. : core banking, paie des sociétés membres (phase 2). |

---

### Chapitre 6 — Bénéfices du KYC *(MA2E)*

✅ **Ce chapitre peut être rempli rapidement** à partir du `CVATL_SPEECH_ARCHITECTURE.md`.

Éléments disponibles par section :

- **Avantages réglementaires** : Conformité ARTCI loi 2013-450, traçabilité pour audit CNDP.
- **Avantages opérationnels** : > 70% automatisation, délai réduit de 2 semaines à < 10 min.
- **Avantages commerciaux** : Enrôlement à distance, zéro déplacement en agence.
- **Avantages risques & crédit** : Score OCR, détection doublons automatique.
- **Avantages technologiques** : Scalabilité Docker, fallback OCR, IA conversationnelle.
- **Avantages pour les sociétaires** : Autonomie WhatsApp / web, notification à chaque étape.
- **Avantages pour les agents back-office** : Interface unifiée, SLA 24h, alertes automatiques.
- **Avantages pour la DG** : Dashboard KPI temps réel, exports CSV/XLSX.
- **Avantages pour l'audit** : Journal immuable, preuve cryptographique du consentement.
- **Synthèse des gains** : Chiffres clés déjà dans la cheat sheet de `CVATL_SPEECH_ARCHITECTURE.md`.

---

### Chapitre 7 — Processus cible KYC digital *(MA2E + DDI + AMOA)*

✅ **Les 14 étapes du processus sont déjà documentées** dans `CVATL_SPEECH.md` et la présentation CVATL.

| Étape | Ce qu'implémente le projet |
|---|---|
| 1. Accueil et choix du canal | WhatsApp webhook + Web chat |
| 2. Information et consentement initial | Notice ARTCI servie par le bot |
| 3. Collecte données personnelles | Formulaire guidé par le bot conversationnel |
| 4. Collecte données professionnelles | Matricule employeur + société du groupe |
| 5. Capture CNI recto/verso | Upload depuis WhatsApp ou interface web |
| 6. OCR et extraction automatique | Azure AI Vision + correction auto |
| 7. Validation/correction des données | Interface de confirmation côté sociétaire |
| 8. Consentement final | Signature électronique ARTCI |
| 9. Soumission du dossier | `POST /dossiers` dans l'API |
| 10. Traitement back-office | Interface agent — module `dossiers` |
| 11. Validation / rejet / complément | Workflow 3 issues dans le back-office |
| 12. Export / intégration SI | Export CSV/XLSX, API vers SI RH |
| 13. Archivage et journal d'audit | Module `audit`, logs append-only |
| 14. Mise à jour périodique KYC | Module `workflows` — re-identification |

---

### Chapitre 8 — Exigences fonctionnelles détaillées *(DDI + AMOA + MA2E)*

> [!NOTE]
> Ce chapitre est co-piloté. MA2E doit surtout **valider** les exigences rédigées par DDI/AMOA et **compléter** celles qui concernent les processus métier.

Les modules déjà implémentés dans votre projet (à confirmer dans le document) :

| Module | Statut backend | API Route |
|---|---|---|
| Canal WhatsApp | ✅ | `/webhooks/whatsapp` |
| Portail web / web chat | ✅ | `/webhooks/web` |
| Assistant virtuel / base de connaissances | ✅ | `/knowledge` |
| OCR CNI | ✅ | Service Azure AI Vision |
| Consentement ARTCI | ✅ | Intégré dans le workflow `dossiers` |
| Formulaire KYC | ✅ | Module `dossiers` |
| Demande de crédit | ❓ | Non visible dans le backend actuel |
| Gestion des pièces justificatives | ✅ | Azure Blob Storage |
| Back-office agent | ✅ | Frontend Next.js |
| Workflow de validation | ✅ | Module `workflows` |
| Gestion des rôles et habilitations | ✅ | Module `roles` |
| Reporting opérationnel | ✅ | Module `stats` |
| Export CSV / XLSX | ✅ | Module `imports` |
| Journal d'audit | ✅ | Module `audit` |
| Administration multi-tenant | ✅ | Module `settings` + `users` |

---

### Chapitre 12 — Gouvernance IA, OCR et RAG *(DDI + MA2E + AMOA)*

✅ **Ce chapitre peut être rempli depuis `CVATL_SPEECH_ARCHITECTURE.md`** (page 18, DCP).

| Section | Éléments disponibles |
|---|---|
| Objectifs de l'assistant virtuel | Guidage du sociétaire, réponses aux FAQ, escalade vers agent humain. |
| Rôle de l'IA dans le parcours KYC | Extraction OCR, conversation guidée, détection d'anomalies. |
| Limites fonctionnelles de l'IA | Ne prend pas de décision finale — agent humain obligatoire pour validation. |
| Données autorisées / interdites | Seules les photos CNI transmises à Azure — pas nom/matricule/téléphone. |
| Gestion des hallucinations | RAG avec sources documentaires — validation par sources avant réponse. |
| Garde-fous anti-prompt injection | À documenter avec DDI. |
| Seuils de confiance OCR | Score de confiance Azure AI Vision — si < seuil, escalade vers agent. |
| Traitement des erreurs OCR | Étape 7 de correction par le sociétaire avant soumission. |
| Procédure d'escalade agent humain | Décrit dans `CVATL_SPEECH.md`. |
| KPI IA et OCR | Taux de reconnaissance CNI, taux d'escalade, temps de traitement OCR. |

---

## 🎯 Plan d'action recommandé pour le point avec votre cheffe

### Priorité 1 — À faire avant le point (informations purement métier MA2E)

- [ ] **Chapitre 2** : Fiche de présentation MA2E (statut, effectifs, services, organisation)
- [ ] **Chapitre 3** : Description du processus actuel (papier, délais, volumes, outils)
- [ ] **Volumétrie actuelle** : Combien de sociétaires actifs ? Combien d'enrôlements / mois ?

### Priorité 2 — À co-remplir lors du point avec DDI/AMOA

- [ ] **Chapitre 1** : Résumé exécutif (validation des messages clés)
- [ ] **Chapitre 4** : Objectifs formalisés (business, réglementaires, SI)
- [ ] **Chapitre 5.7** : Ce qui est hors périmètre (demande de crédit, core banking ?)
- [ ] **Chapitre 8** : Valider les exigences fonctionnelles par module

### Priorité 3 — Apporter les livrables existants comme sources

Les documents suivants sont à **partager directement avec DAPSI au point** :

| Livrable | Utilité pour le document |
|---|---|
| [`CVATL_SPEECH_ARCHITECTURE.md`](file:///c:/Users/LENOVO/Desktop/PROJET/GS2E/virtual-ai/MA2E_Livrables/CVATL_SPEECH_ARCHITECTURE.md) | Chiffres clés, architecture, DCP — chapitres 7, 9, 10, 12 |
| [`MA2E_Architecture_Technique_v1.docx`](file:///c:/Users/LENOVO/Desktop/PROJET/GS2E/virtual-ai/MA2E_Livrables/MA2E_Architecture_Technique_v1.docx) | Chapitre 10 (Architecture SI cible) |
| [`MA2E_Architecture_Deploiement_v1.docx`](file:///c:/Users/LENOVO/Desktop/PROJET/GS2E/virtual-ai/MA2E_Livrables/MA2E_Architecture_Deploiement_v1.docx) | Chapitre 10 (déploiement) |
| [`MA2E_Plan_de_Tests_v1.docx`](file:///c:/Users/LENOVO/Desktop/PROJET/GS2E/virtual-ai/MA2E_Livrables/MA2E_Plan_de_Tests_v1.docx) | Chapitre 17 (stratégie de recette) |
| [`MA2E_Cahier_des_Charges_v1.docx`](file:///c:/Users/LENOVO/Desktop/PROJET/GS2E/virtual-ai/MA2E_Livrables/MA2E_Cahier_des_Charges_v1.docx) | Chapitres 1, 4, 5 |
| [`PLAN_CONDUITE_CHANGEMENT.md`](file:///c:/Users/LENOVO/Desktop/PROJET/GS2E/virtual-ai/MA2E_Livrables/PLAN_CONDUITE_CHANGEMENT.md) | Chapitre 15 (conduite du changement) |

---

## ⚠️ Point d'attention important

> [!WARNING]
> La **demande de crédit (section 5.1.6 et module 8.6)** est listée dans le périmètre mais **n'est pas visible dans le backend actuel**. Il faut clarifier avec votre cheffe si c'est :
> - Hors périmètre MVP (à déclarer dans la section 5.7)
> - Dans le planning V2 (à documenter dans le chapitre 15)
> - Une lacune à combler (besoin de développement)

> [!NOTE]
> Les chapitres **9 (Exigences non fonctionnelles)**, **10 (Architecture SI)**, **11 (Sécurité)**, **13 (Intégrations)**, **14 (Organisation)**, **15 (Planning)**, **16 (Risques)** sont à la charge de **DPI, DDI, AMOA et le CP** — vous n'avez pas à les rédiger, mais vous pouvez fournir les livrables du projet comme base documentaire.
