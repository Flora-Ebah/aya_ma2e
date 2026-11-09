# MA2E — Pitch CVATL : Bloc Architecture (11 slides)

> **À garder en tête** : le jury n'est pas que technique. Il y a des décideurs métier.
> Donc je parle **simple**, je raconte **une histoire**, et je laisse le visuel parler.
> Je ne lis JAMAIS les noms techniques l'un après l'autre — j'explique **à quoi ça sert**.
>
> **Timing cible : 17 à 20 minutes au total pour les 11 slides**.

---

## 🎯 Le fil rouge à répéter

Avant chaque slide, je me remets en tête mon fil rouge :

> **« MA2E, c'est une plateforme qui transforme une procédure papier de 2 semaines
> en une conversation WhatsApp de 10 minutes — tout en restant 100% conforme ARTCI. »**

Mes 11 slides répondent à 11 questions simples :

| Slide | La question à laquelle je réponds | Durée |
|---|---|---|
| Page 6 — Architecture Fonctionnelle | **Qui fait quoi dans le système ?** | 90 s |
| Page 8 — TOP 3 des workflows | **Comment se déroule concrètement un parcours d'identification ?** | 2 min |
| Page 9 — Modélisation des entités | **Qu'est-ce qu'on stocke en base ?** | 90 s |
| Page 10 — Architecture Logicielle 1/2 | **Comment c'est découpé en blocs logiciels ?** | 2 min |
| Page 11 — Architecture Logicielle 2/2 | **Avec quelles technologies on l'a construit ?** | 90 s |
| Page 12 — Architecture Technique 1/2 | **Comment c'est déployé en production ?** | 90 s |
| Page 13 — Architecture Technique 2/2 | **Comment c'est sécurisé par zonage réseau ?** | 90 s |
| Page 14 — Dimensionnement RAM/CPU/OS | **Quelles ressources concrètes on demande à la DSI ?** | 90 s |
| Page 15 — Matrice des flux | **Quels ports et protocoles sont autorisés ?** | 60 s |
| Page 16 — Mode de déploiement | **Où on déploie quoi (Docker / DC / Cloud) ?** | 60 s |
| Page 18 — Matrice des DCP | **Quelles données perso, pour quelles finalités ?** | 2 min |

---

## 📄 PAGE 6 — Architecture Fonctionnelle

### En une phrase
> « Ce schéma résume **qui interagit avec le système**, **par quel canal**, et **vers quels services externes**. »

### Ce que je dis (≈ 90 secondes)

> « À gauche, nos **deux acteurs** : le **sociétaire**, qui est l'employé du groupe GS2E qui veut s'identifier, et l'**agent MA2E**, qui valide les dossiers depuis le back-office.
>
> Chacun a son canal d'entrée. Le sociétaire passe par **WhatsApp ou Web Chat** — là où il est déjà. L'agent passe par un **back-office Next.js**, son outil de travail quotidien.
>
> Au centre, tout converge vers **une seule API FastAPI**. C'est la porte d'entrée unique. Tout passe par là, on contrôle tout à un seul endroit — pratique pour la sécurité et l'audit.
>
> En dessous, le **cœur métier** : sept modules qu'on a découpés par responsabilité. L'authentification, l'onboarding du sociétaire, l'extraction de la pièce d'identité, l'assistant IA, les notifications, la validation des dossiers, et le module **audit & conformité ARTCI** — qui est non-négociable pour nous.
>
> À droite, les **systèmes externes** qu'on consomme : l'**Active Directory ERANOVE** pour authentifier les agents, **WhatsApp Cloud API** pour échanger avec les sociétaires, **Azure AI** pour l'OCR de la CNI et l'IA conversationnelle, et le **SMTP** pour les emails.
>
> Tout est tracé. Tout est journalisé. C'est ça qui nous permet de tenir la conformité ARTCI loi 2013-450. »

### Si on me pose la question 
- **« Pourquoi pas d'app mobile native ? »**
  → « Parce que **97% des Ivoiriens utilisent déjà WhatsApp**. Construire une app native, c'est ajouter une friction — installer, créer un compte, retenir un mot de passe. WhatsApp, c'est zéro installation. »
- **« Et si Azure tombe ? »**
  → « Bonne question. L'OCR a un **fallback OCR.space**, et l'IA conversationnelle a un mode dégradé scripté. Le service ne s'arrête pas. »

---

## 📄 PAGE 8 — TOP 3 des workflows (BPMN swimlanes)

### En une phrase
> « Voici **le parcours d'identification de bout en bout** — trois acteurs, un seul flux. »

### Ce que je dis (≈ 75 secondes)

> « Trois couloirs : le sociétaire en haut, la plateforme au milieu, l'agent en bas. La logique est volontairement asymétrique — **le sociétaire fait le minimum, la plateforme fait le maximum, l'agent ne fait que ce qui demande son jugement.**
>
> Le sociétaire entre sur WhatsApp, accepte la notice ARTCI, fournit son matricule, ces informations et sa CNI, et valide les données extraites. **C'est tout pour lui — moins de dix minutes.**
>
> La plateforme prend le relais : OCR sur la pièce, **vérification du matricule contre le référentiel collaborateurs s'il est chargé** — sinon contrôle de format et détection de doublon dans la base MA2E — puis notification email. **Tout ça automatisé, sans intervention.**
>
> L'agent intervient à un seul endroit — **la décision finale.** Trois issues possibles : valider, demander un complément, ou rejeter avec motif. **Quelle que soit l'issue, le sociétaire est toujours notifié — jamais de silence.**
>
> Deux points de conformité ARTCI sont tissés dans le flux : **la notice à l'étape 2**, **le consentement à l'étape 3**. Si refus, on s'arrête — aucune donnée n'est stockée. C'est la conformité **by design**, pas en option.
>
> Au final : **plus de 70% du parcours est automatisé**, contre une procédure papier qui prenait **deux semaines**. »

### Si on me pose la question
- **« Et si le sociétaire abandonne en cours ? »**
  → « La session est persistée. Il reprend où il s'est arrêté, jusqu'à 30 jours après. »
- **« SLA agent ? »**
  → « 24h ouvrées entre soumission et décision. Suivi en KPI, alerte au-delà de 12h. »
- **« Pourquoi distinguer complément et rejet ? »**
  → « Le complément est **réparable** — photo floue, donnée manquante. Le rejet est **définitif** — non-éligibilité. Mélanger les deux fausse les statistiques et l'expérience utilisateur. »
- **« Et si vous n'avez pas le référentiel collaborateurs chargé ? »**
  → « Le parcours fonctionne quand même. À défaut de matching automatique, on applique un **contrôle de format** sur le matricule, on lance la détection de doublon, et on laisse **l'agent trancher manuellement** lors de la validation. L'import du référentiel est piloté depuis l'admin — au fur et à mesure qu'il est alimenté, l'automatisation monte en puissance. »
- **« Si l'OCR se trompe ? »**
  → « L'étape 5 existe pour ça : le sociétaire **valide ce que l'OCR a lu** et corrige avant de soumettre. Aucune confiance aveugle dans la machine. »

---

## 📄 PAGE 9 — Modélisation du   5 des entités métier

### En une phrase
> « Voici les **objets métier centraux** qu'on stocke en base, et comment ils sont liés entre eux. »

### Ce que je dis (≈ 90 secondes)

> « On a 5 entités centrales, plus 3 tables de référence sur la droite.
>
> Le **sociétaire**, c'est la personne physique qu'on identifie — nom, prénoms, CNI, employeur. C'est le sujet principal.
>
> Le **dossier**, c'est le processus d'identification de ce sociétaire — son canal d'entrée (WhatsApp ou web), les photos de sa CNI, le score de confiance de l'OCR, le consentement ARTCI, et l'agent qui l'a validé.
>
> La **conversation**, c'est la trace de l'échange qui a abouti à ce dossier — canal, durée, nombre de messages. C'est ce qui nous permet plus tard de faire de l'**amélioration continue** sur le bot.
>
> L'**utilisateur**, c'est l'agent MA2E côté back-office, qui a un rôle et un statut.
>
> Et l'**employeur**, c'est la société du groupe GS2E à laquelle le sociétaire est rattaché — CIE, SODECI, SMB, AD ERANOVE.
>
> À droite, les tables de **référence** : les rôles, les statuts utilisateurs, les statuts dossiers. On les a externalisées pour que l'admin puisse en ajouter sans toucher au code.
>
> Les relations sont propres : un sociétaire peut avoir plusieurs dossiers historiques, un dossier a une conversation et plusieurs pièces d'identité (recto + verso). »

### Si on me pose la question
- **« Pourquoi PostgreSQL et pas du NoSQL ? »**
  → « Parce qu'on a un domaine **fortement relationnel** — sociétaire → dossier → pièces — et qu'on a besoin de transactions ACID pour la conformité. Et avec **pgvector** on fait quand même de la recherche sémantique sur les conversations. C'est le meilleur des deux mondes. »
- **« La CNI est stockée où exactement ? »**
  → « Le **fichier image** est dans Azure Blob Storage chiffré. La **base de données** ne stocke que l'URL et le hash SHA-256 pour vérifier l'intégrité. Aucune donnée personnelle n'est dans l'URL. »

---

## 📄 PAGE 10 — Architecture Logicielle 1/2

### En une phrase
> « Maintenant, comment **les blocs logiciels** sont organisés et discutent entre eux. »

### Ce que je dis (≈ 2 minutes)

> « Le schéma se lit de gauche à droite en 3 colonnes.
>
> **À gauche, le frontend.** On a **5 portes d'entrée distinctes** parce qu'on a 5 profils d'utilisateurs avec 5 besoins différents — le sociétaire fait du chat, l'agent valide, le superviseur regarde les KPI, l'administrateur gère le référentiel, le DPO fait l'audit ARTCI. Une UI par profil, c'est plus simple à utiliser que de tout entasser dans une interface unique.
>
> **Au centre, le backend.** Trois zones empilées.
>
> En haut, les **services externes** : WhatsApp, Azure OpenAI, Azure AI OCR, SI RH ERANOVE. On les a tous isolés derrière des **adaptateurs** pour pouvoir en changer sans toucher au code métier.
>
> Au milieu, la **couche métier** : sept services indépendants. L'onboarding accueille le sociétaire, la validation gère le workflow, l'extraction CNI fait l'OCR, l'assistant IA répond aux questions, les notifications partent en mail ou WhatsApp, l'audit ARTCI journalise tout, et l'authentification gère JWT et AD.
>
> En bas, le **modèle de données** — les 7 tables principales — et le moteur de logs structurés qui alimente le journal d'audit ARTCI.
>
> **À droite, la base de données.** Stratégie classique : un **maître PostgreSQL** qui prend toutes les écritures, un **esclave en réplication** qui sert les lectures lourdes — typiquement les exports et le reporting. **Redis** pour le cache et les sessions, et **Azure Blob Storage** pour les pièces d'identité chiffrées.
>
> Pourquoi ce découpage ? Parce qu'on peut **scaler chaque bloc indépendamment**. Si la charge OCR explose, je rajoute des workers d'extraction sans toucher au reste. »

### Si on me pose la question
- **« Pourquoi un maître/esclave et pas un cluster ? »**
  → « Parce que pour notre volumétrie cible — 50 000 sociétaires sur 3 ans — un maître/esclave suffit largement, et c'est **infiniment plus simple à opérer**. Un vrai cluster type Patroni, on le rajoutera à la phase 2 si la charge le justifie. »
- **« Le service d'authentification gère JWT **et** Active Directory ? »**
  → « Oui. Les **agents internes** s'authentifient via l'AD ERANOVE — un seul mot de passe à retenir. Les **sociétaires** n'ont pas de mot de passe du tout, on les identifie via WhatsApp ou un code envoyé par mail. C'est ça qui fait la différence d'expérience. »

---

## 📄 PAGE 11 — Architecture Logicielle 2/2

### En une phrase
> « Le détail des **technologies retenues** et **pourquoi** elles ont été choisies. »

### Ce que je dis (≈ 90 secondes)

> « Trois piles, choisies pour des raisons précises.
>
> **Côté frontend** : **Next.js 14 + TypeScript + Tailwind CSS**. Next.js parce qu'il fait du **rendu serveur** — c'est rapide même sur une connexion 3G, ce qui compte pour un produit destiné à des sociétaires sur le terrain. TypeScript pour la **fiabilité** : les bugs se voient à la compilation, pas en production. Tailwind pour livrer un design system propre **rapidement**.
>
> **Côté backend** : **Python 3.11 + FastAPI + SQLAlchemy 2.0**. FastAPI parce qu'il est **asynchrone par nature** — il tient 10 000 requêtes par seconde sur un seul serveur. Python parce qu'il a **l'écosystème IA et OCR** le plus mature : tout ce qu'on consomme — Azure OpenAI, Pillow pour la compression d'image, lxml pour le scraping — c'est natif Python. SQLAlchemy pour avoir un ORM mais sans perdre la maîtrise du SQL généré.
>
> **Côté données** : **PostgreSQL 16 avec l'extension pgvector** pour la recherche sémantique sur les conversations. **Redis 7** pour le cache et les sessions WhatsApp. **MinIO** en dev, **Azure Blob** en prod, pour stocker les pièces d'identité chiffrées.
>
> Tout est **open source**, sans licence à payer côté logiciel. On paye uniquement les services Azure consommés à l'usage. »

### Si on me pose la question
- **« Python n'est-il pas lent ? »**
  → « Le mythe a la vie dure. FastAPI sur **uvicorn** est dans le **top 5 mondial des frameworks web** en débit, à égalité avec Node.js Express et plus rapide que Spring Boot. Pour notre workload — 99% I/O, 1% CPU — Python est parfait. »
- **« Pourquoi pas Laravel comme dans le PRD initial ? »**
  → « Décision technique prise et documentée : on garde notre stack **FastAPI/Next.js** pour le POC. Pivoter en cours de route, c'est **3 mois de retard** garantis pour zéro bénéfice fonctionnel. La phase 2 réévaluera si on industrialise. »

---

## 📄 PAGE 12 — Architecture Technique 1/2 (déploiement)

### En une phrase
> « Voici comment **MA2E est déployé en production** — la vue physique et réseau. »

### Ce que je dis (≈ 90 secondes)

> « On part de l'utilisateur à gauche. Il arrive en HTTPS sur un **load balancer** qui répartit le trafic entre **deux serveurs web/application identiques** — c'est notre haute disponibilité de base. Si un des deux serveurs tombe, le second prend tout le trafic, l'utilisateur ne voit rien.
>
> Les serveurs applicatifs hébergent **Next.js et FastAPI ensemble**. Ils discutent en TCP via **asyncpg** avec un **serveur PostgreSQL maître** au centre du schéma. Toutes les écritures vont là.
>
> En parallèle, le maître **réplique en continu** vers un serveur **PostgreSQL esclave**. C'est notre **plan de reprise** : si le maître tombe, on bascule sur l'esclave en quelques minutes. Et l'esclave sert aussi les **lectures lourdes** — l'export Excel ne ralentit jamais les écritures du bot.
>
> À droite, **Redis 7** héberge le cache et les sessions WhatsApp — il faut que ce soit en mémoire, sinon le bot devient lent.
>
> En bas à droite, **Azure Blob Storage** stocke les **pièces d'identité chiffrées**. C'est externalisé chez Azure parce que le chiffrement au repos est natif, certifié ISO 27001 et conforme au RGPD européen et à la loi 2013-450 ivoirienne.
>
> Toute la communication interne se fait en **TCP** dans le VPC, toute la communication externe en **HTTPS**. Les ports sont fermés sauf 443. Les clés Azure sont dans un **Key Vault**, jamais dans le code. »

### Si on me pose la question
- **« Combien de requêtes par seconde tient cette archi ? »**
  → « Sur la base de nos benchmarks FastAPI + PostgreSQL avec ces dimensions, on tient **2 000 RPS sans saturer**. Notre cible métier — 200 inscriptions par jour pic — représente **0,002 RPS soutenu**. On a 6 ordres de grandeur de marge. »
- **« Et si on veut scaler ? »**
  → « On rajoute simplement un troisième serveur web/app derrière le load balancer. La base reste maître/esclave. **Linéaire et sans douleur.** »
- **« Disaster recovery ? RTO/RPO ? »**
  → « **RPO 5 minutes** grâce à la réplication asynchrone PostgreSQL. **RTO 30 minutes** : bascule sur l'esclave en lecture/écriture documentée dans le runbook. Snapshots Azure quotidiens conservés **30 jours**. »

---

## 📄 PAGE 13 — Architecture Technique 2/2 (zonage réseau)

### En une phrase
> « Voici le **zonage réseau** : ce qui est exposé sur internet, ce qui est en DMZ, et ce qui reste **strictement local**. »

### Ce que je dis (≈ 90 secondes)

> « Cette vue, c'est la **sécurité périmétrique**. On la lit en **3 zones de confiance**, de gauche à droite.
>
> **Zone INTERNET** — tout à gauche. Le sociétaire avec son mobile WhatsApp. Il passe par le **WAPI**, qui est la passerelle WhatsApp publique. C'est la **seule porte d'entrée** ouverte au monde extérieur. **Flux n°1** sur le schéma.
>
> **Zone DMZ** — au milieu. C'est la zone tampon. On y trouve **HAProxy**, notre reverse proxy qui filtre tout le trafic entrant, applique du rate-limiting et termine le HTTPS. Derrière lui, dans la même DMZ, le **cluster FastAPI** qui héberge l'API MA2E, le module OCR et l'assistant IA RAG.
>
> Donc **rien d'exposé directement** — le sociétaire ne voit jamais l'API. Il voit uniquement HAProxy, qui décide de laisser passer ou pas.
>
> **Zone LOCAL** — à droite, et c'est la zone la plus protégée. **Deux sous-zones**.
>
> En haut, la **base de données MA2E** — PostgreSQL maître + esclave. **Flux 2 et 3** : l'API écrit et lit, mais aucun trafic public ne peut atteindre la base. Elle n'est joignable que depuis la DMZ via le firewall interne.
>
> En bas, le **back-office d'administration MA2E**. **Flux 4 et 5** : les agents et admins l'utilisent uniquement depuis le réseau interne ou via VPN. Il n'est **pas exposé sur internet**.
>
> Cette segmentation 3 zones, c'est la base de la conformité **PCI-DSS et ARTCI**. Si un attaquant compromet HAProxy, il est bloqué par le firewall de la zone LOCAL. Défense en profondeur. »

### Si on me pose la question
- **« Pourquoi HAProxy et pas un WAF commercial type Cloudflare ? »**
  → « Parce qu'on **maîtrise notre infra de bout en bout**, sans dépendance à un tiers payant. HAProxy en DMZ permet aussi le rate-limiting fin, le filtrage par règles métier. Et on peut **rajouter un WAF Cloudflare devant** si la direction le décide, sans rien changer derrière. »
- **« Les agents valident depuis l'extérieur, c'est sécurisé ? »**
  → « Non, justement — les agents passent **toujours par le VPN d'entreprise**. Le back-office n'a aucun port ouvert sur internet. C'est documenté dans la matrice des flux qu'on va voir juste après. »
- **« Et si HAProxy tombe ? »**
  → « Il y aura deux instances en actif/passif derrière une VIP. Bascule transparente en moins de 5 secondes. »

---

## 📄 PAGE 14 — Dimensionnement RAM / CPU / Disque / OS

### En une phrase
> « Voici **précisément ce qu'on demande à la DSI** pour faire tourner MA2E en production. Chaque chiffre est justifié. »

### Ce que je dis (≈ 90 secondes)

> « Ce slide, c'est ma feuille de commande à l'infrastructure. Cinq couches, cinq lignes.
>
> **Front Web Next.js** — l'interface du sociétaire. **200 utilisateurs simultanés**, ce qui est notre pic estimé en heure de pointe. 8 Go de RAM, 4 vCPU, 50 Go SSD. C'est dimensionné petit volontairement parce que Next.js sert surtout du HTML pré-rendu, ce n'est pas lui qui mouline.
>
> **Back-office Next.js** — séparé du front public, plus petit. **30 agents en simultané maximum**. 4 Go de RAM, 2 vCPU. C'est très light parce qu'on a peu d'utilisateurs et peu de trafic.
>
> **API FastAPI** — c'est le cœur. **300 requêtes par minute** soutenues, **16 Go de RAM**, **8 vCPU**, 100 Go SSD. Pourquoi plus gros ? Parce que c'est lui qui appelle Azure OpenAI, qui fait l'OCR, qui orchestre tout. Il faut de la mémoire pour les workers async et du CPU pour le pré-traitement des images.
>
> **Base PostgreSQL 16 + pgvector** — **32 Go de RAM**. C'est généreux mais justifié : PostgreSQL aime la RAM pour son cache, et pgvector charge ses index vectoriels en mémoire pour la recherche sémantique. **500 Go SSD** pour absorber 3 ans de croissance estimée.
>
> **Azure Blob Storage** — c'est managé par Azure. Pas de RAM, pas de CPU à provisionner. Capacité **élastique de 500 Go à 1 To**, on paie ce qu'on consomme.
>
> Tout tourne sur **Ubuntu 22.04 LTS**, parce que c'est supporté jusqu'en 2027, c'est ce que la DSI GS2E maintient déjà, et c'est gratuit. »

### Si on me pose la question
- **« 200 utilisateurs simultanés, c'est suffisant pour 50 000 sociétaires ? »**
  → « Oui, parce qu'un sociétaire s'identifie **une seule fois dans sa vie**. Le throughput est **étalé sur 12 à 18 mois**. Le pic à 200 simultanés, c'est notre estimation haute pour les campagnes d'enrôlement coordonnées. »
- **« Pourquoi pas plus de RAM sur la base ? »**
  → « 32 Go couvre **3 fois** la taille estimée de la base à 3 ans. Si on dépasse, c'est qu'on a réussi au-delà des prévisions — et là on remonte les compteurs, c'est un problème de luxe. »
- **« Et le tout en haute disponibilité ? »**
  → « Oui — chaque couche est doublée. Donc multipliez ces chiffres par 2 pour le besoin réel. Ça reste **modeste pour un projet stratégique du groupe**. »

---

## 📄 PAGE 15 — Matrice des flux réseau

### En une phrase
> « Ce tableau **liste tous les flux réseau autorisés** dans le système. C'est la base du paramétrage firewall. »

### Ce que je dis (≈ 60 secondes)

> « Trois lignes, trois acteurs, et on liste **précisément quel port et quel protocole** chacun a le droit d'utiliser. Aucune ambiguïté pour l'admin réseau.
>
> **Premier flux — le sociétaire**. Il arrive en **HTTPS sur le port 443** uniquement. Il atteint le load balancer, qui le route vers le front web puis l'API. C'est aussi par là que rentrent les **webhooks WhatsApp** quand Meta nous notifie d'un nouveau message. **Un seul port public**.
>
> **Deuxième flux — l'API MA2E vers ses dépendances**. Trois cibles : PostgreSQL sur le **5432** en TCP, Redis sur le **6379** en TCP, et Azure Blob Storage sur le **443** en HTTPS. Ces ports sont **autorisés uniquement depuis la zone DMZ vers la zone LOCAL** — pas de bypass possible.
>
> **Troisième flux — les administrateurs et agents MA2E**. Ils accèdent à la prod en **SSH sur le 22** pour la maintenance, et au back-office en **HTTPS** depuis le réseau interne ou via VPN. Aucun accès direct internet — c'est pour ça que le back-office n'est pas dans la DMZ.
>
> Cette matrice, on la donne directement à la DSI GS2E pour qu'elle configure les règles firewall. **C'est notre contrat avec eux.** »

### Si on me pose la question
- **« Pourquoi SSH et pas un bastion ? »**
  → « En fait, le SSH passe **par un bastion d'entreprise GS2E**. C'est implicite dans le diagramme mais on peut le rendre explicite dans la matrice. Aucun accès SSH direct depuis le poste de l'admin. »
- **« Pourquoi pas TLS sur PostgreSQL ? »**
  → « Le trafic PostgreSQL est **dans le réseau privé**, jamais sur internet. On peut activer TLS interne si la DSI l'impose, sans coût applicatif. C'est une décision DSI. »
- **« Et les flux sortants ? Vers Azure OpenAI par exemple ? »**
  → « Bonne remarque — on peut compléter la matrice avec ça. L'API sort en HTTPS/443 vers les endpoints Azure OpenAI, Azure AI Vision et l'API WhatsApp Cloud de Meta. **Toutes les sorties sont en HTTPS, jamais en HTTP.** »

---

## 📄 PAGE 16 — Mode de déploiement

### En une phrase
> « Voici les **3 modes de déploiement** qu'on combine intelligemment, chacun pour la bonne raison. »

### Ce que je dis (≈ 60 secondes)

> « Pas un mode, **trois**. Et ce n'est pas par indécision, c'est par stratégie.
>
> **Docker** au centre du dispositif. Toute notre application — frontend, backend, OCR, scraper — est conteneurisée. Pourquoi ? Parce que ça **garantit l'identité** entre l'environnement de dev, de recette et de prod. **Un container qui marche chez moi marchera sur le serveur du data center.** Plus de "ça marche en local".
>
> **Le Data Center GS2E** pour héberger les conteneurs critiques. Tout ce qui touche aux **données personnelles** des sociétaires reste **sur le sol ivoirien**, dans l'infrastructure du groupe. C'est non-négociable pour la conformité ARTCI et pour la souveraineté des données.
>
> **Le Cloud Azure** uniquement pour les services qui ne peuvent pas tourner ailleurs : le **modèle IA** Azure OpenAI, l'**OCR Azure AI Vision**, et le **stockage chiffré Azure Blob** pour les pièces d'identité — qui est lui aussi en région compatible avec les exigences ivoiriennes.
>
> Cette répartition, c'est le meilleur compromis entre **performance** (l'IA reste managée par les leaders du marché), **conformité** (les données nominatives ne sortent pas du data center GS2E), et **coût** (on paie l'IA à l'usage, pas à la capacité). »

### Si on me pose la question
- **« Pourquoi pas tout en interne ? »**
  → « Parce qu'**héberger un GPT-4 en interne**, c'est plusieurs centaines de millions de FCFA en infrastructure et personnel spécialisé. Pour notre volume, l'usage Azure OpenAI coûte **moins d'un dollar par sociétaire identifié**. »
- **« Pourquoi pas tout en cloud ? »**
  → « Parce que la loi 2013-450 ARTCI demande à pouvoir **localiser physiquement** les données nominatives. Un data center GS2E ivoirien, c'est sans ambiguïté. Un cloud public, c'est plus complexe à justifier au CNDP. »
- **« Et la portabilité Docker ? »**
  → « C'est l'autre atout : si demain la stratégie groupe change, on **déplace les containers vers un autre cloud ou un autre data center sans réécrire une ligne**. C'est ce qu'on appelle l'évitement du vendor lock-in. »

---

## 📄 PAGE 18 — Matrice des Données à Caractère Personnel (DCP)

### En une phrase
> « Voici **toutes les données personnelles** qu'on traite, avec **pourquoi on les traite**. C'est la base de notre conformité ARTCI. »

### Ce que je dis (≈ 2 minutes)

> « Cette matrice, c'est ce que le **DPO** (Délégué à la Protection des Données) et l'**ARTCI** vont nous demander en premier. On l'a anticipée.
>
> Quatre lignes, quatre sources de données personnelles.
>
> **Premier — le sociétaire**. Quand il s'identifie via WhatsApp ou web, il nous transmet : nom, prénoms, date de naissance, email, téléphone, matricule employeur, numéro CNI, **photos recto/verso de sa CNI**, et son **consentement ARTCI**. Pourquoi ? Pour l'**identifier**, **créer son dossier**, **vérifier qu'il est bien employé du groupe**, et garantir **la traçabilité ARTCI**. Chaque champ a une finalité explicite — c'est ça que demande la loi 2013-450.
>
> **Deuxième — l'agent MA2E**. On stocke son login, son mot de passe **haché** (jamais en clair), nom, email pro, rôle et statut, plus son **login AD ERANOVE**. Finalité : authentifier l'agent, valider les dossiers, et tracer ses actions dans l'audit log. Ça nous permet de répondre à la question "qui a validé ce dossier le 12 juin à 14h32".
>
> **Troisième — l'API MA2E vers Azure**. On envoie **uniquement les fichiers CNI** vers Azure AI pour l'OCR. **Pas le nom, pas le matricule, pas le numéro de téléphone.** Azure ne reçoit que ce dont il a strictement besoin pour faire son travail. C'est le principe de **minimisation des données** ARTCI.
>
> **Quatrième — l'administrateur**. Ses accès et ses actions sont eux aussi journalisés : login, IP, horodatage, actions effectuées. Parce que **l'admin n'est pas au-dessus des règles** — il est même celui qu'on surveille le plus.
>
> Toutes ces données sont **chiffrées au repos** sur Azure Blob, **chiffrées en transit** en HTTPS, et le **droit à l'oubli** est implémenté — un sociétaire peut demander la suppression de ses données, et le DPO l'exécute avec un audit complet. »

### Si on me pose la question
- **« Combien de temps les données sont-elles conservées ? »**
  → « Les données nominatives **5 ans** après la fin de la relation contractuelle, conformément à la pratique courante des mutuelles ivoiriennes. Les logs d'audit ARTCI sont conservés **10 ans** — c'est la durée de prescription. »
- **« Comment vous gérez le droit à l'oubli concrètement ? »**
  → « Le DPO a une **interface dédiée** dans le back-office. Il saisit le numéro du sociétaire, le système efface ou anonymise selon le cas, et **génère une preuve d'exécution** signée cryptographiquement. Tout est tracé. »
- **« Et si Azure subit une fuite de données ? »**
  → « Les fichiers CNI sont chiffrés au repos avec une clé que **nous** gérons côté MA2E (Customer-Managed Keys). Une fuite chez Azure ne donnerait que des fichiers chiffrés inexploitables. C'est défense en profondeur. »
- **« Vous avez une analyse d'impact (PIA) ? »**
  → « Oui, c'est dans nos livrables. La matrice DCP que vous voyez ici, c'est le **socle** du PIA. »

---

## 🎤 Transitions à apprendre par cœur

Je dois enchaîner sans hésiter — c'est ça qui donne l'impression de **maîtrise**.

| De → vers | Ce que je dis |
|---|---|
| Page 6 → Page 8 | « Maintenant qu'on a vu qui fait quoi, regardons **comment ça se passe concrètement** — le parcours du sociétaire de bout en bout. » |
| Page 8 → Page 9 | « Ce parcours s'appuie sur **des objets métier précis** qu'on stocke en base — voici lesquels. » |
| Page 9 → Page 10 | « Ces entités vivent dans une architecture logicielle structurée, qu'on va voir maintenant. » |
| Page 10 → Page 11 | « Le squelette posé, voyons les **briques technologiques** qui le font tenir. » |
| Page 11 → Page 12 | « Voilà pour le logiciel. Maintenant, **comment ça tourne physiquement** en production. » |
| Page 12 → Page 13 | « On a vu l'infra. Maintenant, **comment on la sécurise par zonage réseau**. » |
| Page 13 → Page 14 | « Cette infra demande quelles ressources concrètes ? Voici la **commande détaillée**. » |
| Page 14 → Page 15 | « Et pour faire dialoguer tout ça, voici la **matrice des flux réseau** autorisés. » |
| Page 15 → Page 16 | « Reste à savoir **où on déploie tout ça**. C'est le mode de déploiement. » |
| Page 16 → Page 18 | « Et puisqu'on parle de données personnelles, voici **précisément lesquelles** on traite et pourquoi. » |

---

## ✅ Les 3 messages que je veux absolument faire passer

Si je ne devais retenir que 3 choses du jury, ce serait :

1. **« On a construit une plateforme métier, pas une démo. »** — chaque brique a une raison d'être justifiée, rien n'est gratuit.
2. **« La conformité ARTCI n'est pas un ajout, c'est dans l'ADN. »** — module audit dès la couche métier, journal immuable, chiffrement au repos.
3. **« On est dimensionnés pour 6 ordres de grandeur au-dessus du besoin. »** — tranquillité totale pour la phase de pilotage, scaling linéaire si besoin.

---

## ⚠️ Pièges à éviter pendant la présentation

- **Ne PAS lire les noms techniques** — je dis "le bot", pas "le service d'extraction OCR".
- **Ne PAS m'excuser** — si un slide est dense, je le revendique : « Ce slide est dense parce que… »
- **Ne PAS dire "c'est compliqué"** — je dis "c'est structuré", "c'est isolé", "c'est testable".
- **Toujours revenir au métier** : « ça permet à l'agent MA2E de… », « ça garantit au sociétaire que… ».
- **Pause respiratoire** entre chaque slide — 1 seconde de silence vaut 10 mots de bla-bla.

---

## 🎯 Une dernière phrase qui ferme

Si je termine ce bloc architecture sur une note forte, je peux dire :

> **« Cette architecture n'est pas un schéma de présentation. Elle est dimensionnée,
> elle est sécurisée par zonage réseau, elle est conforme ARTCI dès la conception,
> et elle est prête à recevoir vos 50 000 premiers sociétaires. »**

Et je passe la main à la suite.

---

## 📋 Cheat sheet — chiffres à savoir par cœur

Les chiffres que je dois pouvoir balancer **sans réfléchir** si on me les demande :

| Quoi | Valeur | Pourquoi je dois la connaître |
|---|---|---|
| Cible sociétaires 3 ans | 50 000 | Toute mon archi est dimensionnée pour |
| Durée parcours sociétaire | < 10 min | Argument réduction de friction |
| SLA décision agent | 24h ouvrées | Argument expérience utilisateur |
| Taux d'automatisation parcours | > 70% | Argument efficience opérationnelle |
| Délai ancienne procédure papier | 2 semaines | Argument transformation digitale |
| Pic utilisateurs simultanés | 200 | Référence Front Web |
| Agents back-office simultanés | 30 | Référence Back Office |
| Charge API soutenue | 300 req/min | Référence FastAPI |
| RAM base PostgreSQL | 32 Go | La plus grosse couche, justifiée par pgvector |
| Stockage Azure Blob estimé | 500 Go → 1 To | Élastique, croît avec l'usage |
| RPO / RTO | 5 min / 30 min | Plan de reprise documenté |
| Conservation données nominatives | 5 ans | Pratique mutuelles ivoiriennes |
| Conservation audit ARTCI | 10 ans | Durée de prescription |
| Loi de référence | 2013-450 | Loi ARTCI sur les données personnelles |
| Coût IA par sociétaire | < 1 USD | Argument Cloud vs hébergement interne |
| Marge de scaling | 6 ordres de grandeur | Notre capacité vs notre besoin |
