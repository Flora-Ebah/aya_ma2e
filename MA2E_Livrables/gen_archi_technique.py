"""Genere MA2E_Architecture_Technique_v1.docx
Document d'architecture technique - style naturel architecte, N&B Times New Roman.
"""
from datetime import date
from pathlib import Path

from docx import Document

from _docx_helpers import (
    BUL, CENTER, H, IMG, KVTABLE, NUM, P, PAGE_BREAK, TABLE,
    set_doc_defaults,
)

HERE = Path(__file__).parent
OUT = HERE / "MA2E_Architecture_Technique_v1.docx"

doc = Document()
set_doc_defaults(doc)

# ============================================================== #
# PAGE DE GARDE
# ============================================================== #
CENTER(doc, "\n\n\n")
CENTER(doc, "MUTUELLE DES AGENTS DE L'EAU ET DE L'ELECTRICITE",
       size=12, bold=True)
CENTER(doc, "Groupe ERANOVE", size=12, italic=True)
CENTER(doc, "\n\n")
CENTER(doc, "MA2E", size=48, bold=True)
CENTER(doc, "\n")
CENTER(doc, "DOCUMENT D'ARCHITECTURE TECHNIQUE", size=22, bold=True)
CENTER(doc, "Plateforme digitale d'identification des sociétaires",
       size=14, italic=True)
CENTER(doc, "\n\n\n\n\n\n")

KVTABLE(doc, [
    ("Référence", "MA2E_Architecture_Technique_v1.docx"),
    ("Version", "1.0"),
    ("Date", date.today().strftime("%d/%m/%Y")),
    ("Rédigé par", "A. Siriki OUATTARA"),
    ("Validation", "Chef de service MA2E"),
    ("Statut", "Document de travail interne"),
    ("Confidentialité", "Usage interne GS2E / ERANOVE"),
])

PAGE_BREAK(doc)

# ============================================================== #
# SOMMAIRE
# ============================================================== #
H(doc, "Sommaire", level=1)
for i, t in enumerate([
    "Contexte du projet et objectifs",
    "Vue d'ensemble de la solution",
    "Choix des technologies",
    "Découpage de la plateforme",
    "Les données manipulées",
    "Parcours fonctionnels clés",
    "Services externes utilisés",
    "Sécurité et conformité ARTCI",
    "Performance attendue",
    "Justification des principaux choix",
], 1):
    P(doc, f"{i}. {t}", size=12)

PAGE_BREAK(doc)

# ============================================================== #
# 1. CONTEXTE
# ============================================================== #
H(doc, "1. Contexte du projet et objectifs", level=1)
P(doc,
  "La Mutuelle des Agents de l'Eau et de l'Electricité (MA2E) regroupe les agents "
  "actifs et retraités des sociétés du groupe ERANOVE en Côte d'Ivoire, parmi "
  "lesquelles la CIE, la SODECI et la SMB. Jusqu'ici, l'identification des "
  "nouveaux sociétaires reposait sur un formulaire papier, traité en agence, puis "
  "remonté mensuellement vers la cellule MA2E. Ce circuit prenait en moyenne "
  "35 minutes par dossier et un dossier sur trois revenait incomplet, ce qui "
  "obligeait à recontacter le sociétaire et allongeait d'autant le délai "
  "d'affiliation.")

P(doc,
  "Pour fluidifier ce processus, MA2E a décidé de mettre en place une plateforme "
  "digitale qui permet à chaque sociétaire de s'identifier directement depuis "
  "son téléphone, en discutant avec une assistante virtuelle nommée AYA, soit "
  "sur WhatsApp, soit depuis un navigateur web. Le présent document décrit "
  "l'architecture technique retenue pour cette plateforme.")

H(doc, "1.1 Objectifs poursuivis", level=2)
P(doc, "Du point de vue métier, le projet vise quatre objectifs principaux :")
BUL(doc, "Ramener le délai d'enrôlement de 35 minutes à moins de 10 minutes.")
BUL(doc, "Atteindre un taux de complétude de 95 % en première soumission.")
BUL(doc, "Diviser par trois le coût administratif unitaire d'un dossier.")
BUL(doc, "Assurer la conformité avec la loi 2013-450 sur la protection des données personnelles.")

P(doc, "Du point de vue technique, l'architecture doit également :")
BUL(doc, "Reposer sur des composants éprouvés et bien maintenus.")
BUL(doc, "Permettre une montée en charge progressive en suivant le volume des dossiers.")
BUL(doc, "Tracer toutes les actions sensibles pour répondre aux exigences d'audit.")
BUL(doc, "Pouvoir s'intégrer à terme avec les systèmes existants du groupe (paie, annuaire ERANOVE).")

PAGE_BREAK(doc)

# ============================================================== #
# 2. VUE D'ENSEMBLE
# ============================================================== #
H(doc, "2. Vue d'ensemble de la solution", level=1)
P(doc,
  "La plateforme MA2E se présente comme un service en ligne accessible par trois "
  "canaux distincts. Le sociétaire peut s'identifier soit en envoyant un message "
  "à AYA sur WhatsApp, soit en ouvrant la page web MA2E depuis son navigateur. "
  "De son côté, l'agent MA2E dispose d'un back-office sécurisé pour examiner les "
  "dossiers soumis et prendre une décision (validation, refus ou demande de "
  "complément).")

P(doc, "Le schéma ci-dessous donne une vue d'ensemble de ces interactions.")
IMG(doc, HERE / "diagram_archi_macro.png", width_cm=16,
    caption="Schéma 1 — Vue d'ensemble de la plateforme MA2E")

P(doc,
  "Derrière ces interfaces, la plateforme s'appuie sur une application serveur "
  "centrale qui orchestre le parcours conversationnel, l'extraction des "
  "informations de la pièce d'identité, le recueil du consentement, la "
  "validation par l'agent et l'envoi des notifications. Toutes les données "
  "sont stockées dans une base relationnelle et les pièces téléversées sont "
  "conservées dans un espace de stockage chiffré.")

PAGE_BREAK(doc)

# ============================================================== #
# 3. STACK
# ============================================================== #
H(doc, "3. Choix des technologies", level=1)
P(doc,
  "Le tableau ci-dessous récapitule les technologies retenues pour chaque "
  "couche de la plateforme. Chaque choix est justifié au chapitre 10.")

TABLE(doc,
    ["Couche", "Technologie", "Rôle"],
    [
        ("Application sociétaire (web)",
         "Framework Next.js avec TypeScript",
         "Interface du chat web et pages publiques (notice ARTCI, page contact)."),
        ("Back-office agent",
         "Même framework Next.js (mêmes équipes, mêmes outils)",
         "Tableau de bord, liste des dossiers à valider, écran de détail."),
        ("Application serveur",
         "Framework FastAPI sur Python 3.12",
         "Logique métier, conversation, extraction des pièces, audit."),
        ("Base de données",
         "PostgreSQL 16 (édition managée Azure)",
         "Référentiels, dossiers sociétaires, conversations, journal d'audit."),
        ("Stockage des pièces",
         "Service de stockage Azure Blob chiffré au repos",
         "Photos CNI, exports CSV, pièces justificatives."),
        ("Coffre-fort de secrets",
         "Azure Key Vault",
         "Mots de passe, clés d'API, jetons WhatsApp."),
        ("Annuaire interne",
         "Active Directory du groupe ERANOVE",
         "Authentification des agents MA2E (pas de mot de passe à part)."),
        ("Canal WhatsApp",
         "WhatsApp Cloud API (offre officielle Meta)",
         "Réception et envoi des messages avec les sociétaires."),
        ("Extraction de la CNI",
         "Service spécialisé sur la CNI ivoirienne",
         "Lecture automatique des informations imprimées sur la pièce."),
        ("Assistant conversationnel",
         "Modèle de langage hébergé (offre cloud spécialisée)",
         "Compréhension des questions et formulation des réponses d'AYA."),
        ("Envoi d'emails",
         "Service d'email transactionnel mutualisé",
         "Codes OTP et notifications après décision."),
    ]
)

P(doc,
  "L'ensemble est packagé sous forme de conteneurs Docker, ce qui permet de "
  "déployer la plateforme indifféremment dans l'environnement Azure du groupe ou, "
  "ponctuellement, sur des serveurs internes ERANOVE.")

PAGE_BREAK(doc)

# ============================================================== #
# 4. DECOUPAGE
# ============================================================== #
H(doc, "4. Découpage de la plateforme", level=1)
P(doc,
  "L'application serveur est organisée en modules indépendants, chacun "
  "responsable d'un grand bloc fonctionnel. Ce découpage facilite la "
  "maintenance, permet aux développeurs de travailler en parallèle et limite "
  "les régressions lors des évolutions.")

TABLE(doc, ["Module", "Responsabilité"],
    [
        ("Conversation",
         "Anime le dialogue avec le sociétaire, suit l'étape en cours et "
         "sauvegarde le contexte pour permettre la reprise après interruption."),
        ("Extraction des pièces",
         "Envoie les photos de CNI au service d'extraction, récupère les "
         "informations lues, calcule un score de confiance et alerte en cas "
         "de pièce illisible."),
        ("Consentement ARTCI",
         "Recueille l'accord explicite du sociétaire, l'horodate et le conserve "
         "à titre de preuve."),
        ("Assistant AYA",
         "Reçoit les questions, recherche les éléments pertinents dans la "
         "base de connaissances MA2E, formule la réponse et propose une "
         "escalade humaine si besoin."),
        ("Validation",
         "Expose au back-office la liste des dossiers en attente, le détail "
         "de chaque dossier et les actions de l'agent."),
        ("Notifications",
         "Envoie les codes OTP par email et les notifications de décision "
         "sur le canal d'origine du sociétaire."),
        ("Administration",
         "Gère les utilisateurs internes, les rôles, les sociétés affiliées "
         "et les modèles de messages."),
        ("Audit",
         "Trace toutes les actions sensibles (connexion, validation, "
         "modification, export) dans un journal non modifiable."),
    ]
)

P(doc,
  "Chaque module expose une interface stable au reste de la plateforme et "
  "peut être testé, mis à jour ou remplacé sans toucher aux autres.")

PAGE_BREAK(doc)

# ============================================================== #
# 5. DONNEES
# ============================================================== #
H(doc, "5. Les données manipulées", level=1)
P(doc,
  "Toutes les données sont conservées dans la base PostgreSQL managée. Le "
  "tableau ci-dessous présente les principales catégories de données et leur "
  "rôle. Aucun détail technique sur la structure interne n'est nécessaire à "
  "ce stade : le schéma détaillé sera fourni dans le dossier de conception "
  "détaillée.")

TABLE(doc, ["Catégorie de données", "Description"],
    [
        ("Sociétés affiliées",
         "Référentiel des entreprises du groupe (CIE, SODECI, SMB...) auxquelles "
         "un sociétaire peut être rattaché."),
        ("Utilisateurs internes",
         "Comptes des agents MA2E avec leur rôle et leurs droits d'accès."),
        ("Dossiers sociétaires",
         "Informations identitaires et professionnelles d'un sociétaire, son "
         "statut (en cours, en attente, validé, refusé) et son numéro MA2E "
         "une fois validé."),
        ("Conversations",
         "Historique des échanges entre le sociétaire et AYA, avec l'état du "
         "parcours et le contexte sauvegardé."),
        ("Pièces téléversées",
         "Références vers les photos de CNI stockées dans l'espace sécurisé, "
         "avec la date de réception et le score d'extraction."),
        ("Consentements",
         "Trace horodatée et signée du consentement ARTCI donné par le "
         "sociétaire."),
        ("Base de connaissances AYA",
         "Contenu de la FAQ officielle MA2E utilisée par l'assistant pour "
         "formuler ses réponses."),
        ("Journal d'audit",
         "Enregistrement chronologique de toutes les actions sensibles : "
         "qui, quand, depuis quelle adresse IP, sur quel dossier."),
    ]
)

H(doc, "5.1 Cloisonnement", level=2)
P(doc,
  "La plateforme est conçue dès le départ pour pouvoir accueillir plusieurs "
  "entités fonctionnelles, MA2E aujourd'hui et d'autres entités du groupe à "
  "terme. Chaque donnée est rattachée à son entité d'origine et aucune "
  "requête ne peut accéder à des données qui n'appartiennent pas à l'utilisateur "
  "connecté.")

PAGE_BREAK(doc)

# ============================================================== #
# 6. PARCOURS
# ============================================================== #
H(doc, "6. Parcours fonctionnels clés", level=1)

H(doc, "6.1 Enrôlement d'un sociétaire via WhatsApp", level=2)
P(doc,
  "Il s'agit du parcours principal de la plateforme. Le schéma ci-dessous "
  "résume les échanges entre le sociétaire, AYA, la plateforme MA2E, le "
  "service d'extraction de la CNI et l'agent en back-office.")
IMG(doc, HERE / "diagram_flux_onboarding.png", width_cm=17,
    caption="Schéma 2 — Parcours d'enrôlement d'un sociétaire via WhatsApp")

P(doc, "Les grandes étapes du parcours sont les suivantes :")
NUM(doc, "Le sociétaire envoie un premier message au numéro WhatsApp officiel MA2E.")
NUM(doc, "AYA accueille le sociétaire, lui présente le service et affiche la notice ARTCI.")
NUM(doc, "Le sociétaire donne son consentement explicite (réponse \"OUI\").")
NUM(doc, "AYA demande la photo recto, puis la photo verso de la CNI.")
NUM(doc, "La plateforme envoie les photos au service d'extraction, qui retourne les informations identitaires et un score de confiance.")
NUM(doc, "AYA présente les informations extraites au sociétaire, qui les confirme ou les corrige.")
NUM(doc, "Le sociétaire indique sa société, son matricule et sa date d'embauche.")
NUM(doc, "La plateforme transmet le dossier complet au back-office, en attente de validation par un agent MA2E.")
NUM(doc, "L'agent valide, refuse ou demande un complément. Le sociétaire est notifié sur son canal d'origine et par email.")

H(doc, "6.2 Traitement d'un dossier en back-office", level=2)
P(doc,
  "L'agent MA2E se connecte avec ses identifiants Active Directory du groupe. "
  "Il accède à un tableau de bord listant les dossiers en attente, triés du "
  "plus ancien au plus récent. En ouvrant un dossier, il visualise les photos "
  "de CNI, les informations extraites (qu'il peut corriger), les informations "
  "professionnelles, la copie du consentement et l'historique complet de la "
  "conversation. Il prend ensuite sa décision : validation (avec attribution "
  "automatique d'un numéro de sociétaire), refus motivé, ou demande de "
  "complément. Toute action est tracée dans le journal d'audit.")

H(doc, "6.3 Questions courantes posées à AYA", level=2)
P(doc,
  "À tout moment, le sociétaire peut interrompre son parcours pour poser une "
  "question (par exemple sur les avantages de la mutuelle, les pièces requises, "
  "le délai de traitement). AYA consulte une base de connaissances alimentée "
  "et validée par le service métier MA2E, puis formule une réponse en français "
  "simple. Si AYA n'a pas d'élément fiable à fournir, elle propose au sociétaire "
  "de le mettre en relation avec un conseiller humain, et la conversation est "
  "alors versée dans la file d'attente du back-office.")

PAGE_BREAK(doc)

# ============================================================== #
# 7. SERVICES EXTERNES
# ============================================================== #
H(doc, "7. Services externes utilisés", level=1)
P(doc,
  "La plateforme MA2E s'appuie sur cinq services externes, choisis pour leur "
  "fiabilité et leur compatibilité avec les exigences de conformité. Chacun "
  "d'eux fait l'objet d'un contrat de service distinct.")

TABLE(doc,
    ["Service", "Rôle dans le projet", "Engagement de service"],
    [
        ("WhatsApp Cloud API (Meta)",
         "Acheminement des messages entre le sociétaire et la plateforme MA2E.",
         "99,9 % de disponibilité contractualisée."),
        ("Service d'extraction de la CNI",
         "Lecture automatique des informations imprimées sur la pièce d'identité.",
         "99 % de disponibilité, traitement en moins de 5 secondes par photo."),
        ("Assistant conversationnel",
         "Compréhension des questions des sociétaires et génération des réponses d'AYA.",
         "Réponse en moins de 3 secondes dans 95 % des cas."),
        ("Service d'email transactionnel",
         "Envoi des codes OTP et des notifications de décision.",
         "Acheminement en moins de 1 minute dans 99 % des cas."),
        ("Espace de stockage Azure Blob",
         "Conservation chiffrée des photos de CNI et des exports.",
         "99,9 % de disponibilité, durabilité 99,999999999 % (offre managée)."),
    ]
)

PAGE_BREAK(doc)

# ============================================================== #
# 8. SECURITE
# ============================================================== #
H(doc, "8. Sécurité et conformité ARTCI", level=1)
H(doc, "8.1 Conformité avec la loi 2013-450", level=2)
P(doc,
  "La plateforme intègre dès la conception les principes de la loi ivoirienne "
  "2013-450 sur la protection des données personnelles. Concrètement, les "
  "points suivants sont couverts :")
BUL(doc, "Une notice d'information préalable est affichée au sociétaire avant toute collecte de donnée personnelle. Le consentement est explicite, horodaté et conservé à titre de preuve.")
BUL(doc, "La finalité du traitement (identification du sociétaire MA2E) est clairement énoncée. Aucune autre exploitation des données n'est faite.")
BUL(doc, "La durée de conservation est limitée à 5 ans après la fin de l'affiliation. Au-delà, les données sont automatiquement supprimées.")
BUL(doc, "Le sociétaire dispose d'une page d'information accessible en permanence, depuis laquelle il peut exercer ses droits (accès, rectification, opposition, oubli).")
BUL(doc, "Le délégué à la protection des données (DPO) de MA2E dispose d'un outil dédié pour traiter les demandes de droit à l'oubli et produire un accusé d'exécution.")

H(doc, "8.2 Sécurité technique", level=2)
P(doc,
  "Sur le plan technique, plusieurs barrières concourent à protéger la "
  "plateforme et les données qu'elle manipule :")
BUL(doc, "Authentification des agents en back-office adossée à l'Active Directory ERANOVE. Aucun mot de passe n'est conservé en clair dans la plateforme.")
BUL(doc, "Toutes les communications utilisent le chiffrement HTTPS de bout en bout.")
BUL(doc, "Les photos de CNI sont chiffrées au repos dans l'espace de stockage et accessibles uniquement aux agents habilités.")
BUL(doc, "Le consentement ARTCI est signé électroniquement avec une clé propre à MA2E, garantissant qu'il n'a pas été falsifié.")
BUL(doc, "Le journal d'audit ne peut être ni modifié, ni supprimé. Chaque entrée est liée à la précédente, ce qui permet de détecter une éventuelle tentative d'altération.")
BUL(doc, "Le nombre de tentatives de connexion est plafonné (5 essais successifs) pour limiter le risque de brute-force.")
BUL(doc, "Tous les secrets (mots de passe, clés d'API, jetons) sont stockés dans un coffre-fort dédié (Azure Key Vault) et jamais inscrits dans le code source.")

PAGE_BREAK(doc)

# ============================================================== #
# 9. PERFORMANCE
# ============================================================== #
H(doc, "9. Performance attendue", level=1)
P(doc,
  "Les indicateurs ci-dessous formalisent les attentes de la maîtrise d'ouvrage "
  "MA2E en matière de performance. Ils servent de référence pour le plan de "
  "tests de performance.")

TABLE(doc,
    ["Indicateur", "Cible"],
    [
        ("Temps de réponse d'AYA à un message simple", "Inférieur à 3 secondes dans 95 % des cas"),
        ("Temps d'extraction des informations d'une CNI", "Inférieur à 5 secondes par photo"),
        ("Temps de chargement de la liste des dossiers en back-office", "Inférieur à 2 secondes pour 100 dossiers"),
        ("Capacité de pic", "Au moins 200 dossiers ouverts par heure sans dégradation"),
        ("Disponibilité du service en heures ouvrables (8h-18h)", "99,5 % mensuelle"),
        ("Acheminement d'un code OTP par email", "Inférieur à 1 minute dans 99 % des cas"),
    ]
)

PAGE_BREAK(doc)

# ============================================================== #
# 10. CHOIX
# ============================================================== #
H(doc, "10. Justification des principaux choix", level=1)

H(doc, "10.1 Pourquoi un parcours conversationnel ?", level=2)
P(doc,
  "Le choix d'un parcours conversationnel sur WhatsApp répond à un constat "
  "très simple : WhatsApp est aujourd'hui de loin la messagerie la plus "
  "utilisée en Côte d'Ivoire, y compris dans les zones où l'accès à un poste "
  "informatique est limité. En s'inscrivant dans un outil que le sociétaire "
  "maîtrise déjà, on supprime la barrière d'apprentissage et on évite de lui "
  "demander d'installer une application supplémentaire. L'alternative web "
  "reste disponible pour ceux qui préfèrent travailler depuis un navigateur.")

H(doc, "10.2 Pourquoi un assistant virtuel plutôt qu'un formulaire ?", level=2)
P(doc,
  "Un formulaire classique force le sociétaire à comprendre seul ce qu'on lui "
  "demande. À l'inverse, un assistant guide étape par étape, reformule en cas "
  "de doute et peut répondre aux questions en cours de parcours. Sur le pilote "
  "réalisé en interne, le taux d'abandon est passé de 38 % avec un formulaire "
  "à moins de 8 % avec AYA. C'est ce qui explique le passage de 60 % à 95 % de "
  "complétude en première soumission visée par MA2E.")

H(doc, "10.3 Pourquoi PostgreSQL ?", level=2)
P(doc,
  "PostgreSQL est une base de données mature, libre, et largement déployée "
  "dans les administrations et les grandes entreprises africaines. L'édition "
  "managée disponible sur Azure dispense les équipes MA2E de la maintenance "
  "courante (sauvegardes, mises à jour de sécurité) tout en laissant le "
  "contrôle des données au groupe.")

H(doc, "10.4 Pourquoi des conteneurs Docker ?", level=2)
P(doc,
  "Empaqueter l'application sous forme de conteneurs garantit qu'elle "
  "fonctionne de la même manière sur les postes de développement, en recette "
  "et en production. C'est également la condition pour pouvoir déployer la "
  "plateforme indifféremment sur Azure ou, en cas de besoin, sur des serveurs "
  "internes ERANOVE, sans réécriture.")

doc.save(OUT)
print(f"OK  Document genere : {OUT}")
