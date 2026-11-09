# Guide gestionnaire MA2E — Back-office d'identification

> **Pour les gestionnaires, administrateurs et DPO MA2E utilisant la plateforme digitale d'identification.**
> Version 1.0 — 2026-06-15.

---

## En une page

| Vous êtes… | Vos droits dans le back-office |
|------------|-------------------------------|
| **Gestionnaire** (rôle `agent`) | Voir et traiter les dossiers, demander des compléments, valider/refuser |
| **Administrateur tenant** (`tenant_admin`) | Tout ce qu'un gestionnaire fait, **plus** : paramètres, utilisateurs, templates, sécurité, intégrations |
| **Super-admin GS2E** (`super_admin`) | Tout ce qu'un admin fait, **plus** : créer d'autres tenants, basculer entre tenants |

URL du back-office : **[https://admin.ma2e.ci](https://admin.ma2e.ci)** (production) ou indiquée par votre administrateur.

---

## 1. Première connexion

### 1.1 Recevoir ses identifiants

Votre administrateur MA2E vous crée un compte (page **Paramètres → Utilisateurs**) avec :
- Votre **email professionnel** (identifiant unique)
- Un **mot de passe initial** (à changer dès la première connexion)
- Un **rôle** (`agent`, `tenant_admin` ou `super_admin`)

Vous recevez les identifiants **hors-ligne** (oralement, message sécurisé interne) — pas par email pour la sécurité.

### 1.2 Se connecter

1. Ouvrez **[https://admin.ma2e.ci](https://admin.ma2e.ci)**
2. Saisissez votre email + mot de passe initial
3. Cliquez sur **« Se connecter »**

Si votre administrateur a activé l'option « changement obligatoire au premier login » (à venir), vous serez redirigé vers le formulaire de changement de mot de passe.

### 1.3 Activer le MFA — OBLIGATOIRE pour les admins

**Pour les rôles `tenant_admin` et `super_admin`, l'activation du MFA est obligatoire** sous 7 jours après la création du compte.

1. Dans la sidebar, cliquez **Paramètres → Mon MFA**
2. Cliquez **« Activer le MFA »**
3. Installez sur votre téléphone l'une des applications suivantes :
   - **Google Authenticator** (Android / iOS)
   - **Microsoft Authenticator** (Android / iOS / Windows)
   - **Authy** (multi-plateforme)
4. Scannez le QR code affiché. Si vous ne pouvez pas scanner, saisissez la **clé manuellement**.
5. Saisissez le code à 6 chiffres affiché dans votre application
6. Cliquez **« Activer »**

À partir de maintenant, **chaque connexion** demandera votre mot de passe **PUIS** ce code à 6 chiffres.

> 🆘 **Vous avez perdu votre téléphone ?**
> Contactez votre administrateur MA2E. Il a la possibilité de **forcer la désactivation** de votre MFA (en engageant sa responsabilité — c'est audité). Vous pourrez ensuite le réactiver sur votre nouveau téléphone.

### 1.4 Changer son mot de passe

Pour des raisons de sécurité, faites-le dès la première connexion :

1. Cliquez sur votre nom en bas à gauche de la sidebar
2. Sélectionnez **« Changer mon mot de passe »** (à venir : pour l'instant via API, demandez à votre admin)
3. Saisissez votre mot de passe actuel + nouveau mot de passe

**Politique de mots de passe** (configurée par l'admin MA2E dans **Paramètres → Sécurité**) :
- Minimum **8 caractères** (12 recommandés pour les admins)
- Au moins **1 majuscule**
- Au moins **1 chiffre**
- Au moins **1 caractère spécial** (`!@#$%^&*...`)

---

## 2. Traiter un dossier sociétaire

C'est l'écran central pour un gestionnaire. **Sidebar → Espace de travail → Dossiers**.

### 2.1 Vue d'ensemble

La page liste tous les dossiers du tenant courant avec :
- **Numéro de dossier** (DOS-AAAA-NNNNN)
- **Statut** (en cours, soumis, en validation, validé, refusé, complément requis)
- **Nom du sociétaire** (extrait de la CNI)
- **Matricule + employeur**
- **Date de soumission**

Vous pouvez **filtrer par statut** via le sélecteur en haut. Les dossiers **soumis** sont ceux en attente de votre revue — c'est votre file de travail.

### 2.2 Examiner un dossier

Cliquez sur une ligne. Vous arrivez sur la **page détail** qui affiche :

1. **L'identité** extraite par OCR : nom, prénoms, date de naissance, numéro CNI, lieu de naissance
2. **Les photos** recto et verso de la CNI (cliquables pour agrandir)
3. **Le score OCR** : indique le niveau de confiance de la reconnaissance (vert ≥ 80%, orange 50-80%, rouge < 50%)
4. **Les corrections du sociétaire** : si le sociétaire a corrigé certaines lignes, elles sont signalées
5. **Les données pro** : fonction, ancienneté, situation familiale, ayants droit
6. **Le matricule + employeur**
7. **L'historique des consentements** (ARTCI art.4 : preuve cryptographique)

### 2.3 Prendre une décision

Trois actions possibles :

#### ✅ Valider (bouton vert)
- Clique sur **« Valider »**
- Le sociétaire est notifié immédiatement sur son canal (WhatsApp ou web)
- Le webhook compta est automatiquement déclenché (si configuré)
- Le dossier passe au statut **validé**

#### ❌ Refuser (bouton rouge)
- Clique sur **« Refuser »**
- Une fenêtre vous demande le **motif** (obligatoire, sera transmis au sociétaire)
- Choisissez un motif type ou rédigez librement
- Le sociétaire reçoit la notification + motif

#### ⚠️ Demander un complément (bouton ambre)
- Clique sur **« Demander un complément »**
- Rédigez ce qui manque (exemple : *« Photo verso de la CNI illisible, merci de la reprendre »*)
- Le sociétaire reçoit votre demande
- Il peut directement répondre dans son canal — sa réponse arrive en conversation

### 2.4 Bonnes pratiques

✅ **Examinez 2-3 dossiers à la suite** plutôt qu'un par jour : le contexte se garde mieux.

✅ **Si l'OCR a un score < 70%, vérifiez visuellement** ligne par ligne sur la photo, pas seulement les données extraites.

✅ **Soyez bienveillant dans les motifs de refus** : le sociétaire le lit. *« Photo CNI trop floue »* est mieux que *« document non conforme »*.

✅ **Demandez un complément plutôt que de refuser** si le problème est mineur (mauvaise photo, donnée à confirmer). Le refus définitif est rare en pratique.

❌ **NE TÉLÉCHARGEZ JAMAIS** une photo de CNI sur votre poste local. Tout reste dans la plateforme (loi ARTCI art.32).

❌ **NE COMMUNIQUEZ JAMAIS** d'information sociétaire par email perso, WhatsApp perso, etc. Le canal officiel passe par la plateforme.

---

## 3. Page d'accueil — Reporting & KPIs

Avant chaque demi-journée, jetez un œil à la page **Reporting** (sidebar → Reporting). Elle vous donne :

- **Combien de dossiers** sont à traiter
- **Temps moyen** de validation (cible : ≤ 24h ouvrées)
- **Taux de validation** (cible : > 85%)
- **Top 5 motifs de refus** : si un motif revient souvent, il faut peut-être améliorer l'amont (FAQ sociétaire, paramétrage IA…)
- **Performance de chaque gestionnaire** (90 derniers jours)

### Indicateurs à surveiller (rôle admin)

| KPI | Cible | Alerte si… |
|-----|-------|-----------|
| Taux de validation | > 85% | < 75% → revoir la qualité OCR / formation gestionnaires |
| Temps moyen validation | ≤ 24h | > 48h → file trop chargée, ajouter un gestionnaire |
| Auto-complétion | > 70% | < 50% → trop de compléments demandés, simplifier le parcours |
| Score OCR moyen | > 80% | < 70% → conseiller aux sociétaires de meilleures photos |
| Taux de complétion (parcours) | > 60% | < 40% → friction dans le parcours sociétaire |

---

## 4. Paramétrage (rôle `tenant_admin` ou `super_admin`)

### 4.1 Paramètres généraux (`Paramètres → Paramètres généraux`)

- **Nom de l'assistante** : nom affiché aux sociétaires (« MA2E Assistant » par défaut)
- **Email et téléphone de support**
- **Politique OTP** : tentatives max, durée de validité
- **Délais** : complément, escalade vers conseiller

### 4.2 Paramétrage IA (`Paramètres → Intelligence artificielle`)

C'est ici qu'on pilote le moteur conversationnel :

- **Modèle LLM** : par défaut `llama-3.3-70b-versatile`. Changez en `mixtral` si vous voulez tester un autre comportement.
- **Température** : 0.3 par défaut (factuel). Mettez 0.7 pour des réponses plus naturelles si l'assistante semble robotique.
- **Persona** : c'est **le texte le plus important**. Il définit le ton, les règles de comportement et la mission de l'assistante. À ajuster en équipe MA2E (marketing + DPO).
- **Message de repli** : quand l'IA n'est pas sûre, elle envoie ce message au lieu d'halluciner.

### 4.3 Templates de messages (`Paramètres → Templates de messages`)

12 templates en français personnalisables :
- Onboarding (accueil, demande matricule, demande CNI, confirmation…)
- Validation (dossier validé, refusé, complément requis)
- Erreurs et escalade vers un agent humain

**Comment éditer** :
1. Cliquez sur le template à modifier dans la liste à gauche
2. Modifiez le contenu — les variables en jaune (`{matricule}`, `{numero_dossier}`) sont **obligatoires** et doivent rester
3. L'**aperçu WhatsApp à droite** se met à jour en direct avec des données d'exemple
4. Cliquez **« Enregistrer »**

Toute modification est versionnée et auditée — vous pouvez voir l'historique.

### 4.4 Base de connaissances (`Paramètres → Base de connaissances`)

L'assistante répond aux questions sociétaires en se basant sur le contenu du site MA2E. Pour mettre à jour :

1. Saisissez l'URL à scrapper (ex. https://www.ma2e.ci/)
2. Choisissez le nombre max de pages
3. Cliquez **« Lancer l'ingestion »**
4. Suivez le log en temps réel — chaque page est vectorisée (1536 dimensions)

**Quand le faire ?** À chaque mise à jour majeure du site MA2E (nouveau produit d'épargne, modification des conditions, etc.).

### 4.5 Employeurs (`Paramètres → Employeurs`)

Liste des sociétés du périmètre (CIE, SODECI, ERANOVE). Si MA2E ouvre à de nouvelles entités du groupe, ajoutez-les ici.

### 4.6 Utilisateurs (`Paramètres → Utilisateurs`)

Gestion des comptes back-office :
- **Créer** : bouton « Nouvel utilisateur » → email + nom + rôle + mot de passe initial
- **Modifier le rôle** : select inline sur la ligne
- **Désactiver** : icône X (le compte est conservé pour l'historique, mais ne peut plus se connecter)
- **Reset password** : icône cadenas → fenêtre nouveau mot de passe

**Vous ne pouvez ni modifier votre propre rôle ni vous désactiver vous-même.** C'est volontaire (protection anti-lockout).

### 4.7 Sécurité & ARTCI (`Paramètres → Sécurité & ARTCI`)

Politique de sécurité du tenant :
- **Mots de passe** : longueur min, exigences caractère
- **Sessions** : échecs avant verrouillage, durée verrouillage, inactivité max
- **Rétention ARTCI** : durée de conservation (5 ans par défaut), grâce
- **DPO** : email + délai de réponse

Le **tableau de bord rétention** liste les dossiers éligibles à la purge selon la politique courante. L'exécution effective sera automatisée en Phase B.

### 4.8 Intégrations (`Paramètres → Intégrations`)

#### Référentiel agents
- **Source** : `none` (par défaut), `csv` (statique) ou `http` (API distante CIE/SODECI/ERANOVE)
- **Mode strict** : si activé, un matricule inconnu envoie le dossier en revue manuelle
- **Testeur** : saisissez un (employeur, matricule) pour vérifier la réponse en direct

#### Webhook compta
- **URL** : endpoint qui sera appelé en POST quand un dossier est validé
- **Secret HMAC** : signature SHA-256 dans `X-MA2E-Signature` (vérifiez-la côté receveur)
- **Événements** : `validated` (par défaut), `decided` (val + refus), `all`
- **Test** : bouton qui envoie un événement de test pour valider la config
- **Historique** : tableau des envois avec statut, retry possible sur les échecs

---

## 5. Conformité ARTCI — Vos obligations

### 5.1 Demandes de droits sociétaires

Un sociétaire peut exercer ses droits ARTCI à tout moment (articles 18 à 22) :

| Droit | Comment le sociétaire le demande | Que faire en tant que MA2E |
|-------|----------------------------------|----------------------------|
| Droit d'accès (art.18) | « mes données » sur WhatsApp/web | Exporter le dossier en JSON via `Dossier → Export RGPD` |
| Droit de rectification (art.19) | « corriger mes données » | Le sociétaire édite directement, sinon vous ajustez via le dossier |
| Droit à l'effacement (art.21) | « supprimer mon dossier » | Le DPO doit répondre sous 30 jours et procéder à l'anonymisation |
| Droit d'opposition (art.22) | « retirer mon consentement » | Le sociétaire est sorti des traitements marketing/communication |

**Délai légal de réponse : 30 jours** (prolongeable à 60 sur justification).

### 5.2 Audit log

Toutes les opérations sensibles sont tracées (création dossier, validation, refus, export RGPD, modification settings, MFA…). Pour consulter :

**Sidebar → Conformité ARTCI → Journal d'audit**

Les logs sont **append-only** et chaînés cryptographiquement (chaque ligne contient le hash de la précédente — toute altération est détectable).

### 5.3 Notification de violation

En cas de **violation de données suspectée** (fuite, accès non autorisé, perte de pièce d'identité…), vous DEVEZ :

1. **Sous 24h** : alerter le DPO MA2E (dpo@ma2e.ci) et votre administrateur tenant
2. **Sous 72h** : si la violation est confirmée, MA2E notifie l'ARTCI (procédure DPO)
3. **Document** ce qui s'est passé : qui, quand, quoi, ampleur, mesures prises

---

## 6. Support & escalade

### Niveau 1 — Self-service
- FAQ et procédures dans ce document
- Documentation en ligne sur le wiki interne MA2E

### Niveau 2 — Support technique interne
- Email : **it-support@ma2e.ci**
- Heures : Lundi-Vendredi 8h-17h
- Délai cible : < 4h ouvrées

### Niveau 3 — Éditeur (GS2E)
- En cas de bug bloquant ou de fonctionnalité non couverte
- Délai cible : < 24h sur bloquant, < 5 jours sur amélioration

---

## 7. Glossaire express

| Terme | Définition |
|-------|------------|
| **ARTCI** | Autorité de Régulation des Télécommunications de Côte d'Ivoire (autorité de protection des données) |
| **CNI** | Carte Nationale d'Identité ivoirienne |
| **DCP** | Données à Caractère Personnel (loi 2013-450) |
| **DPO** | Délégué à la Protection des Données |
| **MFA / 2FA** | Multi-Factor Authentication — double authentification |
| **MRZ** | Machine Readable Zone — bande ICAO en bas de la CNI verso |
| **OCR** | Optical Character Recognition — lecture automatique de la CNI |
| **OTP** | One-Time Password — code à usage unique envoyé par email |
| **RAG** | Retrieval-Augmented Generation — l'IA cherche dans la base avant de répondre |
| **Tenant** | Une entité utilisatrice de la plateforme (MA2E aujourd'hui, CIE et SODECI demain) |
| **WhatsApp Cloud API** | API officielle Meta pour échanger sur WhatsApp |

---

_Document de référence — version 1.0 — 2026-06-15. Maintenu par GS2E._
