"""Genere MA2E_Architecture_Deploiement_v1.docx
Style naturel architecte. Hebergement Microsoft Azure. N&B Times New Roman.
"""
from datetime import date
from pathlib import Path

from docx import Document

from _docx_helpers import (
    BUL, CENTER, H, IMG, KVTABLE, NUM, P, PAGE_BREAK, TABLE,
    set_doc_defaults,
)

HERE = Path(__file__).parent
OUT = HERE / "MA2E_Architecture_Deploiement_v1.docx"

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
CENTER(doc, "ARCHITECTURE DE DEPLOIEMENT", size=22, bold=True)
CENTER(doc, "Environnements, mise en production, supervision et reprise d'activité",
       size=14, italic=True)
CENTER(doc, "\n\n\n\n\n\n")

KVTABLE(doc, [
    ("Référence", "MA2E_Architecture_Deploiement_v1.docx"),
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
    "Choix de l'hébergement",
    "Environnements et promotion des versions",
    "Topologie en production",
    "Accès depuis Internet et gestion des noms de domaine",
    "Chaîne de mise en production",
    "Stratégie de mise en service",
    "Supervision et observabilité",
    "Sauvegarde et plan de reprise d'activité",
    "Gestion des secrets et des accès",
    "Procédures opérationnelles courantes",
    "Estimation des coûts d'hébergement",
], 1):
    P(doc, f"{i}. {t}", size=12)

PAGE_BREAK(doc)

# ============================================================== #
# 1. CHOIX HEBERGEMENT
# ============================================================== #
H(doc, "1. Choix de l'hébergement", level=1)
P(doc,
  "L'hébergement de la plateforme MA2E est réalisé sur Microsoft Azure, en "
  "cohérence avec les pratiques déjà en vigueur dans le groupe ERANOVE "
  "(utilisation de Microsoft 365, Active Directory, et services Azure pour "
  "plusieurs filiales). Ce choix présente trois avantages déterminants pour le "
  "projet :")
BUL(doc,
    "Une intégration native avec l'annuaire Active Directory du groupe, qui "
    "permet aux agents MA2E de se connecter avec leurs identifiants ERANOVE "
    "sans gérer un mot de passe supplémentaire.")
BUL(doc,
    "Un niveau d'engagement contractuel de service connu et maîtrisé par la "
    "DSI groupe, avec des procédures de support déjà documentées.")
BUL(doc,
    "Une mutualisation possible avec d'autres projets internes ERANOVE "
    "(facturation centralisée, équipes de support communes).")

P(doc,
  "La région retenue est Azure France Centre. Elle est la plus proche d'Abidjan "
  "parmi les régions Azure disponibles à ce jour, et elle est conforme aux "
  "exigences de proximité géographique souhaitées pour les données du groupe. "
  "Une bascule vers la future région Azure Afrique du Sud Nord pourra être "
  "envisagée en V2 si elle apporte un gain mesurable de latence vers les "
  "utilisateurs ivoiriens.")

P(doc,
  "Il est à noter qu'en cas de besoin opérationnel (par exemple un projet "
  "interne nécessitant un hébergement strictement sur sol ivoirien), la "
  "plateforme peut également être déployée sur des serveurs internes du "
  "groupe. L'architecture s'appuie en effet sur des conteneurs Docker "
  "portables, qui fonctionnent indifféremment sur Azure ou sur une "
  "infrastructure locale.")

PAGE_BREAK(doc)

# ============================================================== #
# 2. ENVIRONNEMENTS
# ============================================================== #
H(doc, "2. Environnements et promotion des versions", level=1)
P(doc,
  "Trois environnements distincts cohabitent : l'environnement de "
  "développement (utilisé par les équipes techniques sur leurs postes), "
  "l'environnement de recette (utilisé par la cellule métier MA2E pour valider "
  "chaque évolution), et l'environnement de production (le service rendu aux "
  "sociétaires et aux agents).")

TABLE(doc,
    ["Environnement", "Usage", "Public"],
    [
        ("Développement",
         "Mise au point des évolutions par les équipes techniques.",
         "Équipe de développement uniquement."),
        ("Recette",
         "Validation fonctionnelle par la cellule MA2E avant mise en production.",
         "Cellule MA2E + équipe technique."),
        ("Production",
         "Service rendu aux sociétaires et aux agents MA2E.",
         "Sociétaires + agents MA2E."),
    ]
)

H(doc, "2.1 Promotion d'une version", level=2)
P(doc,
  "Une évolution développée par l'équipe technique est d'abord déployée "
  "automatiquement en recette. La cellule MA2E procède aux vérifications "
  "fonctionnelles convenues, puis valide la mise en production. Cette "
  "validation est explicite : aucune version ne passe en production sans "
  "approbation écrite d'un responsable MA2E. En cas de problème détecté "
  "après mise en production, un retour à la version précédente est possible "
  "en quelques minutes.")

PAGE_BREAK(doc)

# ============================================================== #
# 3. TOPOLOGIE
# ============================================================== #
H(doc, "3. Topologie en production", level=1)
P(doc,
  "Le schéma ci-dessous présente les composants techniques déployés en "
  "production et la manière dont ils interagissent.")
IMG(doc, HERE / "diagram_topologie.png", width_cm=17,
    caption="Schéma 1 — Topologie de déploiement en production")

P(doc,
  "À l'entrée, une passerelle Azure assure le filtrage du trafic, applique "
  "les règles du pare-feu applicatif (protection contre les attaques "
  "courantes) et termine le chiffrement HTTPS. Le trafic légitime est ensuite "
  "routé vers les composants applicatifs :")

BUL(doc,
    "Le site web MA2E sert à la fois l'application sociétaire (chat web, "
    "page d'information ARTCI, page contact) et le back-office des agents.")
BUL(doc,
    "L'application serveur centrale traite la logique métier : conversation, "
    "extraction des pièces, validation des dossiers, journal d'audit.")
BUL(doc,
    "Un service de notifications dédié envoie les codes OTP par email et "
    "les notifications de décision sur WhatsApp.")

P(doc, "En profondeur, trois espaces de stockage gérés par Azure conservent les données :")
BUL(doc, "Une base de données relationnelle managée (PostgreSQL), qui contient toutes les informations métier.")
BUL(doc, "Un espace de stockage sécurisé (Azure Blob), pour les photos de CNI et les exports CSV.")
BUL(doc, "Un coffre-fort de secrets (Azure Key Vault), pour les mots de passe, clés d'API et jetons d'accès.")

H(doc, "3.1 Dimensionnement initial", level=2)
P(doc,
  "Pour le démarrage, les ressources allouées sont volontairement modestes, "
  "avec la possibilité d'augmenter rapidement la capacité si les volumes "
  "réels dépassent les prévisions.")

TABLE(doc,
    ["Composant", "Dimensionnement initial", "Capacité maximale"],
    [
        ("Site web MA2E", "1 instance, 1 cœur, 1 Go de mémoire", "Jusqu'à 3 instances"),
        ("Application serveur", "1 instance, 2 cœurs, 2 Go de mémoire", "Jusqu'à 4 instances"),
        ("Service de notifications", "1 instance, 1 cœur, 0,5 Go", "1 instance suffisante"),
        ("Base de données PostgreSQL", "2 cœurs, 4 Go de mémoire, 20 Go de stockage", "Extensible jusqu'à 8 Go"),
        ("Stockage des pièces", "Capacité initiale 20 Go", "Extensible à la demande"),
    ]
)

PAGE_BREAK(doc)

# ============================================================== #
# 4. ACCES DEPUIS INTERNET
# ============================================================== #
H(doc, "4. Accès depuis Internet et gestion des noms de domaine", level=1)
P(doc,
  "Les sociétaires et les agents accèdent à la plateforme via des adresses "
  "publiques rattachées au domaine du groupe (gs2e.ci). La DSI groupe gère "
  "déjà ce domaine ; il suffit d'y ajouter les noms suivants, qui sont "
  "publiés vers la passerelle d'entrée Azure :")

TABLE(doc,
    ["Adresse publique", "Usage"],
    [
        ("ma2e.gs2e.ci", "Site web sociétaire (chat web et pages d'information)."),
        ("agent.ma2e.gs2e.ci", "Back-office des agents MA2E."),
        ("ma2e-recette.gs2e.ci", "Environnement de recette (accessible uniquement en interne)."),
    ]
)

P(doc,
  "Chaque adresse dispose d'un certificat de chiffrement (HTTPS) renouvelé "
  "automatiquement. Le grand public ne voit que des adresses propres au "
  "groupe ERANOVE, sans référence aux fournisseurs techniques sous-jacents.")

H(doc, "4.1 Protection contre les usages abusifs", level=2)
P(doc,
  "Plusieurs mécanismes sont mis en place pour préserver la disponibilité du "
  "service :")
BUL(doc, "Un pare-feu applicatif filtre en amont les requêtes anormales (tentatives d'injection, requêtes mal formées).")
BUL(doc, "Une limitation du débit par adresse IP empêche un même client de saturer la plateforme.")
BUL(doc, "Les tentatives répétées de connexion en back-office (5 essais successifs) entraînent un blocage temporaire du compte.")
BUL(doc, "Tout trafic suspect est tracé dans la supervision pour analyse.")

PAGE_BREAK(doc)

# ============================================================== #
# 5. CHAINE MISE EN PRODUCTION
# ============================================================== #
H(doc, "5. Chaîne de mise en production", level=1)
P(doc,
  "La mise en production d'une nouvelle version est encadrée par une chaîne "
  "automatisée qui réduit les risques d'erreur humaine. Le schéma ci-dessous "
  "en présente les grandes étapes.")
IMG(doc, HERE / "diagram_cicd.png", width_cm=17,
    caption="Schéma 2 — Étapes de mise en production")

P(doc,
  "Concrètement, dès qu'un développeur soumet une modification, la chaîne "
  "exécute automatiquement les contrôles de qualité du code, lance la batterie "
  "complète des tests automatisés, et prépare le paquet d'installation. Si "
  "tout est vert, le déploiement en recette se fait sans intervention manuelle. "
  "Une fois la validation par la cellule métier obtenue, la mise en production "
  "se fait en quelques minutes, avec un retour arrière possible en cas de "
  "souci.")

H(doc, "5.1 Rythme des mises en production", level=2)
P(doc,
  "Les mises en production sont planifiées les mardis et jeudis entre 10h et "
  "11h (heure d'Abidjan), créneaux choisis pour leur faible activité sociétaire. "
  "Les correctifs de sécurité urgents échappent à cette règle et sont déployés "
  "dès que nécessaire, après accord du responsable MA2E. La cellule MA2E est "
  "informée par email au moins 24 heures avant chaque mise en production "
  "planifiée.")

PAGE_BREAK(doc)

# ============================================================== #
# 6. STRATEGIE MISE EN SERVICE
# ============================================================== #
H(doc, "6. Stratégie de mise en service", level=1)
P(doc,
  "Le déploiement initial de la plateforme se fait par paliers, pour limiter "
  "le risque opérationnel.")

NUM(doc,
    "Phase 1 — Pilote interne (1 mois) : ouverture du service à un groupe "
    "restreint de 50 sociétaires volontaires d'une seule société (CIE) pour "
    "vérifier que les parcours fonctionnent dans les conditions réelles.")
NUM(doc,
    "Phase 2 — Élargissement progressif (2 mois) : extension aux autres "
    "sociétés affiliées (SODECI, SMB, etc.), une société tous les 15 jours.")
NUM(doc,
    "Phase 3 — Mise en service générale : ouverture à l'ensemble des "
    "sociétaires éligibles, communication officielle MA2E sur les canaux "
    "habituels (affichage en agence, intranet, email).")

P(doc,
  "À chaque palier, une revue est organisée avec la cellule MA2E pour vérifier "
  "que les indicateurs sont au vert (taux de complétude, délai de traitement, "
  "satisfaction sociétaire) avant de passer au palier suivant.")

PAGE_BREAK(doc)

# ============================================================== #
# 7. SUPERVISION
# ============================================================== #
H(doc, "7. Supervision et observabilité", level=1)
P(doc,
  "La supervision de la plateforme s'appuie sur les outils intégrés à Azure "
  "et sur quelques compléments spécialisés.")

TABLE(doc,
    ["Outil", "Périmètre", "Déclenchement d'alerte"],
    [
        ("Azure Application Insights",
         "Performances et erreurs de l'application serveur et du site web.",
         "Email aux équipes techniques au-delà de 5 % d'erreurs sur 5 minutes."),
        ("Azure Monitor",
         "Consommation des ressources (mémoire, CPU, stockage), latence réseau.",
         "Email si la mémoire ou le CPU dépasse 80 % pendant plus de 10 minutes."),
        ("Sondes de disponibilité",
         "Ping toutes les minutes des adresses publiques.",
         "SMS et email si le service est indisponible plus de 2 minutes."),
        ("Journal d'audit applicatif",
         "Toutes les actions sensibles (connexion, validation, refus, export).",
         "Revue hebdomadaire par le DPO et par la cellule sécurité."),
    ]
)

H(doc, "7.1 Indicateurs métier suivis", level=2)
P(doc,
  "Au-delà de la supervision technique, des indicateurs métier sont suivis "
  "quotidiennement et présentés à la cellule MA2E sous forme de tableau de bord :")
BUL(doc, "Nombre de dossiers déposés par jour, par canal (WhatsApp / web) et par société.")
BUL(doc, "Taux de validation au premier passage.")
BUL(doc, "Délai moyen entre dépôt et décision.")
BUL(doc, "Taux d'escalade vers un conseiller humain.")
BUL(doc, "Score moyen d'extraction de la CNI.")

PAGE_BREAK(doc)

# ============================================================== #
# 8. SAUVEGARDE + PRA
# ============================================================== #
H(doc, "8. Sauvegarde et plan de reprise d'activité", level=1)
H(doc, "8.1 Stratégie de sauvegarde", level=2)
P(doc,
  "Toutes les données critiques sont sauvegardées de manière redondante. La "
  "politique retenue est la suivante :")

TABLE(doc,
    ["Type de donnée", "Fréquence de sauvegarde", "Durée de conservation"],
    [
        ("Base de données (sociétaires, conversations, audit)",
         "Sauvegarde incrémentale toutes les 6 heures, complète tous les jours.",
         "30 jours en ligne, 90 jours sur archive."),
        ("Photos de CNI et exports",
         "Versionnage natif sur le stockage Azure (toutes les modifications conservées).",
         "1 an, puis suppression automatique."),
        ("Code source de la plateforme",
         "Sauvegarde permanente sur GitHub (entreprise).",
         "Indéfinie."),
        ("Configuration des environnements et secrets",
         "Export chiffré à chaque modification.",
         "Conservé tant que la version est en service."),
    ]
)

H(doc, "8.2 Plan de reprise d'activité (PRA)", level=2)
P(doc,
  "Le plan de reprise formalise les engagements en termes de perte de données "
  "tolérable et de délai de remise en service.")

KVTABLE(doc, [
    ("Perte de données tolérable (RPO)", "Inférieure à 6 heures"),
    ("Délai de remise en service (RTO)", "Inférieur à 2 heures"),
    ("Scénario 1 : indisponibilité d'un composant applicatif",
     "Redémarrage automatique géré par Azure. Aucune intervention requise dans 95 % des cas."),
    ("Scénario 2 : corruption de la base de données",
     "Restauration de la dernière sauvegarde valide. Procédure documentée, environ 30 minutes."),
    ("Scénario 3 : indisponibilité prolongée de la région Azure",
     "Bascule vers une seconde région Azure. Procédure documentée, environ 2 heures."),
    ("Scénario 4 : compromission d'un secret (clé d'API ou jeton WhatsApp)",
     "Rotation immédiate du secret, révocation des sessions actives, analyse de l'audit."),
    ("Exercice de PRA",
     "Test trimestriel sur un environnement dédié, sans impact sur la production."),
])

PAGE_BREAK(doc)

# ============================================================== #
# 9. SECRETS
# ============================================================== #
H(doc, "9. Gestion des secrets et des accès", level=1)
P(doc,
  "Tous les secrets utilisés par la plateforme (clés d'API, jetons WhatsApp, "
  "mots de passe techniques) sont stockés dans un coffre-fort dédié, Azure "
  "Key Vault. Aucun secret n'apparaît jamais en clair dans le code source ni "
  "dans les fichiers de configuration des conteneurs.")

TABLE(doc,
    ["Secret", "Origine", "Rotation"],
    [
        ("Clé d'accès WhatsApp", "Compte Meta Business MA2E", "Tous les 60 jours (politique Meta)."),
        ("Clé d'accès au service d'extraction", "Contrat avec le partenaire", "Tous les 6 mois."),
        ("Clé de l'assistant conversationnel", "Contrat fournisseur", "Tous les 6 mois."),
        ("Clé du service email", "Contrat fournisseur", "Tous les 6 mois."),
        ("Clé de signature des consentements", "Générée par MA2E à l'installation", "Conservée tant que la plateforme est en service."),
        ("Mots de passe des bases techniques", "Générés et gérés par Azure", "Automatique tous les 90 jours."),
    ]
)

H(doc, "9.1 Bonnes pratiques appliquées", level=2)
BUL(doc, "L'accès au coffre-fort est restreint au responsable technique et à un suppléant désigné.")
BUL(doc, "Chaque accès au coffre-fort est journalisé et revu mensuellement.")
BUL(doc, "Un audit semestriel vérifie que les clés inutilisées sont bien révoquées.")
BUL(doc, "Une copie chiffrée des secrets critiques est conservée hors ligne dans un coffre 1Password administré par la DSI groupe, pour le cas où le coffre-fort Azure serait inaccessible.")

PAGE_BREAK(doc)

# ============================================================== #
# 10. PROCEDURES
# ============================================================== #
H(doc, "10. Procédures opérationnelles courantes", level=1)
P(doc,
  "Cette section décrit la marche à suivre dans les cas les plus fréquents. "
  "Les procédures complètes sont disponibles dans le wiki interne de l'équipe "
  "technique.")

H(doc, "10.1 Un sociétaire signale ne pas recevoir le code OTP par email", level=2)
NUM(doc, "Vérifier dans le journal des notifications que le code a bien été émis.")
NUM(doc, "Si le code n'a pas été émis : vérifier la disponibilité du service d'email auprès du fournisseur.")
NUM(doc, "Si le code a été émis : demander au sociétaire de vérifier son dossier de courriers indésirables.")
NUM(doc, "En dernier recours, l'agent peut générer manuellement un nouveau code depuis le back-office.")

H(doc, "10.2 Le webhook WhatsApp ne fonctionne plus", level=2)
NUM(doc, "Vérifier la supervision : le service est-il déclaré indisponible côté Meta ?")
NUM(doc, "Vérifier la validité du jeton d'accès dans le compte Meta Business.")
NUM(doc, "Vérifier la configuration du numéro WhatsApp dans le coffre-fort.")
NUM(doc, "Si le problème persiste, basculer temporairement les nouveaux sociétaires sur le chat web.")
NUM(doc, "Ouvrir un ticket de support auprès de Meta.")

H(doc, "10.3 Restauration d'un dossier supprimé par erreur", level=2)
NUM(doc, "Identifier le numéro de dossier concerné dans le back-office.")
NUM(doc, "Lancer la procédure de restauration ciblée depuis la sauvegarde la plus récente.")
NUM(doc, "Vérifier la cohérence du dossier restauré.")
NUM(doc, "Informer le sociétaire concerné via son canal habituel.")

PAGE_BREAK(doc)

# ============================================================== #
# 11. COUTS
# ============================================================== #
H(doc, "11. Estimation des coûts d'hébergement", level=1)
P(doc,
  "L'estimation ci-dessous correspond à un volume de fonctionnement normal "
  "MA2E, soit environ 1 500 nouveaux dossiers par mois et 5 000 questions "
  "posées à AYA. Les montants sont indicatifs et peuvent varier selon les "
  "tarifs négociés par la DSI groupe avec ses fournisseurs.")

TABLE(doc,
    ["Poste", "Détail", "Coût mensuel estimé"],
    [
        ("Hébergement Azure",
         "Site web, application serveur, base de données, stockage, coffre-fort.",
         "Environ 80 000 FCFA"),
        ("Service d'extraction de la CNI",
         "Forfait 1 500 documents par mois.",
         "Environ 45 000 FCFA"),
        ("Assistant conversationnel",
         "Forfait basé sur le volume de questions.",
         "Environ 20 000 FCFA"),
        ("Service d'email transactionnel",
         "5 000 emails par mois.",
         "Environ 12 000 FCFA"),
        ("Supervision (Application Insights + sondes)",
         "Suivi des erreurs et de la disponibilité.",
         "Environ 25 000 FCFA"),
        ("WhatsApp Cloud API",
         "Coût par conversation, selon barème Meta.",
         "Variable, à arbitrer avec la cellule MA2E"),
        ("Total estimé hors WhatsApp", "—", "Environ 180 000 FCFA par mois"),
    ]
)

P(doc,
  "À titre de comparaison, ce montant représente moins de 5 % du coût "
  "administratif actuel du traitement papier des dossiers, qui sera fortement "
  "réduit par la mise en service de la plateforme.")

doc.save(OUT)
print(f"OK  Document genere : {OUT}")
