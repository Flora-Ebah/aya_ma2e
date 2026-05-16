# Démo MA2E — comme je vais le dire

---

## Ouverture (2 min) — la vue d'ensemble

> « Donc voilà, en gros, ce qu'on a là, c'est une plateforme d'assistant virtuel pour MA2E. L'idée, c'est de digitaliser tout le rapport entre la mutuelle et ses sociétaires — de l'inscription jusqu'au suivi du dossier — sans qu'ils aient besoin de se déplacer en agence. »

> « Concrètement, le sociétaire a un seul point d'entrée. Soit il scanne un QR code — sur sa facture CIE, à l'agence, dans un mail — soit il clique sur le lien direct. Il arrive sur une page d'accueil propre, et il choisit son canal : **WhatsApp** ou **chat web**. Derrière, peu importe le canal, c'est le même assistant, le même système, la même base de données. »

> « Et cet assistant fait **trois choses**. »

> « **Un — l'identification.** Le sociétaire crée son dossier MA2E de A à Z. Photo de pièce d'identité, données pro, signature des consentements ARTCI, certification sur l'honneur. Tout ça en moins de 10 minutes, au lieu des 35 actuelles. »

> « **Deux — la mise à jour.** Le sociétaire peut changer son adresse, son téléphone, sa situation familiale, sans appeler personne, sans rendez-vous. »

> « **Trois — la vérification de statut.** "Où en est mon dossier ? Il est validé ? On me demande quoi ?" — la réponse arrive directement dans la conversation. »

> « De l'autre côté, on a un **back-office pour les gestionnaires MA2E**. Quand un dossier remonte, le gestionnaire le voit en temps réel sur son dashboard. Il l'ouvre, et c'est présenté comme un vrai dossier numérique, avec un sommaire à gauche : pièces d'identité, données OCR, zone MRZ du verso, données pro, les trois consentements signés, et tout le journal d'audit. »

> « À partir de là, le gestionnaire a **trois actions possibles** : valider, rejeter avec motif, ou demander un complément. **Et chaque action déclenche une notification automatique au sociétaire sur son WhatsApp.** »
>
> *« S'il valide, le sociétaire reçoit "Votre dossier MA2E est validé". »*
> *« S'il rejette, le sociétaire reçoit le motif. »*
> *« S'il demande un complément, le sociétaire reçoit la demande et il peut compléter directement dans la conversation, sans rouvrir un nouveau parcours. »*

> « Tout est **multi-tenant nativement**. Concrètement, ça veut dire que MA2E aujourd'hui, CIE et SODECI demain, c'est la même plateforme, isolée par société, sans réécriture. »

> « Et tout ça respecte **la loi ARTCI 2013-450 dès le premier jour** — c'est pas un add-on qu'on rajoute après. »

> « En résumé : **35 minutes ramenées à 10**. **8 500 FCFA ramenés à 2 800**. Et zéro friction pour le sociétaire. »

> « Maintenant je vous montre comment ça marche en live. »

---

## La démo — je raconte pendant que je clique

> « On va suivre une sociétaire, on va l'appeler Awa, elle est technicienne SODECI à Bouaké. »

### Le QR code et le choix
> « Awa scanne le QR code sur sa facture. Elle arrive ici. »
> « Vous voyez, deux options : WhatsApp ou chat web. Nous derrière, c'est le même backend. »

### Le consentement
> « Elle choisit WhatsApp. Le bot la salue. »
> « Premier moment fort : on lui demande son consentement, conforme article 16. Tant qu'elle n'a pas dit oui explicitement, on ne collecte rien. Et son oui est signé, horodaté, archivé. »

### L'OCR
> « Elle envoie une photo de sa CNI recto. L'IA lit les champs en deux secondes. Verso, on lit la zone MRZ, norme ICAO 9303 — la même que les passeports. »
> « Le bot lui montre ce qu'il a lu. Si l'OCR se trompe, elle corrige. »

### La fin du parcours
> « Elle finit avec ses infos pro — matricule, employeur, fonction. Dernière étape, certification sur l'honneur. Le dossier est créé. »
> « En tout : moins de 3 minutes en démo. »

### Le back-office MA2E
> « Maintenant je passe côté gestionnaire. »
> « Voici le dashboard. La liste des dossiers. Et là, c'est celui d'Awa qui vient d'arriver. »
> « Quand je clique, j'ai une vue type document, avec un sommaire à gauche. Pièces d'identité, OCR, MRZ côte à côte, les trois consentements signés, et le journal d'audit complet. »
> « Je peux **valider**, **rejeter**, ou **demander un complément**. »
> « Si je valide → Awa reçoit la notification sur WhatsApp. Si je rejette → elle reçoit le motif. Si je demande un complément → elle reçoit la demande et elle complète dans la même conversation. »

### Vérification de statut
> « Et à tout moment, si Awa veut savoir où en est son dossier, elle envoie "statut" dans WhatsApp et elle a la réponse. »

### L'argument groupe
> « Une dernière chose. En haut, je peux switcher de société. MA2E aujourd'hui, mais CIE et SODECI sont déjà préparés. »
> « C'est du multi-tenant natif. Le jour où vous voulez onboarder CIE, c'est 30 minutes de configuration. Pas de réécriture. »

---

## La conformité ARTCI (1 min)

> « Trois articles ARTCI à retenir, et concrètement ce qu'on fait. »

- **Article 16, le consentement** — texte versionné, choix explicite, signé HMAC-SHA256.
- **Articles 18 à 22, les droits** — accessibles à tout moment, le sociétaire tape `DROITS` et il les a.
- **Article 31, la sécurité** — TLS 1.3, stockage chiffré, audit immuable avec hash chaîné SHA-256.

> « Vous connaissez Aïdi, le bot d'Orange Bank. Eux ont fait l'usage. Nous, on ajoute la conformité. »

---

## La suite (30 sec)

> « Ce qu'on voit aujourd'hui, c'est le pilote. Trois phases derrière. »

- **Phase 1, le pilote** — ce qu'on voit, sur une centaine de sociétaires test.
- **Phase 2, la production** — templates Meta validés, OCR souverain en secours, FR/EN.
- **Phase 3, la plateforme intelligente** — IA conversationnelle libre, éditeur de parcours no-code pour les équipes métier, support vocal WhatsApp pour les sociétaires non-lettrés. Onboarding CIE et SODECI.

---

## Closing (30 sec)

> « Trois choses à retenir. »
> « **Un**, le parcours marche de bout en bout, vous l'avez vu. »
> « **Deux**, la conformité ARTCI est tenue dès le départ — c'est pas un add-on. »
> « **Trois**, la plateforme est prête pour tout le groupe, pas juste MA2E. »
> « Concrètement, la prochaine étape c'est la déclaration ARTCI et choisir le numéro WhatsApp officiel MA2E. »

---

## Questions qui peuvent tomber

**« Pourquoi Python et pas Laravel comme dans le PRD ? »**
> « Pour aller vite, c'est du POC. La stack est découplée, on peut migrer en Sprint 1 si la DSI le demande. Le code métier ne dépend pas du langage. »

**« Le numéro WhatsApp, ça se passe comment ? »**
> « MA2E ouvre son Business Manager Meta, vérifie un numéro dédié, me donne trois clés. Je les mets dans la config, c'est en ligne. Côté Meta, 3 à 5 jours. Côté technique, un jour. »

**« Le bot ne comprend que des menus 1, 2, 3 ? »**
> « Aujourd'hui oui, c'est volontaire — plus rassurant pour le pilote. Phase 3, on bascule en compréhension libre. L'infra pgvector est déjà en place. »

**« Et les sociétaires non-lettrés ? »**
> « Phase 3, canal vocal WhatsApp. Audio → transcription → réponse texte + audio. Dialectes ivoiriens en V3. »

**« Coût d'exploitation ? »**
> « Groq gratuit jusqu'à un volume. Mindee, dix centimes par dossier. Infra dockerisée. On est très en-dessous de 2 800 FCFA. »

**« Sécurité des pièces d'identité ? »**
> « Stockage chiffré, URLs pré-signées avec durée courte, chaque accès tracé. Exigence PRD section 10.1. »

**« Et si le sociétaire abandonne en cours de parcours ? »**
> « Le dossier est sauvegardé en l'état. Il reprend où il s'était arrêté en envoyant n'importe quoi sur le canal. »

---

## Mes règles le jour J

1. **Parler lentement.** Les chiffres restent, les phrases longues non.
2. **Si WhatsApp lague, je bascule chat web tranquillement** — c'est le même système.
3. **Si une question me dépasse** : *« Bonne question, on couvre ça en Phase 3, je le note. »*
4. **Pas de "j'ai fait", "j'ai conçu"** — *« voilà comment ça marche »*, *« on a »*, *« voici »*.
