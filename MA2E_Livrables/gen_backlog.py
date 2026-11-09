"""Genere MA2E_Backlog_v1.xlsx
Backlog produit oriente metier, calque sur le format SODECI (13 colonnes)
+ planification sprint (4 colonnes additionnelles : SPRINT / DATE DEBUT / DATE FIN / CHARGE J-H).
Calendrier : Sprint 1 du 15/06/2026 au 26/06/2026, Sprint 2 du 29/06/2026 au 10/07/2026.
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

OUT = Path(__file__).parent / "MA2E_Backlog_v1.xlsx"

HEADERS = [
    "ID",
    "ÉPIC / MODULE",
    "FONCTIONNALITÉ",
    "ACTEUR",
    "USER STORY",
    "DESCRIPTION TECHNIQUE",
    "CRITÈRES D'ACCEPTATION",
    "REGLE METIER",
    "PRIORITÉ",
    "SPRINT",
    "DATE DÉBUT",
    "DATE FIN",
    "CHARGE (J-H)",
    "STATUT",
    "DÉPENDANCES",
    "COMMENTAIRES",
    "NOTES AMOA",
]


def crit(*items):
    return "\n".join(f"{i+1}. {t}" for i, t in enumerate(items))


# =================================================================== #
# USER STORIES (38 au total)
# =================================================================== #
STORIES = [
    # ===== AUTHENTIFICATION =====
    {
        "id": "US-01",
        "epic": "AUTHENTIFICATION",
        "feat": "Connexion administrateur",
        "actor": "ADMINISTRATEUR",
        "story": "En tant qu'administrateur, je veux me connecter à la plateforme via login/mot de passe sécurisé, afin d'accéder aux fonctions d'administration.",
        "tech": "Formulaire de connexion email + mot de passe. Gestion des erreurs (identifiants invalides, compte verrouillé). Session avec expiration configurable. Blocage temporaire après 5 tentatives échouées.",
        "accept": crit(
            "Connexion réussie avec identifiants valides",
            "Message d'erreur clair si identifiants incorrects",
            "Blocage du compte après 5 tentatives consécutives",
            "Redirection vers le tableau de bord après connexion",
            "Session expirée redirige vers la page de connexion",
        ),
        "rule": "Mot de passe : minimum 12 caractères, 1 majuscule, 1 chiffre, 1 caractère spécial. Durée de session : 8 heures ouvrées.",
        "prio": "Haute",
        "deps": "",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-02",
        "epic": "AUTHENTIFICATION",
        "feat": "Connexion agent via Active Directory ERANOVE",
        "actor": "UTILISATEUR (Interne MA2E)",
        "story": "En tant qu'agent MA2E, je veux me connecter avec mes identifiants Active Directory du groupe, afin d'utiliser la plateforme sans gérer un mot de passe distinct.",
        "tech": "Authentification déléguée à l'Active Directory du groupe ERANOVE. La plateforme ne stocke aucune information liée au mot de passe. Récupération automatique du nom, de l'email et du service de l'agent.",
        "accept": crit(
            "Connexion réussie avec identifiants AD valides",
            "Message d'erreur clair si compte verrouillé ou mot de passe expiré",
            "Redirection vers le tableau de bord après connexion",
            "Le profil de l'agent est créé automatiquement à la première connexion",
        ),
        "rule": "Réservé aux agents internes MA2E uniquement. Le mot de passe est géré par la politique AD du groupe. Si l'utilisateur n'existe pas dans l'AD, l'accès est refusé.",
        "prio": "Haute",
        "deps": "US-01",
        "comment": "",
        "amoa": "",
    },

    # ===== ADMINISTRATION =====
    {
        "id": "US-03",
        "epic": "ADMINISTRATION",
        "feat": "Gestion des rôles et permissions",
        "actor": "ADMINISTRATEUR",
        "story": "En tant qu'administrateur, je veux gérer les rôles et permissions (Agent validateur, Superviseur, Lecteur, IT), afin de restreindre les accès selon les profils.",
        "tech": "CRUD des rôles. Attribution de permissions fines par module (Validation, Reporting, Administration, Audit).",
        "accept": crit(
            "L'administrateur peut créer, modifier ou supprimer un rôle",
            "Les droits s'appliquent immédiatement après attribution",
            "Le journal d'audit est mis à jour à chaque modification",
        ),
        "rule": "Un rôle ne peut pas être supprimé s'il est encore affecté à un utilisateur.",
        "prio": "Haute",
        "deps": "US-01",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-04",
        "epic": "ADMINISTRATION",
        "feat": "Gestion des utilisateurs internes",
        "actor": "ADMINISTRATEUR",
        "story": "En tant qu'administrateur, je veux gérer les comptes des agents MA2E et leur affecter des rôles, afin de contrôler les accès à la plateforme.",
        "tech": "CRUD des comptes utilisateurs. Attribution de rôles multiples possible. Réactivation et désactivation du compte. Vérification des droits à chaque requête.",
        "accept": crit(
            "L'administrateur peut créer, modifier, supprimer, désactiver ou réactiver un utilisateur",
            "Les droits s'appliquent immédiatement après attribution",
            "Un utilisateur peut porter plusieurs rôles",
            "Le journal d'audit retrace toutes les modifications",
        ),
        "rule": "Email professionnel obligatoire (domaine du groupe). Un utilisateur supprimé conserve ses données historiques (anonymisation). Pas de suppression si l'utilisateur a des données opérationnelles liées.",
        "prio": "Haute",
        "deps": "US-01, US-03",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-05",
        "epic": "ADMINISTRATION",
        "feat": "Paramétrage des sociétés affiliées",
        "actor": "ADMINISTRATEUR",
        "story": "En tant qu'administrateur, je veux paramétrer la liste des sociétés du groupe affiliées à la mutuelle (CIE, SODECI, SMB, etc.), afin de rattacher chaque sociétaire à la bonne entité.",
        "tech": "CRUD des sociétés. Champs : code société, nom, secteur, statut actif/inactif. La liste alimente le choix proposé au sociétaire lors de l'enrôlement.",
        "accept": crit(
            "Création réussie si nom et code uniques",
            "Erreur bloquante si doublon de nom ou de code",
            "Désactivation possible (préférable à la suppression)",
            "Une société désactivée n'apparaît plus dans les listes proposées au sociétaire",
        ),
        "rule": "Pas de doublon sur nom ou code. La désactivation est préférée à la suppression si la société a déjà des sociétaires rattachés.",
        "prio": "Haute",
        "deps": "US-04",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-06",
        "epic": "ADMINISTRATION",
        "feat": "Paramétrage des modèles de messages",
        "actor": "ADMINISTRATEUR",
        "story": "En tant qu'administrateur, je veux configurer les modèles de messages WhatsApp et email envoyés au sociétaire (accueil, demande de pièce, validation, refus, complément), afin d'unifier la communication.",
        "tech": "Interface de personnalisation par type de message. Variables dynamiques disponibles : {prenom}, {nom}, {motif}, {lien_otp}. Validation à la sauvegarde que les variables obligatoires sont présentes.",
        "accept": crit(
            "L'administrateur peut modifier chaque modèle de message",
            "Si une variable obligatoire est absente, la sauvegarde est bloquée avec un message explicite",
            "Une prévisualisation du message rendu est affichée avant sauvegarde",
            "L'historique des modifications est conservé",
        ),
        "rule": "Limite de 1024 caractères pour les messages WhatsApp. Limite de 5000 caractères pour les emails. Les paramètres s'appliquent à toutes les nouvelles communications.",
        "prio": "Moyenne",
        "deps": "US-01",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-37",
        "epic": "ADMINISTRATION",
        "feat": "Import en masse des référentiels",
        "actor": "ADMINISTRATEUR",
        "story": "En tant qu'administrateur, je veux importer en masse les référentiels (rôles, permissions, collaborateurs, employeurs, sociétaires) depuis un fichier CSV ou Excel, afin de peupler rapidement la plateforme sans saisie manuelle ligne par ligne.",
        "tech": "Interface d'import dans le back-office avec sélection du référentiel cible. Validation du fichier (entêtes, types, unicité, contraintes métier) avant insertion. Rapport d'import présentant les lignes acceptées et rejetées avec motif détaillé. Possibilité de rejouer uniquement les lignes en erreur après correction.",
        "accept": crit(
            "L'administrateur sélectionne le référentiel cible : rôle, permission, collaborateur, employeur, sociétaire",
            "Le fichier est validé avant insertion (colonnes attendues, types, unicité, format)",
            "Un rapport d'import s'affiche : nombre de lignes acceptées, rejetées avec motif",
            "Un template téléchargeable est disponible pour chaque référentiel",
            "Le rapport d'import est téléchargeable au format CSV",
            "L'import est tracé dans le journal d'audit (qui, quoi, quand, volume)",
        ),
        "rule": "Formats acceptés : CSV (UTF-8) et Excel (xlsx). Taille maximale 10 Mo. En cas d'erreur de validation, aucune ligne n'est insérée partiellement (transaction atomique). Les imports sont réservés aux administrateurs.",
        "prio": "Haute",
        "deps": "US-03, US-04, US-05",
        "comment": "",
        "amoa": "",
    },

    # ===== ONBOARDING SOCIETAIRE =====
    {
        "id": "US-07",
        "epic": "ONBOARDING SOCIÉTAIRE",
        "feat": "Démarrage de l'enrôlement via WhatsApp",
        "actor": "SOCIÉTAIRE",
        "story": "En tant que sociétaire, je veux démarrer mon enrôlement en écrivant simplement à MA2E sur WhatsApp, afin d'éviter le déplacement et le formulaire papier.",
        "tech": "Le sociétaire envoie un message au numéro WhatsApp officiel MA2E. L'assistante virtuelle répond et guide le sociétaire étape par étape. La conversation est sauvegardée pour permettre la reprise ultérieure.",
        "accept": crit(
            "Le premier message du sociétaire déclenche un accueil par l'assistante virtuelle en moins de 5 secondes",
            "Le sociétaire est guidé par un parcours conversationnel clair",
            "Aucune installation ni création de compte n'est demandée",
            "La conversation peut être reprise plus tard si elle est interrompue",
        ),
        "rule": "Le numéro WhatsApp officiel MA2E est unique et communiqué par les canaux du groupe. Le service est disponible 24h/24, 7j/7.",
        "prio": "Haute",
        "deps": "",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-08",
        "epic": "ONBOARDING SOCIÉTAIRE",
        "feat": "Démarrage de l'enrôlement via Web Chat",
        "actor": "SOCIÉTAIRE",
        "story": "En tant que sociétaire qui n'utilise pas WhatsApp, je veux démarrer mon enrôlement directement depuis un navigateur web, afin d'avoir un parcours équivalent.",
        "tech": "Page web publique embarquant le même parcours conversationnel que WhatsApp. Pas d'authentification requise. Conversation persistée dans le navigateur pour permettre la reprise.",
        "accept": crit(
            "L'accès se fait depuis une URL publique communiquée par MA2E",
            "Le parcours est identique au parcours WhatsApp (mêmes questions, même assistance)",
            "L'interface est responsive et fonctionne sur smartphone, tablette et ordinateur",
            "La conversation est reprise automatiquement si l'utilisateur revient sur le navigateur",
        ),
        "rule": "Pas de compte ni de mot de passe demandé. Chiffrement HTTPS obligatoire. L'historique reste local au navigateur tant que l'enrôlement n'est pas finalisé.",
        "prio": "Haute",
        "deps": "US-07",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-09",
        "epic": "ONBOARDING SOCIÉTAIRE",
        "feat": "Recueil du consentement ARTCI",
        "actor": "SOCIÉTAIRE",
        "story": "En tant que sociétaire, je veux comprendre clairement comment mes données seront utilisées et donner mon accord explicite, afin d'être en confiance avant de partager mes informations.",
        "tech": "Affichage d'une notice d'information préalable expliquant la finalité, les destinataires, la durée de conservation et les droits. Validation explicite par le sociétaire (réponse OUI / J'ACCEPTE). Le consentement est horodaté, signé et conservé en pièce justificative.",
        "accept": crit(
            "La notice d'information s'affiche avant toute collecte d'information personnelle",
            "Le sociétaire ne peut pas poursuivre sans accord explicite",
            "Le consentement est horodaté et conservé",
            "Le sociétaire peut consulter à tout moment le consentement qu'il a donné",
        ),
        "rule": "Conformité loi ivoirienne 2013-450 sur la protection des données personnelles. Conservation du consentement pendant 5 ans après la fin de l'affiliation. Droit à l'oubli implémenté.",
        "prio": "Haute",
        "deps": "US-07, US-08",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-10",
        "epic": "ONBOARDING SOCIÉTAIRE",
        "feat": "Saisie des informations professionnelles",
        "actor": "SOCIÉTAIRE",
        "story": "En tant que sociétaire, je veux indiquer ma société, mon matricule et ma date d'embauche, afin que MA2E rattache mon dossier au bon employeur.",
        "tech": "Étape conversationnelle proposant la liste des sociétés actives (US-05). Saisie guidée du matricule et de la date d'embauche. Vérification de format simple sur le matricule.",
        "accept": crit(
            "La liste des sociétés affichée correspond aux sociétés actives uniquement",
            "Le matricule est demandé après la sélection de la société",
            "La date d'embauche est saisie au format JJ/MM/AAAA",
            "Une erreur claire s'affiche si le format est invalide",
        ),
        "rule": "La liste des sociétés provient du référentiel administré (US-05). Le matricule est obligatoire. La date d'embauche doit être antérieure à la date du jour.",
        "prio": "Haute",
        "deps": "US-05, US-09",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-11",
        "epic": "ONBOARDING SOCIÉTAIRE",
        "feat": "Reprise d'une session d'enrôlement interrompue",
        "actor": "SOCIÉTAIRE",
        "story": "En tant que sociétaire, je veux pouvoir reprendre mon enrôlement là où je m'étais arrêté, afin de ne pas tout recommencer si j'ai été interrompu.",
        "tech": "Sauvegarde automatique de l'état de la conversation à chaque étape. Quand le sociétaire écrit à nouveau, le parcours reprend à la dernière étape validée.",
        "accept": crit(
            "Lorsqu'un sociétaire envoie un message après une pause, l'assistante reprend le contexte",
            "Le sociétaire peut demander à recommencer depuis le début à tout moment",
            "Les données déjà saisies sont conservées jusqu'à 7 jours",
        ),
        "rule": "Si le sociétaire reste inactif plus de 7 jours, la session est purgée et un nouveau parcours commence à zéro.",
        "prio": "Moyenne",
        "deps": "US-07",
        "comment": "",
        "amoa": "",
    },

    # ===== EXTRACTION DES PIECES =====
    {
        "id": "US-12",
        "epic": "EXTRACTION & VÉRIFICATION DES PIÈCES",
        "feat": "Téléversement de la pièce d'identité",
        "actor": "SOCIÉTAIRE",
        "story": "En tant que sociétaire, je veux envoyer la photo de ma CNI (recto et verso), afin que MA2E identifie de manière fiable mon identité.",
        "tech": "Le sociétaire envoie deux photos (recto et verso) directement dans la conversation. Les photos sont stockées de manière chiffrée et associées à la conversation.",
        "accept": crit(
            "L'assistante demande successivement la photo recto puis la photo verso",
            "Les formats acceptés sont JPG, PNG, HEIC, taille maximale 5 Mo par photo",
            "Si le format est invalide, un message explicite invite à réessayer",
            "Les photos sont stockées de manière chiffrée",
        ),
        "rule": "Les photos sont conservées pendant la durée de l'affiliation puis supprimées 5 ans après la désaffiliation. Aucun tiers ne peut accéder aux photos en dehors des agents habilités MA2E.",
        "prio": "Haute",
        "deps": "US-10",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-13",
        "epic": "EXTRACTION & VÉRIFICATION DES PIÈCES",
        "feat": "Extraction automatique des données de la CNI",
        "actor": "PLATEFORME",
        "story": "En tant que plateforme, je veux extraire automatiquement les informations de la CNI (nom, prénoms, date de naissance, numéro), afin d'éviter la ressaisie manuelle par le sociétaire et de réduire le risque d'erreur.",
        "tech": "Les photos sont envoyées au service OCR partenaire spécialisé sur la CNI ivoirienne. Lecture combinée de la zone visuelle et de la zone machine MRZ pour fiabiliser le résultat. Un score de confiance est calculé.",
        "accept": crit(
            "Les informations extraites sont présentées au sociétaire pour confirmation",
            "Le sociétaire peut corriger manuellement une donnée mal lue",
            "Le score de confiance est conservé pour la revue de l'agent",
            "Le traitement aboutit en moins de 5 secondes dans 95 % des cas",
        ),
        "rule": "Si le score de confiance est inférieur à 70 %, le dossier est marqué pour revue manuelle prioritaire par un agent. Aucune information n'est partagée avec des tiers en dehors de la chaîne d'extraction.",
        "prio": "Haute",
        "deps": "US-12",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-14",
        "epic": "EXTRACTION & VÉRIFICATION DES PIÈCES",
        "feat": "Détection des pièces illisibles ou non conformes",
        "actor": "PLATEFORME",
        "story": "En tant que plateforme, je veux détecter automatiquement les photos floues, sombres ou non conformes, afin de demander au sociétaire de re-soumettre avant transmission à l'agent.",
        "tech": "Contrôle automatique : luminosité, netteté, présence des champs attendus, taux de remplissage. Si un critère est manquant, l'assistante demande une nouvelle photo en expliquant le défaut.",
        "accept": crit(
            "Une photo floue déclenche un message demandant une nouvelle photo plus nette",
            "Une photo trop sombre déclenche un message demandant un meilleur éclairage",
            "Une photo qui ne contient pas une CNI ivoirienne est refusée avec un message clair",
            "Le sociétaire peut re-soumettre jusqu'à 3 fois avant escalade vers un agent",
        ),
        "rule": "Au bout de 3 échecs successifs, le dossier est mis en attente d'un échange humain. L'assistante ne juge jamais l'authenticité de la pièce : seul l'agent en back-office est habilité à valider.",
        "prio": "Haute",
        "deps": "US-13",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-36",
        "epic": "EXTRACTION & VÉRIFICATION DES PIÈCES",
        "feat": "Détection des doublons d'identification (anti-fraude)",
        "actor": "PLATEFORME",
        "story": "En tant que plateforme, je veux empêcher qu'un sociétaire ne s'identifie plusieurs fois (contrôle sur matricule, numéro de CNI et combinaison nom + prénoms + date de naissance), afin d'éviter les doublons et les tentatives d'usurpation dans le fichier MA2E.",
        "tech": "Contrôle automatique à la fin de l'enrôlement : recherche d'un dossier existant par matricule, par numéro de CNI, et par combinaison nom + prénoms + date de naissance. Si une correspondance est trouvée (dossier en cours ou validé), l'enrôlement est bloqué côté sociétaire et le doublon est listé pour revue agent dans un onglet dédié.",
        "accept": crit(
            "Un matricule déjà associé à un dossier en cours ou validé déclenche un blocage immédiat",
            "Un numéro de CNI déjà connu déclenche un blocage immédiat",
            "Une combinaison nom + prénoms + date de naissance déjà connue déclenche une alerte de doublon souple",
            "Le sociétaire bloqué reçoit un message clair l'invitant à contacter MA2E",
            "Les doublons potentiels sont consultables par les agents dans un onglet « Doublons à arbitrer »",
            "Seul un agent peut lever une alerte de doublon souple après vérification",
        ),
        "rule": "Doublon strict (blocage automatique) : matricule ou numéro de CNI déjà présent. Doublon souple (alerte agent) : nom + prénoms + date de naissance déjà connus. Aucune levée de doublon strict sans intervention d'un administrateur.",
        "prio": "Haute",
        "deps": "US-10, US-13",
        "comment": "",
        "amoa": "",
    },

    # ===== ASSISTANT IA =====
    {
        "id": "US-15",
        "epic": "ASSISTANT IA",
        "feat": "Réponse aux questions des sociétaires",
        "actor": "SOCIÉTAIRE",
        "story": "En tant que sociétaire, je veux poser une question à l'assistante à tout moment (par exemple sur les avantages MA2E, les pièces requises, le délai de traitement), afin d'obtenir une réponse claire sans appeler le service.",
        "tech": "L'assistante dispose d'une base de connaissances officielle MA2E (FAQ validée par le service métier). Pour chaque question, elle recherche les éléments pertinents et formule une réponse en français simple. Les réponses sans certitude renvoient vers un conseiller humain.",
        "accept": crit(
            "L'assistante répond en moins de 3 secondes dans 95 % des cas",
            "La réponse cite la source officielle lorsque c'est pertinent",
            "Si l'assistante n'a pas d'élément fiable, elle propose explicitement de transférer à un conseiller humain",
            "Le sociétaire peut demander une reformulation à tout moment",
        ),
        "rule": "L'assistante ne donne jamais d'information juridique ou financière non validée. Le périmètre des réponses est limité au contenu officiel MA2E. Les conversations sont supervisées pour amélioration continue de la base de connaissances.",
        "prio": "Haute",
        "deps": "US-06",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-16",
        "epic": "ASSISTANT IA",
        "feat": "Escalade vers un conseiller humain",
        "actor": "SOCIÉTAIRE",
        "story": "En tant que sociétaire, je veux pouvoir être mis en relation avec un conseiller humain à tout moment, afin de traiter un cas complexe ou une réclamation.",
        "tech": "Mot-clé déclencheur (conseiller, agent, humain) ou détection automatique si l'assistante n'a pas d'élément fiable. La demande est transférée vers la file d'attente des agents MA2E avec l'historique complet de la conversation.",
        "accept": crit(
            "L'escalade peut être demandée par le sociétaire à tout moment",
            "L'agent reçoit la conversation complète, y compris les pièces déjà téléversées",
            "Le sociétaire est informé du délai de prise en charge et reçoit un accusé de réception",
            "Pendant les heures ouvrables, la prise en charge intervient en moins de 30 minutes",
        ),
        "rule": "Horaires d'ouverture du service : du lundi au vendredi, 8h-17h. Hors horaires, le sociétaire est informé du délai. Les conversations escaladées sont prioritaires.",
        "prio": "Moyenne",
        "deps": "US-15",
        "comment": "",
        "amoa": "",
    },

    # ===== VALIDATION =====
    {
        "id": "US-17",
        "epic": "VALIDATION DOSSIER",
        "feat": "Tableau de bord des dossiers à traiter",
        "actor": "Agent MA2E",
        "story": "En tant qu'agent MA2E, je veux disposer d'un tableau de bord listant les dossiers en attente de validation, triés par ancienneté, afin d'organiser mon travail quotidien.",
        "tech": "Liste paginée des dossiers avec statut À valider. Filtres : société, date de soumission, score d'extraction. Indicateur visuel pour les dossiers prioritaires (score d'extraction faible ou ancienneté supérieure à 48h).",
        "accept": crit(
            "L'agent voit immédiatement le nombre de dossiers en attente",
            "Les filtres permettent de cibler une société, une période ou un niveau de confiance",
            "Le dossier ouvert par un autre agent affiche un indicateur en cours de traitement",
            "Le tri par défaut est par ancienneté (du plus ancien au plus récent)",
        ),
        "rule": "Un dossier ne peut être traité que par un seul agent à la fois. Les dossiers en attente plus de 48h sont signalés comme prioritaires.",
        "prio": "Haute",
        "deps": "US-04",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-18",
        "epic": "VALIDATION DOSSIER",
        "feat": "Consultation du détail d'un dossier",
        "actor": "Agent MA2E",
        "story": "En tant qu'agent MA2E, je veux consulter en un seul écran toutes les informations d'un dossier (photos CNI, données extraites, informations professionnelles, consentement), afin de prendre ma décision rapidement.",
        "tech": "Page de détail avec : photos CNI agrandies en double colonne, informations extraites éditables, informations professionnelles, copie du consentement signé, historique complet de la conversation avec le sociétaire.",
        "accept": crit(
            "Toutes les informations du dossier sont visibles sans changer d'écran",
            "Les photos CNI peuvent être agrandies pour vérification",
            "L'historique de la conversation est consultable en panneau latéral",
            "L'agent peut corriger une donnée mal extraite avant validation",
        ),
        "rule": "Toute correction manuelle est tracée dans le journal d'audit. La consultation seule ne déclenche pas d'action sur le dossier.",
        "prio": "Haute",
        "deps": "US-17",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-19",
        "epic": "VALIDATION DOSSIER",
        "feat": "Validation d'un dossier",
        "actor": "Agent MA2E",
        "story": "En tant qu'agent MA2E, je veux valider un dossier conforme, afin d'enregistrer définitivement le sociétaire dans le fichier MA2E.",
        "tech": "Bouton Valider le dossier. Génération du numéro de sociétaire MA2E selon la règle de nomenclature en vigueur. Notification au sociétaire et transmission au système de paie.",
        "accept": crit(
            "Le statut du dossier passe à Validé",
            "Un numéro de sociétaire MA2E est attribué automatiquement",
            "Le sociétaire reçoit une notification de validation (WhatsApp + email)",
            "L'action est tracée dans le journal d'audit (agent, date, dossier)",
        ),
        "rule": "Un dossier validé ne peut plus être modifié sauf par un administrateur. Le numéro de sociétaire est unique et non réutilisable.",
        "prio": "Haute",
        "deps": "US-18",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-20",
        "epic": "VALIDATION DOSSIER",
        "feat": "Refus d'un dossier avec motif obligatoire",
        "actor": "Agent MA2E",
        "story": "En tant qu'agent MA2E, je veux refuser un dossier non conforme avec un motif explicite, afin que le sociétaire comprenne la décision et puisse re-soumettre.",
        "tech": "Bouton Refuser. Sélection d'un motif parmi une liste prédéfinie (pièce non conforme, sociétaire non éligible, doublon, autre avec champ libre). Notification au sociétaire avec le motif.",
        "accept": crit(
            "Le motif de refus est obligatoire",
            "Le statut du dossier passe à Refusé",
            "Le sociétaire reçoit une notification expliquant le motif et les actions à entreprendre",
            "Le refus est tracé dans le journal d'audit",
        ),
        "rule": "Les motifs prédéfinis sont gérés depuis l'administration. Un dossier refusé peut être resoumis par le sociétaire dans un nouveau parcours.",
        "prio": "Haute",
        "deps": "US-18",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-21",
        "epic": "VALIDATION DOSSIER",
        "feat": "Demande de complément d'information",
        "actor": "Agent MA2E",
        "story": "En tant qu'agent MA2E, je veux demander un complément d'information au sociétaire (par exemple une nouvelle photo de CNI), afin de finaliser le dossier sans le refuser.",
        "tech": "Bouton Demander complément. Choix du type de complément (nouvelle photo recto, nouvelle photo verso, justificatif employeur, autre) et message libre. Notification au sociétaire avec la liste précise des éléments attendus.",
        "accept": crit(
            "L'agent sélectionne le ou les compléments demandés",
            "Le sociétaire reçoit un message clair et la conversation reprend à l'étape correspondante",
            "Le dossier reste en attente jusqu'à réception du complément",
            "Au bout de 15 jours sans réponse, le dossier est automatiquement clôturé et l'agent est notifié",
        ),
        "rule": "Le sociétaire dispose de 15 jours pour fournir le complément. Au-delà, le dossier est clôturé mais conservé pour archivage. Une nouvelle demande nécessite un nouveau parcours.",
        "prio": "Moyenne",
        "deps": "US-18",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-38",
        "epic": "VALIDATION DOSSIER",
        "feat": "Filtres avancés et tableau de bord expert sur /dossiers",
        "actor": "Agent / Superviseur MA2E",
        "story": "En tant qu'agent ou superviseur MA2E, je veux des filtres avancés et combinables (employeur, statut, période, score d'extraction, agent assigné) ainsi qu'un tableau de bord synthétique en tête de la page /dossiers, afin d'analyser finement le portefeuille et de piloter l'activité au quotidien.",
        "tech": "Enrichissement de la page /dossiers : barre de filtres multi-critères combinables (employeur, statut, période, score d'extraction, agent assigné), persistance des filtres dans l'URL pour partage et historisation, indicateurs synthétiques en tête de page (nombre par statut, ancienneté moyenne, taux de validation, taux de refus, taux de complément), tri multi-colonnes.",
        "accept": crit(
            "Plusieurs filtres peuvent être combinés simultanément",
            "Le filtre par employeur est disponible et affiche les employeurs configurés (US-05)",
            "Les indicateurs synthétiques se recalculent automatiquement à chaque changement de filtre",
            "Les filtres actifs sont reflétés dans l'URL pour permettre le partage et le retour en arrière",
            "Un bouton « Réinitialiser » remet tous les filtres à zéro",
            "Le tri multi-colonnes est conservé entre les sessions de l'utilisateur",
        ),
        "rule": "Les filtres respectent les droits de l'utilisateur (seuls les employeurs autorisés sont visibles). Les filtres sont persistés en session pour confort d'utilisation. Pas de filtre exposant des données hors périmètre de l'utilisateur.",
        "prio": "Haute",
        "deps": "US-05, US-17",
        "comment": "",
        "amoa": "",
    },

    # ===== NOTIFICATIONS =====
    {
        "id": "US-22",
        "epic": "NOTIFICATIONS",
        "feat": "Vérification d'identité par code OTP email",
        "actor": "SOCIÉTAIRE",
        "story": "En tant que sociétaire, je veux confirmer mon adresse email en saisissant un code reçu, afin de prouver que cet email m'appartient bien.",
        "tech": "Envoi automatique d'un code à 6 chiffres par email. Saisie du code dans la conversation. Validité du code limitée à 10 minutes. Maximum 3 tentatives avant blocage.",
        "accept": crit(
            "Le code est reçu dans la boîte email du sociétaire en moins de 1 minute",
            "Si le code est correct, le sociétaire passe à l'étape suivante",
            "Si le code est incorrect, un message explicite l'invite à réessayer",
            "Après 3 codes incorrects, le sociétaire est invité à recommencer la procédure",
        ),
        "rule": "Code à 6 chiffres, durée de validité 10 minutes, maximum 3 tentatives. Pas plus de 5 demandes de code par tranche de 15 minutes pour une même adresse email.",
        "prio": "Haute",
        "deps": "US-10",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-23",
        "epic": "NOTIFICATIONS",
        "feat": "Notification au sociétaire après décision",
        "actor": "PLATEFORME",
        "story": "En tant que plateforme, je veux notifier le sociétaire dès qu'une décision est prise sur son dossier (validation, refus, demande de complément), afin qu'il soit informé sans délai.",
        "tech": "Notification automatique sur le canal d'origine (WhatsApp ou Web) ET par email. Contenu adapté selon la décision : numéro de sociétaire en cas de validation, motif en cas de refus, liste précise en cas de complément.",
        "accept": crit(
            "La notification est envoyée en moins de 5 minutes après la décision de l'agent",
            "Le message est envoyé sur les deux canaux (canal d'origine + email)",
            "Le contenu reflète la décision avec un ton humain et professionnel",
            "Le sociétaire peut répondre directement sur le canal pour poser une question complémentaire",
        ),
        "rule": "Les modèles de notification sont configurables (voir US-06). Le journal d'audit conserve la trace de chaque notification émise.",
        "prio": "Haute",
        "deps": "US-19, US-20, US-21",
        "comment": "",
        "amoa": "",
    },

    # ===== REPORTING =====
    {
        "id": "US-24",
        "epic": "REPORTING & ANALYSE",
        "feat": "Suivi en temps réel de l'activité",
        "actor": "Superviseur MA2E",
        "story": "En tant que superviseur MA2E, je veux disposer d'un tableau de bord temps réel (nombre de dossiers déposés, traités, en attente, refusés, par société), afin de piloter l'activité au quotidien.",
        "tech": "Tableau de bord avec compteurs en temps réel, courbes de l'activité sur les 30 derniers jours, répartition par société et par type de décision. Filtres : période, société, agent.",
        "accept": crit(
            "Les compteurs sont actualisés toutes les minutes",
            "Le superviseur peut filtrer par période (jour, semaine, mois, plage personnalisée)",
            "Les répartitions sont affichées en graphiques (cercles, barres, courbes)",
            "L'export PDF du tableau de bord est disponible en un clic",
        ),
        "rule": "Les données affichées respectent les droits du superviseur (uniquement les sociétés autorisées). L'accès est tracé dans le journal d'audit.",
        "prio": "Haute",
        "deps": "US-19, US-20",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-25",
        "epic": "REPORTING & ANALYSE",
        "feat": "Export des sociétaires validés",
        "actor": "Administrateur MA2E",
        "story": "En tant qu'administrateur MA2E, je veux exporter la liste des sociétaires validés au format CSV ou Excel, afin de la transmettre au service paie ou à la mutuelle partenaire.",
        "tech": "Export généré avec les colonnes demandées par MA2E : numéro de sociétaire, nom, prénoms, société, matricule, date d'embauche, date de validation. Filtres par période et société. Format CSV (UTF-8) ou Excel.",
        "accept": crit(
            "L'export reflète exactement les filtres appliqués",
            "Le nom du fichier inclut la date et l'horodatage de l'export",
            "L'export est disponible en moins de 30 secondes pour un volume de 10 000 lignes",
            "Le téléchargement est tracé dans le journal d'audit (utilisateur, filtres, volume)",
        ),
        "rule": "Format conforme au gabarit communiqué par le service paie. Encodage UTF-8 avec BOM pour ouverture native dans Excel. Limite de volume par export : 50 000 lignes (au-delà : pagination).",
        "prio": "Haute",
        "deps": "US-19",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-26",
        "epic": "REPORTING & ANALYSE",
        "feat": "Indicateurs opérationnels (KPI)",
        "actor": "Superviseur MA2E",
        "story": "En tant que superviseur, je veux suivre les indicateurs clés de l'activité (délai moyen de traitement, taux de validation au premier passage, taux d'escalade vers un conseiller, taux de complétude OCR), afin de mesurer la performance du dispositif.",
        "tech": "Page dédiée aux KPI avec calcul périodique. Comparaison par rapport à la période précédente. Seuil d'alerte configurable par KPI. Export PDF disponible.",
        "accept": crit(
            "Les indicateurs sont calculés sur la période sélectionnée",
            "La comparaison avec la période précédente est affichée (variation en %)",
            "Un seuil d'alerte peut être configuré par KPI",
            "L'utilisateur peut exporter le rapport au format PDF",
        ),
        "rule": "Les KPI sont définis avec le service métier MA2E. Les seuils d'alerte sont indicatifs et n'impactent pas les données historiques.",
        "prio": "Moyenne",
        "deps": "US-24",
        "comment": "",
        "amoa": "",
    },

    # ===== AUDIT & CONFORMITE =====
    {
        "id": "US-27",
        "epic": "AUDIT & CONFORMITÉ",
        "feat": "Journalisation des actions sensibles",
        "actor": "ADMINISTRATEUR",
        "story": "En tant qu'administrateur, je veux disposer d'un journal d'audit retraçant toutes les actions sensibles (connexion, validation, refus, modification, export), afin de garantir la traçabilité et faciliter les investigations.",
        "tech": "Chaque action sensible est journalisée : utilisateur, date-heure, adresse IP, type d'action, dossier concerné. Le journal est consultable par les administrateurs uniquement.",
        "accept": crit(
            "Chaque action critique est enregistrée en moins d'1 seconde",
            "Le journal contient au minimum : utilisateur, IP, action, date-heure",
            "Rétention du journal : 12 mois minimum",
            "L'accès est réservé aux administrateurs et au DPO",
        ),
        "rule": "Rétention 12 mois. Horodatage en heure d'Abidjan (UTC). Accès uniquement administrateurs et DPO. Les entrées ne peuvent jamais être modifiées. Export CSV disponible pour audit externe.",
        "prio": "Haute",
        "deps": "US-01, US-04, US-19",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-28",
        "epic": "AUDIT & CONFORMITÉ",
        "feat": "Droit à l'oubli et anonymisation",
        "actor": "DPO",
        "story": "En tant que DPO MA2E, je veux pouvoir donner suite à une demande de droit à l'oubli d'un ancien sociétaire, afin de respecter la loi 2013-450.",
        "tech": "Procédure d'anonymisation : remplacement des données nominatives (nom, prénoms, photos, email, téléphone) par des valeurs anonymes. Conservation des données techniques nécessaires (statistiques, audit). Génération d'un accusé d'exécution.",
        "accept": crit(
            "Le DPO peut déclencher la procédure depuis le back-office",
            "Une confirmation explicite est demandée avant exécution",
            "Le dossier devient inaccessible en lecture nominale après anonymisation",
            "Un accusé d'exécution daté est produit pour le DPO",
        ),
        "rule": "L'anonymisation est irréversible. Les données statistiques et le journal d'audit sont conservés mais sans lien nominatif. Conformité loi 2013-450.",
        "prio": "Haute",
        "deps": "US-27",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-29",
        "epic": "AUDIT & CONFORMITÉ",
        "feat": "Page d'information ARTCI accessible en permanence",
        "actor": "SOCIÉTAIRE",
        "story": "En tant que sociétaire, je veux pouvoir consulter à tout moment la notice d'information ARTCI et l'exercice de mes droits, afin de garder le contrôle sur mes données.",
        "tech": "Page web publique dédiée présentant la finalité du traitement, les destinataires, la durée de conservation, l'identité du DPO et la procédure d'exercice des droits (accès, rectification, opposition, oubli).",
        "accept": crit(
            "La page est accessible depuis un lien présent dans chaque message envoyé au sociétaire",
            "La page contient les coordonnées du DPO MA2E et un formulaire de contact",
            "Toutes les demandes via le formulaire sont notifiées au DPO en moins de 24h",
            "La page est responsive et accessible aux personnes malvoyantes (norme WCAG niveau AA)",
        ),
        "rule": "Conformité loi 2013-450 et recommandations ARTCI. La page doit être tenue à jour à chaque évolution du traitement. Le DPO valide chaque mise à jour.",
        "prio": "Haute",
        "deps": "US-09",
        "comment": "",
        "amoa": "",
    },

    # ===== INTERFAÇAGE & INTÉGRATIONS =====
    {
        "id": "US-30",
        "epic": "INTERFAÇAGE & INTÉGRATIONS",
        "feat": "Connecteur API REST sécurisé vers Perfect Vision",
        "actor": "ADMINISTRATEUR",
        "story": "En tant qu'administrateur, je veux que la plateforme MA2E communique avec Perfect Vision via une API REST sécurisée, afin de synchroniser les données des sociétaires et d'éviter la double saisie dans deux systèmes distincts.",
        "tech": "Mise en place d'un client HTTP dédié vers Perfect Vision, authentification par mTLS (certificats mutuels) ou OAuth2 client_credentials. Toutes les requêtes sont signées et tracées. Le contrat d'interface (champs, formats, codes retour) est consigné dans un document Swagger / OpenAPI versionné. Les secrets de connexion sont stockés dans le coffre-fort (Azure Key Vault).",
        "accept": crit(
            "La plateforme MA2E authentifie chaque appel via mTLS ou OAuth2",
            "Toutes les requêtes sortantes sont chiffrées en TLS 1.3",
            "Le contrat d'interface est documenté en OpenAPI et versionné",
            "Aucun secret n'apparaît dans les logs applicatifs",
            "Un test de connectivité automatique est exécuté toutes les heures",
        ),
        "rule": "L'URL de Perfect Vision, les certificats et les clés sont fournis par la DSI ERANOVE. En cas de changement de contrat, la version précédente reste supportée pendant 90 jours.",
        "prio": "Haute",
        "deps": "US-01",
        "comment": "Le contrat d'interface précis sera défini conjointement avec l'équipe Perfect Vision.",
        "amoa": "",
    },
    {
        "id": "US-31",
        "epic": "INTERFAÇAGE & INTÉGRATIONS",
        "feat": "Export automatique des dossiers validés vers Perfect Vision",
        "actor": "AGENT MA2E",
        "story": "En tant qu'agent MA2E, je veux que chaque dossier validé soit automatiquement transféré à Perfect Vision, afin que la fiche sociétaire soit créée sans intervention manuelle ni risque de re-saisie erronée.",
        "tech": "Dès qu'un dossier passe au statut « validé », un job asynchrone construit le payload Perfect Vision (mapping des champs MA2E → Perfect Vision) et déclenche l'appel API. En cas d'échec, le dossier est mis dans une file d'attente de re-essai avec back-off exponentiel. Le journal d'audit retrace chaque tentative et chaque réponse de Perfect Vision.",
        "accept": crit(
            "Tout dossier validé est transmis à Perfect Vision en moins de 60 secondes",
            "Le mapping des champs est conforme au contrat d'interface documenté",
            "En cas d'échec, 3 tentatives sont effectuées avec back-off (1, 5, 30 minutes)",
            "Après 3 échecs, une alerte est envoyée à l'administrateur",
            "Le journal d'audit conserve l'horodatage et le code retour de chaque tentative",
        ),
        "rule": "Le dossier reste considéré comme validé côté MA2E même si l'export échoue. Les dossiers en échec sont visibles dans un onglet « Anomalies d'intégration » du back-office.",
        "prio": "Haute",
        "deps": "US-30, US-19",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-32",
        "epic": "INTERFAÇAGE & INTÉGRATIONS",
        "feat": "Webhook de notification temps réel vers Perfect Vision",
        "actor": "ADMINISTRATEUR",
        "story": "En tant qu'administrateur, je veux que les changements de statut d'un dossier (validation, rejet, mise à jour, droit à l'oubli) soient notifiés en temps réel à Perfect Vision, afin de garantir la cohérence permanente entre les deux systèmes.",
        "tech": "Mise en place d'un système d'événements internes (event bus) qui déclenche un webhook sortant vers une URL de réception côté Perfect Vision. Le payload est signé en HMAC-SHA256 pour permettre à Perfect Vision de vérifier l'authenticité. Les webhooks en échec sont retentés et tracés.",
        "accept": crit(
            "Chaque changement de statut produit un événement dans l'event bus",
            "Le webhook sortant est envoyé à Perfect Vision en moins de 5 secondes",
            "Le payload contient une signature HMAC vérifiable",
            "En cas d'échec, 5 tentatives sont effectuées avec back-off exponentiel",
            "Un endpoint de re-livraison manuelle est disponible pour l'administrateur",
        ),
        "rule": "Perfect Vision doit répondre par un code HTTP 2xx pour considérer le webhook comme livré. Les événements concernés : dossier_validated, dossier_rejected, dossier_updated, droit_a_l_oubli_execute.",
        "prio": "Haute",
        "deps": "US-30",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-33",
        "epic": "INTERFAÇAGE & INTÉGRATIONS",
        "feat": "Synchronisation des matricules depuis le SI RH groupe",
        "actor": "ADMINISTRATEUR",
        "story": "En tant qu'administrateur, je veux que la liste des matricules valides soit récupérée automatiquement auprès du SI RH du groupe ERANOVE, afin de vérifier en temps réel l'éligibilité d'un sociétaire à l'enrôlement et de bloquer les usurpations.",
        "tech": "Synchronisation quotidienne (cron) avec le SI RH du groupe via API REST. Stockage local d'une table de référence (matricule, société, statut actif/retraité, date d'embauche). À chaque enrôlement, le matricule saisi par le sociétaire est vérifié dans cette table. Les requêtes vers le SI RH sont mises en cache pendant 24 heures.",
        "accept": crit(
            "La synchronisation est effectuée chaque nuit à une heure paramétrable",
            "Un matricule inconnu déclenche un rejet automatique au moment de l'enrôlement",
            "Un matricule retraité est accepté mais marqué pour traitement spécifique",
            "Le rapport de synchronisation est consultable dans le back-office",
            "Une alerte est envoyée si la synchronisation échoue 2 fois consécutives",
        ),
        "rule": "La table de référence est en lecture seule pour la plateforme MA2E. La source de vérité reste le SI RH groupe. Aucune donnée RH n'est exposée à des tiers.",
        "prio": "Haute",
        "deps": "US-30, US-05",
        "comment": "L'API du SI RH ERANOVE doit être fournie. Si elle n'existe pas encore, un import CSV manuel est prévu en mode dégradé.",
        "amoa": "",
    },
    {
        "id": "US-34",
        "epic": "INTERFAÇAGE & INTÉGRATIONS",
        "feat": "Tableau de bord de supervision des flux d'intégration",
        "actor": "ADMINISTRATEUR",
        "story": "En tant qu'administrateur, je veux disposer d'un tableau de bord supervisant l'état des flux d'intégration entre MA2E et les systèmes externes (Perfect Vision, SI RH, etc.), afin de détecter rapidement les anomalies et de garantir la continuité de service.",
        "tech": "Page de supervision dans le back-office présentant : statut courant de chaque flux, nombre d'appels réussis / en échec sur les dernières 24 heures, latence moyenne, dernière exécution réussie. Les indicateurs sont rafraîchis automatiquement toutes les 30 secondes. Un historique sur 30 jours est consultable.",
        "accept": crit(
            "Le tableau de bord affiche un statut Vert / Orange / Rouge par flux",
            "Les indicateurs sont rafraîchis automatiquement",
            "Le détail d'un flux affiche les 100 derniers appels avec leur statut",
            "Un opérateur peut filtrer par date, par code retour, par direction (entrant / sortant)",
            "Un export CSV des appels est disponible pour analyse",
        ),
        "rule": "Seuls les administrateurs et les agents IT ont accès au tableau de bord. Les corps des messages contenant des DCP sont masqués sauf consultation par le DPO.",
        "prio": "Moyenne",
        "deps": "US-31, US-32",
        "comment": "",
        "amoa": "",
    },
    {
        "id": "US-35",
        "epic": "INTERFAÇAGE & INTÉGRATIONS",
        "feat": "Reprise automatique des intégrations en échec",
        "actor": "ADMINISTRATEUR",
        "story": "En tant qu'administrateur, je veux que les flux d'intégration en échec soient automatiquement repris dès que le système distant redevient disponible, afin de garantir la fiabilité des échanges sans intervention manuelle.",
        "tech": "Mise en place d'un mécanisme de file d'attente persistante (Redis ou table dédiée) pour les appels en échec. Une routine de reprise est exécutée toutes les 5 minutes : elle réessaie les appels jusqu'à 24 heures avec un back-off exponentiel. Au-delà, les appels sont mis en quarantaine et nécessitent une action manuelle.",
        "accept": crit(
            "Tout appel en échec est mis en file d'attente avec son contexte complet",
            "La routine de reprise s'exécute toutes les 5 minutes",
            "Le back-off respecte une suite (1, 5, 15, 60, 240, 1440 minutes)",
            "Au-delà de 24 heures, le flux est mis en quarantaine et l'administrateur est notifié",
            "Une action manuelle « Rejouer » permet de relancer un flux en quarantaine",
        ),
        "rule": "Les flux en quarantaine n'expirent pas tant qu'un administrateur ne les traite pas. Aucune perte de donnée n'est tolérée sur les flux critiques (dossiers validés, droit à l'oubli).",
        "prio": "Haute",
        "deps": "US-31, US-32",
        "comment": "",
        "amoa": "",
    },
]


# =================================================================== #
# PLANIFICATION SPRINTS
# Sprint 1 : 15/06/2026 (Lun) -> 26/06/2026 (Ven) - 10 j ouvres
# Sprint 2 : 29/06/2026 (Lun) -> 10/07/2026 (Ven) - 10 j ouvres
# Format: id -> (sprint, date_debut, date_fin, charge_jh)
# =================================================================== #
SPRINT_PLAN = {
    # ----- SPRINT 1 : Fondations (Auth, Admin, Onboarding, Extraction, IA base, Audit) -----
    "US-01": ("Sprint 1", "15/06/2026", "15/06/2026", 0.5),
    "US-02": ("Sprint 1", "15/06/2026", "15/06/2026", 0.5),
    "US-03": ("Sprint 1", "16/06/2026", "16/06/2026", 0.5),
    "US-04": ("Sprint 1", "16/06/2026", "16/06/2026", 0.5),
    "US-05": ("Sprint 1", "17/06/2026", "17/06/2026", 0.5),
    "US-06": ("Sprint 1", "17/06/2026", "17/06/2026", 0.5),
    "US-07": ("Sprint 1", "18/06/2026", "18/06/2026", 1.0),
    "US-08": ("Sprint 1", "19/06/2026", "19/06/2026", 0.5),
    "US-09": ("Sprint 1", "19/06/2026", "19/06/2026", 0.5),
    "US-10": ("Sprint 1", "22/06/2026", "22/06/2026", 0.5),
    "US-11": ("Sprint 1", "22/06/2026", "22/06/2026", 0.5),
    "US-12": ("Sprint 1", "23/06/2026", "23/06/2026", 0.5),
    "US-14": ("Sprint 1", "23/06/2026", "23/06/2026", 0.5),
    "US-13": ("Sprint 1", "24/06/2026", "24/06/2026", 1.0),
    "US-37": ("Sprint 1", "24/06/2026", "24/06/2026", 0.5),
    "US-15": ("Sprint 1", "25/06/2026", "25/06/2026", 1.0),
    "US-36": ("Sprint 1", "25/06/2026", "25/06/2026", 0.5),
    "US-27": ("Sprint 1", "26/06/2026", "26/06/2026", 0.5),
    "US-29": ("Sprint 1", "26/06/2026", "26/06/2026", 0.5),

    # ----- SPRINT 2 : Validation, Reporting, Notifications, Intégrations Perfect Vision / SI RH -----
    "US-16": ("Sprint 2", "29/06/2026", "29/06/2026", 0.5),
    "US-22": ("Sprint 2", "29/06/2026", "29/06/2026", 0.5),
    "US-17": ("Sprint 2", "30/06/2026", "30/06/2026", 0.5),
    "US-18": ("Sprint 2", "30/06/2026", "30/06/2026", 0.5),
    "US-19": ("Sprint 2", "01/07/2026", "01/07/2026", 0.5),
    "US-20": ("Sprint 2", "01/07/2026", "01/07/2026", 0.5),
    "US-21": ("Sprint 2", "02/07/2026", "02/07/2026", 0.5),
    "US-23": ("Sprint 2", "02/07/2026", "02/07/2026", 0.5),
    "US-24": ("Sprint 2", "03/07/2026", "03/07/2026", 1.0),
    "US-25": ("Sprint 2", "06/07/2026", "06/07/2026", 0.5),
    "US-26": ("Sprint 2", "06/07/2026", "06/07/2026", 0.5),
    "US-38": ("Sprint 2", "06/07/2026", "06/07/2026", 0.5),
    "US-28": ("Sprint 2", "07/07/2026", "07/07/2026", 0.5),
    "US-34": ("Sprint 2", "07/07/2026", "07/07/2026", 0.5),
    "US-30": ("Sprint 2", "08/07/2026", "08/07/2026", 1.0),
    "US-31": ("Sprint 2", "09/07/2026", "09/07/2026", 0.5),
    "US-32": ("Sprint 2", "09/07/2026", "09/07/2026", 0.5),
    "US-33": ("Sprint 2", "10/07/2026", "10/07/2026", 0.5),
    "US-35": ("Sprint 2", "10/07/2026", "10/07/2026", 0.5),
}


# =================================================================== #
# Generation Excel
# =================================================================== #
wb = Workbook()
ws = wb.active
ws.title = "Backlog Produit"

# Lignes 1 et 2 : titre + sous-titre
ws.cell(row=1, column=1,
        value="BACKLOG PRODUIT — Plateforme MA2E (Mutuelle des Agents de l'Eau et de l'Électricité)")
ws.cell(row=2, column=1,
        value="Planning : Sprint 1 du 15/06/2026 au 26/06/2026 — Sprint 2 du 29/06/2026 au 10/07/2026  |  "
              "Modules : Authentification, Administration, Onboarding sociétaire, Extraction & Vérification des pièces, "
              "Assistant IA, Validation, Notifications, Reporting, Audit & Conformité, "
              "Interfaçage & Intégrations (Perfect Vision, SI RH groupe)")

ws.merge_cells(start_row=1, end_row=1, start_column=1, end_column=len(HEADERS))
ws.merge_cells(start_row=2, end_row=2, start_column=1, end_column=len(HEADERS))

ws.cell(row=1, column=1).font = Font(name="Calibri", size=13, bold=True)
ws.cell(row=2, column=1).font = Font(name="Calibri", size=10, italic=True)
ws.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
ws.cell(row=2, column=1).alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

# Ligne 3 : en-tetes
SPRINT_COLS = {"SPRINT", "DATE DÉBUT", "DATE FIN", "CHARGE (J-H)"}
for j, h in enumerate(HEADERS, start=1):
    cell = ws.cell(row=3, column=j, value=h)
    cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFFFF")
    # Couleur differente pour les colonnes de planification
    fill_color = "FFB45309" if h in SPRINT_COLS else "FF1F4E79"
    cell.fill = PatternFill("solid", fgColor=fill_color)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

# Couleur de fond legere pour les cellules de planification (sprint 1 vs sprint 2)
sprint1_fill = PatternFill("solid", fgColor="FFFEF3C7")  # jaune tres clair
sprint2_fill = PatternFill("solid", fgColor="FFDCFCE7")  # vert tres clair

# Donnees
for i, s in enumerate(STORIES, start=4):
    plan = SPRINT_PLAN.get(s["id"], ("", "", "", ""))
    sprint, d_deb, d_fin, charge = plan
    row = [
        s["id"],
        s["epic"],
        s["feat"],
        s["actor"],
        s["story"],
        s["tech"],
        s["accept"],
        s["rule"],
        s["prio"],
        sprint,
        d_deb,
        d_fin,
        charge,
        "À faire",
        s["deps"],
        s["comment"],
        s["amoa"],
    ]
    for j, v in enumerate(row, start=1):
        cell = ws.cell(row=i, column=j, value=v)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.font = Font(name="Calibri", size=10)
        # Surligner les colonnes de planification selon le sprint
        if HEADERS[j - 1] in SPRINT_COLS:
            if sprint == "Sprint 1":
                cell.fill = sprint1_fill
            elif sprint == "Sprint 2":
                cell.fill = sprint2_fill
            cell.alignment = Alignment(wrap_text=True, vertical="top", horizontal="center")

# Bordures fines sur l'ensemble
thin = Side(border_style="thin", color="FF7F7F7F")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
for row in ws.iter_rows(min_row=3, max_row=3 + len(STORIES),
                         min_col=1, max_col=len(HEADERS)):
    for cell in row:
        cell.border = border

# Largeurs de colonnes
widths = {
    "A": 8,    # ID
    "B": 22,   # EPIC
    "C": 28,   # FONCTIONNALITE
    "D": 22,   # ACTEUR
    "E": 50,   # USER STORY
    "F": 45,   # DESCRIPTION TECHNIQUE
    "G": 50,   # CRITERES
    "H": 45,   # REGLE METIER
    "I": 11,   # PRIORITE
    "J": 11,   # SPRINT
    "K": 13,   # DATE DEBUT
    "L": 13,   # DATE FIN
    "M": 12,   # CHARGE (J-H)
    "N": 11,   # STATUT
    "O": 18,   # DEPENDANCES
    "P": 22,   # COMMENTAIRES
    "Q": 22,   # NOTES AMOA
}
for col, w in widths.items():
    ws.column_dimensions[col].width = w

# Hauteur ligne 1 et 2
ws.row_dimensions[1].height = 24
ws.row_dimensions[2].height = 40
ws.row_dimensions[3].height = 32

# Hauteur min raisonnable pour les lignes de stories
for i in range(4, 4 + len(STORIES)):
    ws.row_dimensions[i].height = 110

# Geler les en-tetes
ws.freeze_panes = "B4"

# Filtre automatique
ws.auto_filter.ref = f"A3:{get_column_letter(len(HEADERS))}{3 + len(STORIES)}"


# =================================================================== #
# Onglet 2 : Synthese
# =================================================================== #
ws2 = wb.create_sheet("Synthèse")
ws2["A1"] = "SYNTHÈSE DU BACKLOG MA2E"
ws2["A1"].font = Font(name="Calibri", size=14, bold=True)
ws2.merge_cells("A1:D1")

ws2["A3"] = "Nombre total d'user stories"
ws2["B3"] = len(STORIES)

# Repartition par epic
epics = {}
for s in STORIES:
    epics[s["epic"]] = epics.get(s["epic"], 0) + 1

ws2["A5"] = "Répartition par module"
ws2["A5"].font = Font(name="Calibri", size=12, bold=True)
ws2["A6"] = "Module"
ws2["B6"] = "Nombre d'US"
ws2["A6"].font = Font(name="Calibri", size=11, bold=True)
ws2["B6"].font = Font(name="Calibri", size=11, bold=True)

for i, (epic, n) in enumerate(sorted(epics.items()), start=7):
    ws2.cell(row=i, column=1, value=epic)
    ws2.cell(row=i, column=2, value=n)

# Repartition par priorite
prios = {}
for s in STORIES:
    prios[s["prio"]] = prios.get(s["prio"], 0) + 1

start = 7 + len(epics) + 2
ws2.cell(row=start, column=1,
         value="Répartition par priorité").font = Font(name="Calibri", size=12, bold=True)
ws2.cell(row=start + 1, column=1, value="Priorité").font = Font(name="Calibri", size=11, bold=True)
ws2.cell(row=start + 1, column=2, value="Nombre").font = Font(name="Calibri", size=11, bold=True)
for i, (p, n) in enumerate(sorted(prios.items()), start=start + 2):
    ws2.cell(row=i, column=1, value=p)
    ws2.cell(row=i, column=2, value=n)

# Repartition par sprint (US + charge)
sprint_us = {"Sprint 1": 0, "Sprint 2": 0}
sprint_charge = {"Sprint 1": 0.0, "Sprint 2": 0.0}
for sid, plan in SPRINT_PLAN.items():
    sp, _, _, charge = plan
    if sp in sprint_us:
        sprint_us[sp] += 1
        sprint_charge[sp] += charge

start = start + 2 + len(prios) + 2
ws2.cell(row=start, column=1,
         value="Répartition par sprint").font = Font(name="Calibri", size=12, bold=True)
ws2.cell(row=start + 1, column=1, value="Sprint").font = Font(name="Calibri", size=11, bold=True)
ws2.cell(row=start + 1, column=2, value="Nombre d'US").font = Font(name="Calibri", size=11, bold=True)
ws2.cell(row=start + 1, column=3, value="Charge totale (J-H)").font = Font(name="Calibri", size=11, bold=True)
ws2.cell(row=start + 1, column=4, value="Période").font = Font(name="Calibri", size=11, bold=True)

periods = {
    "Sprint 1": "15/06/2026 → 26/06/2026 (10 j ouvrés)",
    "Sprint 2": "29/06/2026 → 10/07/2026 (10 j ouvrés)",
}
for i, sp in enumerate(["Sprint 1", "Sprint 2"], start=start + 2):
    ws2.cell(row=i, column=1, value=sp)
    ws2.cell(row=i, column=2, value=sprint_us[sp])
    ws2.cell(row=i, column=3, value=round(sprint_charge[sp], 1))
    ws2.cell(row=i, column=4, value=periods[sp])

# Ligne total
total_row = start + 4
ws2.cell(row=total_row, column=1, value="TOTAL").font = Font(name="Calibri", size=11, bold=True)
ws2.cell(row=total_row, column=2, value=sum(sprint_us.values())).font = Font(name="Calibri", size=11, bold=True)
ws2.cell(row=total_row, column=3,
         value=round(sum(sprint_charge.values()), 1)).font = Font(name="Calibri", size=11, bold=True)
ws2.cell(row=total_row, column=4,
         value="15/06/2026 → 10/07/2026 (20 j ouvrés)").font = Font(name="Calibri", size=11, bold=True)

ws2.column_dimensions["A"].width = 40
ws2.column_dimensions["B"].width = 18
ws2.column_dimensions["C"].width = 22
ws2.column_dimensions["D"].width = 42

wb.save(OUT)
print(f"OK  {len(STORIES)} user stories ecrites dans {OUT}")
print(f"    Sprint 1 : {sprint_us['Sprint 1']} US / {sprint_charge['Sprint 1']:.1f} j-h")
print(f"    Sprint 2 : {sprint_us['Sprint 2']} US / {sprint_charge['Sprint 2']:.1f} j-h")
