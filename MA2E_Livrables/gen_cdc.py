"""Genere MA2E_Cahier_des_Charges_v1.docx
Cahier des charges - style naturel architecte/maitrise d'ouvrage, N&B Times New Roman.
"""
from datetime import date
from pathlib import Path

from docx import Document

from _docx_helpers import (
    BUL, CENTER, H, KVTABLE, NUM, P, PAGE_BREAK, TABLE,
    set_doc_defaults,
)

HERE = Path(__file__).parent
OUT = HERE / "MA2E_Cahier_des_Charges_v1.docx"

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
CENTER(doc, "CAHIER DES CHARGES", size=22, bold=True)
CENTER(doc, "Plateforme digitale d'identification des sociétaires",
       size=14, italic=True)
CENTER(doc, "\n\n\n\n\n\n")

KVTABLE(doc, [
    ("Référence", "MA2E_Cahier_des_Charges_v1.docx"),
    ("Version", "1.0"),
    ("Date", date.today().strftime("%d/%m/%Y")),
    ("Maître d'ouvrage", "MA2E (Mutuelle des Agents de l'Eau et de l'Electricité)"),
    ("Sponsor métier", "Direction MA2E"),
    ("Maître d'oeuvre", "GS2E"),
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
TOC = [
    "Préambule",
    "Objet du marché et périmètre",
    "Objectifs et indicateurs de performance",
    "Description du besoin fonctionnel",
    "Exigences techniques",
    "Sécurité et conformité ARTCI",
    "Exigences non fonctionnelles",
    "Planning et livraison",
    "Critères d'acceptation et recette",
    "Garantie et maintenance",
    "Modalités contractuelles",
    "Annexes",
]
for i, t in enumerate(TOC, 1):
    P(doc, f"{i}. {t}", size=12)

PAGE_BREAK(doc)

# ============================================================== #
# 1. PREAMBULE
# ============================================================== #
H(doc, "1. Préambule", level=1)

H(doc, "1.1 Présentation du maître d'ouvrage", level=2)
P(doc,
  "La Mutuelle des Agents de l'Eau et de l'Electricité (MA2E) est une mutuelle "
  "professionnelle regroupant les agents actifs et retraités des sociétés du "
  "groupe ERANOVE en Côte d'Ivoire, en particulier la Compagnie Ivoirienne "
  "d'Electricité (CIE), la Société de Distribution d'Eau de Côte d'Ivoire "
  "(SODECI) et la Société Multinationale de Bitumes (SMB).")
P(doc,
  "MA2E offre à ses sociétaires des services de prévoyance, d'épargne et "
  "d'assistance sociale. Elle assure également la gestion administrative des "
  "dossiers d'affiliation, le calcul des droits, ainsi que le versement des "
  "prestations.")

H(doc, "1.2 Contexte du groupe ERANOVE", level=2)
P(doc,
  "Le groupe ERANOVE est un acteur panafricain de premier plan dans la "
  "production et la distribution d'électricité, d'eau potable et "
  "d'assainissement. Le groupe est présent dans plusieurs pays d'Afrique de "
  "l'Ouest et conduit une politique active de transformation digitale de "
  "l'ensemble de ses filiales.")
P(doc,
  "Dans cette dynamique, MA2E souhaite moderniser le processus d'identification "
  "et d'enrôlement de ses sociétaires en proposant une expérience entièrement "
  "digitale, conforme à la réglementation ivoirienne, et capable d'être étendue "
  "à l'ensemble des filiales du groupe.")

H(doc, "1.3 Situation actuelle et problématique", level=2)
P(doc,
  "Jusqu'à présent, l'identification des nouveaux sociétaires reposait sur un "
  "formulaire papier, traité en agence puis remonté mensuellement vers la "
  "cellule MA2E. Ce circuit présente plusieurs limites identifiées :")
BUL(doc, "Délai moyen de traitement de l'ordre de 35 minutes par dossier.")
BUL(doc, "Taux de complétude au premier dépôt insuffisant : un dossier sur trois revient incomplet.")
BUL(doc, "Charge administrative importante pour les agents d'accueil et les agences.")
BUL(doc, "Difficulté à fournir des reportings consolidés au niveau groupe.")
BUL(doc, "Absence de traçabilité numérique conforme aux exigences de la loi ivoirienne 2013-450 sur la protection des données.")

P(doc,
  "Face à ce constat, MA2E souhaite mettre en place une plateforme digitale "
  "permettant aux sociétaires de s'identifier depuis leur téléphone, accompagnés "
  "par une assistante virtuelle, dans un cadre strictement conforme à la "
  "réglementation ARTCI.")

PAGE_BREAK(doc)

# ============================================================== #
# 2. OBJET DU MARCHE
# ============================================================== #
H(doc, "2. Objet du marché et périmètre", level=1)

H(doc, "2.1 Objet", level=2)
P(doc,
  "Le présent cahier des charges a pour objet la conception, le développement, "
  "la mise en oeuvre et la mise en service d'une plateforme digitale "
  "d'identification des sociétaires de la mutuelle MA2E, accessible via "
  "WhatsApp et via un navigateur web.")
P(doc,
  "La plateforme inclut une assistante virtuelle, capable d'accompagner le "
  "sociétaire pas à pas dans son parcours d'enrôlement, d'extraire "
  "automatiquement les données de sa pièce d'identité et de répondre à ses "
  "questions courantes relatives à MA2E. Le nom commercial de cette "
  "assistante sera défini ultérieurement par MA2E.")

H(doc, "2.2 Périmètre fonctionnel", level=2)
P(doc,
  "Le périmètre fonctionnel couvert par le présent marché est composé des "
  "modules suivants :")
NUM(doc, "Application sociétaire conversationnelle (WhatsApp + Web Chat).")
NUM(doc, "Assistante virtuelle conversationnelle avec base de connaissances dynamique.")
NUM(doc, "Module d'extraction OCR de la pièce d'identité ivoirienne (CNI).")
NUM(doc, "Module de gestion des consentements ARTCI signés.")
NUM(doc, "Back-office de validation des dossiers par les agents MA2E.")
NUM(doc, "Module de reporting et d'export pour la conformité.")
NUM(doc, "Journal d'audit append-only avec hash chaîné SHA-256.")
NUM(doc, "Module d'administration multi-tenant pour extension groupe.")

H(doc, "2.3 Périmètre géographique", level=2)
P(doc,
  "La plateforme est déployée initialement pour les sociétaires MA2E de Côte "
  "d'Ivoire. L'architecture est prévue pour permettre une extension à d'autres "
  "filiales ERANOVE dans la sous-région UEMOA sans réécriture applicative.")

H(doc, "2.4 Public cible", level=2)
P(doc,
  "Trois catégories d'utilisateurs sont prévues sur la plateforme :")
TABLE(doc,
      headers=["Acteur", "Profil", "Canal principal"],
      rows=[
          ["Sociétaire actif", "Agent CIE / SODECI / SMB en activité",
           "WhatsApp + Web"],
          ["Sociétaire retraité", "Ancien agent ERANOVE",
           "WhatsApp + Web"],
          ["Agent MA2E (gestionnaire)", "Personnel administratif MA2E",
           "Back-office Web"],
          ["Administrateur GS2E", "Equipe technique GS2E",
           "Back-office Web (RBAC)"],
          ["Délégué à la Protection des Données (DPO)", "Conformité ARTCI",
           "Back-office Web"],
      ])

PAGE_BREAK(doc)

# ============================================================== #
# 3. OBJECTIFS
# ============================================================== #
H(doc, "3. Objectifs et indicateurs de performance", level=1)

H(doc, "3.1 Objectifs business", level=2)
P(doc,
  "La plateforme doit permettre à MA2E d'atteindre les objectifs suivants :")
NUM(doc, "Réduire significativement le délai d'enrôlement d'un nouveau sociétaire.")
NUM(doc, "Améliorer la qualité des dossiers reçus au premier dépôt.")
NUM(doc, "Diminuer le coût administratif unitaire de traitement d'un dossier.")
NUM(doc, "Garantir la traçabilité légale de tous les consentements ARTCI.")
NUM(doc, "Faciliter le reporting groupe consolidé.")
NUM(doc, "Préparer l'extension à d'autres filiales du groupe ERANOVE.")

H(doc, "3.2 Indicateurs clés de performance (KPI)", level=2)
P(doc,
  "Les indicateurs suivants sont retenus pour mesurer l'atteinte des "
  "objectifs :")
TABLE(doc,
      headers=["Indicateur", "Valeur actuelle", "Cible à 6 mois"],
      rows=[
          ["Délai moyen d'enrôlement", "35 min", "Moins de 10 min"],
          ["Taux de complétude au premier dépôt", "67 %", "95 %"],
          ["Coût administratif unitaire d'un dossier", "Référence 100",
           "Référence 33"],
          ["Taux de conformité ARTCI", "Non mesurable",
           "100 % consentements tracés"],
          ["Taux d'adoption par les nouveaux sociétaires", "0 %",
           "70 % minimum"],
          ["Disponibilité de la plateforme", "Non mesurable", "99,5 % minimum"],
      ])

PAGE_BREAK(doc)

# ============================================================== #
# 4. BESOIN FONCTIONNEL
# ============================================================== #
H(doc, "4. Description du besoin fonctionnel", level=1)

H(doc, "4.1 Canaux d'interaction", level=2)
P(doc,
  "Le sociétaire peut interagir avec la plateforme via deux canaux principaux "
  "fonctionnant en parallèle :")
BUL(doc,
    "WhatsApp Cloud API (Meta), via un numéro officiel MA2E. C'est le canal "
    "principal, choisi pour sa pénétration massive auprès des sociétaires.")
BUL(doc,
    "Chat Web embarqué dans le site MA2E, accessible directement ou via un "
    "QR code partageable affiché en agence ou sur les factures.")
P(doc,
  "Les deux canaux partagent strictement le même parcours et la même "
  "assistante virtuelle. Une conversation peut être démarrée sur un canal et "
  "poursuivie sur l'autre.")

H(doc, "4.2 Parcours d'enrôlement digital", level=2)
P(doc,
  "Le parcours d'enrôlement est guidé par l'assistante virtuelle et "
  "structuré en huit étapes principales :")
TABLE(doc,
      headers=["#", "Etape", "Description"],
      rows=[
          ["1", "Accueil & langue",
           "Sélection du français ou de l'anglais."],
          ["2", "Consentement ARTCI (Gate 1)",
           "Présentation de la notice ARTCI, recueil du consentement explicite."],
          ["3", "Données professionnelles",
           "Société employeuse, matricule, fonction, ancienneté."],
          ["4", "Upload CNI recto",
           "Prise de la photo recto, OCR via Mindee."],
          ["5", "Upload CNI verso",
           "Prise de la photo verso, extraction MRZ ICAO 9303."],
          ["6", "Confirmation des données",
           "Le sociétaire valide ou corrige les données extraites."],
          ["7", "Consentement final (Gate 2)",
           "Acceptation du traitement complet du dossier."],
          ["8", "Soumission & accusé",
           "Le dossier est envoyé en validation, un accusé est délivré."],
      ])

P(doc,
  "Tous les consentements sont signés numériquement par un mécanisme HMAC-SHA256 "
  "et horodatés en UTC. Le sociétaire peut interrompre son parcours à tout "
  "moment et le reprendre ultérieurement.")

H(doc, "4.3 Assistante virtuelle conversationnelle", level=2)
P(doc,
  "L'assistante virtuelle conversationnelle accompagne le sociétaire tout au "
  "long de son parcours. Elle dispose de deux capacités principales :")
BUL(doc,
    "Conduire le parcours d'enrôlement par une machine à états déterministe "
    "garantissant la complétude et la cohérence du dossier final.")
BUL(doc,
    "Répondre librement aux questions des sociétaires sur la base d'une "
    "base de connaissances vectorisée (RAG), alimentée par les contenus "
    "officiels du site MA2E et les documents de référence.")
P(doc,
  "La base de connaissances est mise à jour par les administrateurs MA2E via "
  "un module dédié dans le back-office. Chaque réponse fournie par "
  "l'assistante cite ses sources documentaires.")

H(doc, "4.4 Back-office de validation", level=2)
P(doc,
  "Le back-office est l'outil de travail quotidien des agents MA2E. Il permet "
  "notamment :")
BUL(doc, "La consultation de la liste des dossiers selon différents filtres.")
BUL(doc, "L'examen complet d'un dossier individuel avec ses pièces d'identité.")
BUL(doc, "La validation, le rejet motivé, ou la demande de complément.")
BUL(doc, "La consultation du journal d'audit lié au dossier.")
BUL(doc, "L'export consolidé des dossiers validés pour le reporting groupe.")
BUL(doc, "La gestion fine des droits via le modèle RBAC (rôles agent, admin, super_admin, DPO).")

H(doc, "4.5 Reporting et exports", level=2)
P(doc,
  "La plateforme fournit aux administrateurs un module de reporting permettant :")
BUL(doc, "Le suivi des KPI métier en temps réel (volume, statuts, délais).")
BUL(doc, "L'export structuré au format CSV ou XLSX des dossiers validés.")
BUL(doc, "L'export du journal d'audit sur une période donnée, pour la conformité ARTCI.")

PAGE_BREAK(doc)

# ============================================================== #
# 5. EXIGENCES TECHNIQUES
# ============================================================== #
H(doc, "5. Exigences techniques", level=1)

H(doc, "5.1 Architecture cible", level=2)
P(doc,
  "L'architecture cible repose sur une séparation claire entre la couche de "
  "présentation, la couche métier orchestrée par un backend applicatif, et "
  "une couche de persistance s'appuyant sur une base relationnelle "
  "PostgreSQL. L'ensemble de la plateforme est conteneurisé via Docker et "
  "peut être déployé indifféremment sur Microsoft Azure ou sur le data center "
  "interne du groupe ERANOVE sans modification du code applicatif.")

H(doc, "5.2 Technologies imposées", level=2)
TABLE(doc,
      headers=["Couche", "Technologie", "Justification"],
      rows=[
          ["Frontend Web", "Next.js 14 (TypeScript) + Tailwind CSS",
           "Stack moderne, performante et facilement maintenable."],
          ["Backend applicatif", "Python 3.11 + FastAPI + SQLAlchemy",
           "Productivité, écosystème mature, intégration IA native."],
          ["Base de données", "PostgreSQL 16 + extension pgvector",
           "BD éprouvée, support natif des vecteurs pour le RAG."],
          ["Cache / sessions", "Redis 7",
           "Sessions WhatsApp, files d'attente OCR."],
          ["Stockage des pièces", "Azure Blob Storage / MinIO en alternatif",
           "Stockage objet chiffré au repos."],
          ["Conteneurisation", "Docker + docker-compose",
           "Portabilité totale entre environnements."],
          ["Authentification agents", "JWT + LDAPS Active Directory ERANOVE",
           "Réutilisation de l'annuaire groupe existant."],
      ])

H(doc, "5.3 Multi-tenant et extensibilité groupe", level=2)
P(doc,
  "L'architecture est nativement multi-tenant. Chaque entité du groupe "
  "(MA2E, futures filiales) dispose de son propre espace logique avec ses "
  "propres données, ses propres utilisateurs et sa propre configuration "
  "graphique. L'ajout d'une nouvelle entité ne nécessite pas de redéploiement "
  "applicatif.")

H(doc, "5.4 Intégrations externes", level=2)
TABLE(doc,
      headers=["Service externe", "Rôle", "Protocole"],
      rows=[
          ["WhatsApp Cloud API (Meta)",
           "Canal conversationnel principal du sociétaire",
           "HTTPS Webhook + REST"],
          ["Mindee API",
           "Extraction OCR de la CNI ivoirienne (recto + verso MRZ)",
           "HTTPS REST"],
          ["Groq (Llama 3.3 70B)",
           "Modèle de langage de l'assistante virtuelle",
           "HTTPS REST"],
          ["Azure OpenAI Embeddings (text-embedding-3-small)",
           "Vectorisation 1536 dimensions de la base de connaissances",
           "HTTPS REST"],
          ["SMTP transactionnel",
           "Notifications email aux sociétaires et agents",
           "SMTP TLS"],
          ["Active Directory ERANOVE",
           "Authentification des agents MA2E sur le back-office",
           "LDAPS"],
      ])

PAGE_BREAK(doc)

# ============================================================== #
# 6. SECURITE ET CONFORMITE
# ============================================================== #
H(doc, "6. Sécurité et conformité ARTCI", level=1)

H(doc, "6.1 Cadre légal", level=2)
P(doc,
  "La plateforme doit être strictement conforme à la loi ivoirienne n° 2013-450 "
  "du 19 juin 2013 relative à la protection des données à caractère personnel, "
  "ainsi qu'aux décisions et délibérations émises par l'Autorité de Régulation "
  "des Télécommunications et des TIC de Côte d'Ivoire (ARTCI).")
P(doc,
  "Le maître d'oeuvre doit également respecter les principes du Règlement "
  "Général sur la Protection des Données (RGPD européen) à titre de "
  "référence internationale, en particulier les principes de minimisation, "
  "de finalité et de durée limitée de conservation.")

H(doc, "6.2 Données à caractère personnel collectées", level=2)
P(doc,
  "Les données à caractère personnel collectées dans le cadre de l'enrôlement "
  "d'un sociétaire sont les suivantes :")
TABLE(doc,
      headers=["Donnée", "Catégorie", "Sensibilité"],
      rows=[
          ["Nom, prénoms, date de naissance", "Identité civile", "Normale"],
          ["Numéro CNI, photo recto et verso", "Identité civile", "Sensible"],
          ["Email, téléphone", "Contact", "Normale"],
          ["Société, matricule, fonction, ancienneté", "Professionnel", "Normale"],
          ["Conversations WhatsApp et Web", "Technique", "Normale"],
          ["Adresse IP et user-agent", "Technique", "Normale"],
          ["Score OCR et données extraites de la CNI", "Dérivée IA", "Sensible"],
          ["Consentement signé HMAC", "Preuve légale", "Normale"],
      ])

H(doc, "6.3 Consentements", level=2)
P(doc,
  "Trois portes de consentement (gates) sont implémentées dans le parcours :")
NUM(doc,
    "Gate 1 - Consentement ARTCI initial, présenté en début de parcours, "
    "obligatoire pour démarrer le traitement du dossier.")
NUM(doc,
    "Gate 2 - Consentement final, présenté avant la soumission définitive du "
    "dossier, attestant que le sociétaire valide l'intégralité des données.")
NUM(doc,
    "Gate 3 - Consentement spécifique au traitement de l'image biométrique "
    "extraite de la CNI, obligatoire dès qu'une photo est téléversée.")

P(doc,
  "Chaque consentement est signé par un mécanisme HMAC-SHA256 utilisant une "
  "clé spécifique stockée dans le coffre-fort de secrets. La signature, le "
  "texte exact présenté et la version du texte sont conservés en base.")

H(doc, "6.4 Journal d'audit", level=2)
P(doc,
  "Toutes les actions sensibles sont tracées dans un journal d'audit "
  "append-only. Chaque entrée comporte :")
BUL(doc, "L'identifiant de l'utilisateur (sociétaire, agent ou système).")
BUL(doc, "Le type d'action (création, validation, rejet, consultation, etc.).")
BUL(doc, "L'identifiant de la ressource concernée.")
BUL(doc, "L'horodatage UTC et l'adresse IP source.")
BUL(doc, "Le hash SHA-256 de l'entrée précédente (chaînage cryptographique).")
P(doc,
  "Ce mécanisme de hash chaîné garantit qu'aucune entrée du journal ne peut "
  "être supprimée ou modifiée sans détection. Le journal est conservé au "
  "minimum 12 mois et peut être exporté pour audit par l'ARTCI.")

H(doc, "6.5 Chiffrement et secrets", level=2)
BUL(doc, "Tous les flux entrants et internes sont chiffrés via TLS 1.3.")
BUL(doc, "Les photos de CNI sont chiffrées au repos dans le stockage objet.")
BUL(doc, "Les secrets applicatifs (clés API, mots de passe SMTP, clés HMAC) sont stockés dans Azure Key Vault ou un coffre équivalent on-premise.")
BUL(doc, "Aucun secret n'est versionné dans le code source ni dans les images Docker.")
BUL(doc, "Les sauvegardes PostgreSQL sont chiffrées et stockées sur un site géographiquement distinct.")

PAGE_BREAK(doc)

# ============================================================== #
# 7. EXIGENCES NON FONCTIONNELLES
# ============================================================== #
H(doc, "7. Exigences non fonctionnelles", level=1)

H(doc, "7.1 Disponibilité", level=2)
P(doc,
  "La plateforme doit présenter un taux de disponibilité minimal de 99,5 % "
  "en heures ouvrées (8h - 18h, jours ouvrés). Une haute disponibilité est "
  "assurée par la mise en place d'au moins deux instances pour le frontend "
  "et le backend applicatif, ainsi qu'une réplication PostgreSQL maître / "
  "réplica.")

H(doc, "7.2 Performance", level=2)
TABLE(doc,
      headers=["Indicateur", "Cible"],
      rows=[
          ["Temps de réponse de l'assistante virtuelle",
           "Inférieur à 3 secondes (P95)"],
          ["Temps d'extraction OCR d'une CNI complète",
           "Inférieur à 8 secondes (P95)"],
          ["Temps de chargement du back-office", "Inférieur à 2 secondes"],
          ["Volume cible d'utilisateurs simultanés",
           "200 sociétaires + 50 agents"],
          ["Volume mensuel d'enrôlements", "Capacité de 5 000 par mois"],
          ["Performance Lighthouse du site sociétaire",
           "Score supérieur à 90 sur les 3 axes (performance, accessibilité, bonnes pratiques)"],
      ])

H(doc, "7.3 Évolutivité", level=2)
P(doc,
  "L'architecture doit pouvoir absorber une multiplication par cinq du "
  "volume de sociétaires sans réécriture applicative. La scalabilité "
  "horizontale est privilégiée : ajout d'instances frontend ou backend sans "
  "interruption de service, et possibilité de séparer la base de données "
  "principale d'une base de reporting dédiée.")

H(doc, "7.4 Maintenabilité", level=2)
BUL(doc, "Code source documenté et indenté selon les standards de chaque langage.")
BUL(doc, "Couverture de tests automatisés minimale de 70 % sur le backend.")
BUL(doc, "Migrations de base de données gérées par Alembic, versionnées avec le code.")
BUL(doc, "Documentation technique livrée à jour à chaque mise en production.")
BUL(doc, "Logs applicatifs structurés en JSON, agrégés et conservés au minimum 30 jours.")

PAGE_BREAK(doc)

# ============================================================== #
# 8. PLANNING
# ============================================================== #
H(doc, "8. Planning et livraison", level=1)

H(doc, "8.1 Macro planning", level=2)
P(doc,
  "Le projet est organisé en quatre étapes principales qui s'enchaînent "
  "entre juin et juillet 2026. Les dates précises de la recette et de la "
  "mise en production sont à confirmer conjointement avec MA2E et la DSI "
  "ERANOVE.")

TABLE(doc,
      headers=["Etape", "Période", "Description"],
      rows=[
          ["01 - Mise à disposition du CDC et du Backlog produit",
           "04 juin 2026",
           "Livraison du présent cahier des charges et du backlog produit "
           "consolidé."],
          ["02 - Passage au CVATL",
           "04 juin - 08 juin 2026",
           "Préparation de la documentation CVATL (du 04 juin) puis "
           "passage au comité CVATL le 08 juin."],
          ["03 - Recette métier",
           "Date à préciser",
           "Démarrage de la recette avec les agents et le métier MA2E."],
          ["04 - Mise en production de l'application",
           "Date à préciser - début juillet 2026",
           "Conduite du changement, déploiement en pré-production, "
           "tests de sécurité et de montée en charge, puis déploiement "
           "en production début juillet."],
      ])

H(doc, "8.2 Jalons clés", level=2)
TABLE(doc,
      headers=["#", "Jalon", "Date cible", "Livrable associé"],
      rows=[
          ["01",
           "Mise à disposition du cahier des charges et du Backlog produit",
           "04 juin 2026",
           "Cahier des charges signé · Backlog produit"],
          ["02",
           "Préparation de la documentation CVATL",
           "04 juin 2026",
           "Dossier CVATL constitué (CVATL, DAT, DAS, Plan de tests)"],
          ["03",
           "Passage au comité CVATL",
           "08 juin 2026",
           "Validation par le comité CVATL"],
          ["04",
           "Démarrage de la recette métier",
           "Date à préciser",
           "Cahier de recette + environnement de recette"],
          ["05",
           "Conduite du changement",
           "Date à préciser",
           "Plan de conduite du changement, formation des agents"],
          ["06",
           "Déploiement en pré-production",
           "Date à préciser",
           "Plateforme déployée en environnement de pré-production"],
          ["07",
           "Tests de sécurité et de montée en charge",
           "Date à préciser",
           "Rapport de tests sécurité · Rapport de tests de charge"],
          ["08",
           "Déploiement en production",
           "Début juillet 2026",
           "Plateforme en production sur le périmètre MA2E"],
      ])

P(doc,
  "Les dates marquées « Date à préciser » seront figées conjointement entre "
  "MA2E, GS2E et la DSI ERANOVE à l'issue du comité CVATL du 08 juin 2026.",
  italic=True)

H(doc, "8.3 Livrables attendus", level=2)
P(doc, "Le maître d'oeuvre s'engage à fournir les livrables suivants :")
NUM(doc, "Document de Conception Validée par l'Architecte Technique Lead (CVATL).")
NUM(doc, "Document d'Architecture Technique (DAT).")
NUM(doc, "Document d'Architecture de Déploiement (DAD).")
NUM(doc, "Document d'Architecture de Sécurité (DAS).")
NUM(doc, "Backlog produit consolidé avec estimation et priorisation.")
NUM(doc, "Plan de tests fonctionnels, techniques et sécurité.")
NUM(doc, "Code source complet, déposé dans le dépôt Git du groupe ERANOVE.")
NUM(doc, "Documentation utilisateur (sociétaire et agent).")
NUM(doc, "Documentation d'exploitation (procédures, runbooks).")
NUM(doc, "PV de recette signés à l'issue de chaque phase.")

PAGE_BREAK(doc)

# ============================================================== #
# 9. RECETTE
# ============================================================== #
H(doc, "9. Critères d'acceptation et recette", level=1)

H(doc, "9.1 Recette technique", level=2)
P(doc,
  "La recette technique vérifie le bon fonctionnement de la plateforme dans "
  "son ensemble. Elle est conduite conjointement par MA2E et le maître "
  "d'oeuvre sur un environnement dédié et porte notamment sur :")
BUL(doc, "L'installation complète du système depuis les sources.")
BUL(doc, "La conformité aux exigences de performance définies au chapitre 7.")
BUL(doc, "Le bon fonctionnement des sauvegardes et de la restauration.")
BUL(doc, "Le bon fonctionnement de la chaîne CI/CD et des déploiements.")

H(doc, "9.2 Recette fonctionnelle", level=2)
P(doc,
  "La recette fonctionnelle vérifie que les parcours utilisateur sont "
  "conformes au cahier des charges. Elle s'appuie sur un cahier de tests "
  "couvrant au minimum :")
BUL(doc, "Le parcours d'enrôlement complet en français et en anglais.")
BUL(doc, "Les cas d'erreur OCR (CNI illisible, expirée, étrangère).")
BUL(doc, "Le parcours de mise à jour d'un dossier existant.")
BUL(doc, "Le parcours de validation, rejet et complément côté agent.")
BUL(doc, "La gestion des rôles et des permissions du back-office.")

H(doc, "9.3 Recette sécurité ARTCI", level=2)
P(doc,
  "La recette sécurité est conduite par le Délégué à la Protection des "
  "Données (DPO) de MA2E avec l'appui du responsable sécurité GS2E. Elle "
  "porte notamment sur :")
BUL(doc, "La conformité de la notice ARTCI affichée avant collecte.")
BUL(doc, "La présence et la signature de tous les consentements.")
BUL(doc, "Le non-modifiabilité du journal d'audit (test d'altération).")
BUL(doc, "L'isolation effective des données entre tenants.")
BUL(doc, "La vérification du chiffrement TLS 1.3 sur tous les flux entrants.")
BUL(doc, "L'audit blanc d'un dossier de bout en bout.")

PAGE_BREAK(doc)

# ============================================================== #
# 10. GARANTIE ET MAINTENANCE
# ============================================================== #
H(doc, "10. Garantie et maintenance", level=1)

H(doc, "10.1 Période de garantie", level=2)
P(doc,
  "Le maître d'oeuvre garantit le bon fonctionnement de la plateforme pendant "
  "une période de douze mois calendaires à compter de la date de mise en "
  "production effective.")
P(doc,
  "Pendant cette période, toute anomalie reproductible imputable au logiciel "
  "livré est corrigée sans coût supplémentaire pour MA2E.")

H(doc, "10.2 Maintenance corrective", level=2)
P(doc,
  "Trois niveaux de criticité sont définis pour les anomalies, avec des "
  "délais de prise en compte et de résolution associés :")
TABLE(doc,
      headers=["Niveau", "Description", "Prise en compte", "Correction"],
      rows=[
          ["Bloquante",
           "Plateforme indisponible ou perte de données",
           "Sous 2 heures ouvrées", "Sous 8 heures ouvrées"],
          ["Majeure",
           "Une fonction métier critique est dégradée",
           "Sous 4 heures ouvrées", "Sous 2 jours ouvrés"],
          ["Mineure",
           "Anomalie d'affichage ou de confort",
           "Sous 1 jour ouvré", "Selon planification mutualisée"],
      ])

H(doc, "10.3 Maintenance évolutive", level=2)
P(doc,
  "La maintenance évolutive fait l'objet d'un contrat séparé optionnel, "
  "renouvelable annuellement. Elle couvre l'ajout de nouvelles fonctionnalités "
  "demandées par MA2E hors du périmètre initial, ainsi que les mises à jour "
  "majeures des dépendances logicielles.")

PAGE_BREAK(doc)

# ============================================================== #
# 11. CONTRAT
# ============================================================== #
H(doc, "11. Modalités contractuelles", level=1)

H(doc, "11.1 Propriété intellectuelle", level=2)
P(doc,
  "Le code source spécifiquement développé pour la plateforme MA2E est la "
  "propriété pleine et entière de MA2E. Le maître d'oeuvre conserve la "
  "propriété de ses outils internes et des composants génériques préexistants. "
  "Les composants open-source utilisés conservent leur licence d'origine et "
  "sont listés dans une annexe dédiée.")

H(doc, "11.2 Confidentialité", level=2)
P(doc,
  "Le maître d'oeuvre s'engage à respecter la confidentialité de toutes les "
  "données et informations communiquées dans le cadre de la prestation. Tous "
  "les intervenants signent un engagement de confidentialité préalable. "
  "L'engagement de confidentialité reste en vigueur pendant cinq ans après la "
  "fin de la prestation.")

H(doc, "11.3 Pénalités", level=2)
P(doc,
  "En cas de non-respect des jalons contractuels du chapitre 8.2, des "
  "pénalités peuvent être appliquées dans la limite globale de 5 % du montant "
  "total du marché. Aucune pénalité n'est due en cas de retard imputable au "
  "maître d'ouvrage ou à un cas de force majeure dûment justifié.")

PAGE_BREAK(doc)

# ============================================================== #
# 12. ANNEXES
# ============================================================== #
H(doc, "12. Annexes", level=1)

H(doc, "12.1 Glossaire", level=2)
TABLE(doc,
      headers=["Terme", "Définition"],
      rows=[
          ["ARTCI",
           "Autorité de Régulation des Télécommunications et des TIC de Côte d'Ivoire"],
          ["CIE",
           "Compagnie Ivoirienne d'Electricité, filiale du groupe ERANOVE"],
          ["CNI",
           "Carte Nationale d'Identité ivoirienne"],
          ["CVATL",
           "Conception Validée par l'Architecte Technique Lead"],
          ["DAT",
           "Document d'Architecture Technique"],
          ["DAS",
           "Document d'Architecture de Sécurité"],
          ["DCP",
           "Données à Caractère Personnel"],
          ["DPO",
           "Délégué à la Protection des Données"],
          ["GS2E",
           "Groupement de Services et d'Etudes en Energie"],
          ["LDAPS",
           "Lightweight Directory Access Protocol over SSL"],
          ["MA2E",
           "Mutuelle des Agents de l'Eau et de l'Electricité"],
          ["MRZ",
           "Machine Readable Zone (zone lisible par machine au verso de la CNI)"],
          ["OCR",
           "Optical Character Recognition (reconnaissance optique de caractères)"],
          ["RAG",
           "Retrieval Augmented Generation (génération augmentée par recherche)"],
          ["RBAC",
           "Role-Based Access Control"],
          ["SODECI",
           "Société de Distribution d'Eau de la Côte d'Ivoire"],
          ["SMB",
           "Société Multinationale de Bitumes"],
          ["TLS",
           "Transport Layer Security"],
      ])

H(doc, "12.2 Références documentaires", level=2)
P(doc,
  "Le présent cahier des charges s'appuie sur les documents et textes "
  "suivants :")
BUL(doc, "Loi ivoirienne n° 2013-450 du 19 juin 2013 sur la protection des données personnelles.")
BUL(doc, "Délibérations et avis publiés par l'ARTCI sur les traitements de données.")
BUL(doc, "Standard ICAO 9303 - Machine Readable Travel Documents.")
BUL(doc, "Référentiel sécurité du groupe ERANOVE (version en vigueur).")
BUL(doc, "Politique de protection des données personnelles de MA2E.")
BUL(doc, "Charte qualité projet MA2E.")

# ============================================================== #
# Sauvegarde
# ============================================================== #
doc.save(str(OUT))
print(f"OK  Cahier des charges genere : {OUT}")
print(f"    Taille : {OUT.stat().st_size / 1024:.0f} Ko")
