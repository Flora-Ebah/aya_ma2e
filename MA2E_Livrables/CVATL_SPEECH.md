# MA2E — Script de présentation CVATL (slide par slide)

> **Document de support** pour la présentation du CVATL le **08 juin 2026**.
> Pour chaque slide : **ce qu'il faut dire** + **questions pièges anticipées** + **réponses prêtes**.
>
> Conseil global : ne pas lire mot à mot. Garder le timing total à **~30 min** + **15 min Q&A**.

---

## ⏱️ Plan de timing

| Slides | Durée cible | Objectif |
|---|---|---|
| 1-3 | 1 min | Accroche + sommaire |
| 4-6 | 4 min | Contexte, enjeux, planning |
| 7-10 | 8 min | Architecture fonctionnelle + workflows + entités |
| 11-17 | 10 min | Architecture technique (le cœur du CVATL) |
| 18-21 | 4 min | Eco-conception + DCP + Sécurité |
| 22 | 1 min | Risques |
| 23-25 | 2 min | Démos |
| 26-27 | 1 min | Tests + Merci |

---

## SLIDE 1 — Page de garde

**À dire (10 sec)** :
> "Bonjour à tous, merci de votre présence. Je vais vous présenter la plateforme digitale d'identification des sociétaires de la **mutuelle MA2E**, projet conduit par GS2E pour le groupe ERANOVE. Présentation prévue en 30 minutes, suivie de vos questions."

---

## SLIDE 2 — "Innover Pour Mieux Servir"

**À dire (20 sec)** :
> "Le slogan résume notre ambition : **digitaliser l'expérience du sociétaire**, supprimer le papier, mais surtout **garantir un service conforme aux exigences ARTCI** de protection des données. C'est un projet à la fois technologique et conformité."

---

## SLIDE 3 — Sommaire

**À dire (15 sec)** :
> "On va dérouler 7 grandes parties : le contexte, l'architecture fonctionnelle, le top des workflows et entités, l'architecture logicielle et technique, l'éco-conception, la sécurité et conformité ARTCI, et enfin les risques et démos."

---

## SLIDE 4 — Présentation du projet (Contexte, Enjeux, Objectifs)

**À dire (90 sec)** :
> "**Contexte** : MA2E gère aujourd'hui ses adhésions au **format papier** — 35 minutes par dossier, 1 dossier sur 3 incomplet, traçabilité ARTCI inexistante.
>
> **Enjeux** : conformité légale loi 2013-450, expérience sociétaire moderne, préparation du scaling à toutes les filiales ERANOVE.
>
> **Objectifs mesurables** :
> - Délai d'enrôlement : **35 min → 10 min**
> - Taux de complétude : **67 % → 95 %**
> - Conformité ARTCI : **100 % des consentements tracés**
> - Adoption : **70 % minimum** des nouveaux sociétaires
> - Disponibilité : **99,5 % minimum**"

**Question piège** : *"35 min, c'est mesuré comment ?"*
> *"Mesure terrain réalisée sur 20 dossiers en agence en mai 2026. Source disponible en annexe."*

---

## SLIDE 5 — Type de projet

**À dire (30 sec)** :
> "C'est un projet de **transformation digitale métier**, pas une simple refonte technique. Il combine **chatbot conversationnel WhatsApp**, **OCR automatique de la CNI** et **assistant IA RAG** pour répondre aux questions des sociétaires. C'est innovant dans l'écosystème mutualiste ivoirien."

---

## SLIDE 6 — Étapes projet / Macro planning

**À dire (60 sec)** :
> "Le projet se déroule en **4 étapes** :
> 1. **04 juin** : remise du cahier des charges et du backlog produit (35 user stories réparties sur 2 sprints)
> 2. **04-08 juin** : préparation et passage au CVATL — c'est aujourd'hui
> 3. **À préciser** : recette métier avec les agents MA2E
> 4. **Début juillet** : déploiement en production
>
> On est dans une **dynamique sprint** — on a déjà 2 sprints planifiés sur juin avec **38 user stories** au total."

**Question piège** : *"Délai juin-juillet, c'est ambitieux ?"*
> *"Oui, c'est tendu mais réaliste — on a un POC fonctionnel validé. La Phase 2 (industrialisation) se fera après le passage au CVATL avec des sprints dédiés."*

---

## SLIDE 7 — Architecture fonctionnelle

**À dire (90 sec)** :
> "Vous voyez ici la **vue d'oiseau** de la plateforme : trois grands acteurs — **sociétaire**, **agent MA2E**, **administrateur** — qui interagissent via deux canaux principaux : **WhatsApp** et **Web Chat**.
>
> Toute la logique métier passe par un **backend FastAPI** qui orchestre :
> - L'**assistante virtuelle** conversationnelle
> - L'**OCR automatique** de la pièce d'identité
> - Les **3 portes de consentement ARTCI** (Gates HMAC-SHA256)
> - Le **back-office de validation**
> - Le **module de reporting** conformité
> - Le **journal d'audit** append-only avec hash chaîné"

**À pointer du doigt** : Les 3 acteurs à gauche, les 8 modules au centre, le journal d'audit qui traverse tout.

---

## SLIDE 8 — Évaluation PRI (matrice probabilité × impact)

**À dire (60 sec)** :
> "On a identifié **5 risques majeurs**. Le **top 3** est en bas du document — je le détaillerai plus tard.
>
> Ce qui ressort de la matrice :
> - Un risque **inévitable** : l'indisponibilité de WhatsApp Cloud API (dépendance Meta)
> - Un risque **maîtrisable** : la non-conformité ARTCI (avec un audit blanc + DPO)
> - Un risque **prévisible** : la faible adoption par les sociétaires retraités
>
> Pour chacun, on a une **mesure de mitigation** documentée."

---

## SLIDE 9 — TOP 3 des workflows (logigrammes BPMN)

**À dire (90 sec)** :
> "On a modélisé les **3 workflows critiques** en BPMN :
>
> 1. **Onboarding sociétaire** — du premier message WhatsApp jusqu'à la validation finale, en passant par les 3 Gates ARTCI et les 14 étapes de la machine à états.
>
> 2. **Validation dossier agent** — l'agent ouvre son tableau de bord, consulte les dossiers en attente, et peut soit valider, soit refuser avec motif obligatoire, soit demander un complément.
>
> 3. **Assistant IA + Escalade humaine** — le sociétaire pose une question, l'IA cherche dans la base de connaissances RAG, et soit elle répond directement, soit elle propose une escalade vers un conseiller humain."

**Question piège** : *"Pourquoi BPMN ?"*
> *"C'est le standard pour les processus métier transverses — ça permet aux non-techniques de comprendre, et aux développeurs d'implémenter une machine à états déterministe."*

---

## SLIDE 10 — TOP 5 des entités métier (MCD)

**À dire (60 sec)** :
> "Vous voyez ici les **5 entités principales** du modèle de données :
>
> 1. **sociétaires** — identité du sociétaire (matricule, CNI, infos perso)
> 2. **dossiers** — la demande d'enrôlement avec son cycle de vie
> 3. **utilisateurs** — les agents MA2E + admins
> 4. **employeurs** — sociétés affiliées (CIE, SODECI, SMB, etc.)
> 5. **conversations** — les échanges WhatsApp/Web
>
> Et 5 tables de référence : statuts + rôles + pièces d'identité chiffrées.
>
> Tout est en **PostgreSQL 16 avec extension pgvector** pour le RAG."

**Question piège** : *"Pourquoi pas MongoDB ou autre NoSQL ?"*
> *"Les données sont structurées et critiques (audit, conformité). PostgreSQL nous donne ACID, contraintes, audit automatique. pgvector nous évite d'ajouter une BD vectorielle séparée."*

---

## SLIDE 11 — Architecture Logicielle 1/2

**À dire (120 sec)** :
> "L'architecture est en **3 couches** strictement séparées :
>
> 1. **COUCHE PRÉSENTATION** (à gauche) : WhatsApp/Web Chat pour le sociétaire, Backoffice Next.js pour l'agent
>
> 2. **COUCHE API** (au milieu, en rouge) : FastAPI qui sert d'API unique et de gateway
>
> 3. **COUCHE BUSINESS** (au centre, en orange) : tous nos modules métier :
>    - Module Authentification (JWT + AD ERANOVE)
>    - Module Onboarding (la machine à états)
>    - Module Extraction CNI (OCR via Mindee/Azure AI)
>    - Module Assistant IA (RAG + Groq/Azure OpenAI)
>    - Module Validation Dossier
>    - Module Notifications
>    - Module Audit & Conformité
>
> À droite, les **services externes** : AD ERANOVE pour l'authentification, WhatsApp Cloud API, Azure AI OCR, Azure OpenAI pour les embeddings, et SMTP.
>
> En bas, la base de données : **PostgreSQL 16 + pgvector + Azure Blob Storage** pour les photos CNI chiffrées."

**Question piège** : *"Pourquoi pas un microservice séparé pour l'IA ?"*
> *"Pour le périmètre actuel — 200 utilisateurs simultanés — le coût de l'orchestration microservices dépasse le bénéfice. Le module IA est intégré dans le cluster FastAPI, ce qui simplifie le déploiement et garantit que les données ne quittent jamais le périmètre MA2E."*

---

## SLIDE 12 — Architecture Logicielle 2/2 (stack technique)

**À dire (60 sec)** :
> "Les versions précises :
>
> | Couche | Stack |
> |---|---|
> | **Frontend** | HTML5, CSS3, **TypeScript 5.6**, **Next.js 14.2**, Tailwind CSS 3.4 |
> | **Backend** | **Python 3.11**, **FastAPI 0.115**, SQLAlchemy 2.0, Alembic 1.14 |
> | **BD** | **PostgreSQL 16 + pgvector 0.3**, Redis 7 |
> | **Stockage** | **Azure Blob Storage** (cloud-managed, chiffré KMS) |
> | **IA** | Azure OpenAI (embeddings), Azure AI OCR, Groq (LLM) |
> | **Canaux** | WhatsApp Cloud API v18 (Meta) |
> | **Conteneurisation** | Docker 24, docker-compose |
>
> Tout est **conteneurisé**, donc portable Azure ou on-premise."

---

## SLIDE 13 — Architecture Technique 1/2

**À dire (120 sec)** :
> "Voici l'architecture technique côté **infrastructure** — c'est le **'comment ça tourne en production'**.
>
> Au centre, le **SITE DE PRODUCTION** (cadre pointillé bleu) avec :
>
> - **2 serveurs Web + Application** (numéro ①) — **2 instances en haute disponibilité**. Si l'un tombe, l'autre prend le relais sans interruption pour le sociétaire.
>
> - **2 bases PostgreSQL** : **Maître (②)** pour écriture/lecture, **Réplica (③)** synchronisé par réplication streaming pour la lecture seule et le PRA.
>
> - **1 Redis 7 (④)** pour le cache et les sessions JWT, accessible en TCP port 6379.
>
> - **1 Azure Blob Storage (⑤)** pour les photos CNI chiffrées au repos.
>
> Devant tout ça, un **Load Balancer** qui répartit le trafic HTTPS sur les 2 web servers.
>
> Le sociétaire ne voit que le LB, il ne touche jamais directement la BD."

**Légende numérotée à lire à voix haute** :
> "① Serveur Web + Application — Next.js + FastAPI, 2 instances HA
> ② Serveur BD Maître — PostgreSQL 16 + pgvector
> ③ Serveur BD Esclave — Réplica streaming
> ④ Redis 7 — Cache + Sessions
> ⑤ Azure Blob Storage — Stockage CNI chiffré"

**Question piège** : *"Et le PRA en cas de catastrophe ?"*
> *"Le réplica BD est sur une zone Azure différente. On a un RPO de 5 min et un RTO de 1h. Backups quotidiens + PITR 7 jours minimum."*

---

## SLIDE 14 — Architecture Technique 2/2 (zones réseau)

**À dire (150 sec)** :
> "Ce schéma montre les **3 zones de sécurité réseau** — c'est ce qui rassure la DSI et SecOp :
>
> **INTERNET** (gauche) : le sociétaire mobile envoie un message via WhatsApp. Ça arrive sur un **WAPI** (Web Application Firewall) qui filtre toutes les attaques classiques avant d'atteindre la DMZ.
>
> **DMZ** (centre) : zone exposée mais **protégée**. Elle contient le HAProxy et le **cluster API MA2E** — 2 instances FastAPI en HA. **Le cluster inclut nativement le module OCR et l'Assistant IA** — pas de microservice séparé, tout est dans le même code.
>
> **LOCAL** (droite) : zone **strictement interne**, inaccessible depuis Internet :
> - **Base de données MA2E** (PostgreSQL Maître + Réplica + Redis)
> - **Backoffice / Admin MA2E** où travaillent les agents et admins en local
>
> Les 5 flux numérotés :
> 1. Sociétaire → WAPI → HAProxy
> 2. API → BD (lecture)
> 3. BD → API (réponse)
> 4/5. API ↔ Backoffice / Admin"

**Question piège** : *"Pourquoi pas une zone séparée pour la BD ?"*
> *"C'est le rôle du LOCAL. La BD n'est joignable QUE par les serveurs de la DMZ, jamais depuis Internet. C'est la défense en profondeur."*

---

## SLIDE 15 — Synthèse RAM/CPU/Disques/OS

**À dire (90 sec)** :
> "Le dimensionnement **cible production** :
>
> | Couche | RAM | CPU | Disque | OS |
> |---|---|---|---|---|
> | Front Web (Next.js) | 4 Go | 2 vCPU | 30 Go SSD | Ubuntu 22.04 LTS |
> | Back Office (Next.js) | 2 Go | 2 vCPU | 20 Go SSD | Ubuntu 22.04 LTS |
> | API (FastAPI) | 8 Go | 4 vCPU | 50 Go SSD | Ubuntu 22.04 LTS |
> | BD PostgreSQL + pgvector | 16 Go | 4 vCPU | 100 Go SSD NVMe | Ubuntu 22.04 LTS |
> | Azure Blob Storage | N/A | N/A | 500 Go - 1 To élastique | Service Azure managé |
>
> Pour le **POC + 1ère année de production** (~10 000 sociétaires). Au-delà, scaling vertical recommandé (RAM ×2 sur API et BD)."

**Question piège** : *"16 Go pour PostgreSQL avec pgvector c'est suffisant ?"*
> *"Pour 100 000 vecteurs indexés HNSW c'est dimensionné. Si on dépasse 300 000 vecteurs, on passe à 32 Go. C'est documenté dans la roadmap Phase 2."*

---

## SLIDE 16 — Matrice des Flux

**À dire (90 sec)** :
> "Cette matrice répond à la DSI / SecOp : **'qui parle à qui, sur quel port'**.
>
> 3 lignes principales :
>
> 1. **Sociétaire → API MA2E** : HTTPS port 443 — webhook WhatsApp + interface web
> 2. **API MA2E → BD/Cache/Stockage** : PostgreSQL 5432, Redis 6379, Azure Blob 443
> 3. **Administrateur** : SSH port 22 pour la maintenance, HTTPS pour le backoffice depuis le LOCAL ou via VPN
>
> Tous les flux sortants (vers Azure OpenAI, Azure OCR, WhatsApp Cloud API, SMTP) sont **autorisés explicitement** dans le firewall — pas d'ouverture large."

**Question piège** : *"Vous avez prévu un firewall sortant ?"*
> *"Oui, allowlist stricte : api.groq.com, *.openai.azure.com, graph.facebook.com, et le provider SMTP. Aucun autre flux sortant n'est autorisé."*

---

## SLIDE 17 — Mode de déploiement

**À dire (60 sec)** :
> "Le déploiement est **conteneurisé Docker**. Cohérent pour les deux cibles possibles :
>
> - **Cible cloud** : Azure Container Apps ou AKS (recommandé pour le scaling)
> - **Cible on-premise** : Datacenter ERANOVE avec orchestrateur K8s ou Docker Swarm
>
> Le passage de l'un à l'autre **ne nécessite aucune modification du code applicatif**. C'est une décision purement opérationnelle.
>
> **3 environnements isolés** : dev, staging, prod. Avec un pipeline CI/CD qui exécute build → tests → push registry → déploiement. Migrations Alembic exécutées automatiquement."

---

## SLIDE 18 — Éco-conception et performance web

**À dire (60 sec)** :
> "On vise un **score Lighthouse > 90** sur les 3 axes (performance, accessibilité, bonnes pratiques) côté frontend.
>
> Mesures concrètes :
> - **SSR + ISR** Next.js pour minimiser le JavaScript côté client
> - **Lazy loading** des images
> - **Conteneurisation légère** (images Docker Alpine quand possible)
> - **Pas de modèle IA en local** dans le navigateur (économie batterie mobile)
> - **WebP/AVIF** pour les images
> - **HTTP/2 multiplexing** au niveau LB
>
> Objectif : un sociétaire avec un téléphone bas de gamme et une connexion 3G doit pouvoir s'enrôler en moins de **10 minutes**."

---

## SLIDE 19 — DCP (Matrice des DCP)

**À dire (90 sec)** :
> "Voici la matrice des **Données à Caractère Personnel** — c'est l'élément central pour l'**audit ARTCI** :
>
> **4 lignes** (corrigées et à jour) :
>
> 1. **Sociétaire → API MA2E** : nom, prénoms, ddn, email, téléphone, matricule, n° CNI, photo CNI recto/verso, consentement ARTCI
> 2. **Agent MA2E → API MA2E** : login, hash mot de passe, email pro, rôle, AD login ERANOVE
> 3. **API MA2E → Azure AI** : photos CNI + contenu des conversations (pour OCR + RAG)
> 4. **Administrateur → API + BD + Redis + Azure Blob** : login, audit (IP, horodatage, actions)
>
> Pour **chaque flux**, on a documenté la **finalité** précise (loi 2013-450 article 16) : identification, validation, traçabilité, anonymisation."

**Question piège** : *"Les conversations envoyées à Azure AI, c'est conforme ARTCI ?"*
> *"Azure OpenAI a une politique de **non-rétention** activable. On a aussi un consentement explicite (Gate 1) qui mentionne ce traitement. Le contrat Azure est signé avec engagement de localisation des données en Europe (UE) — précisé dans la notice ARTCI v1.0."*

---

## SLIDE 20 — DCP collectées (détail)

**À dire (60 sec)** :
> "Pour chaque DCP on a documenté :
>
> - **Catégorie** (identité civile, contact, professionnel, technique, dérivée IA, preuve légale)
> - **Sensibilité** (normale ou sensible — photo CNI et OCR sont sensibles)
> - **Durée de conservation** (selon finalité)
> - **Base légale** (consentement explicite + obligation contractuelle)
>
> Toutes les DCP sensibles sont **chiffrées au repos** dans Azure Blob et **anonymisables sur demande** (droit à l'oubli)."

---

## SLIDE 21 — Politique de sécurité (Conformité DCP / RGPD / Loi 2013-450)

**À dire (120 sec)** :
> "Notre politique de sécurité est **'défense en profondeur'** :
>
> **Couche 1 — Réseau** :
> - TLS 1.3 partout
> - WAPI en entrée (anti-injection, anti-DDoS)
> - Firewall sortant en allowlist
>
> **Couche 2 — Authentification** :
> - JWT HS256 + AD ERANOVE pour les agents
> - OTP email pour les sociétaires (3 tentatives max, 10 min de validité)
>
> **Couche 3 — Donnée** :
> - Chiffrement au repos KMS sur Azure Blob
> - Mots de passe hashés bcrypt
> - Secrets dans Azure Key Vault, jamais en clair dans le code
>
> **Couche 4 — Audit** :
> - Journal append-only avec hash chaîné SHA-256 (toute modification est détectable)
> - Rétention 12 mois minimum, exportable à l'ARTCI
>
> **Couche 5 — Conformité** :
> - 3 Gates de consentement HMAC-SHA256 horodatés
> - Droit à l'oubli + anonymisation par le DPO
> - Page d'information ARTCI permanente"

**Question piège** : *"Vous avez fait un audit ARTCI ?"*
> *"L'audit blanc est prévu en Phase 2 avant la mise en prod. La notice ARTCI v1.0 a déjà été préparée. Le DPO MA2E sera désigné avant le démarrage."*

---

## SLIDE 22 — TOP 3 des risques

**À dire (90 sec)** :
> "Les **2 risques principaux** sur lesquels on s'engage :
>
> **R1 — Indisponibilité WhatsApp Cloud API** :
> Si Meta tombe, on perd le canal principal. **Mesure** : basculement temporaire sur le chat web, communication aux agences pour repli papier exceptionnel.
>
> **R2 — Non-conformité ARTCI** :
> Un audit défavorable suspendrait le traitement des données. **Mesure** : validation préalable de la notice ARTCI par le DPO + audit blanc en recette.
>
> Tous les risques résiduels sont **acceptés et tracés** dans un registre."

---

## SLIDES 23-25 — Démos (captures d'écran)

**À dire pour chacune (40 sec chaque)** :

**DEMO 1 — Parcours sociétaire WhatsApp** :
> "Voici le parcours complet du sociétaire sur WhatsApp : accueil, présentation de la notice ARTCI, recueil du consentement (Gate 1), saisie matricule, OTP email, upload photo CNI, extraction OCR avec score de confiance, confirmation des données et soumission. **35 secondes de bout en bout**."

**DEMO 2 — Backoffice de validation agent** :
> "L'agent voit son tableau de bord avec les dossiers en attente triés par ancienneté. Il ouvre un dossier — photos CNI agrandies, données extraites, conversation complète. Il peut **valider, refuser avec motif obligatoire, ou demander un complément**. Tout est tracé dans l'audit."

**DEMO 3 — Assistant IA + base de connaissances** :
> "Un sociétaire pose une question : 'quels sont les avantages MA2E ?' L'IA cherche dans la base de connaissances vectorisée (RAG sur pgvector), formule une réponse en citant la source, et propose le transfert vers un conseiller si pas certaine. C'est la magie du RAG : on garde le contrôle sur les sources."

---

## SLIDE 26 — Rapport de tests

**À dire (60 sec)** :
> "Notre stratégie de tests suit la **pyramide classique** :
>
> - **Tests unitaires** : couverture cible 70 % sur le backend
> - **Tests d'intégration** : machine à états, OCR, Azure AI
> - **Tests E2E** : parcours sociétaire et agent
> - **Tests de charge** : 200 utilisateurs simultanés, P95 < 3s
> - **Tests de sécurité** : SAST (audit code) + DAST (pen-test) avant prod
> - **Tests de conformité** : audit blanc ARTCI + validation DPO
>
> Tout est documenté dans le **Plan de Tests** annexé."

---

## SLIDE 27 — Merci

**À dire (15 sec)** :
> "Merci de votre attention. Je suis à votre disposition pour vos questions."

---

# 🎙️ Questions générales à anticiper

| Question | Réponse courte |
|---|---|
| *"Coût total du projet ?"* | "Je vous renvoie au volet financier remis avec le CDC — pas dans le périmètre CVATL technique." |
| *"Combien de personnes sur l'équipe ?"* | "Pour le POC : un développeur fullstack. Pour la prod : équipe de 3 (dev, devops, support métier)." |
| *"Vous garantissez 99,5 % de dispo ?"* | "Oui sur les heures ouvrées (8h-17h). C'est inscrit au SLA. Maintien possible 24/7 si demandé." |
| *"Vous avez prévu une formation des agents ?"* | "Oui, Phase 2 inclut un plan de conduite du changement : manuel + sessions + pilote sur 1 agence." |
| *"Et si Azure tombe ?"* | "Architecture **multi-zone** par défaut. Azure West Europe + une zone DR. RPO 5 min, RTO 1h." |
| *"Le code est-il open-source ou propriétaire ?"* | "Propriétaire MA2E / GS2E. Mais utilise des composants open-source (FastAPI, Next.js, PostgreSQL)." |
| *"Que se passe-t-il si vous quittez le projet ?"* | "Toute la documentation est livrée (CVATL, DAT, DAS, Plan de tests, runbooks). Le code est commenté et testé. Maintenance reprise par l'équipe MA2E + GS2E." |
| *"Vous gérez les pics d'enrôlement (ex: nouvelle campagne) ?"* | "Oui via autoscaling. Et on a un mode 'queue' Redis pour absorber les pics OCR / IA." |

---

# 🎯 Phrase de clôture (si on demande votre conclusion)

> "Cette plateforme MA2E n'est pas qu'un projet de digitalisation — c'est une **mise en conformité ARTCI**, une **modernisation de l'expérience sociétaire**, et une **base technique mutualisable** pour l'ensemble du groupe ERANOVE. On est prêts à passer en production."

---

*Document de support — à imprimer en A4 ou consulter sur tablette pendant la présentation.*
*Bon courage pour le 08 juin 🎙️*
